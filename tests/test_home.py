from aidb import AIDB, Note, Resource, Specification


def test_home_defaults_to_private_and_can_publish():
    db = AIDB(":memory:")
    home = db.initialize_home(owner="agent:one")
    assert home["visibility"] == "private"
    note = db.create_note("private thought", "keep this here", owner="agent:one")
    assert isinstance(note, Note)
    assert note.visibility == "private"
    assert db.list_notes(include_private=False) == []
    published = db.publish_resource(note.id)
    assert isinstance(published, Resource)
    assert published.visibility == "public"
    assert db.list_notes(include_private=False)[0].id == note.id


def test_resources_keep_owner_separate_from_visibility():
    db = AIDB(":memory:")
    note = db.create_note("public note", "shared", owner="agent:one", visibility="public")
    assert note.owner == "agent:one"
    private_copy = db.create_resource("note", {"copy": True}, owner="agent:one", visibility="private")
    assert private_copy.owner == "agent:one"
    assert private_copy.visibility == "private"


def test_specification_is_runtime_discoverable():
    db = AIDB(":memory:")
    spec = db.current_specification()
    assert isinstance(spec, Specification)
    payload = db.specification_dict()
    assert payload["node"]["id"] == spec.node_id
    assert "notes" in payload["capabilities"]
    assert "public_private" in payload["capabilities"]
    assert "ownership" in payload["capabilities"]


def test_home_change_history_is_ordered_and_incremental():
    db = AIDB(":memory:")
    first = db.create_note("one", "1", owner="agent:one")
    second = db.create_resource("idea", {"x": 2}, owner="agent:one")
    changes = db.list_changes()
    assert len(changes) == 2
    assert changes[0]["operation"] == "create"
    assert changes[0]["resource_id"] == first.id
    assert changes[1]["resource_id"] == second.id
    assert db.list_changes(after_id=changes[0]["id"])[0]["id"] == changes[1]["id"]


def test_publish_is_idempotent():
    db = AIDB(":memory:")
    note = db.create_note("n", "c")
    db.publish_resource(note.id)
    db.publish_resource(note.id)
    assert len([c for c in db.list_changes() if c["operation"] == "publish"]) == 1


def test_relationships_and_optimistic_updates():
    db = AIDB(":memory:")
    a = db.create_note("a", "A")
    b = db.create_note("b", "B")
    db.relate_resources(a.id, b.id, "supports")
    assert db.resource_relations(a.id)[0]["relation"] == "supports"
    updated = db.update_resource(a.id, content="A2", owner=None, expected_revision=1)
    assert updated.revision == 2
    try:
        db.update_resource(a.id, content="stale", expected_revision=1)
    except ValueError:
        pass
    else:
        raise AssertionError("stale revision must be rejected")


def test_snapshot_is_content_addressed_and_restorable():
    db = AIDB(":memory:")
    db.initialize_home(node_id="node:one", owner="agent:one")
    note = db.create_note("portable", "state", owner="agent:one")
    snap = db.create_snapshot()
    assert snap["snapshot_id"].endswith(snap["content_hash"])

    restored = db.restore_snapshot(snap["snapshot_id"])
    assert restored.node_id == "node:one"
    assert db.get_note(note.id).content == "state"

def test_public_changes_hide_private_resources():
    db = AIDB(":memory:")
    private = db.create_note("secret", "x")
    public = db.create_note("public", "y", visibility="public")
    changes = db.public_changes()
    assert all(c["resource_id"] != private.id for c in changes)
    assert any(c["resource_id"] == public.id for c in changes)

def test_note_update_keeps_resource_and_note_views_consistent():
    db = AIDB(":memory:")
    note = db.create_note("title", "before", metadata={"source": "test"})
    updated = db.update_resource(
        note.id,
        content={"title": "new title", "content": "after", "kind": "observation"},
        metadata={"source": "updated"},
        expected_revision=1,
    )
    current_note = db.get_note(note.id)
    assert updated.content == {
        "title": "new title", "content": "after", "kind": "observation"
    }
    assert current_note.title == updated.content["title"]
    assert current_note.content == updated.content["content"]
    assert current_note.kind == updated.content["kind"]
    assert current_note.metadata == updated.metadata
    assert current_note.revision == updated.revision


def test_note_scalar_update_preserves_title_and_kind():
    db = AIDB(":memory:")
    note = db.create_note("title", "before", kind="question")
    db.update_resource(note.id, content="after")
    assert db.get_note(note.id).title == "title"
    assert db.get_note(note.id).content == "after"
    assert db.get_note(note.id).kind == "question"


def test_public_export_excludes_private_relation_endpoints_and_history():
    db = AIDB(":memory:")
    public = db.create_resource("document", {"text": "public"}, visibility="public")
    private = db.create_resource("secret", {"text": "private-secret-marker"})
    db.relate_resources(public.id, private.id, "references")

    exported = db.export_home(include_private=False)
    serialized = repr(exported)
    assert private.id not in serialized
    assert "private-secret-marker" not in serialized
    assert exported["tables"]["resource_relations"] == []
    assert all(
        row["resource_id"] != private.id
        for row in exported["tables"]["home_changes"]
    )


def test_public_change_feed_hides_relation_to_private_target():
    db = AIDB(":memory:")
    public = db.create_resource("document", {"text": "public"}, visibility="public")
    private = db.create_resource("secret", {"text": "private"})
    db.relate_resources(public.id, private.id, "references")
    changes = db.public_changes()
    assert all(
        not (c["operation"] == "relate" and private.id in c["payload"])
        for c in changes
    )


def test_snapshots_do_not_embed_prior_snapshots():
    db = AIDB(":memory:")
    db.create_note("n", "v1")
    first = db.create_snapshot()
    first_row = db.db.execute(
        "SELECT content FROM home_snapshots WHERE snapshot_id=?", (first["snapshot_id"],)
    ).fetchone()
    first_payload = __import__("json").loads(first_row["content"])
    assert "home_snapshots" not in first_payload["tables"]

    db.create_note("n2", "v2")
    second = db.create_snapshot()
    second_row = db.db.execute(
        "SELECT content FROM home_snapshots WHERE snapshot_id=?", (second["snapshot_id"],)
    ).fetchone()
    second_payload = __import__("json").loads(second_row["content"])
    assert "home_snapshots" not in second_payload["tables"]
