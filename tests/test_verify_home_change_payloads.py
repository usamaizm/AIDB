import json

from aidb import AIDB


def _home():
    db = AIDB(":memory:")
    db.initialize_home(owner="agent:one")
    n1 = db.create_note("first", "body one", owner="agent:one")
    n2 = db.create_note("second", "body two", owner="agent:one")
    db.update_resource(
        n1.id,
        content={"title": "first", "content": "body one v2", "kind": "note"},
    )
    db.publish_resource(n1.id)
    db.relate_resources(n1.id, n2.id, "references")
    return db, n1, n2


def _tamper(db, sql, params=()):
    db.db.execute(sql, params)
    db.db.commit()


def _issues(result):
    return result["issues"]


def test_valid_home_verifies_ok():
    db, _, _ = _home()
    assert db.verify_home() == {"ok": True, "issues": []}


def test_create_payload_resource_type_mismatch():
    db, n1, _ = _home()
    _tamper(
        db,
        "UPDATE home_changes SET payload=? WHERE operation='create' AND resource_id=?",
        (json.dumps({"resource_type": "bogus", "visibility": "private"}), n1.id),
    )
    result = db.verify_home()
    assert result["ok"] is False
    assert any(i.startswith("create payload mismatch:") for i in _issues(result))


def test_create_payload_visibility_flip_on_unpublished_resource():
    db, _, n2 = _home()
    _tamper(
        db,
        "UPDATE home_changes SET payload=? WHERE operation='create' AND resource_id=?",
        (json.dumps({"resource_type": "note", "visibility": "public"}), n2.id),
    )
    result = db.verify_home()
    assert result["ok"] is False
    assert any(i == "visibility mismatch:" + n2.id for i in _issues(result))


def test_relate_payload_target_missing():
    db, _, _ = _home()
    _tamper(
        db,
        "UPDATE home_changes SET payload=? WHERE operation='relate'",
        (json.dumps({"target_resource_id": "res:does-not-exist", "relation": "references"}),),
    )
    result = db.verify_home()
    assert result["ok"] is False
    assert any(i.startswith("relate target missing:") for i in _issues(result))


def test_relation_row_deleted_but_relate_change_kept():
    db, _, _ = _home()
    _tamper(db, "DELETE FROM resource_relations")
    result = db.verify_home()
    assert result["ok"] is False
    assert any(i.startswith("relate payload mismatch:") for i in _issues(result))


def test_broken_revision_chain_reports_once():
    db, _, _ = _home()
    _tamper(
        db,
        "UPDATE home_changes SET previous_revision=999 WHERE operation='update'",
    )
    result = db.verify_home()
    assert result["ok"] is False
    chain = [i for i in _issues(result) if i.startswith("revision chain broken:")]
    assert len(chain) == 1
    assert result["issues"] == chain


def test_invalid_json_payload():
    db, n1, _ = _home()
    _tamper(
        db,
        "UPDATE home_changes SET payload='{not json' WHERE operation='create' AND resource_id=?",
        (n1.id,),
    )
    result = db.verify_home()
    assert result["ok"] is False
    assert any(i.startswith("invalid change payload:") for i in _issues(result))


def test_deleted_publish_change_breaks_visibility_replay():
    db, n1, _ = _home()
    _tamper(db, "DELETE FROM home_changes WHERE operation='publish'")
    result = db.verify_home()
    assert result["ok"] is False
    assert any(i == "visibility mismatch:" + n1.id for i in _issues(result))


def test_deleted_update_change_breaks_chain():
    db, n1, _ = _home()
    db.update_resource(
        n1.id,
        content={"title": "first", "content": "body one v3", "kind": "note"},
    )
    _tamper(
        db,
        "DELETE FROM home_changes WHERE operation='update' AND resource_id=? AND new_revision=2",
        (n1.id,),
    )
    result = db.verify_home()
    assert result["ok"] is False
    assert any(i.startswith("revision chain broken:") for i in _issues(result))


def test_unknown_operation_flagged():
    db, n1, _ = _home()
    _tamper(
        db,
        "UPDATE home_changes SET operation='delete' WHERE operation='relate'",
    )
    result = db.verify_home()
    assert result["ok"] is False
    assert any(i.startswith("unknown change operation:") for i in _issues(result))


def test_update_payload_flags_must_be_booleans():
    db, n1, _ = _home()
    _tamper(
        db,
        "UPDATE home_changes SET payload=? WHERE operation='update'",
        (json.dumps({"content_changed": "yes", "metadata_changed": False}),),
    )
    result = db.verify_home()
    assert result["ok"] is False
    assert any(i.startswith("update payload mismatch:") for i in _issues(result))


def test_orphan_create_change_still_flagged():
    db, _, _ = _home()
    db.db.execute(
        "INSERT INTO home_changes(change_id,resource_id,operation,actor,new_revision,payload)"
        " VALUES(?,?,?,?,?,?)",
        (
            "chg:orphan",
            "res:ghost",
            "create",
            "agent:one",
            1,
            json.dumps({"resource_type": "note", "visibility": "private"}),
        ),
    )
    db.db.commit()
    result = db.verify_home()
    assert result["ok"] is False
    assert "missing resource:res:ghost" in _issues(result)


def test_unanchored_update_flagged():
    db, n1, _ = _home()
    _tamper(
        db,
        "DELETE FROM home_changes WHERE operation='create' AND resource_id=?",
        (n1.id,),
    )
    result = db.verify_home()
    assert result["ok"] is False
    assert any(i.startswith("unanchored revision:") for i in _issues(result))


def test_tamper_isolated_to_one_resource():
    db, n1, n2 = _home()
    _tamper(
        db,
        "UPDATE home_changes SET payload=? WHERE operation='create' AND resource_id=?",
        (json.dumps({"resource_type": "bogus", "visibility": "private"}), n2.id),
    )
    result = db.verify_home()
    assert result["ok"] is False
    assert all(n1.id not in i for i in _issues(result))
    assert any(i.startswith("create payload mismatch:") for i in _issues(result))


def test_tampered_payload_reflected_in_export_verification():
    db, n1, _ = _home()
    _tamper(
        db,
        "UPDATE home_changes SET payload=? WHERE operation='create' AND resource_id=?",
        (json.dumps({"resource_type": "bogus", "visibility": "private"}), n1.id),
    )
    payload = db.export_home()
    assert payload["verification"]["ok"] is False
    assert any(i.startswith("create payload mismatch:") for i in payload["verification"]["issues"])


def test_resource_row_revision_bumped_without_change():
    db, n1, _ = _home()
    _tamper(
        db,
        "UPDATE home_resources SET revision=revision+1 WHERE id=?",
        (n1.id,),
    )
    result = db.verify_home()
    assert result["ok"] is False
    assert any(i == "revision mismatch:" + n1.id for i in _issues(result))
