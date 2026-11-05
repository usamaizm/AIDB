"""Import ID validation (E1 cases N1a/N1b, issue #29 comment 6648458298).

import_home must reject rows whose `id` is not a non-empty string for the
tables whose `id` is a semantic TEXT primary key (home_resources, notes):
SQLite TEXT affinity silently coerces an integer id, and a TEXT primary key
without an explicit NOT NULL silently stores a NULL id. Rejection happens
during whole-payload validation, before any insert, so a rejected payload
imports nothing. Tables whose `id` is an integer rowid surrogate
(relations, changes, snapshots, artifacts) legitimately export integer
ids and must not be rejected.
"""

import json

import pytest

from aidb import AIDB


def _table_counts(db):
    return {table: len(rows) for table, rows in db.export_home()["tables"].items()}


def _payload_with_bad_resource_id(bad_id):
    source = AIDB(":memory:")
    source.create_resource("document", {"body": "payload"})
    payload = source.export_home()
    assert payload["tables"]["home_resources"]
    payload["tables"]["home_resources"][0]["id"] = bad_id
    return payload


def test_integer_resource_id_rejected_and_nothing_imported():
    target = AIDB(":memory:")
    before = _table_counts(target)
    with pytest.raises(ValueError, match="invalid id in home import row for table: home_resources"):
        target.import_home(_payload_with_bad_resource_id(123))
    assert _table_counts(target) == before


def test_null_resource_id_rejected_and_nothing_imported():
    target = AIDB(":memory:")
    before = _table_counts(target)
    with pytest.raises(ValueError, match="invalid id in home import row for table: home_resources"):
        target.import_home(_payload_with_bad_resource_id(None))
    assert _table_counts(target) == before


def test_empty_string_resource_id_rejected():
    target = AIDB(":memory:")
    with pytest.raises(ValueError, match="invalid id in home import row for table: home_resources"):
        target.import_home(_payload_with_bad_resource_id(""))


def test_missing_resource_id_rejected():
    payload = _payload_with_bad_resource_id("res:placeholder")
    del payload["tables"]["home_resources"][0]["id"]
    with pytest.raises(ValueError, match="invalid id in home import row for table: home_resources"):
        AIDB(":memory:").import_home(payload)


def test_integer_note_id_rejected_and_nothing_imported():
    source = AIDB(":memory:")
    source.create_note("title", "body")
    payload = source.export_home()
    assert payload["tables"]["notes"]
    payload["tables"]["notes"][0]["id"] = 7

    target = AIDB(":memory:")
    before = _table_counts(target)
    with pytest.raises(ValueError, match="invalid id in home import row for table: notes"):
        target.import_home(payload)
    assert _table_counts(target) == before


def test_valid_export_json_round_trip_imports_and_reimports():
    source = AIDB(":memory:")
    first = source.create_resource("document", {"body": "one"})
    second = source.create_resource("document", {"body": "two"})
    source.relate_resources(first.id, second.id, "supports")
    source.create_note("a note", "note body")

    wire = json.loads(json.dumps(source.export_home()))

    target = AIDB(":memory:")
    target.import_home(wire)
    assert target.get_resource(first.id).id == first.id
    assert target.get_resource(second.id).id == second.id

    # Idempotent identical re-import still succeeds.
    target.import_home(json.loads(json.dumps(source.export_home())))
    assert target.get_resource(first.id).id == first.id


def test_artifact_bearing_export_imports_in_process(tmp_path):
    # Artifact rows carry integer rowid ids; they must not be rejected.
    # (The serialized JSON path for artifact exports is a separate known
    # defect, so this case deliberately stays on the in-process dict path.)
    source = AIDB(tmp_path / "source.sqlite3")
    artifact = source.register_artifact_from_bytes(
        name="binary.dat", data=b"artifact bytes", media_type="application/octet-stream"
    )
    exported = source.export_home()
    assert exported["tables"]["artifacts"]

    restored = AIDB(tmp_path / "restored.sqlite3")
    restored.import_home(exported)
    assert restored.get_artifact_bytes(artifact.id) == b"artifact bytes"
