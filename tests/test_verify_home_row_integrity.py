"""verify_home() must catch corrupt stored JSON in the rows it verifies.

On main, verify_home() only checked home_changes rows (missing resource /
future revision). Every JSON-text column in the exported tables could hold
text that no longer parses — or parses into the wrong shape — while
verification still reported ok, even though the read paths (get_resource,
get_note, get_artifact, current_specification) use plain json.loads and
break on the same rows.
"""

from aidb import AIDB


def _populated_db():
    db = AIDB(":memory:")
    db.initialize_home(owner="agent:one")
    note = db.create_note("title", "body", owner="agent:one")
    resource = db.create_resource("note", {"text": "hello"}, owner="agent:one")
    db.relate_resources(resource.id, note.id, "references")
    artifact = db.register_artifact("a1", "text/plain", 3, "sha256:abc", metadata={"k": "v"})
    db.current_specification()
    return db, note, resource, artifact


def _corrupt(db, sql, params=()):
    db.db.execute(sql, params)
    db.db.commit()


def _assert_flagged(db, table, column, row_id):
    result = db.verify_home()
    assert result["ok"] is False
    assert result["issues"]
    assert any(
        table in issue and column in issue and str(row_id) in issue for issue in result["issues"]
    ), result["issues"]


def test_corrupt_resource_content_is_reported():
    db, _, resource, _ = _populated_db()
    _corrupt(
        db,
        "UPDATE home_resources SET content='{oops' WHERE id=?",
        (resource.id,),
    )
    _assert_flagged(db, "home_resources", "content", resource.id)


def test_corrupt_resource_metadata_is_reported():
    db, _, resource, _ = _populated_db()
    _corrupt(
        db,
        "UPDATE home_resources SET metadata='not json' WHERE id=?",
        (resource.id,),
    )
    _assert_flagged(db, "home_resources", "metadata", resource.id)


def test_nan_relation_metadata_is_reported():
    db, _, _, _ = _populated_db()
    _corrupt(db, "UPDATE resource_relations SET metadata='{\"a\": NaN}'")
    result = db.verify_home()
    assert result["ok"] is False
    assert any(
        "resource_relations" in issue and "metadata" in issue for issue in result["issues"]
    ), result["issues"]


def test_corrupt_note_metadata_is_reported():
    db, note, _, _ = _populated_db()
    _corrupt(db, "UPDATE notes SET metadata='[1,2' WHERE id=?", (note.id,))
    _assert_flagged(db, "notes", "metadata", note.id)


def test_corrupt_artifact_provenance_is_reported():
    db, _, _, artifact = _populated_db()
    _corrupt(
        db,
        "UPDATE artifacts SET provenance='{\"a\": }' WHERE id=?",
        (artifact.id,),
    )
    _assert_flagged(db, "artifacts", "provenance", artifact.id)


def test_corrupt_artifact_metadata_is_reported():
    db, _, _, artifact = _populated_db()
    _corrupt(
        db,
        "UPDATE artifacts SET metadata='not json' WHERE id=?",
        (artifact.id,),
    )
    _assert_flagged(db, "artifacts", "metadata", artifact.id)


def test_corrupt_artifact_transformation_history_is_reported():
    db, _, _, artifact = _populated_db()
    _corrupt(
        db,
        "UPDATE artifacts SET transformation_history='[bad' WHERE id=?",
        (artifact.id,),
    )
    _assert_flagged(db, "artifacts", "transformation_history", artifact.id)


def test_corrupt_node_identity_metadata_is_reported():
    db, _, _, _ = _populated_db()
    _corrupt(db, "UPDATE node_identity SET metadata='not json' WHERE id=1")
    _assert_flagged(db, "node_identity", "metadata", 1)


def test_corrupt_node_specification_capabilities_is_reported():
    db, _, _, _ = _populated_db()
    _corrupt(db, "UPDATE node_specifications SET capabilities='[bad'")
    result = db.verify_home()
    assert result["ok"] is False
    assert any(
        "node_specifications" in issue and "capabilities" in issue for issue in result["issues"]
    ), result["issues"]


def test_metadata_storing_a_list_is_a_shape_issue():
    db, _, resource, _ = _populated_db()
    _corrupt(
        db,
        "UPDATE home_resources SET metadata='[1, 2]' WHERE id=?",
        (resource.id,),
    )
    result = db.verify_home()
    assert result["ok"] is False
    assert any(
        "home_resources.metadata" in issue and "expected object" in issue
        for issue in result["issues"]
    ), result["issues"]


def test_string_list_column_with_non_string_items_is_a_shape_issue():
    db, _, _, _ = _populated_db()
    _corrupt(db, "UPDATE node_specifications SET transports='[\"ok\", 7]'")
    result = db.verify_home()
    assert result["ok"] is False
    assert any(
        "node_specifications.transports" in issue and "expected list of strings" in issue
        for issue in result["issues"]
    ), result["issues"]


def test_duplicate_keys_and_nan_are_rejected_as_invalid_json():
    db, note, _, _ = _populated_db()
    _corrupt(
        db,
        'UPDATE notes SET metadata=\'{"a": 1, "a": 2}\' WHERE id=?',
        (note.id,),
    )
    _assert_flagged(db, "notes", "metadata", note.id)
    db, _, resource, _ = _populated_db()
    _corrupt(
        db,
        "UPDATE home_resources SET content='{\"a\": NaN}' WHERE id=?",
        (resource.id,),
    )
    _assert_flagged(db, "home_resources", "content", resource.id)


def test_one_tamper_reports_exactly_one_issue():
    db, _, resource, _ = _populated_db()
    _corrupt(
        db,
        "UPDATE home_resources SET content='{oops' WHERE id=?",
        (resource.id,),
    )
    result = db.verify_home()
    assert result == {
        "ok": False,
        "issues": [f"invalid JSON in home_resources.content for id={resource.id}"],
    }


def test_populated_home_with_valid_rows_verifies_ok():
    db, _, _, _ = _populated_db()
    assert db.verify_home() == {"ok": True, "issues": []}


def test_corrupt_row_also_flags_the_export_verification_block():
    db, _, resource, _ = _populated_db()
    _corrupt(
        db,
        "UPDATE home_resources SET content='{oops' WHERE id=?",
        (resource.id,),
    )
    result = db.export_home()["verification"]
    assert result["ok"] is False
    assert any("home_resources.content" in issue for issue in result["issues"])
