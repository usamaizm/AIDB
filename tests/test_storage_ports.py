from aidb import AIDB, HomeStore, ResourceStore


def exercise_resource_store(store: ResourceStore) -> None:
    first = store.create_resource(
        "document",
        {"body": "initial"},
        owner="agent:one",
        visibility="public",
        metadata={"origin": "contract-test"},
    )
    second = store.create_resource("reference", {"body": "related"})

    assert store.get_resource(first.id).content == {"body": "initial"}
    assert [item.id for item in store.list_resources(resource_type="document")] == [
        first.id
    ]

    updated = store.update_resource(
        first.id,
        content={"body": "revised"},
        expected_revision=1,
    )
    assert updated.revision == 2
    assert updated.content == {"body": "revised"}

    store.relate_resources(first.id, second.id, "references")
    relations = store.resource_relations(first.id)
    assert len(relations) == 1
    assert relations[0]["target_resource_id"] == second.id
    assert relations[0]["relation"] == "references"


def test_sqlite_store_implements_resource_port():
    store = AIDB(":memory:")
    try:
        assert isinstance(store, ResourceStore)
        exercise_resource_store(store)
    finally:
        store.close()


def test_sqlite_store_implements_http_home_port():
    store = AIDB(":memory:")
    try:
        assert isinstance(store, HomeStore)
        with store.operation_lock:
            assert store.specification_dict()["node"]["id"]
    finally:
        store.close()
