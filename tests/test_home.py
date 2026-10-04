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
    assert note.visibility == "public"

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
    db=AIDB(":memory:")
    note=db.create_note("n","c")
    db.publish_resource(note.id)
    db.publish_resource(note.id)
    assert len([c for c in db.list_changes() if c["operation"]=="publish"]) == 1
