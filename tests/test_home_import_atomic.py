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
