"""Streaming support (Q32): bounded export/import, the NDJSON change
feed, and bounded artifact-blob iteration.

The streaming APIs must be behavior-identical to the buffered ones —
same export content, same import validation and atomicity, same public
change events — while never materializing a whole home, a whole feed,
or a whole blob in memory.
"""

import io
import json
from collections.abc import Iterator
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from threading import Thread

import pytest

from aidb import AIDB
from aidb.server import create_handler

BLOB_DATA = bytes(range(256)) * 800  # 204,800 bytes: several 64KiB slices.


def populated_home():
    db = AIDB(":memory:")
    db.initialize_home(node_id="node:stream", owner="agent:stream")
    db.register_agent("streamer", description="streaming test agent")
    public = db.create_resource("document", {"text": "public body"}, visibility="public")
    private = db.create_resource("secret", {"text": "private body"})
    db.create_note("public note", "café ☕ public", visibility="public")
    db.create_note("private note", "hidden")
    db.relate_resources(public.id, private.id, "references")
    other = db.create_resource("document", {"text": "second public"}, visibility="public")
    db.relate_resources(public.id, other.id, "supports")
    db.update_resource(public.id, content="public body v2")
    db.publish_resource(private.id)
    db.update_resource(private.id, content="now public")
    db.register_artifact_from_bytes("blob.bin", BLOB_DATA, "application/octet-stream")
    # Materialize the node's specification row, as any specification
    # read on a live home does.
    db.current_specification()
    return db


def normalized_export(db):
    """export_home() with the derived specification row's volatile
    fields masked: importing returns current_specification(), which
    mints a fresh specification_id and issued_at, so two homes holding
    the same imported content legitimately differ only there."""
    payload = db.export_home()
    for row in payload["tables"]["node_specifications"]:
        row["specification_id"] = "<derived>"
        row["issued_at"] = "<derived>"
    return payload


def collect_tables(batches):
    tables = {}
    for table, batch in batches:
        tables.setdefault(table, []).extend(batch)
    return tables


# ---------------------------------------------------------------------------
# Streaming export
# ---------------------------------------------------------------------------


def test_iter_export_home_matches_export_home_full():
    db = populated_home()
    batches = list(db.iter_export_home(batch_size=2))
    assert all(len(batch) <= 2 for _, batch in batches)
    # The populated home has more than two changes, so batching is real.
    assert sum(1 for table, _ in batches if table == "home_changes") > 1
    assert collect_tables(batches) == db.export_home()["tables"]


def test_iter_export_home_matches_export_home_public_only():
    db = populated_home()
    batches = list(db.iter_export_home(include_private=False, batch_size=3))
    tables = collect_tables(batches)
    assert tables == db.export_home(include_private=False)["tables"]
    rendered = json.dumps(tables)
    assert "private body" not in rendered
    assert "hidden" not in rendered
    assert tables["home_changes"] == []
    assert tables["agents"] == []


def test_iter_export_home_is_a_lazy_iterator():
    db = populated_home()
    stream = db.iter_export_home()
    assert isinstance(stream, Iterator)
    assert not isinstance(stream, (dict, list))
    # The first table is available without consuming the rest.
    table, batch = next(stream)
    assert table == "node_identity"
    assert batch


def test_export_home_json_to_round_trips_through_import():
    source = populated_home()
    buffer = io.StringIO()
    verification = source.export_home_json_to(buffer)
    text = buffer.getvalue()
    assert verification == source.export_home()["verification"]
    # The written envelope parses to exactly export_home's payload...
    assert json.loads(text) == source.export_home()
    # ...and the existing import path restores an equal home.
    restored = AIDB(":memory:")
    restored.import_home_json(text)
    assert normalized_export(restored) == normalized_export(source)


def test_export_home_json_to_accepts_binary_files_and_writes_incrementally():
    source = populated_home()
    writes = []

    class Recorder:
        def write(self, data):
            writes.append(data)
            return len(data)

    source.export_home_json_to(Recorder())
    full = "".join(chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk for chunk in writes)
    assert json.loads(full) == source.export_home()
    # Incremental writing: many writes, none of them the whole document.
    assert len(writes) > 10
    assert all(len(chunk) < len(full) for chunk in writes)

    binary = io.BytesIO()
    source.export_home_json_to(binary)
    assert json.loads(binary.getvalue().decode("utf-8")) == source.export_home()


def test_export_home_json_to_public_only_matches_filtered_export():
    source = populated_home()
    buffer = io.StringIO()
    source.export_home_json_to(buffer, include_private=False)
    payload = json.loads(buffer.getvalue())
    expected = source.export_home(include_private=False)
    assert payload["tables"] == expected["tables"]
    assert payload["verification"] == {
        "ok": None,
        "issues": [],
        "scope": "filtered_public_export",
    }


# ---------------------------------------------------------------------------
# Streaming import
# ---------------------------------------------------------------------------


def chunked(text, size):
    return (text[index : index + size] for index in range(0, len(text), size))


def test_import_home_stream_matches_import_home_in_odd_chunks():
    source = populated_home()
    text = json.dumps(source.export_home())
    streamed = AIDB(":memory:")
    streamed.import_home_stream(chunked(text, 7))
    buffered = AIDB(":memory:")
    buffered.import_home_json(text)
    assert normalized_export(streamed) == normalized_export(buffered) == normalized_export(source)


def test_import_home_stream_handles_split_multibyte_characters():
    source = populated_home()
    raw = json.dumps(source.export_home(), ensure_ascii=False).encode("utf-8")
    assert "☕".encode("utf-8") in raw  # the fixture really has multibyte text
    target = AIDB(":memory:")
    target.import_home_stream((raw[index : index + 1] for index in range(len(raw))))
    assert normalized_export(target) == normalized_export(source)


def test_import_home_stream_invalid_late_row_persists_nothing():
    source = populated_home()
    payload = source.export_home()
    # agents is the last table in the envelope: everything before this
    # row has already been consumed and inserted when it fails.
    payload["tables"]["agents"].append({"id": -5, "name": "bad-agent"})
    target = AIDB(":memory:")
    with pytest.raises(ValueError):
        target.import_home_stream(chunked(json.dumps(payload), 64))
    assert all(rows == [] for rows in target.export_home()["tables"].values())


def test_import_home_stream_malformed_document_persists_nothing():
    source = populated_home()
    text = json.dumps(source.export_home())
    truncated = text[: int(len(text) * 0.6)]
    target = AIDB(":memory:")
    with pytest.raises(ValueError):
        target.import_home_stream(chunked(truncated, 64))
    assert all(rows == [] for rows in target.export_home()["tables"].values())

    broken = text.replace('"format": "aidb-home-v1"', '"format" "aidb-home-v1"', 1)
    assert broken != text
    target = AIDB(":memory:")
    with pytest.raises(ValueError):
        target.import_home_stream(chunked(broken, 64))
    assert all(rows == [] for rows in target.export_home()["tables"].values())


def test_import_home_stream_rejects_duplicate_keys_like_buffered_import():
    source = populated_home()
    text = json.dumps(source.export_home())
    duplicated = text[:-1] + ', "format": "aidb-home-v1"}'
    target = AIDB(":memory:")
    with pytest.raises(ValueError, match="duplicate"):
        target.import_home_stream(chunked(duplicated, 64))
    assert all(rows == [] for rows in target.export_home()["tables"].values())


def test_import_home_stream_rejects_dangling_reference_and_rolls_back():
    source = populated_home()
    payload = source.export_home()
    payload["tables"]["notes"].append(
        {
            "id": "res:missing",
            "resource_id": "res:missing",
            "kind": "note",
            "title": "dangling",
            "content": "points nowhere",
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
    )
    target = AIDB(":memory:")
    with pytest.raises(ValueError, match="missing resource"):
        target.import_home_stream(chunked(json.dumps(payload), 64))
    assert all(rows == [] for rows in target.export_home()["tables"].values())


# ---------------------------------------------------------------------------
# Streaming change feed
# ---------------------------------------------------------------------------


def test_iter_public_changes_matches_public_changes():
    db = populated_home()
    expected = db.public_changes(after_id=0, limit=10000)
    assert len(expected) >= 4
    batches = list(db.iter_public_changes(batch_size=2))
    assert all(len(batch) <= 2 for batch in batches)
    flattened = [event for batch in batches for event in batch]
    assert flattened == expected
    # The cursor composes: resuming after the second event yields the rest.
    cursor = expected[1]["id"]
    resumed = [
        event for batch in db.iter_public_changes(after_id=cursor, batch_size=2) for event in batch
    ]
    assert resumed == db.public_changes(after_id=cursor, limit=10000)
    assert [event["id"] for event in resumed] == [event["id"] for event in expected[2:]]


def serve(db):
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(db, "test-token"))
    Thread(target=server.serve_forever, daemon=True).start()
    return server


def get_stream(port, path):
    connection = HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        body = response.read()
        headers = {key.lower(): value for key, value in response.getheaders()}
        return response.status, headers, body
    finally:
        connection.close()


def test_change_feed_streams_ndjson_and_resumes_without_overlap():
    db = populated_home()
    server = serve(db)
    try:
        port = server.server_port
        expected = db.public_changes(after_id=0, limit=10000)
        status, headers, body = get_stream(port, "/v1/changes?stream=1&limit=2")
        assert status == 200
        assert headers["transfer-encoding"] == "chunked"
        assert headers["content-type"].startswith("application/x-ndjson")
        first_page = [json.loads(line) for line in body.decode("utf-8").splitlines()]
        assert [event["id"] for event in first_page] == [event["id"] for event in expected[:2]]
        status, _, body = get_stream(
            port, f"/v1/changes?stream=true&after_id={first_page[-1]['id']}"
        )
        assert status == 200
        remainder = [json.loads(line) for line in body.decode("utf-8").splitlines()]
        assert remainder == expected[2:]
        streamed_ids = [event["id"] for event in first_page + remainder]
        assert streamed_ids == [event["id"] for event in expected]
        assert len(set(streamed_ids)) == len(streamed_ids)
    finally:
        server.shutdown()
        server.server_close()
        db.close()


def test_change_feed_events_equal_buffered_response():
    db = populated_home()
    server = serve(db)
    try:
        _, _, body = get_stream(server.server_port, "/v1/changes?stream=1")
        streamed = [json.loads(line) for line in body.decode("utf-8").splitlines()]
        assert streamed == db.public_changes(after_id=0, limit=100)
        assert all(event["actor"] is None for event in streamed)
    finally:
        server.shutdown()
        server.server_close()
        db.close()


# ---------------------------------------------------------------------------
# Artifact blob streaming
# ---------------------------------------------------------------------------


def test_iter_artifact_content_reassembles_bounded_chunks():
    db = AIDB(":memory:")
    db.initialize_home()
    artifact = db.register_artifact_from_bytes("blob.bin", BLOB_DATA, "application/octet-stream")
    chunks = list(db.iter_artifact_content(artifact.id, chunk_size=65536))
    assert len(chunks) == 4  # 204,800 bytes in 64KiB slices
    assert all(0 < len(chunk) <= 65536 for chunk in chunks)
    assert b"".join(chunks) == BLOB_DATA
    small = list(db.iter_artifact_content(artifact.id, chunk_size=100))
    assert all(len(chunk) <= 100 for chunk in small)
    assert b"".join(small) == BLOB_DATA
    assert b"".join(db.iter_artifact_content(artifact.id)) == BLOB_DATA


def test_iter_artifact_content_unknown_artifact_raises():
    db = AIDB(":memory:")
    db.initialize_home()
    with pytest.raises(ValueError, match="does not exist"):
        list(db.iter_artifact_content(999999))


def test_iter_artifact_content_metadata_only_artifact_is_empty():
    db = AIDB(":memory:")
    db.initialize_home()
    artifact = db.register_artifact("meta.bin", "application/octet-stream", 0, "0" * 64)
    assert list(db.iter_artifact_content(artifact.id)) == []
