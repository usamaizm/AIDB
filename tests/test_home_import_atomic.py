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
