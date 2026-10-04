from aidb import AIDB


def test_home_import_restores_relationships_and_history():
    source = AIDB(":memory:")
    first = source.create_note("one", "1", owner="agent:one", visibility="public")
    second = source.create_note("two", "2", owner="agent:one", visibility="public")
    source.relate_resources(first.id, second.id, "supports")
    exported = source.export_home()

    restored = AIDB(":memory:")
    restored.import_home(exported)

    relations = restored.resource_relations(first.id)
    assert len(relations) == 1
    assert relations[0]["target_resource_id"] == second.id
    assert relations[0]["relation"] == "supports"
    assert len(restored.list_changes()) == len(source.list_changes())
