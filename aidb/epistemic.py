"""Compatibility exports for canonical models defined in :mod:`aidb.core`.

This module used to define a second, divergent copy of the epistemic dataclasses.
Re-exporting the canonical classes preserves import compatibility and class identity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .core import (
    Agent,
    Artifact,
    EpistemicChain,
    EpistemicChainBrokenError,
    Extraction,
    ExtractionOutput,
    Interpretation,
    Knowledge,
    KnowledgeRecord,
    KnowledgeRelation,
    Memory,
    Message,
    Session,
    Task,
    Tool,
    ToolCall,
    WorkflowEvent,
)


@dataclass
class LegacyMemoryRecord:
    """Legacy memory payload retained for migration compatibility."""

    agent_id: int
    content: str
    kind: str = "fact"
    importance: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)
    id: int | None = None


__all__ = [
    "Agent",
    "Artifact",
    "EpistemicChain",
    "EpistemicChainBrokenError",
    "Extraction",
    "ExtractionOutput",
    "Interpretation",
    "Knowledge",
    "KnowledgeRecord",
    "KnowledgeRelation",
    "LegacyMemoryRecord",
    "Memory",
    "Message",
    "Session",
    "Task",
    "Tool",
    "ToolCall",
    "WorkflowEvent",
]
