from __future__ import annotations

import json
import sqlite3
import uuid
from math import sqrt
from pathlib import Path
from typing import Any

from .core import (
    Agent,
    KnowledgeRecord,
    Memory,
    Message,
    Session,
    Task,
    Tool,
    ToolCall,
    WorkflowEvent,
)


class AIDB:
    """SQLite-backed state layer for AI agents, sessions, tasks, memory, tools, and workflow events."""

    def __init__(self, path: str | Path = "aidb.sqlite3"):
        self.path = str(path)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self) -> None:
        self.db.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS agents (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                model TEXT,
                role TEXT NOT NULL DEFAULT 'agent',
                permissions TEXT NOT NULL DEFAULT '[]',
                capabilities TEXT NOT NULL DEFAULT '[]',
                metadata TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                metadata TEXT NOT NULL DEFAULT '{}',
                created_by INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'active',
                FOREIGN KEY(created_by) REFERENCES agents(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS session_participants (
                id INTEGER PRIMARY KEY,
                session_id TEXT NOT NULL,
                agent_id INTEGER NOT NULL,
                joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(session_id, agent_id),
                FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
                FOREIGN KEY(agent_id) REFERENCES agents(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY,
                agent_id INTEGER,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT NOT NULL DEFAULT '[]',
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(agent_id) REFERENCES agents(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY,
                agent_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                kind TEXT NOT NULL DEFAULT 'fact',
                importance REAL NOT NULL DEFAULT 0.5,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(agent_id) REFERENCES agents(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS tools (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                schema TEXT NOT NULL DEFAULT '{}',
                endpoint TEXT
            );

            CREATE TABLE IF NOT EXISTS tool_calls (
                id INTEGER PRIMARY KEY,
                agent_id INTEGER,
                tool_name TEXT NOT NULL,
                arguments TEXT NOT NULL DEFAULT '{}',
                result TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'success',
                session_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(agent_id) REFERENCES agents(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                assigned_to INTEGER,
                status TEXT NOT NULL DEFAULT 'queued',
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                depends_on INTEGER,
                priority INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(assigned_to) REFERENCES agents(id) ON DELETE SET NULL,
                FOREIGN KEY(depends_on) REFERENCES tasks(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS workflow_events (
                id INTEGER PRIMARY KEY,
                kind TEXT NOT NULL,
                message TEXT NOT NULL DEFAULT '',
                agent_id INTEGER,
                task_id INTEGER,
                session_id TEXT,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(agent_id) REFERENCES agents(id) ON DELETE SET NULL,
                FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE SET NULL,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY,
                agent_id INTEGER,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                session_id TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(agent_id) REFERENCES agents(id) ON DELETE SET NULL,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS message_reads (
                id INTEGER PRIMARY KEY,
                message_id INTEGER NOT NULL,
                agent_id INTEGER NOT NULL,
                read_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(message_id, agent_id),
                FOREIGN KEY(message_id) REFERENCES messages(id) ON DELETE CASCADE,
                FOREIGN KEY(agent_id) REFERENCES agents(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id);
            CREATE INDEX IF NOT EXISTS idx_messages_agent ON messages(agent_id, id);
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status, updated_at);
            """
        )
        self.db.commit()

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value if value is not None else {})

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [part.lower() for part in text.replace("-", " ").replace("/", " ").split() if part]

    @staticmethod
    def _embedding(text: str) -> dict[str, float]:
        counts: dict[str, float] = {}
        for token in AIDB._tokenize(text):
            counts[token] = counts.get(token, 0.0) + 1.0
        return counts

    @staticmethod
    def _cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
        vocab = set(a) | set(b)
        if not vocab:
            return 0.0
        dot = sum(a.get(token, 0.0) * b.get(token, 0.0) for token in vocab)
        mag_a = sqrt(sum(value * value for value in a.values()))
        mag_b = sqrt(sum(value * value for value in b.values()))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)

    def register_agent(
        self,
        name: str,
        description: str = "",
        model: str = "",
        role: str = "agent",
        permissions: list[str] | None = None,
        capabilities: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Agent:
        cur = self.db.execute(
            "INSERT INTO agents(name, description, model, role, permissions, capabilities, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                name,
                description,
                model,
                role,
                self._json(permissions or []),
                self._json(capabilities or []),
                self._json(metadata or {}),
            ),
        )
        self.db.commit()
        return Agent(
            name,
            description,
            model,
            role,
            permissions or [],
            capabilities or [],
            metadata or {},
            cur.lastrowid,
        )

    def list_agents(self) -> list[Agent]:
        rows = self.db.execute("SELECT * FROM agents ORDER BY name").fetchall()
        return [
            Agent(
                r["name"],
                r["description"] or "",
                r["model"] or "",
                r["role"],
                json.loads(r["permissions"]),
                json.loads(r["capabilities"]),
                json.loads(r["metadata"]),
                r["id"],
            )
            for r in rows
        ]

    def require_permission(self, agent_id: int, permission: str) -> bool:
        row = self.db.execute("SELECT permissions FROM agents WHERE id = ?", (agent_id,)).fetchone()
        if row is None:
            return False
        permissions = json.loads(row["permissions"])
        return permission in permissions or "*" in permissions

    def create_session(
        self,
        title: str,
        description: str = "",
        metadata: dict[str, Any] | None = None,
        created_by: int | None = None,
        session_id: str | None = None,
        status: str = "active",
    ) -> Session:
        key = session_id or uuid.uuid4().hex
        self.db.execute(
            "INSERT INTO sessions(session_id, title, description, metadata, created_by, status) VALUES (?, ?, ?, ?, ?, ?)",
            (key, title, description, self._json(metadata or {}), created_by, status),
        )
        self.db.commit()
        if created_by is not None:
            self.join_session(key, created_by)
        return Session(key, title, description, metadata or {}, created_by, None, status)

    def update_session_status(self, session_id: str, status: str) -> Session:
        self.db.execute("UPDATE sessions SET status = ? WHERE session_id = ?", (status, session_id))
        self.db.commit()
        row = self.db.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        return self._session_from_row(row)

    def join_session(self, session_id: str, agent_id: int) -> None:
        self.db.execute(
            "INSERT OR IGNORE INTO session_participants(session_id, agent_id) VALUES (?, ?)",
            (session_id, agent_id),
        )
        self.db.commit()

    def list_sessions(self) -> list[Session]:
        rows = self.db.execute("SELECT * FROM sessions ORDER BY created_at DESC").fetchall()
        return [self._session_from_row(row) for row in rows]

    def session_members(self, session_id: str) -> list[Agent]:
        rows = self.db.execute(
            "SELECT a.* FROM agents a INNER JOIN session_participants sp ON sp.agent_id = a.id WHERE sp.session_id = ? ORDER BY a.name",
            (session_id,),
        ).fetchall()
        return [
            Agent(
                r["name"],
                r["description"] or "",
                r["model"] or "",
                r["role"],
                json.loads(r["permissions"]),
                json.loads(r["capabilities"]),
                json.loads(r["metadata"]),
                r["id"],
            )
            for r in rows
        ]

    def add_document(
        self,
        title: str,
        content: str,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        agent_id: int | None = None,
    ) -> KnowledgeRecord:
        cur = self.db.execute(
            "INSERT INTO knowledge(agent_id, title, content, tags, metadata) VALUES (?, ?, ?, ?, ?)",
            (agent_id, title, content, self._json(tags or []), self._json(metadata or {})),
        )
        self.db.commit()
        return KnowledgeRecord(title, content, tags or [], metadata or {}, 0.0, cur.lastrowid, agent_id)

    def search(self, query: str, limit: int = 10) -> list[KnowledgeRecord]:
        rows = self.db.execute("SELECT * FROM knowledge ORDER BY id DESC").fetchall()
        tokens = set(query.lower().split())
        scored: list[KnowledgeRecord] = []
        for row in rows:
            text = f'{row["title"]} {row["content"]} {row["tags"]}'.lower()
            score = sum(token in text for token in tokens)
            if score or not tokens:
                scored.append(
                    KnowledgeRecord(
                        row["title"],
                        row["content"],
                        json.loads(row["tags"]),
                        json.loads(row["metadata"]),
                        score,
                        row["id"],
                        row["agent_id"],
                    )
                )
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:limit]

    def semantic_search(self, query: str, limit: int = 10, threshold: float = 0.0) -> list[KnowledgeRecord]:
        q_vector = self._embedding(query)
        rows = self.db.execute("SELECT * FROM knowledge ORDER BY id DESC").fetchall()
        scored: list[KnowledgeRecord] = []
        for row in rows:
            text = f"{row['title']} {row['content']}"
            vector = self._embedding(text)
            score = self._cosine_similarity(q_vector, vector)
            if score >= threshold:
                scored.append(
                    KnowledgeRecord(
                        row["title"],
                        row["content"],
                        json.loads(row["tags"]),
                        json.loads(row["metadata"]),
                        score,
                        row["id"],
                        row["agent_id"],
                    )
                )
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:limit]

    def remember(
        self,
        agent_id: int,
        content: str,
        kind: str = "fact",
        importance: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> Memory:
        cur = self.db.execute(
            "INSERT INTO memories(agent_id, content, kind, importance, metadata) VALUES (?, ?, ?, ?, ?)",
            (agent_id, content, kind, importance, self._json(metadata or {})),
        )
        self.db.commit()
        return Memory(agent_id, content, kind, importance, metadata or {}, cur.lastrowid)

    def recall(self, agent_id: int, query: str = "", limit: int = 20) -> list[Memory]:
        rows = self.db.execute(
            "SELECT * FROM memories WHERE agent_id=? ORDER BY importance DESC, id DESC",
            (agent_id,),
        ).fetchall()
        tokens = set(query.lower().split())
        results: list[Memory] = []
        for row in rows:
            if not tokens or tokens & set(row["content"].lower().split()):
                results.append(
                    Memory(
                        row["agent_id"],
                        row["content"],
                        row["kind"],
                        row["importance"],
                        json.loads(row["metadata"]),
                        row["id"],
                    )
                )
            if len(results) >= limit:
                break
        return results

    def register_tool(
        self,
        name: str,
        description: str = "",
        schema: dict[str, Any] | None = None,
        endpoint: str | None = None,
    ) -> Tool:
        cur = self.db.execute(
            "INSERT INTO tools(name, description, schema, endpoint) VALUES (?, ?, ?, ?)",
            (name, description, self._json(schema or {}), endpoint),
        )
        self.db.commit()
        return Tool(name, description, schema or {}, endpoint, cur.lastrowid)

    def log_tool_call(
        self,
        agent_id: int | None,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        result: Any = None,
        status: str = "success",
        session_id: str | None = None,
    ) -> ToolCall:
        cur = self.db.execute(
            "INSERT INTO tool_calls(agent_id, tool_name, arguments, result, status, session_id) VALUES (?, ?, ?, ?, ?, ?)",
            (agent_id, tool_name, self._json(arguments or {}), self._json(result if result is not None else {}), status, session_id),
        )
        self.db.commit()
        row = self.db.execute("SELECT * FROM tool_calls WHERE id=?", (cur.lastrowid,)).fetchone()
        return self._tool_call_from_row(row)

    def list_tool_calls(self, agent_id: int | None = None, tool_name: str | None = None) -> list[ToolCall]:
        if agent_id is not None and tool_name is not None:
            rows = self.db.execute(
                "SELECT * FROM tool_calls WHERE agent_id=? AND tool_name=? ORDER BY id DESC",
                (agent_id, tool_name),
            ).fetchall()
        elif agent_id is not None:
            rows = self.db.execute(
                "SELECT * FROM tool_calls WHERE agent_id=? ORDER BY id DESC",
                (agent_id,),
            ).fetchall()
        elif tool_name is not None:
            rows = self.db.execute(
                "SELECT * FROM tool_calls WHERE tool_name=? ORDER BY id DESC",
                (tool_name,),
            ).fetchall()
        else:
            rows = self.db.execute("SELECT * FROM tool_calls ORDER BY id DESC").fetchall()
        return [self._tool_call_from_row(row) for row in rows]

    def add_event(
        self,
        kind: str,
        message: str = "",
        agent_id: int | None = None,
        task_id: int | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowEvent:
        cur = self.db.execute(
            "INSERT INTO workflow_events(kind, message, agent_id, task_id, session_id, metadata) VALUES (?, ?, ?, ?, ?, ?)",
            (kind, message, agent_id, task_id, session_id, self._json(metadata or {})),
        )
        self.db.commit()
        row = self.db.execute("SELECT * FROM workflow_events WHERE id=?", (cur.lastrowid,)).fetchone()
        return self._event_from_row(row)

    def list_events(self, task_id: int | None = None, session_id: str | None = None) -> list[WorkflowEvent]:
        if task_id is not None:
            rows = self.db.execute(
                "SELECT * FROM workflow_events WHERE task_id=? ORDER BY id DESC",
                (task_id,),
            ).fetchall()
        elif session_id is not None:
            rows = self.db.execute(
                "SELECT * FROM workflow_events WHERE session_id=? ORDER BY id DESC",
                (session_id,),
            ).fetchall()
        else:
            rows = self.db.execute("SELECT * FROM workflow_events ORDER BY id DESC").fetchall()
        return [self._event_from_row(row) for row in rows]

    def create_task(
        self,
        title: str,
        description: str = "",
        assigned_to: int | None = None,
        status: str = "queued",
        metadata: dict[str, Any] | None = None,
        depends_on: int | None = None,
        priority: int = 0,
    ) -> Task:
        cur = self.db.execute(
            "INSERT INTO tasks(title, description, assigned_to, status, metadata, depends_on, priority, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
            (title, description, assigned_to, status, self._json(metadata or {}), depends_on, priority),
        )
        self.db.commit()
        row = self.db.execute("SELECT * FROM tasks WHERE id=?", (cur.lastrowid,)).fetchone()
        return self._task_from_row(row)

    def update_task_status(self, task_id: int, status: str) -> Task:
        self.db.execute(
            "UPDATE tasks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, task_id),
        )
        self.db.commit()
        row = self.db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return self._task_from_row(row)

    def list_tasks(self, assigned_to: int | None = None) -> list[Task]:
        if assigned_to is None:
            rows = self.db.execute("SELECT * FROM tasks ORDER BY priority DESC, updated_at DESC").fetchall()
        else:
            rows = self.db.execute(
                "SELECT * FROM tasks WHERE assigned_to=? ORDER BY priority DESC, updated_at DESC",
                (assigned_to,),
            ).fetchall()
        return [self._task_from_row(row) for row in rows]

    def ready_tasks(self, agent_id: int | None = None) -> list[Task]:
        rows = self.db.execute(
            "SELECT * FROM tasks WHERE status = 'queued' ORDER BY priority DESC, id DESC"
        ).fetchall()
        ready: list[Task] = []
        for row in rows:
            if row["depends_on"] is None:
                if agent_id is None or row["assigned_to"] == agent_id:
                    ready.append(self._task_from_row(row))
                continue
            parent = self.db.execute("SELECT status FROM tasks WHERE id = ?", (row["depends_on"],)).fetchone()
            if parent is not None and parent["status"] == "completed":
                if agent_id is None or row["assigned_to"] == agent_id:
                    ready.append(self._task_from_row(row))
        return ready

    def send_message(
        self,
        sender_id: int,
        content: str,
        session_id: str,
        role: str = "assistant",
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        self.db.execute(
            "INSERT OR IGNORE INTO sessions(session_id, title) VALUES (?, '')",
            (session_id,),
        )
        self.db.commit()
        cur = self.db.execute(
            "INSERT INTO messages(agent_id, role, content, session_id, metadata) VALUES (?, ?, ?, ?, ?)",
            (sender_id, role, content, session_id, self._json(metadata or {})),
        )
        self.db.commit()
        row = self.db.execute("SELECT * FROM messages WHERE id=?", (cur.lastrowid,)).fetchone()
        return self._message_from_row(row)

    def broadcast(self, sender_id: int, content: str, session_id: str, metadata: dict[str, Any] | None = None) -> Message:
        return self.send_message(sender_id, content, session_id, "broadcast", metadata)

    def mark_message_read(self, agent_id: int, message_id: int) -> None:
        self.db.execute(
            "INSERT OR IGNORE INTO message_reads(message_id, agent_id) VALUES (?, ?)",
            (message_id, agent_id),
        )
        self.db.commit()

    def unread_messages(self, agent_id: int, session_id: str | None = None, limit: int = 50) -> list[Message]:
        if session_id is None:
            rows = self.db.execute(
                "SELECT m.* FROM messages m LEFT JOIN message_reads mr ON mr.message_id = m.id AND mr.agent_id = ? WHERE m.agent_id != ? AND mr.id IS NULL ORDER BY m.id DESC LIMIT ?",
                (agent_id, agent_id, limit),
            ).fetchall()
        else:
            rows = self.db.execute(
                "SELECT m.* FROM messages m LEFT JOIN message_reads mr ON mr.message_id = m.id AND mr.agent_id = ? WHERE m.session_id = ? AND m.agent_id != ? AND mr.id IS NULL ORDER BY m.id DESC LIMIT ?",
                (agent_id, session_id, agent_id, limit),
            ).fetchall()
        return [self._message_from_row(row) for row in rows]

    def receive(self, agent_id: int, session_id: str | None = None, after_id: int = 0, limit: int = 50) -> list[Message]:
        if session_id is None:
            rows = self.db.execute(
                "SELECT * FROM messages WHERE id > ? AND agent_id != ? ORDER BY id LIMIT ?",
                (after_id, agent_id, limit),
            ).fetchall()
        else:
            rows = self.db.execute(
                "SELECT * FROM messages WHERE session_id=? AND id > ? AND agent_id != ? ORDER BY id LIMIT ?",
                (session_id, after_id, agent_id, limit),
            ).fetchall()
        return [self._message_from_row(row) for row in rows]

    def conversation(self, session_id: str, limit: int = 100) -> list[Message]:
        rows = self.db.execute(
            "SELECT * FROM messages WHERE session_id=? ORDER BY id LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return [self._message_from_row(row) for row in rows]

    def _session_from_row(self, row: sqlite3.Row) -> Session:
        return Session(
            row["session_id"],
            row["title"],
            row["description"],
            json.loads(row["metadata"]),
            row["created_by"],
            row["created_at"],
            row["status"],
        )

    def _task_from_row(self, row: sqlite3.Row) -> Task:
        return Task(
            title=row["title"],
            description=row["description"],
            assigned_to=row["assigned_to"],
            status=row["status"],
            metadata=json.loads(row["metadata"]),
            id=row["id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            depends_on=row["depends_on"],
            priority=row["priority"],
        )

    def _tool_call_from_row(self, row: sqlite3.Row) -> ToolCall:
        return ToolCall(
            agent_id=row["agent_id"],
            tool_name=row["tool_name"],
            arguments=json.loads(row["arguments"]),
            result=json.loads(row["result"]),
            status=row["status"],
            session_id=row["session_id"],
            id=row["id"],
            created_at=row["created_at"],
        )

    def _event_from_row(self, row: sqlite3.Row) -> WorkflowEvent:
        return WorkflowEvent(
            kind=row["kind"],
            message=row["message"],
            agent_id=row["agent_id"],
            task_id=row["task_id"],
            session_id=row["session_id"],
            metadata=json.loads(row["metadata"]),
            id=row["id"],
            created_at=row["created_at"],
        )

    def _message_from_row(self, row: sqlite3.Row) -> Message:
        return Message(
            row["role"],
            row["content"],
            row["agent_id"],
            row["session_id"],
            json.loads(row["metadata"]),
            row["id"],
            row["created_at"],
        )

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> "AIDB":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
