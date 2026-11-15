"""import_home() must validate home_changes payloads, not just their rows.

The store writes each change payload in a fixed per-operation shape
(create {"resource_type", "visibility"} at revision 1; update
{"content_changed", "metadata_changed"} stepping one revision; publish {}
stepping one revision; relate {"target_resource_id", "relation"} with no
revisions and a matching resource_relations row). Before this lane,
import_home() never parsed the payload text at all, so any string --
invalid JSON, NaN literals, duplicate keys, wrong shapes, dangling
relate targets -- entered the home and later passed verify_home()
unchallenged. These tests pin the fail-closed import gate.
"""

import copy
import json

import pytest

from aidb import AIDB


def _seeded_export():
    """A small valid home: one public resource, one private resource,
    one relation between them, and the store-written history."""
    db = AIDB(":memory:")
    first = db.create_resource("document", {"title": "A"}, owner="alice", visibility="public")
    second = db.create_resource("document", {"title": "B"}, owner="alice", visibility="private")
    db.relate_resources(first.id, second.id, "references")
    return db, db.export_home(include_private=True)


def _change(base, **overrides):
    change = {
        "id": 99,
        "change_id": "chg:probe",
        "resource_id": "res:a",
        "operation": "create",
        "actor": "alice",
        "previous_revision": None,
        "new_revision": 1,
        "payload": '{"resource_type": "document", "visibility": "public"}',
        "created_at": "2026-11-15T00:00:00Z",
    }
    change.update(overrides)
    tables = base["tables"]
    tables["home_resources"] = [
        {
            "id": "res:a",
            "resource_type": "document",
            "content": '{"title": "A"}',
            "owner": "alice",
            "visibility": "public",
            "metadata": "{}",
            "revision": 1,
        },
        {
            "id": "res:b",
            "resource_type": "document",
            "content": '{"title": "B"}',
            "owner": "alice",
            "visibility": "private",
            "metadata": "{}",
            "revision": 1,
        },
    ]
    tables["home_changes"] = [change]
    # The seeded relation row is cleared by default: relate tests add
    # back exactly the relation row their case needs.
    tables["resource_relations"] = []
    return base


def _payload_with_change(**overrides):
    _, exported = _seeded_export()
    text = json.dumps(exported)
    first_id = exported["tables"]["home_resources"][0]["id"]
    second_id = exported["tables"]["home_resources"][1]["id"]
    text = text.replace(first_id, "res:a").replace(second_id, "res:b")
    return _change(json.loads(text), **overrides)


def _expect_rejected(payload, match):
    db = AIDB(":memory:")
    with pytest.raises(ValueError, match=match):
        db.import_home(payload)
    assert db.db.execute("SELECT COUNT(*) FROM home_changes").fetchone()[0] == 0
    assert db.db.execute("SELECT COUNT(*) FROM home_resources").fetchone()[0] == 0


def test_unmodified_export_still_imports():
    _, exported = _seeded_export()
    db = AIDB(":memory:")
    db.import_home(copy.deepcopy(exported))
    assert db.db.execute("SELECT COUNT(*) FROM home_changes").fetchone()[0] == 3


def test_reimport_of_valid_export_is_idempotent():
    _, exported = _seeded_export()
    db = AIDB(":memory:")
    db.import_home(copy.deepcopy(exported))
    db.import_home(copy.deepcopy(exported))
    assert db.db.execute("SELECT COUNT(*) FROM home_changes").fetchone()[0] == 3


def test_create_after_publish_keeps_private_create_payload():
    # A resource created private and later published has a public row
    # with a private create payload: legitimate history, must import.
    db = AIDB(":memory:")
    resource = db.create_resource("document", {"title": "A"}, owner="alice", visibility="private")
    db.publish_resource(resource.id)
    exported = db.export_home(include_private=True)
    restored = AIDB(":memory:")
    restored.import_home(copy.deepcopy(exported))
    row = restored.db.execute(
        "SELECT payload FROM home_changes WHERE operation='create'"
    ).fetchone()
    assert '"private"' in row["payload"]


def test_invalid_json_payload_rejected():
    _expect_rejected(
        _payload_with_change(payload="{not json"),
        "home change payload must be strict JSON",
    )


def test_nan_literal_payload_rejected():
    _expect_rejected(
        _payload_with_change(payload='{"resource_type": "document", "visibility": NaN}'),
        "home change payload must be strict JSON",
    )


def test_duplicate_key_payload_rejected():
    _expect_rejected(
        _payload_with_change(
            payload='{"resource_type": "document", "resource_type": "note", "visibility": "public"}'
        ),
        "home change payload must be strict JSON",
    )


def test_non_object_payload_rejected():
    _expect_rejected(
        _payload_with_change(payload='["create"]'),
        "home change payload must be a JSON object",
    )


def test_create_payload_with_bogus_visibility_rejected():
    _expect_rejected(
        _payload_with_change(payload='{"resource_type": "document", "visibility": "secret"}'),
        "home change create payload visibility must be public or private",
    )


def test_create_payload_missing_resource_type_rejected():
    _expect_rejected(
        _payload_with_change(payload='{"visibility": "public"}'),
        "home change create payload must have resource_type and visibility",
    )


def test_create_payload_resource_type_mismatch_rejected():
    _expect_rejected(
        _payload_with_change(payload='{"resource_type": "note", "visibility": "public"}'),
        "home change create payload resource_type does not match the resource",
    )


def test_create_revision_must_start_at_one():
    _expect_rejected(
        _payload_with_change(previous_revision=7),
        "home change create revision must be new_revision 1",
    )


def test_update_payload_with_non_boolean_flags_rejected():
    _expect_rejected(
        _payload_with_change(
            operation="update",
            previous_revision=1,
            new_revision=2,
            payload='{"content_changed": "yes", "metadata_changed": null}',
        ),
        "home change update payload flags must be booleans",
    )


def test_update_revision_must_step_by_one():
    _expect_rejected(
        _payload_with_change(
            operation="update",
            previous_revision=999,
            new_revision=5,
            payload='{"content_changed": true, "metadata_changed": false}',
        ),
        "home change update revision must step by exactly one",
    )


def test_publish_payload_must_be_empty():
    _expect_rejected(
        _payload_with_change(
            operation="publish",
            previous_revision=1,
            new_revision=2,
            payload='{"extra": 1}',
        ),
        "home change publish payload must be empty",
    )


def test_valid_publish_change_imports():
    db = AIDB(":memory:")
    resource = db.create_resource("document", {"title": "A"}, owner="alice", visibility="private")
    db.publish_resource(resource.id)
    exported = db.export_home(include_private=True)
    restored = AIDB(":memory:")
    restored.import_home(copy.deepcopy(exported))
    assert restored.db.execute("SELECT COUNT(*) FROM home_changes").fetchone()[0] == 2


def test_unknown_operation_rejected():
    _expect_rejected(
        _payload_with_change(operation="delete", payload="{}"),
        "unknown home change operation",
    )


def test_relate_to_missing_target_rejected():
    _expect_rejected(
        _payload_with_change(
            operation="relate",
            previous_revision=None,
            new_revision=None,
            payload='{"target_resource_id": "res:missing", "relation": "references"}',
        ),
        "home change relate payload references a missing resource",
    )


def test_relate_without_matching_relation_row_rejected():
    _expect_rejected(
        _payload_with_change(
            operation="relate",
            previous_revision=None,
            new_revision=None,
            payload='{"target_resource_id": "res:b", "relation": "references"}',
        ),
        "home change relate payload has no matching relation row",
    )


def test_relate_to_self_rejected():
    _expect_rejected(
        _payload_with_change(
            operation="relate",
            previous_revision=None,
            new_revision=None,
            payload='{"target_resource_id": "res:a", "relation": "references"}',
        ),
        "home change relate payload target must differ",
    )


def test_relate_with_matching_row_imports():
    payload = _payload_with_change(
        operation="relate",
        previous_revision=None,
        new_revision=None,
        payload='{"target_resource_id": "res:b", "relation": "references"}',
    )
    payload["tables"]["resource_relations"] = [
        {
            "id": 1,
            "source_resource_id": "res:a",
            "target_resource_id": "res:b",
            "relation": "references",
            "metadata": "{}",
            "created_at": "2026-11-15T00:00:00Z",
        }
    ]
    db = AIDB(":memory:")
    db.import_home(payload)
    assert db.db.execute("SELECT COUNT(*) FROM home_changes").fetchone()[0] == 1


def test_well_formed_duplicate_change_still_conflicts():
    # PR #37 semantics preserved: a duplicate change_id whose payload is
    # well-formed but differs from the stored row still reaches the
    # insert-time conflict check (the payload validator passes it first).
    _, exported = _seeded_export()
    extra = dict(exported["tables"]["home_changes"][0])
    extra["payload"] = '{"resource_type": "document", "visibility": "private"}'
    exported["tables"]["home_changes"].append(extra)
    db = AIDB(":memory:")
    with pytest.raises(ValueError, match="conflicting existing row"):
        db.import_home(exported)
    assert db.db.execute("SELECT COUNT(*) FROM home_changes").fetchone()[0] == 0


def test_relate_against_relation_row_already_in_home_imports():
    # The matching relation row may already live in the receiving home;
    # only the change row arrives in the payload.
    db = AIDB(":memory:")
    first = db.create_resource("document", {"title": "A"}, owner="alice", visibility="public")
    second = db.create_resource("document", {"title": "B"}, owner="alice", visibility="private")
    db.relate_resources(first.id, second.id, "references")
    payload = _payload_with_change(
        resource_id=first.id,
        operation="relate",
        previous_revision=None,
        new_revision=None,
        payload='{"target_resource_id": "%s", "relation": "references"}' % second.id,
    )
    payload["tables"]["home_resources"] = []
    payload["tables"]["home_changes"][0]["change_id"] = "chg:late-relate"
    db.import_home(payload)
    assert (
        db.db.execute("SELECT COUNT(*) FROM home_changes WHERE operation='relate'").fetchone()[0]
        == 2
    )
