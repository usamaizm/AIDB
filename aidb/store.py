from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from .core import Agent, KnowledgeRecord, Memory, Tool


class AIDB:
    """SQLite-backed registry and memory store for AI agents.

    The database is intentionally model-agnostic: any AI application can register
    agents, tools, knowledge, memories, and messages using this small API.
    """

    def __init__(self, path: str | Path = "aidb.sqlite3"):
        self.path = str(path)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self) -> None:
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, description TEXT,
            model TEXT, capabilities TEXT NOT NULL DEFAULT '[]', metadata TEXT NOT NULL DEFAULT '{}'
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
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY, agent_id INTEGER, role TEXT NOT NULL, content TEXT NOT NULL,
            session_id TEXT, metadata TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(agent_id) REFERENCES agents(id) ON DELETE SET NULL
        );
        """)
        self.db.commit()

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value if value is not None else {})

    def register_agent(self, name: str, description: str = "", model: str = "",
                       capabilities: list[str] | None = None,
                       metadata: dict[str, Any] | None = None) -> Agent:
        cur = self.db.execute("INSERT INTO agents(name,description,model,capabilities,metadata) VALUES(?,?,?,?,?)",
            (name, description, model, self._json(capabilities or []), self._json(metadata or {})))
        self.db.commit()
        return Agent(name, description, model, capabilities or [], metadata or {}, cur.lastrowid)

    def list_agents(self) -> list[Agent]:
        rows = self.db.execute("SELECT * FROM agents ORDER BY name").fetchall()
        return [Agent(r["name"], r["description"] or "", r["model"] or "", json.loads(r["capabilities"]), json.loads(r["metadata"]), r["id"]) for r in rows]

    def add_document(self, title: str, content: str, tags: list[str] | None = None,
                     metadata: dict[str, Any] | None = None, agent_id: int | None = None) -> KnowledgeRecord:
        cur = self.db.execute("INSERT INTO knowledge(agent_id,title,content,tags,metadata) VALUES(?,?,?,?,?)",
            (agent_id, title, content, self._json(tags or []), self._json(metadata or {})))
        self.db.commit()
        return KnowledgeRecord(title, content, tags or [], metadata or {}, id=cur.lastrowid, agent_id=agent_id)

    def remember(self, agent_id: int, content: str, kind: str = "fact", importance: float = 0.5,
                 metadata: dict[str, Any] | None = None) -> Memory:
        cur = self.db.execute("INSERT INTO memories(agent_id,content,kind,importance,metadata) VALUES(?,?,?,?,?)",
            (agent_id, content, kind, importance, self._json(metadata or {})))
        self.db.commit()
        return Memory(agent_id, content, kind, importance, metadata or {}, cur.lastrowid)

    def recall(self, agent_id: int, query: str = "", limit: int = 20) -> list[Memory]:
        rows = self.db.execute("SELECT * FROM memories WHERE agent_id=? ORDER BY importance DESC, id DESC", (agent_id,)).fetchall()
        tokens = set(query.lower().split())
        result = []
        for r in rows:
            if not tokens or tokens & set(r["content"].lower().split()):
                result.append(Memory(r["agent_id"], r["content"], r["kind"], r["importance"], json.loads(r["metadata"]), r["id"]))
            if len(result) >= limit:
                break
        return result

    def register_tool(self, name: str, description: str = "", schema: dict[str, Any] | None = None, endpoint: str | None = None) -> Tool:
        cur = self.db.execute("INSERT INTO tools(name,description,schema,endpoint) VALUES(?,?,?,?)", (name, description, self._json(schema or {}), endpoint))
        self.db.commit()
        return Tool(name, description, schema or {}, endpoint, cur.lastrowid)

    def add_message(self, role: str, content: str, agent_id: int | None = None, session_id: str | None = None, metadata: dict[str, Any] | None = None) -> int:
        cur = self.db.execute("INSERT INTO messages(agent_id,role,content,session_id,metadata) VALUES(?,?,?,?,?)", (agent_id, role, content, session_id, self._json(metadata or {})))
        self.db.commit()
        return int(cur.lastrowid)

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
