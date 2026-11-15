"""SQLite implementation of the resource repository port.

This module owns SQL representation and transaction details. It does not
contain the resource application service or import the AIDB façade.
"""
from __future__ import annotations

import json
import sqlite3
from uuid import uuid4
from collections.abc import Callable
from typing import Any, ContextManager

from ...core import Resource


class SQLiteResourceRepository:
    def __init__(
        self,
        connection: sqlite3.Connection,
        lock: ContextManager[Any],
        record_event: Callable[..., Any],
    ) -> None:
        self._db = connection
        self._lock = lock
        self._record_event = record_event

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value if value is not None else {})

    @staticmethod
    def _from_row(row: sqlite3.Row) -> Resource:
        return Resource(
            resource_type=row["resource_type"],
            content=json.loads(row["content"]),
            owner=row["owner"],
            visibility=row["visibility"],
            metadata=json.loads(row["metadata"]),
            id=row["id"],
            revision=row["revision"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _begin(self) -> None:
        self._db.execute("SAVEPOINT aidb_resource_mutation")

    def _rollback(self) -> None:
        self._db.execute("ROLLBACK TO SAVEPOINT aidb_resource_mutation")
        self._db.execute("RELEASE SAVEPOINT aidb_resource_mutation")

    def _commit(self) -> None:
        self._db.execute("RELEASE SAVEPOINT aidb_resource_mutation")

    def create(self, resource: Resource) -> Resource:
        with self._lock:
            self._begin()
            try:
                self._db.execute(
                    "INSERT INTO home_resources(id,resource_type,content,owner,visibility,metadata) "
                    "VALUES(?,?,?,?,?,?)",
                    (
                        resource.id,
                        resource.resource_type,
                        json.dumps(resource.content),
                        resource.owner,
                        resource.visibility,
                        self._json(resource.metadata),
                    ),
                )
                self._record_event(
                    "resource_created",
                    "resource created",
                    metadata={
                        "resource_id": resource.id,
                        "resource_type": resource.resource_type,
                        "owner": resource.owner,
                        "visibility": resource.visibility,
                    },
                )
                self._db.execute(
                    "INSERT INTO home_changes(change_id,resource_id,operation,actor,new_revision,payload) "
                    "VALUES(?,?,?,?,?,?)",
                    (
                        "chg:" + str(uuid4()),
                        resource.id,
                        "create",
                        resource.owner,
                        1,
                        self._json(
                            {
                                "resource_type": resource.resource_type,
                                "visibility": resource.visibility,
                            }
                        ),
                    ),
                )
                self._commit()
            except Exception:
                self._rollback()
                raise
            return self.get(resource.id)

    def get(self, resource_id: str) -> Resource | None:
        with self._lock:
            row = self._db.execute(
                "SELECT * FROM home_resources WHERE id=?", (resource_id,)
            ).fetchone()
            return self._from_row(row) if row is not None else None

    def list(
        self,
        resource_type: str | None = None,
        visibility: str | None = None,
        include_private: bool = True,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Resource]:
        clauses: list[str] = []
        params: list[Any] = []
        if resource_type:
            clauses.append("resource_type=?")
            params.append(resource_type)
        if visibility:
            clauses.append("visibility=?")
            params.append(visibility)
        elif not include_private:
            clauses.append("visibility='public'")
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = "SELECT * FROM home_resources" + where + " ORDER BY updated_at DESC, id ASC"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        if offset:
            if limit is None:
                sql += " LIMIT -1"
            sql += " OFFSET ?"
            params.append(offset)
        with self._lock:
            rows = self._db.execute(sql, params).fetchall()
            return [self._from_row(row) for row in rows]

    def update(
        self,
        resource_id: str,
        content: Any = None,
        metadata: dict[str, Any] | None = None,
        owner: str | None = None,
        expected_revision: int | None = None,
    ) -> Resource:
        with self._lock:
            row = self._db.execute(
                "SELECT * FROM home_resources WHERE id=?", (resource_id,)
            ).fetchone()
            if row is None:
                raise ValueError("resource does not exist")
            if owner is not None and row["owner"] != owner:
                raise PermissionError("owner mismatch")
            if expected_revision is not None and row["revision"] != expected_revision:
                raise ValueError("revision conflict")

            old_revision = row["revision"]
            new_metadata = json.loads(row["metadata"]) if metadata is None else metadata
            new_content = json.loads(row["content"]) if content is None else content
            self._begin()
            try:
                self._db.execute(
                    "UPDATE home_resources SET content=?, metadata=?, revision=revision+1, "
                    "updated_at=strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id=?",
                    (json.dumps(new_content), self._json(new_metadata), resource_id),
                )
                note = self._db.execute(
                    "SELECT * FROM notes WHERE resource_id=?", (resource_id,)
                ).fetchone()
                if note is not None:
                    if isinstance(new_content, dict):
                        if not {"title", "content"}.issubset(new_content):
                            raise ValueError(
                                "note resource content must include title and content"
                            )
                        note_title = new_content["title"]
                        note_content = new_content["content"]
                        note_kind = new_content.get("kind", note["kind"])
                    else:
                        # Retain the legacy shorthand: a scalar update replaces
                        # the note body but preserves its title and kind.
                        note_title = note["title"]
                        note_content = new_content
                        note_kind = note["kind"]
                        new_content = {
                            "title": note_title,
                            "content": note_content,
                            "kind": note_kind,
                        }
                        self._db.execute(
                            "UPDATE home_resources SET content=? WHERE id=?",
                            (json.dumps(new_content), resource_id),
                        )
                    self._db.execute(
                        "UPDATE notes SET title=?, content=?, kind=?, metadata=?, "
                        "revision=revision+1, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ', 'now') "
                        "WHERE resource_id=?",
                        (
                            note_title,
                            note_content,
                            note_kind,
                            self._json(new_metadata),
                            resource_id,
                        ),
                    )
                self._db.execute(
                    "INSERT INTO home_changes(change_id,resource_id,operation,actor,"
                    "previous_revision,new_revision,payload) VALUES(?,?,?,?,?,?,?)",
                    (
                        "chg:" + str(uuid4()),
                        resource_id,
                        "update",
                        owner or row["owner"],
                        old_revision,
                        old_revision + 1,
                        self._json(
                            {
                                "content_changed": content is not None,
                                "metadata_changed": metadata is not None,
                            }
                        ),
                    ),
                )
                self._commit()
            except Exception:
                self._rollback()
                raise
            updated = self.get(resource_id)
            assert updated is not None
            return updated

    def relate(
        self,
        source_resource_id: str,
        target_resource_id: str,
        relation: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            for resource_id in (source_resource_id, target_resource_id):
                if (
                    self._db.execute(
                        "SELECT 1 FROM home_resources WHERE id=?", (resource_id,)
                    ).fetchone()
                    is None
                ):
                    raise ValueError("resource does not exist: " + resource_id)
            self._begin()
            try:
                self._db.execute(
                    "INSERT OR IGNORE INTO resource_relations"
                    "(source_resource_id,target_resource_id,relation,metadata) "
                    "VALUES(?,?,?,?)",
                    (
                        source_resource_id,
                        target_resource_id,
                        relation,
                        self._json(metadata or {}),
                    ),
                )
                self._db.execute(
                    "INSERT INTO home_changes(change_id,resource_id,operation,actor,payload) "
                    "VALUES(?,?,?,?,?)",
                    (
                        "chg:" + str(uuid4()),
                        source_resource_id,
                        "relate",
                        None,
                        self._json(
                            {
                                "target_resource_id": target_resource_id,
                                "relation": relation,
                            }
                        ),
                    ),
                )
                self._commit()
            except Exception:
                self._rollback()
                raise

    def relations(self, resource_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._db.execute(
                "SELECT * FROM resource_relations WHERE source_resource_id=? "
                "OR target_resource_id=? ORDER BY id ASC",
                (resource_id, resource_id),
            ).fetchall()
            return [dict(row) for row in rows]
