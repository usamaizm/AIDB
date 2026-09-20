from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Agent:
    name: str
    description: str = ""
    model: str = ""
    capabilities: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    id: int | None = None


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
        return {"id": self.id, "title": self.title, "content": self.content,
                "tags": self.tags, "metadata": self.metadata, "score": self.score,
                "agent_id": self.agent_id}


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
