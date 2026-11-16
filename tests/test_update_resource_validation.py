"""update_resource() rejects invalid inputs at the boundary.

On main before this fix, the update path passed its arguments straight to
json.dumps/SQLite: NaN/Infinity content and metadata were stored as
non-strict-JSON literals that round-trip, tuples were silently coerced to
lists, non-dict metadata was stored, and note updates accepted mistyped
titles, contents, and kinds (ints silently coerced to strings by SQLite)
while a list scalar update failed only as a raw sqlite3.ProgrammingError
and a NaN note body only as a raw sqlite3.IntegrityError. None content /
metadata still mean "keep existing" and are not validated.
"""

import pytest

from aidb import AIDB


def _fresh():
    db = AIDB(":memory:")
    db.initialize_home(owner="agent:one")
    return db


def _resource(db):
    return db.create_resource("document", {"text": "v1"}, owner="agent:one")


def _note(db):
    return db.create_note("title", "body", owner="agent:one", kind="note")


def _counts(db):
    resources = db.db.execute("SELECT COUNT(*) FROM home_resources").fetchone()[0]
    notes = db.db.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    changes = db.db.execute("SELECT COUNT(*) FROM home_changes").fetchone()[0]
    return resources, notes, changes


# --- update_resource: content (non-note resource) ---


def test_update_resource_rejects_nan_content():
    db = _fresh()
    resource = _resource(db)
    with pytest.raises(ValueError, match="must contain only finite numbers"):
        db.update_resource(resource.id, content=float("nan"))


def test_update_resource_rejects_infinite_content():
    db = _fresh()
    resource = _resource(db)
    with pytest.raises(ValueError, match="must contain only finite numbers"):
        db.update_resource(resource.id, content=float("inf"))


def test_update_resource_rejects_nested_nan_content():
    db = _fresh()
    resource = _resource(db)
    with pytest.raises(ValueError, match="must contain only finite numbers"):
        db.update_resource(resource.id, content={"a": [1, float("nan")]})


def test_update_resource_rejects_tuple_content():
    db = _fresh()
    resource = _resource(db)
    # json.dumps would silently coerce the tuple to a list.
    with pytest.raises(ValueError, match="must be a JSON value"):
        db.update_resource(resource.id, content=(1, 2))
    with pytest.raises(ValueError, match="must be a JSON value"):
        db.update_resource(resource.id, content={"v": (1, 2)})


def test_update_resource_rejects_bytes_content():
    db = _fresh()
    resource = _resource(db)
    with pytest.raises(ValueError, match="must be a JSON value"):
        db.update_resource(resource.id, content=b"raw")


def test_update_resource_rejects_set_content():
    db = _fresh()
    resource = _resource(db)
    with pytest.raises(ValueError, match="must be a JSON value"):
        db.update_resource(resource.id, content={1, 2})


# --- update_resource: metadata ---


def test_update_resource_rejects_non_dict_metadata():
    db = _fresh()
    resource = _resource(db)
    with pytest.raises(ValueError, match="metadata must be a JSON object"):
        db.update_resource(resource.id, metadata=["a"])
    with pytest.raises(ValueError, match="metadata must be a JSON object"):
        db.update_resource(resource.id, metadata="x")


def test_update_resource_rejects_nan_metadata():
    db = _fresh()
    resource = _resource(db)
    with pytest.raises(ValueError, match="must contain only finite numbers"):
        db.update_resource(resource.id, metadata={"v": float("nan")})


def test_update_resource_rejects_non_string_metadata_key():
    db = _fresh()
    resource = _resource(db)
    with pytest.raises(ValueError, match="keys must be non-empty strings"):
        db.update_resource(resource.id, metadata={1: "x"})


def test_update_resource_rejects_empty_metadata_key():
    db = _fresh()
    resource = _resource(db)
    with pytest.raises(ValueError, match="keys must be non-empty strings"):
        db.update_resource(resource.id, metadata={"": "x"})


def test_update_resource_rejects_tuple_metadata_value():
    db = _fresh()
    resource = _resource(db)
    with pytest.raises(ValueError, match="must be a JSON value"):
        db.update_resource(resource.id, metadata={"v": (1, 2)})


# --- update_resource: note dict content ---


def test_update_resource_rejects_non_string_note_title():
    db = _fresh()
    note = _note(db)
    with pytest.raises(ValueError, match="note title must be a non-empty string"):
        db.update_resource(note.id, content={"title": 42, "content": "x"})


def test_update_resource_rejects_empty_note_title():
    db = _fresh()
    note = _note(db)
    with pytest.raises(ValueError, match="note title must be a non-empty string"):
        db.update_resource(note.id, content={"title": "", "content": "x"})
    with pytest.raises(ValueError, match="note title must be a non-empty string"):
        db.update_resource(note.id, content={"title": "   ", "content": "x"})


def test_update_resource_rejects_non_string_note_content():
    db = _fresh()
    note = _note(db)
    with pytest.raises(ValueError, match="note content must be a string"):
        db.update_resource(note.id, content={"title": "t", "content": 5})


def test_update_resource_rejects_nan_note_content_with_value_error():
    db = _fresh()
    note = _note(db)
    # Was a raw sqlite3.IntegrityError from the NOT NULL constraint.
    with pytest.raises(ValueError, match="must contain only finite numbers"):
        db.update_resource(note.id, content={"title": "t", "content": float("nan")})


def test_update_resource_rejects_empty_note_kind():
    db = _fresh()
    note = _note(db)
    with pytest.raises(ValueError, match="note kind must be a non-empty string"):
        db.update_resource(note.id, content={"title": "t", "content": "x", "kind": ""})


def test_update_resource_rejects_non_string_note_kind():
    db = _fresh()
    note = _note(db)
    with pytest.raises(ValueError, match="note kind must be a non-empty string"):
        db.update_resource(note.id, content={"title": "t", "content": "x", "kind": 3})


def test_update_resource_rejects_note_content_missing_keys():
    db = _fresh()
    note = _note(db)
    with pytest.raises(ValueError, match="note resource content must include title and content"):
        db.update_resource(note.id, content={"content": "x"})
    with pytest.raises(ValueError, match="note resource content must include title and content"):
        db.update_resource(note.id, content={"title": "t"})


# --- update_resource: note scalar content (legacy shorthand) ---


def test_update_resource_rejects_non_string_scalar_note_content():
    db = _fresh()
    note = _note(db)
    with pytest.raises(ValueError, match="note content must be a string"):
        db.update_resource(note.id, content=5)
    with pytest.raises(ValueError, match="note content must be a string"):
        db.update_resource(note.id, content=True)
    with pytest.raises(ValueError, match="note content must be a string"):
        db.update_resource(note.id, content=1.5)


def test_update_resource_rejects_list_scalar_note_content_with_value_error():
    db = _fresh()
    note = _note(db)
    # Was a raw sqlite3.ProgrammingError from parameter binding.
    with pytest.raises(ValueError, match="note content must be a string"):
        db.update_resource(note.id, content=["a"])


# --- update_resource: valid behaviour ---


def test_update_resource_valid_inputs_round_trip():
    db = _fresh()
    resource = _resource(db)
    updated = db.update_resource(
        resource.id,
        content={"a": [1, 2.5, "x", True, None]},
        metadata={"k": "v"},
        expected_revision=1,
    )
    assert updated.content == {"a": [1, 2.5, "x", True, None]}
    assert updated.metadata == {"k": "v"}
    assert updated.revision == 2
    assert db.get_resource(resource.id).content == updated.content


def test_update_resource_none_content_and_metadata_keep_existing():
    db = _fresh()
    resource = _resource(db)
    updated = db.update_resource(resource.id, metadata={"k": "v"})
    assert updated.content == {"text": "v1"}
    assert updated.metadata == {"k": "v"}
    kept = db.update_resource(resource.id, content={"text": "v2"})
    assert kept.content == {"text": "v2"}
    assert kept.metadata == {"k": "v"}


def test_update_resource_note_dict_update_round_trip_and_kind_kept():
    db = _fresh()
    note = _note(db)
    updated = db.update_resource(
        note.id,
        content={"title": "new title", "content": "after", "kind": "observation"},
        metadata={"source": "updated"},
        expected_revision=1,
    )
    current = db.get_note(note.id)
    assert updated.content == {
        "title": "new title",
        "content": "after",
        "kind": "observation",
    }
    assert current.title == "new title"
    assert current.content == "after"
    assert current.kind == "observation"
    assert current.metadata == {"source": "updated"}
    # A dict update without kind keeps the existing kind.
    db.update_resource(note.id, content={"title": "t2", "content": "x2"})
    assert db.get_note(note.id).kind == "observation"


def test_update_resource_note_scalar_update_preserves_title_and_kind():
    db = _fresh()
    note = db.create_note("title", "before", kind="question")
    db.update_resource(note.id, content="after")
    current = db.get_note(note.id)
    assert current.title == "title"
    assert current.content == "after"
    assert current.kind == "question"


# --- update_resource: validation order and atomicity ---


def test_update_resource_revision_conflict_checked_before_content():
    db = _fresh()
    resource = _resource(db)
    db.update_resource(resource.id, content={"text": "v2"})
    with pytest.raises(ValueError, match="revision conflict"):
        db.update_resource(resource.id, content=float("nan"), expected_revision=1)


def test_update_resource_missing_resource_checked_before_content():
    db = _fresh()
    with pytest.raises(ValueError, match="resource does not exist"):
        db.update_resource("res:missing", content=float("nan"))


def test_update_resource_rejection_writes_nothing():
    db = _fresh()
    resource = _resource(db)
    note = _note(db)
    before = _counts(db)
    revision = db.get_resource(resource.id).revision
    note_revision = db.get_resource(note.id).revision
    with pytest.raises(ValueError):
        db.update_resource(resource.id, content=float("nan"))
    with pytest.raises(ValueError):
        db.update_resource(resource.id, metadata={"v": (1, 2)})
    with pytest.raises(ValueError):
        db.update_resource(note.id, content={"title": 42, "content": "x"})
    with pytest.raises(ValueError):
        db.update_resource(note.id, content=5)
    assert _counts(db) == before
    assert db.get_resource(resource.id).revision == revision
    assert db.get_resource(note.id).revision == note_revision
    assert db.get_resource(resource.id).content == {"text": "v1"}
    assert db.get_note(note.id).content == "body"
