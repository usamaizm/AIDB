from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from .core import Agent, KnowledgeRecord, Memory, Message, Session, Task, Tool


class AIDB:
    """SQLite-backed registry, memory store, task system, and message bus for AI agents."""

    def __init__(self, path: str | Path = "aidb.sqlite3"):
        self.path = str(path)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self) -> None:
        self.db.executescript("""
        PRAGMA foreign_keys = ON;
        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, description TEXT,
            model TEXT, capabilities TEXT NOT NULL DEFAULT '[]', metadata TEXT NOT NULL DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY, title TEXT NOT NULL DEFAULT '', description TEXT NOT NULL DEFAULT '',
            metadata TEXT NOT NULL DEFAULT '{}', created_by INTEGER, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(created_by) REFERENCES agents(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS session_participants (
            id INTEGER PRIMARY KEY, session_id TEXT NOT NULL, agent_id INTEGER NOT NULL,
            joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(session_id, agent_id),
            FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
            FOREIGN KEY(agent_id) REFERENCES agents(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY, agent_id INTEGER, title TEXT NOT NULL, content TEXT NOT NULL,
            tags TEXT NOT NULL DEFAULT '[]', metadata TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(agent_id) REFERENCES agents(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY, agent_id INTEGER NOT NULL, content TEXT NOT NULL,
            kind TEXT NOT NULL DEFAULT 'fact', importance REAL NOT NULL DEFAULT 0.5,
            metadata TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(agent_id) REFERENCES agents(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS tools (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, description TEXT,
            schema TEXT NOT NULL DEFAULT '{}', endpoint TEXT
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
            assigned_to INTEGER, status TEXT NOT NULL DEFAULT 'queued', metadata TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(assigned_to) REFERENCES agents(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY, agent_id INTEGER, role TEXT NOT NULL, content TEXT NOT NULL,
            session_id TEXT NOT NULL, metadata TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(agent_id) REFERENCES agents(id) ON DELETE SET NULL,
            FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS messages_session_idx ON messages(session_id, id);
        CREATE INDEX IF NOT EXISTS messages_agent_idx ON messages(agent_id, id);
        CREATE INDEX IF NOT EXISTS tasks_status_idx ON tasks(status, updated_at);
        """)
        self.db.commit()

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value if value is not None else {})

    def register_agent(self, name: str, description: str = "", model: str = "",
                       capabilities: list[str] | None = None,
                       metadata: dict[str, Any] | None = None) -> Agent:
        cur = self.db.execute(
            "INSERT INTO agents(name,description,model,capabilities,metadata) VALUES(?,?,?,?,?)",
            (name, description, model, self._json(capabilities or []), self._json(metadata or {})),
        )
        self.db.commit()
        return Agent(name, description, model, capabilities or [], metadata or {}, cur.lastrowid)

    def list_agents(self) -> list[Agent]:
        rows = self.db.execute("SELECT * FROM agents ORDER BY name").fetchall()
        return [
            Agent(r["name"], r["description"] or "", r["model"] or "",
                  json.loads(r["capabilities"]), json.loads(r["metadata"]), r["id"])
            for r in rows
        ]

    def create_session(self, title: str, description: str = "", metadata: dict[str, Any] | None = None,
                       created_by: int | None = None, session_id: str | None = None) -> Session:
        session_key = session_id or uuid.uuid4().hex
        self.db.execute(
            "INSERT INTO sessions(session_id,title,description,metadata,created_by) VALUES(?,?,?,?,?)",
            (session_key, title, description, self._json(metadata or {}), created_by),
        )
        self.db.commit()
        if created_by is not None:
            self.join_session(session_key, created_by)
        return Session(session_key, title, description, metadata or {}, created_by)

    def join_session(self, session_id: str, agent_id: int) -> None:
        self.db.execute(
            "INSERT OR IGNORE INTO session_participants(session_id, agent_id) VALUES(?, ?)",
            (session_id, agent_id),
        )
        self.db.commit()

    def list_sessions(self) -> list[Session]:
        rows = self.db.execute("SELECT * FROM sessions ORDER BY created_at DESC").fetchall()
        return [
            Session(r["session_id"], r["title"], r["description"], json.loads(r["metadata"]), r["created_by"], r["created_at"])
            for r in rows
        ]

    def session_members(self, session_id: str) -> list[Agent]:
        rows = self.db.execute(
            "SELECT a.* FROM agents a INNER JOIN session_participants sp ON sp.agent_id = a.id WHERE sp.session_id = ? ORDER BY a.name",
            (session_id,),
        ).fetchall()
        return [
            Agent(r["name"], r["description"] or "", r["model"] or "",
                  json.loads(r["capabilities"]), json.loads(r["metadata"]), r["id"])
            for r in rows
        ]

    def add_document(self, title: str, content: str, tags: list[str] | None = None,
                     metadata: dict[str, Any] | None = None, agent_id: int | None = None) -> KnowledgeRecord:
        cur = self.db.execute(
            "INSERT INTO knowledge(agent_id,title,content,tags,metadata) VALUES(?,?,?,?,?)",
            (agent_id, title, content, self._json(tags or []), self._json(metadata or {})),
        )
        self.db.commit()
        return KnowledgeRecord(title, content, tags or [], metadata or {}, id=cur.lastrowid, agent_id=agent_id)

    def remember(self, agent_id: int, content: str, kind: str = "fact", importance: float = 0.5,
                 metadata: dict[str, Any] | None = None) -> Memory:
        cur = self.db.execute(
            "INSERT INTO memories(agent_id,content,kind,importance,metadata) VALUES(?,?,?,?,?)",
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
        result = []
        for r in rows:
            if not tokens or tokens & set(r["content"].lower().split()):
                result.append(Memory(r["agent_id"], r["content"], r["kind"], r["importance"], json.loads(r["metadata"]), r["id"]))
            if len(result) >= limit:
                break
        return result

    def register_tool(self, name: str, description: str = "", schema: dict[str, Any] | None = None, endpoint: str | None = None) -> Tool:
        cur = self.db.execute(
            "INSERT INTO tools(name,description,schema,endpoint) VALUES(?,?,?,?)",
            (name, description, self._json(schema or {}), endpoint),
        )
        self.db.commit()
        return Tool(name, description, schema or {}, endpoint, cur.lastrowid)

    def create_task(self, title: str, description: str = "", assigned_to: int | None = None,
                   status: str = "queued", metadata: dict[str, Any] | None = None) -> Task:
        cur = self.db.execute(
            "INSERT INTO tasks(title,description,assigned_to,status,metadata,updated_at) VALUES(?,?,?,?,?,CURRENT_TIMESTAMP)",
            (title, description, assigned_to, status, self._json(metadata or {})),
        )
        self.db.commit()
        row = self.db.execute("SELECT * FROM tasks WHERE id=?", (cur.lastrowid,)).fetchone()
        return self._task(row)

    def update_task_status(self, task_id: int, status: str) -> Task:
        self.db.execute(
            "UPDATE tasks SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (status, task_id),
        )
        self.db.commit()
        row = self.db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return self._task(row)

    def list_tasks(self, assigned_to: int | None = None) -> list[Task]:
        if assigned_to is None:
            rows = self.db.execute("SELECT * FROM tasks ORDER BY updated_at DESC").fetchall()
        else:
            rows = self.db.execute(
                "SELECT * FROM tasks WHERE assigned_to=? ORDER BY updated_at DESC",
                (assigned_to,),
            ).fetchall()
        return [self._task(r) for r in rows]

    def send_message(self, sender_id: int, content: str, session_id: str,
                     role: str = "assistant", metadata: dict[str, Any] | None = None) -> Message:
        """Send a message from one registered AI into a shared conversation."""
        self.db.execute(
            "INSERT OR IGNORE INTO sessions(session_id, title) VALUES (?, '')",
            (session_id,),
        )
        self.db.commit()
        return self._insert_message(sender_id, role, content, session_id, metadata)

    def broadcast(self, sender_id: int, content: str, session_id: str,
                  metadata: dict[str, Any] | None = None) -> Message:
        """Publish an agent message to a session; subscribers read it with receive()."""
        return self.send_message(sender_id, content, session_id, "broadcast", metadata)

    def receive(self, agent_id: int, session_id: str | None = None,
                after_id: int = 0, limit: int = 50) -> list[Message]:
        """Read messages in a session, excluding the agent's own messages."""
        if session_id is None:
            rows = self.db.execute(
                "SELECT * FROM messages WHERE id>? AND agent_id!=? ORDER BY id LIMIT ?",
                (after_id, agent_id, limit),
            ).fetchall()
        else:
            rows = self.db.execute(
                "SELECT * FROM messages WHERE session_id=? AND id>? AND agent_id!=? ORDER BY id LIMIT ?",
                (session_id, after_id, agent_id, limit),
            ).fetchall()
        return [self._message(row) for row in rows]

    def conversation(self, session_id: str, limit: int = 100) -> list[Message]:
        rows = self.db.execute(
            "SELECT * FROM messages WHERE session_id=? ORDER BY id LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return [self._message(row) for row in rows]

    def _insert_message(self, agent_id: int | None, role: str, content: str, session_id: str,
                        metadata: dict[str, Any] | None) -> Message:
        cur = self.db.execute(
            "INSERT INTO messages(agent_id,role,content,session_id,metadata) VALUES(?,?,?,?,?)",
            (agent_id, role, content, session_id, self._json(metadata or {})),
        )
        self.db.commit()
        row = self.db.execute("SELECT * FROM messages WHERE id=?", (cur.lastrowid,)).fetchone()
        return self._message(row)

    @staticmethod
    def _task(row: sqlite3.Row) -> Task:
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

    @staticmethod
    def _message(row: sqlite3.Row) -> Message:
        return Message(
            row["role"], row["content"], row["agent_id"], row["session_id"],
            json.loads(row["metadata"]), row["id"], row["created_at"],
        )

    def add_message(self, role: str, content: str, agent_id: int | None = None, session_id: str = "default",
                   metadata: dict[str, Any] | None = None) -> int:
        return self._insert_message(agent_id, role, content, session_id, metadata).id  # type: ignore[return-value]

    def search(self, query: str, limit: int = 10) -> list[KnowledgeRecord]:
        rows = self.db.execute("SELECT * FROM knowledge ORDER BY id DESC").fetchall()
        tokens = set(query.lower().split())
        scored = []
        for r in rows:
            text = f'{r["title"]} {r["content"]} {r["tags"]}'.lower()
            score = sum(token in text for token in tokens)
            if score or not tokens:
                scored.append(KnowledgeRecord(r["title"], r["content"], json.loads(r["tags"]), json.loads(r["metadata"]), score, r["id"], r["agent_id"]))
        return sorted(scored, key=lambda item: item.score, reverse=True)[:limit]

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> "AIDB":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
