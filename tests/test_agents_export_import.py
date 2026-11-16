"""Agents-table export/import (Q13, issue #22 agent-home evaluation).

The P3 keystone gap from the agent-home probes: on main, export_home
never emitted the agents table and import_home rejected any payload
containing one, so agent identity did not travel between homes.
"""

import copy
import json

import pytest

from aidb import AIDB


def _agents_payload(rows):
    return {"format": "aidb-home-v1", "tables": {"agents": rows}}


def _agent_row(**overrides):
    row = {
        "id": 1,
        "name": "alice",
        "description": "first agent",
        "model": "model-x",
        "role": "agent",
        "permissions": '["read"]',
        "capabilities": '["search"]',
        "metadata": '{"team": "alpha"}',
    }
    row.update(overrides)
    return row


def _agents_in(db):
    return db.export_home()["tables"]["agents"]


def test_round_trip_preserves_agents_with_all_fields():
    source = AIDB(":memory:")
    source.register_agent(
        "alice",
        description="first agent",
        model="model-x",
        role="reviewer",
        permissions=["read", "write"],
        capabilities=["search"],
        metadata={"team": "alpha"},
    )
    source.register_agent("bob", model="model-y")

    exported = source.export_home()
    assert len(exported["tables"]["agents"]) == 2

    restored = AIDB(":memory:")
    restored.import_home(copy.deepcopy(exported))

    rows = {row["name"]: row for row in _agents_in(restored)}
    alice = rows["alice"]
    assert alice["description"] == "first agent"
    assert alice["model"] == "model-x"
    assert alice["role"] == "reviewer"
    assert json.loads(alice["permissions"]) == ["read", "write"]
    assert json.loads(alice["capabilities"]) == ["search"]
    assert json.loads(alice["metadata"]) == {"team": "alpha"}
    bob = rows["bob"]
    assert bob["model"] == "model-y"
    assert bob["role"] == "agent"
    assert json.loads(bob["permissions"]) == []
    assert json.loads(bob["metadata"]) == {}


def test_public_export_includes_agents():
    source = AIDB(":memory:")
    source.register_agent("alice", model="model-x")

    exported = source.export_home(include_private=False)
    rows = exported["tables"]["agents"]
    assert len(rows) == 1
    assert rows[0]["name"] == "alice"
    assert rows[0]["model"] == "model-x"


def test_import_rejects_unknown_table():
    db = AIDB(":memory:")
    payload = _agents_payload([_agent_row()])
    payload["tables"]["not_a_table"] = []
    with pytest.raises(ValueError, match="unknown home import table"):
        db.import_home(payload)
    assert _agents_in(db) == []


def test_import_rejects_colliding_id():
    db = AIDB(":memory:")
    db.register_agent("alice", model="model-x")
    existing_id = _agents_in(db)[0]["id"]

    with pytest.raises(ValueError, match="collides with an existing agent"):
        db.import_home(_agents_payload([_agent_row(id=existing_id, name="mallory")]))
    assert [row["name"] for row in _agents_in(db)] == ["alice"]


def test_import_rejects_colliding_name():
    db = AIDB(":memory:")
    db.register_agent("alice", model="model-x")

    with pytest.raises(ValueError, match="collides with an existing agent"):
        db.import_home(_agents_payload([_agent_row(id=99, name="alice", model="other")]))
    assert [row["name"] for row in _agents_in(db)] == ["alice"]


def test_import_rejects_colliding_name_within_payload():
    db = AIDB(":memory:")
    rows = [
        _agent_row(id=1, name="alice"),
        _agent_row(id=2, name="alice", model="other"),
    ]
    with pytest.raises(ValueError, match="collides with an existing agent"):
        db.import_home(_agents_payload(rows))
    assert _agents_in(db) == []


def test_import_rejects_negative_id():
    db = AIDB(":memory:")
    with pytest.raises(ValueError, match="invalid id"):
        db.import_home(_agents_payload([_agent_row(id=-1)]))
    assert _agents_in(db) == []


def test_import_rejects_empty_name():
    db = AIDB(":memory:")
    with pytest.raises(ValueError, match="invalid name"):
        db.import_home(_agents_payload([_agent_row(name="   ")]))
    assert _agents_in(db) == []


def test_import_rejects_missing_name():
    db = AIDB(":memory:")
    row = _agent_row()
    del row["name"]
    with pytest.raises(ValueError, match="invalid name"):
        db.import_home(_agents_payload([row]))
    assert _agents_in(db) == []


def test_import_rejects_empty_role():
    db = AIDB(":memory:")
    with pytest.raises(ValueError, match="invalid role"):
        db.import_home(_agents_payload([_agent_row(role="")]))
    assert _agents_in(db) == []


def test_import_rejects_unparseable_permissions_json():
    db = AIDB(":memory:")
    with pytest.raises(ValueError, match="invalid JSON in agent permissions"):
        db.import_home(_agents_payload([_agent_row(permissions='["read"')]))
    assert _agents_in(db) == []


def test_import_rejects_non_list_permissions():
    db = AIDB(":memory:")
    with pytest.raises(ValueError, match="invalid permissions"):
        db.import_home(_agents_payload([_agent_row(permissions='{"read": true}')]))
    assert _agents_in(db) == []


def test_import_rejects_non_string_capability_entry():
    db = AIDB(":memory:")
    with pytest.raises(ValueError, match="invalid capabilities"):
        db.import_home(_agents_payload([_agent_row(capabilities='["search", 7]')]))
    assert _agents_in(db) == []


def test_import_rejects_unparseable_metadata_json():
    db = AIDB(":memory:")
    with pytest.raises(ValueError, match="invalid JSON in agent metadata"):
        db.import_home(_agents_payload([_agent_row(metadata="{bad json")]))
    assert _agents_in(db) == []


def test_import_rejects_non_object_metadata():
    db = AIDB(":memory:")
    with pytest.raises(ValueError, match="agent metadata must be a JSON object"):
        db.import_home(_agents_payload([_agent_row(metadata='["team"]')]))
    assert _agents_in(db) == []


def test_import_rejects_non_standard_json_constant_in_metadata():
    db = AIDB(":memory:")
    with pytest.raises(ValueError, match="invalid JSON in agent metadata"):
        db.import_home(_agents_payload([_agent_row(metadata='{"score": NaN}')]))
    assert _agents_in(db) == []


def test_import_rejects_wrong_types():
    db = AIDB(":memory:")
    with pytest.raises(ValueError, match="invalid"):
        db.import_home(_agents_payload([_agent_row(model=42)]))
    with pytest.raises(ValueError, match="invalid"):
        db.import_home(_agents_payload([_agent_row(id="1")]))
    assert _agents_in(db) == []


def test_import_valid_agents_only_payload_into_empty_home():
    db = AIDB(":memory:")
    db.import_home(_agents_payload([_agent_row(), _agent_row(id=2, name="bob")]))
    rows = {row["name"]: row for row in _agents_in(db)}
    assert set(rows) == {"alice", "bob"}
    assert rows["alice"]["id"] == 1
    assert json.loads(rows["bob"]["permissions"]) == ["read"]


def test_import_agents_row_without_id_assigns_rowid():
    db = AIDB(":memory:")
    row = _agent_row()
    del row["id"]
    db.import_home(_agents_payload([row]))
    rows = _agents_in(db)
    assert len(rows) == 1
    assert rows[0]["name"] == "alice"
    assert isinstance(rows[0]["id"], int)


def test_identical_reimport_is_idempotent():
    # Snapshot restore re-imports a home's own rows; a byte-identical
    # agents row is not a conflict and must not fail the restore.
    db = AIDB(":memory:")
    db.register_agent("alice", model="model-x")
    exported = db.export_home()
    db.import_home(copy.deepcopy(exported))
    assert [row["name"] for row in _agents_in(db)] == ["alice"]


def test_snapshot_restore_keeps_agents():
    # A snapshot restore re-imports the home's own rows; the identical
    # agents rows must pass the fail-closed check as a no-op.
    db = AIDB(":memory:")
    db.register_agent("alice", model="model-x")
    snapshot = db.create_snapshot()
    db.restore_snapshot(snapshot["snapshot_id"])
    assert [row["name"] for row in _agents_in(db)] == ["alice"]


def test_failed_agents_import_leaves_home_untouched():
    db = AIDB(":memory:")
    db.register_agent("alice", model="model-x")
    before = _agents_in(db)
    bad = _agents_payload(
        [
            _agent_row(id=2, name="bob"),
            _agent_row(id=3, name="carol", metadata="{bad json"),
        ]
    )
    with pytest.raises(ValueError):
        db.import_home(bad)
    assert _agents_in(db) == before
