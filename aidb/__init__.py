from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from .core import Agent, KnowledgeRecord, Memory, Message, Session, Task, Tool, ToolCall


class AIDB:
    """SQLite-backed state layer for agents, sessions, tasks, memory, tools, and tool-call auditing."""

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
                FOREIGN KEY(assigned_to) REFERENCES agents(id) ON DELETE SET NULL
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

    def register_agent(
        self,
        name: str,
        description: str = "",
        model: str = "",
        capabilities: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Agent:
        cur = self.db.execute(
            "INSERT INTO agents(name, description, model, capabilities, metadata) VALUES (?, ?, ?, ?, ?)",
            (name, description, model, self._json(capabilities or []), self._json(metadata or {})),
        )
        self.db.commit()
        return Agent(name, description, model, capabilities or [], metadata or {}, cur.lastrowid)

    def list_agents(self) -> list[Agent]:
        rows = self.db.execute("SELECT * FROM agents ORDER BY name").fetchall()
        return [
            Agent(
                r["name"],
                r["description"] or "",
                r["model"] or "",
                json.loads(r["capabilities"]),
                json.loads(r["metadata"]),
                r["id"],
            )
            for r in rows
        ]

    def create_session(
        self,
        title: str,
        description: str = "",
        metadata: dict[str, Any] | None = None,
        created_by: int | None = None,
        session_id: str | None = None,
    ) -> Session:
        key = session_id or uuid.uuid4().hex
        self.db.execute(
            "INSERT INTO sessions(session_id, title, description, metadata, created_by) VALUES (?, ?, ?, ?, ?)",
            (key, title, description, self._json(metadata or {}), created_by),
        )
        self.db.commit()
        if created_by is not None:
            self.join_session(key, created_by)
        return Session(key, title, description, metadata or {}, created_by)

    def join_session(self, session_id: str, agent_id: int) -> None:
        self.db.execute(
            "INSERT OR IGNORE INTO session_participants(session_id, agent_id) VALUES (?, ?)",
            (session_id, agent_id),
        )
        self.db.commit()

    def list_sessions(self) -> list[Session]:
        rows = self.db.execute("SELECT * FROM sessions ORDER BY created_at DESC").fetchall()
        return [
            Session(
                r["session_id"],
                r["title"],
                r["description"],
                json.loads(r["metadata"]),
                r["created_by"],
                r["created_at"],
            )
            for r in rows
        ]

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

    def create_task(
        self,
        title: str,
        description: str = "",
        assigned_to: int | None = None,
        status: str = "queued",
        metadata: dict[str, Any] | None = None,
    ) -> Task:
        cur = self.db.execute(
            "INSERT INTO tasks(title, description, assigned_to, status, metadata, updated_at) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
            (title, description, assigned_to, status, self._json(metadata or {})),
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
            rows = self.db.execute("SELECT * FROM tasks ORDER BY updated_at DESC").fetchall()
        else:
            rows = self.db.execute(
                "SELECT * FROM tasks WHERE assigned_to=? ORDER BY updated_at DESC",
                (assigned_to,),
            ).fetchall()
        return [self._task_from_row(row) for row in rows]

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
