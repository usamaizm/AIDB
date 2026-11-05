"""Structural persistence ports for AIDB application and transport layers.

Adapters implement these protocols without inheriting from the SQLite-backed
AIDB class. The protocols describe observable operations, not schema or
connection details.
"""
from __future__ import annotations

from typing import Any, ContextManager, Protocol, runtime_checkable

from .core import Note, Resource


@runtime_checkable
class ResourceStore(Protocol):
    """Persistence contract for the resource/relationship vertical slice."""

    def create_resource(
        self,
        resource_type: str,
        content: Any = None,
        owner: str | None = None,
        visibility: str = "private",
        metadata: dict[str, Any] | None = None,
    ) -> Resource: ...

    def get_resource(
        self, resource_id: str, include_private: bool = True
    ) -> Resource: ...

    def list_resources(
        self,
        resource_type: str | None = None,
        visibility: str | None = None,
        include_private: bool = True,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Resource]: ...

    def update_resource(
        self,
        resource_id: str,
        content: Any = None,
        metadata: dict[str, Any] | None = None,
        owner: str | None = None,
        expected_revision: int | None = None,
    ) -> Resource: ...

    def relate_resources(
        self,
        source_resource_id: str,
        target_resource_id: str,
        relation: str,
        metadata: dict[str, Any] | None = None,
    ) -> None: ...

    def resource_relations(self, resource_id: str) -> list[dict[str, Any]]: ...


@runtime_checkable
class HomeStore(ResourceStore, Protocol):
    """Persistence operations required by the existing HTTP home adapter.

    operation_lock serializes multi-step operations when an adapter uses a
    shared connection. Backends with operation-level concurrency safety may
    expose a no-op context manager instead.
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

    def public_changes(
        self, after_id: int = 0, limit: int = 100
    ) -> list[dict[str, Any]]: ...
