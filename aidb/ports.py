"""Ports separating AIDB application behavior from persistence adapters.

The protocols describe behavior at the boundary. They deliberately contain no
SQLite types, SQL statements, table names, or backend identifiers.
"""
from __future__ import annotations

from typing import Any, ContextManager, Protocol, runtime_checkable

from .core import Note, Resource


@runtime_checkable
class ResourceRepository(Protocol):
    """Persistence operations required by the resource application service."""

    def create(self, resource: Resource) -> Resource: ...

    def get(self, resource_id: str) -> Resource | None: ...

    def list(
        self,
        resource_type: str | None = None,
        visibility: str | None = None,
        include_private: bool = True,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Resource]: ...

    def update(
        self,
        resource_id: str,
        content: Any = None,
        metadata: dict[str, Any] | None = None,
        owner: str | None = None,
        expected_revision: int | None = None,
    ) -> Resource: ...

    def relate(
        self,
        source_resource_id: str,
        target_resource_id: str,
        relation: str,
        metadata: dict[str, Any] | None = None,
    ) -> None: ...

    def relations(self, resource_id: str) -> list[dict[str, Any]]: ...


@runtime_checkable
class HomeApplication(Protocol):
    """Operations consumed by the current HTTP transport adapter.

    The operation lock is a concurrency boundary for adapters sharing a
    non-thread-local session. Transports do not need to know its implementation.
    """

    @property
    def operation_lock(self) -> ContextManager[Any]: ...

    def specification_dict(self) -> dict[str, Any]: ...

    def list_notes(
        self,
        owner: str | None = None,
        visibility: str | None = None,
        include_private: bool = True,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Note]: ...

    def create_note(
        self,
        title: str,
        content: str,
        owner: str | None = None,
        visibility: str = "private",
        kind: str = "note",
        metadata: dict[str, Any] | None = None,
    ) -> Note: ...

    def create_resource(
        self,
        resource_type: str,
        content: Any = None,
        owner: str | None = None,
        visibility: str = "private",
        metadata: dict[str, Any] | None = None,
    ) -> Resource: ...

    def list_resources(
        self,
        resource_type: str | None = None,
        visibility: str | None = None,
        include_private: bool = True,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Resource]: ...

    def relate_resources(
        self,
        source_resource_id: str,
        target_resource_id: str,
        relation: str,
        metadata: dict[str, Any] | None = None,
    ) -> None: ...

    def public_changes(self, after_id: int = 0, limit: int = 100) -> list[dict[str, Any]]: ...
