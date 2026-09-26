"""AIDB architectural invariants and semantics.

This document defines the core epistemic boundaries and invariants that AIDB must maintain.
These are properties of the system, not necessarily first-class tables—but every operation
must preserve them.
"""

# Boundary 1: Artifact → Extraction
# ================================
# Invariant: Every extraction identifies exactly what artifact/version it operated on and how.
#
# This means:
# - extraction.artifact_id must exist and be immutable
# - extraction.method must be recorded (ocr, text_extraction, summarization, etc.)
# - extraction.status must track success/partial/failure explicitly
# - if extraction fails, it is still recorded (not silently dropped)
# - the same artifact can have multiple extractions using different methods
# - extraction results are immutable once recorded
#
# Consequence: You can always ask "what was extracted from artifact X?" and
# "did extraction Y succeed?"

# Boundary 2: Extraction → Interpretation
# ========================================
# Invariant: Every interpretation identifies its evidence and method.
#
# This means:
# - interpretation.extraction_id must exist and be immutable
# - interpretation.interpreter must be recorded (model-name, version, timestamp)
# - interpretation.method must describe how the extraction was interpreted
# - interpretation.confidence must be explicit (even if 0.5)
# - if interpretation fails/is uncertain, that is recorded explicitly
# - the same extraction can have multiple interpretations from different models/methods
# - interpretation results are immutable once recorded
#
# Consequence: You can always ask "what interpretations exist for extraction Z?"
# and "did model X and model Y interpret the same evidence differently?"

# Boundary 3: Interpretation → Knowledge
# ========================================
# Invariant: Every knowledge claim can be traced to its supporting interpretation/evidence.
#
# This means:
# - knowledge.interpretation_id must reference the interpretation that produced it
# - if a claim comes from human assertion, interpretation_id can reference a special
#   "human" interpretation record
# - knowledge.status must be one of: proposed, accepted, rejected, deprecated
# - knowledge.status history is preserved in WorkflowEvents
# - knowledge can reference multiple interpretations as support
# - knowledge itself is mutable (status changes) but history is immutable
#
# Consequence: You can always ask "why does the system believe X?" and trace back
# through interpretation → extraction → artifact.

# Boundary 4: Knowledge → Memory
# ===============================
# Invariant: Agent memory explicitly identifies what it is remembering and its context.
#
# This means:
# - memory.knowledge_id must reference the knowledge being remembered
# - memory.agent_id is the agent remembering it
# - memory.kind must describe the memory type (belief, fact, observation, hypothesis)
# - memory.context must record when/how the agent encountered this knowledge
# - memory.confidence is the agent's subjective confidence, distinct from knowledge.confidence
# - memory.status can be: active, dormant, forgotten
# - memory itself is mutable (status changes) but acquisition history is preserved
#
# Consequence: You can ask "what does agent X remember about knowledge Y?" and
# distinguish the system's confidence in knowledge from the agent's confidence in remembering it.

# Boundary 5: Everything → Event
# ===============================
# Invariant: Significant state changes are append-only auditable events.
#
# This means:
# - Every creation (artifact, extraction, interpretation, knowledge, memory) is an event
# - Every status change (proposed→accepted, active→forgotten) is an event
# - Every contradiction detected is an event
# - Every retrieval or query can be logged as an event
# - Events are immutable once recorded
# - Events preserve who/what triggered the change and when
#
# Consequence: You can reconstruct the full history of any knowledge or memory,
# and audit who changed what and when.

# Knowledge Relations
# ===================
# Instead of embedding contradictions or relationships in Knowledge itself,
# use a separate relation model:
#
#   KnowledgeRelation
#   -----------------
#   source_id        (knowledge ID)
#   target_id        (knowledge ID)
#   relation         (contradicts, supports, refines, supersedes, derived_from, duplicates)
#   confidence       (how certain is this relationship?)
#   created_by       (who asserted this relationship? human? model?)
#   evidence_id      (what artifact/interpretation grounds this relationship?)
#   created_at       (when was this relationship established?)
#
# This lets you build a knowledge graph without making the entire system graph-centric.

# Current State vs. History
# ==========================
# For mutable entities (Knowledge, Memory), we use two layers:
#
# Current state table (optimized for queries):
#   - id, content, status, confidence, updated_at
#   - fast to query "what do we know?"
#
# History table (immutable append-only events):
#   - entity_id, event_type, old_state, new_state, timestamp, actor
#   - complete audit trail of how entity got to current state
#
# This fits naturally with AIDB's existing WorkflowEvent concept.

# Epistemic Foundation
# ====================
# Artifact is the bottom of the chain. A model-generated claim is NOT automatically
# evidence merely because an LLM generated it.
#
# Valid epistemic chains:
#   Artifact → Extraction → Interpretation → Knowledge ← Memory
#   Human Assertion → Knowledge ← Memory
#   Contradiction Detection (event-driven) → KnowledgeRelation
#
# Invalid chains that AIDB should explicitly prevent:
#   LLM output → Knowledge (without extraction/interpretation/evidence)
#   Memory → Knowledge (remembering is not asserting)
#
# This preserves the distinction between evidence, inference, and agent context.

print(
    "AIDB Invariants loaded. These define the architectural boundaries that must be preserved."
)
