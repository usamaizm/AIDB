from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Agent:
    name: str
    description: str = ""
    model: str = ""
    role: str = "agent"
    permissions: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    id: int | None = None


@dataclass
class Session:
    session_id: str
    title: str = ""
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_by: int | None = None
    created_at: str | None = None
    status: str = "active"


@dataclass
class Task:
    title: str
    description: str = ""
    assigned_to: int | None = None
    status: str = "queued"
    metadata: dict[str, Any] = field(default_factory=dict)
    id: int | None = None
    created_at: str | None = None
    updated_at: str | None = None
    depends_on: int | None = None
    priority: int = 0


@dataclass
class KnowledgeRecord:
    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    id: int | None = None
    agent_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "tags": self.tags,
            "metadata": self.metadata,
            "score": self.score,
            "agent_id": self.agent_id,
        }


@dataclass
class Memory:
    agent_id: int
    content: str
    kind: str = "fact"
    importance: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)
    id: int | None = None


@dataclass
class Tool:
    name: str
    description: str = ""
    schema: dict[str, Any] = field(default_factory=dict)
    endpoint: str | None = None
    id: int | None = None


@dataclass
class ToolCall:
    agent_id: int | None
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    result: Any = None
    status: str = "success"
    session_id: str | None = None
    id: int | None = None
    created_at: str | None = None


@dataclass
class WorkflowEvent:
    kind: str
    message: str = ""
    agent_id: int | None = None
    task_id: int | None = None
    session_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    id: int | None = None
    created_at: str | None = None


@dataclass
class Message:
    role: str
    content: str
    agent_id: int | None = None
    session_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    id: int | None = None
    created_at: str | None = None
