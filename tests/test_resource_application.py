from __future__ import annotations

from typing import Any

import pytest

from aidb import AIDB, HomeApplication, Resource
from aidb.application.resources import ResourceService


class MemoryResourceRepository:
    """Small test double proving the use case layer needs no SQLite API."""

    def __init__(self) -> None:
        self.items: dict[str, Resource] = {}
        self.relationships: list[dict[str, Any]] = []

    def create(self, resource: Resource) -> Resource:
        self.items[resource.id] = resource
        return resource

    def get(self, resource_id: str) -> Resource | None:
        return self.items.get(resource_id)

    def list(
        self,
        resource_type: str | None = None,
        visibility: str | None = None,
        include_private: bool = True,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Resource]:
        items = list(self.items.values())
        if resource_type:
            items = [item for item in items if item.resource_type == resource_type]
        if visibility:
            items = [item for item in items if item.visibility == visibility]
        elif not include_private:
            items = [item for item in items if item.visibility == "public"]
        return items[offset : offset + limit if limit is not None else None]

    def update(
        self,
        resource_id: str,
        content: Any = None,
        metadata: dict[str, Any] | None = None,
        owner: str | None = None,
        expected_revision: int | None = None,
    ) -> Resource:
        item = self.items.get(resource_id)
        if item is None:
            raise ValueError("resource does not exist")
        if owner is not None and item.owner != owner:
            raise PermissionError("owner mismatch")
        if expected_revision is not None and item.revision != expected_revision:
            raise ValueError("revision conflict")
        if content is not None:
            item.content = content
        if metadata is not None:
            item.metadata = metadata
        item.revision += 1
        return item

    def relate(
        self,
        source_resource_id: str,
        target_resource_id: str,
        relation: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if source_resource_id not in self.items or target_resource_id not in self.items:
            raise ValueError("resource does not exist")
        self.relationships.append(
            {
                "source_resource_id": source_resource_id,
                "target_resource_id": target_resource_id,
                "relation": relation,
                "metadata": metadata or {},
            }
        )

    def relations(self, resource_id: str) -> list[dict[str, Any]]:
        return [
            item
            for item in self.relationships
            if item["source_resource_id"] == resource_id
            or item["target_resource_id"] == resource_id
        ]


def test_resource_service_runs_against_non_sqlite_repository() -> None:
    repository = MemoryResourceRepository()
    service = ResourceService(repository)

    public = service.create("document", {"body": "public"}, visibility="public")
    private = service.create("document", {"body": "private"})

    assert service.get(public.id).content == {"body": "public"}
    assert service.list(include_private=False) == [public]
    with pytest.raises(PermissionError, match="private resource"):
        service.get(private.id, include_private=False)

    service.relate(public.id, private.id, "references")
    assert service.relations(public.id)[0]["relation"] == "references"


def test_resource_service_rejects_invalid_visibility_before_persistence() -> None:
    repository = MemoryResourceRepository()
    service = ResourceService(repository)

    with pytest.raises(ValueError, match="visibility"):
        service.create("document", visibility="world")

    assert repository.items == {}


def test_resource_service_validates_pagination_before_persistence() -> None:
    repository = MemoryResourceRepository()
    service = ResourceService(repository)

    with pytest.raises(ValueError, match="limit"):
        service.list(limit=0)
    with pytest.raises(ValueError, match="offset"):
        service.list(offset=-1)


def test_sqlite_backed_facade_satisfies_http_application_contract() -> None:
    db = AIDB(":memory:")
    try:
        assert isinstance(db, HomeApplication)
        resource = db.create_resource("document", {"body": "hello"})
        assert db.get_resource(resource.id).content == {"body": "hello"}
    finally:
        db.close()


def test_invalid_note_resource_update_rolls_back_all_resource_state() -> None:
    db = AIDB(":memory:")
    try:
        note = db.create_note("stable title", "before")
        with pytest.raises(ValueError, match="title and content"):
            db.update_resource(note.id, content={"incomplete": True})

        assert db.get_resource(note.id).content == {
            "title": "stable title",
            "content": "before",
            "kind": "note",
        }
        assert db.get_note(note.id).content == "before"
        assert db.get_resource(note.id).revision == 1
    finally:
        db.close()
