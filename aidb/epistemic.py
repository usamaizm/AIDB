"""AIDB core epistemic datatypes.

The canonical definitions live in :mod:`aidb.core`; this module is a thin
re-export shim so existing ``aidb.epistemic`` imports keep working. Every
shared name here is the very same object as in ``aidb.core``
(``aidb.epistemic.Artifact is aidb.core.Artifact``, and so on), so there is
exactly one identity model for each concept.

``LegacyMemoryRecord`` is the one class defined here: it has no counterpart
in ``aidb.core`` and is retained for migration compatibility.
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
    Note,
    Resource,
    Session,
    Specification,
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
    "Note",
    "Resource",
    "Session",
    "Specification",
    "Task",
    "Tool",
    "ToolCall",
    "WorkflowEvent",
]
