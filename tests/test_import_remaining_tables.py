"""Import-path validation for the remaining home tables (Q21).

home_resources, notes, and resource_relations rows — plus the
node_identity / node_specifications JSON columns — were validated only
for column names, value types, and visibility by import_home(). The
JSON-text columns were never parsed, revisions could be zero or
negative, a note's id could differ from its resource_id, a relation
could point at itself or at a resource that does not exist, and a row
missing a NOT NULL column only failed later with a misleading
"conflicting existing row" or a raw sqlite IntegrityError.

Every malformed case below is rejected atomically: nothing from the
payload is stored.
"""

import copy
import json

import pytest

from aidb import AIDB


def _source_payload():
    source = AIDB(":memory:")
    first = source.create_note("one", "1", owner="agent:one", visibility="public")
    second = source.create_note("two", "2", owner="agent:one", visibility="public")
    source.relate_resources(first.id, second.id, "supports", metadata={"weight": 1})
    source.current_specification()
    return source.export_home()


def _table_counts(db):
    return {
        table: db.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ("home_resources", "notes", "resource_relations")
    }


def _assert_rejected(payload, match):
    db = AIDB(":memory:")
    with pytest.raises(ValueError, match=match):
        db.import_home(copy.deepcopy(payload))
    assert _table_counts(db) == {
        "home_resources": 0,
        "notes": 0,
        "resource_relations": 0,
    }


def _set(payload, table, index, **changes):
    payload["tables"][table][index].update(changes)
    return payload


def _drop(payload, table, index, *columns):
    for column in columns:
        payload["tables"][table][index].pop(column, None)
    return payload


def test_valid_export_imports_and_round_trips():
    payload = _source_payload()
    db = AIDB(":memory:")
    db.import_home(copy.deepcopy(payload))

    resources = db.list_resources()
    assert len(resources) == 2
    first = next(r for r in resources if r.content["title"] == "one")
    second = next(r for r in resources if r.content["title"] == "two")
    note = db.get_note(first.id)
    assert note.id == note.resource_id == first.id
    assert note.title == "one" and note.content == "1"
    relations = db.resource_relations(first.id)
    assert len(relations) == 1
    assert relations[0]["target_resource_id"] == second.id
    assert relations[0]["relation"] == "supports"


def test_reimport_is_idempotent():
    payload = _source_payload()
    db = AIDB(":memory:")
    db.import_home(copy.deepcopy(payload))
    db.import_home(copy.deepcopy(payload))
    assert _table_counts(db) == {
        "home_resources": 2,
        "notes": 2,
        "resource_relations": 1,
    }


@pytest.mark.parametrize(
    "content,expected",
    [
        ('"text"', "text"),
        ("[1, 2]", [1, 2]),
        ("null", None),
        ("42", 42),
        ('{"a": 1}', {"a": 1}),
    ],
)
def test_resource_content_accepts_any_json_value(content, expected):
    payload = _set(_source_payload(), "home_resources", 0, content=content)
    db = AIDB(":memory:")
    db.import_home(copy.deepcopy(payload))
    resource_id = payload["tables"]["home_resources"][0]["id"]
    assert db.get_resource(resource_id).content == expected


def test_rows_missing_defaulted_columns_import_with_defaults():
    payload = _source_payload()
    _drop(payload, "home_resources", 0, "content", "metadata")
    _drop(payload, "notes", 0, "metadata", "kind")
    db = AIDB(":memory:")
    db.import_home(copy.deepcopy(payload))
    resource_id = payload["tables"]["home_resources"][0]["id"]
    resource = db.get_resource(resource_id)
    assert resource.content is None
    assert resource.metadata == {}
    assert resource.revision == 1
    note = db.get_note(resource_id)
    assert note.kind == "note"
    assert note.metadata == {}


def test_filtered_public_export_imports():
    source = AIDB(":memory:")
    first = source.create_note("one", "1", owner="agent:one", visibility="public")
    second = source.create_note("two", "2", owner="agent:one", visibility="public")
    source.relate_resources(first.id, second.id, "supports")
    payload = source.export_home(include_private=False)
    assert payload["tables"]["resource_relations"][0]["metadata"] == "{}"
    db = AIDB(":memory:")
    db.import_home(copy.deepcopy(payload))
    assert len(db.resource_relations(first.id)) == 1


def test_relation_against_resource_already_in_home_imports():
    # Both endpoints live in the receiving home, not the payload: the
    # linkage check must accept resources already in the home, the way
    # the home_changes check does.
    db = AIDB(":memory:")
    first = db.create_resource("document", {"title": "A"})
    second = db.create_resource("document", {"title": "B"})
    payload = {
        "format": "aidb-home-v1",
        "tables": {
            "resource_relations": [
                {
                    "source_resource_id": first.id,
                    "target_resource_id": second.id,
                    "relation": "supports",
                    "metadata": "{}",
                }
            ],
            "home_changes": [
                {
                    "change_id": "chg:relate-1",
                    "resource_id": first.id,
                    "operation": "relate",
                    "actor": None,
                    "previous_revision": None,
                    "new_revision": None,
                    "payload": json.dumps(
                        {
                            "target_resource_id": second.id,
                            "relation": "supports",
                        }
                    ),
                }
            ],
        },
    }
    db.import_home(copy.deepcopy(payload))
    relations = db.resource_relations(first.id)
    assert len(relations) == 1
    assert relations[0]["target_resource_id"] == second.id


def test_note_against_resource_already_in_home_imports():
    # The note's resource lives in the receiving home, not the payload.
    db = AIDB(":memory:")
    target = db.create_resource("document", {"title": "T", "content": "C", "kind": "note"})
    payload = {
        "format": "aidb-home-v1",
        "tables": {
            "notes": [
                {
                    "id": target.id,
                    "resource_id": target.id,
                    "title": "T",
                    "content": "C",
                    "owner": None,
                    "visibility": "private",
                    "kind": "note",
                    "metadata": "{}",
                    "revision": 1,
                }
            ],
        },
    }
    db.import_home(copy.deepcopy(payload))
    assert db.get_note(target.id).title == "T"


@pytest.mark.parametrize(
    "content,match",
    [
        ('{"a": NaN}', "non-standard JSON numeric constant"),
        ("not json at all", "invalid JSON in home_resources content"),
        ('{"a": 1, "a": 2}', "duplicate JSON object key"),
    ],
)
def test_resource_content_must_be_strict_json(content, match):
    payload = _set(_source_payload(), "home_resources", 0, content=content)
    _assert_rejected(payload, match)


@pytest.mark.parametrize(
    "metadata,match",
    [
        ('{"a": NaN}', "non-standard JSON numeric constant"),
        ("[1, 2]", "home_resources metadata must be a JSON object"),
        ("not json at all", "invalid JSON in home_resources metadata"),
    ],
)
def test_resource_metadata_must_be_strict_json_object(metadata, match):
    payload = _set(_source_payload(), "home_resources", 0, metadata=metadata)
    _assert_rejected(payload, match)


@pytest.mark.parametrize("revision", [-1, 0])
def test_resource_revision_must_be_positive(revision):
    payload = _set(_source_payload(), "home_resources", 0, revision=revision)
    _assert_rejected(payload, "invalid revision")


@pytest.mark.parametrize("column", ["id", "resource_type"])
def test_resource_row_missing_required_column_rejected(column):
    payload = _drop(_source_payload(), "home_resources", 0, column)
    _assert_rejected(payload, f"missing {column}")


@pytest.mark.parametrize("column", ["content", "metadata"])
def test_resource_row_with_null_defaulted_column_rejected(column):
    payload = _set(_source_payload(), "home_resources", 0, **{column: None})
    _assert_rejected(payload, f"home_resources {column}")


@pytest.mark.parametrize(
    "metadata,match",
    [
        ('{"a": NaN}', "non-standard JSON numeric constant"),
        ("[1, 2]", "notes metadata must be a JSON object"),
    ],
)
def test_note_metadata_must_be_strict_json_object(metadata, match):
    payload = _set(_source_payload(), "notes", 0, metadata=metadata)
    _assert_rejected(payload, match)


def test_note_with_dangling_resource_id_rejected():
    payload = _source_payload()
    # id == resource_id, so the linkage check (not the id-equality
    # check) is what fires.
    _set(payload, "notes", 0, id="res:missing", resource_id="res:missing")
    _assert_rejected(payload, "note references a missing resource")


def test_note_id_must_equal_resource_id():
    payload = _set(_source_payload(), "notes", 0, id="note:other")
    _assert_rejected(payload, "note id must equal its resource_id")


def test_note_revision_must_be_positive():
    payload = _set(_source_payload(), "notes", 0, revision=-1)
    _assert_rejected(payload, "invalid revision")


@pytest.mark.parametrize("column", ["title", "resource_id", "content"])
def test_note_row_missing_required_column_rejected(column):
    payload = _drop(_source_payload(), "notes", 0, column)
    _assert_rejected(payload, f"missing {column}")


@pytest.mark.parametrize(
    "metadata,match",
    [
        ('{"a": NaN}', "non-standard JSON numeric constant"),
        ("[1, 2]", "resource_relations metadata must be a JSON object"),
    ],
)
def test_relation_metadata_must_be_strict_json_object(metadata, match):
    payload = _set(_source_payload(), "resource_relations", 0, metadata=metadata)
    _assert_rejected(payload, match)


@pytest.mark.parametrize("field", ["source_resource_id", "target_resource_id"])
def test_relation_with_dangling_endpoint_rejected(field):
    payload = _set(_source_payload(), "resource_relations", 0, **{field: "res:missing"})
    _assert_rejected(payload, "resource relation references a missing resource")


def test_relation_to_self_rejected():
    payload = _source_payload()
    row = payload["tables"]["resource_relations"][0]
    _set(payload, "resource_relations", 0, target_resource_id=row["source_resource_id"])
    _assert_rejected(payload, "cannot relate to itself")


@pytest.mark.parametrize("column", ["relation", "source_resource_id"])
def test_relation_row_missing_required_column_rejected(column):
    payload = _drop(_source_payload(), "resource_relations", 0, column)
    _assert_rejected(payload, f"missing {column}")


@pytest.mark.parametrize(
    "metadata,match",
    [
        ('{"a": NaN}', "non-standard JSON numeric constant"),
        ("[1, 2]", "node_identity metadata must be a JSON object"),
    ],
)
def test_node_identity_metadata_must_be_strict_json_object(metadata, match):
    payload = _set(_source_payload(), "node_identity", 0, metadata=metadata)
    _assert_rejected(payload, match)


def test_node_identity_row_missing_node_id_rejected():
    payload = _drop(_source_payload(), "node_identity", 0, "node_id")
    _assert_rejected(payload, "missing node_id")


def test_node_identity_id_must_be_one():
    payload = _set(_source_payload(), "node_identity", 0, id=2)
    _assert_rejected(payload, "invalid node_identity id")


@pytest.mark.parametrize(
    "field,value,match",
    [
        (
            "capabilities",
            '{"a": NaN}',
            "non-standard JSON numeric constant",
        ),
        (
            "capabilities",
            '{"a": 1}',
            "node_specifications capabilities must be a JSON list",
        ),
        (
            "resource_types",
            '{"a": 1}',
            "node_specifications resource_types must be a JSON list",
        ),
        (
            "transports",
            '{"a": 1}',
            "node_specifications transports must be a JSON list",
        ),
        (
            "extensions",
            '{"a": 1}',
            "node_specifications extensions must be a JSON list",
        ),
    ],
)
def test_node_spec_list_columns_must_be_strict_json_lists(field, value, match):
    payload = _set(_source_payload(), "node_specifications", 0, **{field: value})
    _assert_rejected(payload, match)


def test_node_spec_constraints_must_be_strict_json_object():
    payload = _set(_source_payload(), "node_specifications", 0, constraints="[1, 2]")
    _assert_rejected(payload, "node_specifications constraints must be a JSON object")


def test_node_spec_extensions_list_is_valid():
    payload = _set(_source_payload(), "node_specifications", 0, extensions='["x"]')
    db = AIDB(":memory:")
    db.import_home(copy.deepcopy(payload))
    assert db.current_specification().extensions == ["x"]
