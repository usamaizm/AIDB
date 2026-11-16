"""create_resource()/create_note() reject invalid inputs at the boundary.

On main before this fix, both write paths passed their arguments straight to
json.dumps/SQLite: empty and mistyped resource_type/title/kind were stored
(and ints silently coerced to strings by SQLite), NaN/Infinity content and
metadata were stored as non-strict-JSON literals that round-trip, tuples were
silently coerced to lists, non-dict metadata was stored, and None
resource_type/title/content failed only as a raw sqlite3.IntegrityError.
"""

import pytest

from aidb import AIDB


def _fresh():
    db = AIDB(":memory:")
    db.initialize_home(owner="agent:one")
    return db


def _counts(db):
    resources = db.db.execute("SELECT COUNT(*) FROM home_resources").fetchone()[0]
    notes = db.db.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    changes = db.db.execute("SELECT COUNT(*) FROM home_changes").fetchone()[0]
    return resources, notes, changes


# --- create_resource: resource_type ---


def test_create_resource_rejects_empty_resource_type():
    db = _fresh()
    with pytest.raises(ValueError, match="resource_type must be a non-empty string"):
        db.create_resource("")


def test_create_resource_rejects_whitespace_resource_type():
    db = _fresh()
    with pytest.raises(ValueError, match="resource_type must be a non-empty string"):
        db.create_resource("   ")


def test_create_resource_rejects_non_string_resource_type():
    db = _fresh()
    with pytest.raises(ValueError, match="resource_type must be a non-empty string"):
        db.create_resource(42)


def test_create_resource_rejects_none_resource_type_with_value_error():
    db = _fresh()
    # Was a raw sqlite3.IntegrityError from the NOT NULL constraint.
    with pytest.raises(ValueError, match="resource_type must be a non-empty string"):
        db.create_resource(None)


# --- create_resource: content ---


def test_create_resource_rejects_nan_content():
    db = _fresh()
    with pytest.raises(ValueError, match="must contain only finite numbers"):
        db.create_resource("note", content=float("nan"))


def test_create_resource_rejects_infinite_content():
    db = _fresh()
    with pytest.raises(ValueError, match="must contain only finite numbers"):
        db.create_resource("note", content=float("inf"))


def test_create_resource_rejects_nested_nan_content():
    db = _fresh()
    with pytest.raises(ValueError, match="must contain only finite numbers"):
        db.create_resource("note", content={"v": float("nan")})


def test_create_resource_rejects_tuple_content_value():
    db = _fresh()
    # json.dumps would silently coerce the tuple to a list.
    with pytest.raises(ValueError, match="must be a JSON value"):
        db.create_resource("note", content={"v": (1, 2)})


def test_create_resource_rejects_bytes_content():
    db = _fresh()
    with pytest.raises(ValueError, match="must be a JSON value"):
        db.create_resource("note", content=b"raw")


# --- create_resource: metadata and owner ---


def test_create_resource_rejects_non_dict_metadata():
    db = _fresh()
    with pytest.raises(ValueError, match="metadata must be a JSON object"):
        db.create_resource("note", metadata=["a"])
    with pytest.raises(ValueError, match="metadata must be a JSON object"):
        db.create_resource("note", metadata="x")


def test_create_resource_rejects_nan_metadata():
    db = _fresh()
    with pytest.raises(ValueError, match="must contain only finite numbers"):
        db.create_resource("note", metadata={"v": float("nan")})


def test_create_resource_rejects_non_string_metadata_key():
    db = _fresh()
    with pytest.raises(ValueError, match="keys must be non-empty strings"):
        db.create_resource("note", metadata={1: "x"})


def test_create_resource_rejects_empty_metadata_key():
    db = _fresh()
    with pytest.raises(ValueError, match="keys must be non-empty strings"):
        db.create_resource("note", metadata={"": "x"})


def test_create_resource_rejects_non_string_owner():
    db = _fresh()
    with pytest.raises(ValueError, match="owner must be a string"):
        db.create_resource("note", owner=7)


def test_create_resource_valid_inputs_round_trip():
    db = _fresh()
    resource = db.create_resource(
        "note", content={"a": [1, 2.5, "x", True, None]}, metadata={"k": "v"}
    )
    back = db.get_resource(resource.id)
    assert back.resource_type == "note"
    assert back.content == {"a": [1, 2.5, "x", True, None]}
    assert back.metadata == {"k": "v"}


def test_create_resource_none_content_and_metadata_accepted():
    db = _fresh()
    resource = db.create_resource("note")
    assert resource.content is None
    assert resource.metadata == {}


def test_create_resource_rejection_writes_nothing():
    db = _fresh()
    before = _counts(db)
    with pytest.raises(ValueError):
        db.create_resource("", content=float("nan"), metadata=["a"])
    assert _counts(db) == before


# --- create_note ---


def test_create_note_rejects_empty_title():
    db = _fresh()
    with pytest.raises(ValueError, match="title must be a non-empty string"):
        db.create_note("", "body")


def test_create_note_rejects_none_title_with_value_error():
    db = _fresh()
    # Was a raw sqlite3.IntegrityError from the NOT NULL constraint.
    with pytest.raises(ValueError, match="title must be a non-empty string"):
        db.create_note(None, "body")


def test_create_note_rejects_non_string_content():
    db = _fresh()
    # SQLite would silently coerce 5 to the string "5".
    with pytest.raises(ValueError, match="content must be a string"):
        db.create_note("t", 5)


def test_create_note_rejects_none_content_with_value_error():
    db = _fresh()
    # Was a raw sqlite3.IntegrityError from the NOT NULL constraint.
    with pytest.raises(ValueError, match="content must be a string"):
        db.create_note("t", None)


def test_create_note_rejects_empty_kind():
    db = _fresh()
    with pytest.raises(ValueError, match="kind must be a non-empty string"):
        db.create_note("t", "b", kind="")


def test_create_note_rejects_non_string_kind():
    db = _fresh()
    with pytest.raises(ValueError, match="kind must be a non-empty string"):
        db.create_note("t", "b", kind=3)


def test_create_note_rejects_invalid_metadata():
    db = _fresh()
    with pytest.raises(ValueError, match="metadata must be a JSON object"):
        db.create_note("t", "b", metadata=["a"])
    with pytest.raises(ValueError, match="must contain only finite numbers"):
        db.create_note("t", "b", metadata={"v": float("nan")})


def test_create_note_rejects_non_string_owner():
    db = _fresh()
    with pytest.raises(ValueError, match="owner must be a string"):
        db.create_note("t", "b", owner=7)


def test_create_note_valid_inputs_round_trip():
    db = _fresh()
    note = db.create_note("t", "b", kind="question", metadata={"source": "test"})
    back = db.get_note(note.id)
    assert back.title == "t"
    assert back.content == "b"
    assert back.kind == "question"
    assert back.metadata == {"source": "test"}


def test_create_note_rejection_writes_nothing():
    db = _fresh()
    before = _counts(db)
    with pytest.raises(ValueError):
        db.create_note("", 5, kind="", metadata=["a"])
    assert _counts(db) == before
