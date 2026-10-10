import pytest

from aidb import AIDB


def test_invalid_home_import_rolls_back_all_changes():
    db = AIDB(":memory:")
    note = db.create_note("existing", "keep")
    payload = db.export_home()
    payload["tables"]["home_resources"].append({
        "id": "bad",
        "resource_type": "note",
        "content": "{}",
        "unknown_column": True,
    })

    with pytest.raises(ValueError):
        db.import_home(payload)

    assert db.get_note(note.id).content == "keep"
    with pytest.raises(ValueError):
        db.get_resource("bad")
