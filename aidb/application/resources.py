"""Storage-independent resource use cases."""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from ..core import Resource
from ..ports import ResourceRepository


class ResourceService:
    """Owns resource use-case rules and delegates durable state to a port."""

    def __init__(self, repository: ResourceRepository) -> None:
        self._repository = repository

    def create(
        self,
        resource_type: str,
        content: Any = None,
        owner: str | None = None,
        visibility: str = "private",
        metadata: dict[str, Any] | None = None,
    ) -> Resource:
        if visibility not in {"public", "private"}:
            raise ValueError("visibility must be public or private")
        resource = Resource(
            resource_type=resource_type,
            content=content,
            owner=owner,
            visibility=visibility,
            metadata=metadata or {},
            id="res:" + str(uuid4()),
        )
        return self._repository.create(resource)

    def get(self, resource_id: str, include_private: bool = True) -> Resource:
        resource = self._repository.get(resource_id)
        if resource is None:
            raise ValueError("resource does not exist")
        if resource.visibility == "private" and not include_private:
            raise PermissionError("private resource")
        return resource

    def list(
        self,
        resource_type: str | None = None,
        visibility: str | None = None,
        include_private: bool = True,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Resource]:
        if limit is not None and (not isinstance(limit, int) or limit < 1):
            raise ValueError("limit must be a positive integer")
        if not isinstance(offset, int) or offset < 0:
            raise ValueError("offset must be a non-negative integer")
        return self._repository.list(
            resource_type=resource_type,
            visibility=visibility,
            include_private=include_private,
            limit=limit,
            offset=offset,
        )

    def update(
        self,
        resource_id: str,
        content: Any = None,
        metadata: dict[str, Any] | None = None,
        owner: str | None = None,
        expected_revision: int | None = None,
    ) -> Resource:
        return self._repository.update(
            resource_id,
            content=content,
            metadata=metadata,
            owner=owner,
            expected_revision=expected_revision,
        )

    def relate(
        self,
        source_resource_id: str,
        target_resource_id: str,
        relation: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if source_resource_id == target_resource_id:
            raise ValueError("a resource cannot relate to itself")
        self._repository.relate(
            source_resource_id, target_resource_id, relation, metadata
        )

    def relations(self, resource_id: str) -> list[dict[str, Any]]:
        return self._repository.relations(resource_id)
