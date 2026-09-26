"""AIDB core epistemic datatypes.

These dataclasses enforce the epistemic contract through their structure.
They are immutable once created; mutation is tracked through WorkflowEvents.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Artifact:
    """First-class material that can become evidence.

    Artifacts are immutable once created. New versions are new artifacts.
    Artifacts are identified by checksum and have explicit provenance.
    """

    name: str
    media_type: str
    size_bytes: int
    checksum: str
    checksum_algorithm: str = "sha-256"
    provenance: dict[str, Any] = field(default_factory=dict)
    status: str = "raw"
    id: int | None = None
    filename: str | None = None
    encoding: str | None = None
    parent_artifact_id: int | None = None
    transformation_history: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None


@dataclass
class Extraction:
    """Transformation from input artifact to zero or more output artifacts.

    An Extraction records a method, status, and confidence.
    Output artifacts are first-class Artifact records.
    Failed extractions have status=failed and zero outputs.
    """

    input_artifact_id: int
    method: str
    status: str = "pending"
    confidence: float = 0.5
    id: int | None = None
    created_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionOutput:
    """Link between an Extraction and its output Artifact(s).

    An Extraction may produce zero, one, or many artifacts.
    Sequence determines ordering if relevant (e.g., PDF → page 1, page 2, ...).
    """

    extraction_id: int
    output_artifact_id: int
    sequence: int = 0
    id: int | None = None


@dataclass
class Interpretation:
    """Claim about an artifact produced by an interpreter.

    Interpretations are unstructured; the claim is free-form text.
    Confidence measures interpreter confidence in validity, not objective truth.
    Multiple interpreters can interpret the same artifact.
    """

    output_artifact_id: int
    claim: str
    interpreter: str
    confidence: float = 0.5
    id: int | None = None
    created_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Knowledge:
    """System's current epistemic state regarding an interpretation.

    Knowledge links an Interpretation and assigns it status.
    Status can change (proposed → accepted → deprecated); history is in events.
    Knowledge confidence is independent of Interpretation confidence.
    """

    interpretation_id: int
    status: str = "proposed"
    confidence: float = 0.5
    id: int | None = None
    created_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeRelation:
    """Relationship between two knowledge claims.

    Relations include: contradicts, supports, refines, supersedes, derived_from, duplicates.
    Relations can be grounded in evidence (an artifact) or reasoning.
    """

    source_knowledge_id: int
    target_knowledge_id: int
    relation: str
    confidence: float = 0.5
    evidence_artifact_id: int | None = None
    created_by: str | None = None
    id: int | None = None
    created_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Memory:
    """Agent's relationship to a knowledge claim.

    Memory is about agent state, not epistemic provenance.
    Status can change (active → forgotten); history is in events.
    Confidence is agent's subjective confidence, independent of knowledge confidence.
    """

    agent_id: int
    knowledge_id: int
    kind: str
    confidence: float = 0.5
    status: str = "active"
    context: dict[str, Any] = field(default_factory=dict)
    id: int | None = None
    created_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Agent:
    """An agent that can hold memories and interpret artifacts."""

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
    """A session of activity."""

    session_id: str
    title: str = ""
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_by: int | None = None
    created_at: str | None = None
    status: str = "active"


@dataclass
class Task:
    """A unit of work."""

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
    """Legacy knowledge representation (deprecated in favor of Interpretation → Knowledge)."""

    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    id: int | None = None
    agent_id: int | None = None


@dataclass
class Memory:
    """Agent's subjective relationship to knowledge."""

    agent_id: int
    content: str
    kind: str = "fact"
    importance: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)
    id: int | None = None


@dataclass
class Tool:
    """A tool an agent can invoke."""

    name: str
    description: str = ""
    schema: dict[str, Any] = field(default_factory=dict)
    endpoint: str | None = None
    id: int | None = None


@dataclass
class ToolCall:
    """A record of a tool invocation."""

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
    """Immutable audit event for state transitions."""

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
    """A message in a session."""

    role: str
    content: str
    agent_id: int | None = None
    session_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    id: int | None = None
    created_at: str | None = None
