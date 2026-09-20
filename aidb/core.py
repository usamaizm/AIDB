from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class KnowledgeRecord:
    """A single knowledge item stored in the database."""

    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content,
            "tags": self.tags,
            "metadata": self.metadata,
            "score": self.score,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KnowledgeRecord":
        return cls(
            title=data.get("title", ""),
            content=data.get("content", ""),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            score=float(data.get("score", 0.0)),
        )
