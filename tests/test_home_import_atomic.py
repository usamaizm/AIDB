import base64
import hashlib
import json
import sqlite3

import pytest

from aidb import AIDB


def test_invalid_home_import_rejects_unknown_columns_without_changes():
    db = AIDB(":memory:")
    note = db.create_note("existing", "keep")
    payload = db.export_home()
    payload["tables"]["home_resources"].append(
        {
            "id": "unexpected",
            "resource_type": "note",
            "content": "{}",
            "unknown_column": True,
        }
    )

    with pytest.raises(ValueError, match="invalid column"):
        db.import_home(payload)

    assert db.get_note(note.id).content == "keep"
    with pytest.raises(ValueError, match="resource does not exist"):
        db.get_resource("unexpected")


def test_home_import_rolls_back_when_foreign_key_validation_fails():
    db = AIDB(":memory:")
    payload = db.export_home()
    payload["tables"]["home_resources"].append(
        {
            "id": "must-rollback",
            "resource_type": "note",
            "content": "{}",
            "owner": None,
            "visibility": "private",
            "metadata": "{}",
            "revision": 1,
        }
    )
    payload["tables"]["resource_relations"].append(
        {
            "source_resource_id": "must-rollback",
            "target_resource_id": "missing-resource",
            "relation": "supports",
            "metadata": "{}",
        }
    )

    with pytest.raises(sqlite3.IntegrityError):
        db.import_home(payload)

    with pytest.raises(ValueError, match="resource does not exist"):
        db.get_resource("must-rollback")

def test_artifact_bytes_are_stored_and_survive_home_export_import(tmp_path):
    source = AIDB(tmp_path / "source.sqlite3")
    payload = b"original artifact bytes\x00\x01"
    artifact = source.register_artifact_from_bytes(
        name="binary.dat", data=payload, media_type="application/octet-stream"
    )
    assert source.get_artifact_bytes(artifact.id) == payload

    exported = source.export_home()
    assert exported["tables"]["artifacts"]
    assert exported["tables"]["artifact_blobs"]

    restored = AIDB(tmp_path / "restored.sqlite3")
    restored.import_home(exported)
    assert restored.get_artifact_bytes(artifact.id) == payload


def test_import_rejects_conflicting_existing_rows():
    db = AIDB(":memory:")
    note = db.create_note("original", "content")
    payload = db.export_home()
    payload["tables"]["home_resources"][0]["content"] = '{"title":"tampered","content":"changed"}'
    with pytest.raises(ValueError, match="conflicting existing row"):
        db.import_home(payload)
    assert db.get_note(note.id).title == "original"
    assert db.get_note(note.id).content == "content"

def test_artifact_payload_reads_verify_checksum(tmp_path):
    db = AIDB(tmp_path / "artifact-integrity.sqlite3")
    artifact = db.register_artifact_from_bytes(
        name="verified.bin", data=b"trusted", media_type="application/octet-stream"
    )
    db.db.execute(
        "UPDATE artifact_blobs SET content=? WHERE artifact_id=?",
        (b"tamper!", artifact.id),
    )
    db.db.commit()
    with pytest.raises(ValueError, match="checksum verification failed"):
        db.get_artifact_bytes(artifact.id)


def test_home_export_with_artifact_is_json_serializable(tmp_path):
    db = AIDB(tmp_path / "export-json.sqlite3")
    db.register_artifact_from_bytes(
        name="binary.dat", data=b"payload\\x00\\xff", media_type="application/octet-stream"
    )
    exported = db.export_home()
    blob_row = exported["tables"]["artifact_blobs"][0]
    assert blob_row["content_encoding"] == "base64"
    assert isinstance(blob_row["content"], str)
    json.dumps(exported)


def test_artifact_survives_json_export_import_round_trip(tmp_path):
    source = AIDB(tmp_path / "source.sqlite3")
    payload = b"original artifact bytes\\x00\\x01"
    artifact = source.register_artifact_from_bytes(
        name="binary.dat", data=payload, media_type="application/octet-stream"
    )
    restored = AIDB(tmp_path / "restored.sqlite3")
    restored.import_home(json.loads(json.dumps(source.export_home())))
    assert restored.get_artifact_bytes(artifact.id) == payload


def test_snapshot_round_trip_with_artifact(tmp_path):
    db = AIDB(tmp_path / "snapshot.sqlite3")
    payload = b"snapshot me"
    artifact = db.register_artifact_from_bytes(
        name="snap.bin", data=payload, media_type="application/octet-stream"
    )
    snapshot = db.create_snapshot()
    db.restore_snapshot(snapshot["snapshot_id"])
    assert db.get_artifact_bytes(artifact.id) == payload


def test_import_rejects_tampered_base64_artifact_payload(tmp_path):
    source = AIDB(tmp_path / "source.sqlite3")
    payload = b"trusted bytes"
    artifact = source.register_artifact_from_bytes(
        name="verified.bin", data=payload, media_type="application/octet-stream"
    )
    exported = json.loads(json.dumps(source.export_home()))
    blob_row = exported["tables"]["artifact_blobs"][0]
    tampered = bytes(byte ^ 0xFF for byte in payload)
    blob_row["content"] = base64.b64encode(tampered).decode("ascii")
    restored = AIDB(tmp_path / "restored.sqlite3")
    with pytest.raises(ValueError, match="checksum verification failed"):
        restored.import_home(exported)
    assert restored.list_artifacts() == []
    assert restored.get_artifact_bytes(artifact.id) is None


def test_public_export_still_excludes_artifact_blobs(tmp_path):
    db = AIDB(tmp_path / "public.sqlite3")
    db.register_artifact_from_bytes(
        name="binary.dat", data=b"payload", media_type="application/octet-stream"
    )
    exported = db.export_home(include_private=False)
    assert exported["tables"]["artifacts"] == []
    assert exported["tables"]["artifact_blobs"] == []
    json.dumps(exported)


def test_import_rejects_unknown_top_level_fields():
    db = AIDB(":memory:")
    payload = {"format": "aidb-home-v1", "tables": {}, "extensions": []}
    with pytest.raises(ValueError, match="unknown home import field"):
        db.import_home(payload)
    assert db.list_resources() == []


def test_import_rejects_unsupported_required_extensions():
    db = AIDB(":memory:")
    payload = {
        "format": "aidb-home-v1",
        "tables": {},
        "required_extensions": ["aidb/ext-x"],
    }
    with pytest.raises(ValueError, match="unsupported required home extension"):
        db.import_home(payload)
    assert db.list_resources() == []


@pytest.mark.parametrize("resource_id", [123, None, ""])
def test_import_rejects_invalid_resource_ids(resource_id):
    db = AIDB(":memory:")
    payload = {
        "format": "aidb-home-v1",
        "tables": {
            "home_resources": [{
                "id": resource_id,
                "resource_type": "document",
                "content": "{}",
                "owner": None,
                "visibility": "private",
                "metadata": "{}",
                "revision": 1,
            }]
        },
    }
    with pytest.raises(ValueError, match="invalid id"):
        db.import_home(payload)
    assert db.list_resources() == []


def test_import_rejects_dangling_home_change_reference_atomically():
    db = AIDB(":memory:")
    payload = {
        "format": "aidb-home-v1",
        "tables": {
            "home_resources": [{
                "id": "incoming-resource",
                "resource_type": "document",
                "content": "{}",
                "owner": None,
                "visibility": "public",
                "metadata": "{}",
                "revision": 1,
            }],
            "home_changes": [{
                "change_id": "change:missing-target",
                "resource_id": "not-in-payload",
                "operation": "update",
                "actor": None,
                "previous_revision": 1,
                "new_revision": 2,
                "payload": "{}",
            }],
        },
    }
    with pytest.raises(ValueError, match="home change references a missing resource"):
        db.import_home(payload)
    assert db.list_resources() == []


def test_import_rejects_tampered_snapshot_before_writing():
    db = AIDB(":memory:")
    content = json.dumps({"format": "aidb-home-v1", "tables": {}})
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    payload = {
        "format": "aidb-home-v1",
        "tables": {
            "home_snapshots": [{
                "snapshot_id": "snap:" + digest,
                "home_format": "aidb-home-v1",
                "content": content + "tampered",
                "content_hash": digest,
            }]
        },
    }
    with pytest.raises(ValueError, match="snapshot integrity check failed"):
        db.import_home(payload)
    assert db.db.execute("SELECT COUNT(*) FROM home_snapshots").fetchone()[0] == 0


def test_import_rejects_programmatic_non_finite_numbers():
    db = AIDB(":memory:")
    payload = {
        "format": "aidb-home-v1",
        "tables": {
            "home_changes": [{
                "change_id": "change:nan",
                "resource_id": None,
                "operation": "system",
                "previous_revision": float("nan"),
                "new_revision": 1,
                "payload": "{}",
            }]
        },
    }
    with pytest.raises(ValueError, match="non-finite number"):
        db.import_home(payload)
    assert db.db.execute("SELECT COUNT(*) FROM home_changes").fetchone()[0] == 0


def test_import_home_json_rejects_duplicate_object_keys():
    db = AIDB(":memory:")
    raw = '{"format":"aidb-home-v1","format":"aidb-home-v2","tables":{}}'
    with pytest.raises(ValueError, match="duplicate JSON object key"):
        db.import_home_json(raw)
    assert db.list_resources() == []


def test_import_home_json_rejects_non_standard_numeric_constants():
    db = AIDB(":memory:")
    raw = '{"format":"aidb-home-v1","tables":{},"value":NaN}'
    with pytest.raises(ValueError, match="non-standard JSON numeric constant"):
        db.import_home_json(raw)
    assert db.list_resources() == []
