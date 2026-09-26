# AIDB Epistemic Contract

This document defines the minimal, testable epistemic substrate for AIDB.

The contract specifies what invariants must hold, what the schema guarantees, and what operations preserve the epistemic chain from evidence to memory.

## Core Invariants

1. **Artifacts are first-class material.**
   - Every piece of material that can become evidence for downstream reasoning is an Artifact.
   - Artifacts are immutable once created (new versions are new artifacts).
   - Artifacts are identified by checksum and have explicit provenance.

2. **Extraction transforms artifacts; extraction output is always an artifact.**
   - An Extraction operation takes an input artifact and produces zero, one, or many output artifacts.
   - An Extraction records the method, status, and confidence of the transformation.
   - If extraction fails, the Extraction record still exists with status=failed.
   - Failed extractions have zero output artifacts.
   - Partial extractions have confidence < 1.0 but still produce output artifacts.

3. **Interpretations make claims about artifacts.**
   - An Interpretation examines an artifact and produces a claim.
   - The claim is unstructured text (not pre-tokenized, not reduced to subject/predicate/object).
   - Interpretation confidence measures the interpreter's confidence in the validity of the interpretation, not objective truth.
   - Multiple interpreters can interpret the same artifact, producing different claims.
   - An interpreter can be an LLM, human, adapter, model, or heuristic.

4. **Knowledge represents the system's current epistemic state regarding an interpretation.**
   - A Knowledge record links an Interpretation and assigns it a status (proposed, accepted, rejected, deprecated).
   - Knowledge confidence is distinct from Interpretation confidence.
   - Knowledge is mutable (status can change); history is preserved in WorkflowEvents.
   - Multiple interpretations can contribute to a single knowledge claim (later feature).

5. **Knowledge relations represent relationships between claims.**
   - A KnowledgeRelation links two Knowledge records with a semantic relation.
   - Relations include: contradicts, supports, refines, supersedes, derived_from, duplicates.
   - Relations can be grounded in evidence (an artifact) or reasoning (another knowledge relation).
   - Relations are not mandatory; Knowledge can exist without relations.

6. **Memory represents an agent's relationship to knowledge, not to raw evidence.**
   - A Memory record links an Agent to a Knowledge record.
   - Memory includes kind (belief, fact, observation, hypothesis, etc.), confidence, and context.
   - Memory status can change (active, dormant, forgotten); history is preserved in WorkflowEvents.
   - An agent's confidence in a memory is distinct from the system's confidence in the knowledge.

7. **Events preserve state-transition history.**
   - Every creation (artifact, extraction, interpretation, knowledge, memory) is an event.
   - Every status change (proposed→accepted, active→forgotten) is an event.
   - Every relationship change is an event.
   - Events are immutable; they form the audit trail.
   - Current-state tables (Knowledge, Memory) are mutable projections; events are the source of truth for history.

8. **No generated claim becomes evidence merely because a model generated it.**
   - Model outputs are Interpretations or Knowledge, not Artifacts.
   - An artifact is material that was extracted from or created by external means (user upload, OCR, data ingestion, etc.).
   - A model-generated claim becomes evidence only if it is explicitly serialized as an artifact (e.g., saved to disk, ingested as a document).

## Schema Overview

```
Artifact
   ↓ (input)
Extraction
   ↓ (output)
Artifact
   ↓ (interpret)
Interpretation
   ↓ (recognize)
Knowledge ←──────┐
   ↑              │
   │ (relates)    │ (relates)
   └─ KnowledgeRelation ─┘
   ↓ (remember)
Memory
   ↓ (audit)
WorkflowEvent
```

## Lineage Invariant

Given a Memory M:

```
M.knowledge_id → K
K.interpretation_id → I
I.output_artifact_id → A
A.parent_artifact_id → B (may be null)
Extraction(input=B, output=A)
```

You can reconstruct the complete epistemic chain from memory back to original evidence.

## Confidence Semantics

- **Interpretation.confidence**: The interpreter's confidence that the claim is a valid interpretation of the artifact. Range: [0.0, 1.0].
- **Knowledge.confidence**: The system's confidence in the knowledge claim. Range: [0.0, 1.0].
- **Memory.confidence**: The agent's subjective confidence in the memory. Range: [0.0, 1.0].
- **KnowledgeRelation.confidence**: The confidence in the relationship itself (e.g., how certain is it that K1 contradicts K2?). Range: [0.0, 1.0].

These are independent; high interpretation confidence does not imply high knowledge confidence.

## Implementation Roadmap

1. Schema: Artifact, Extraction, ExtractionOutput
2. Add: Interpretation, Knowledge
3. Add: KnowledgeRelation
4. Add: Memory
5. Add: WorkflowEvent integration for audit trail
6. Write end-to-end lineage test
7. Write contradiction test
8. Write temporal history test

Each step includes:
- Schema additions
- Dataclass models
- Persistence methods (AIDB)
- Unit tests
- Integration tests proving the invariant holds

## What This Is Not

This contract does NOT specify:

- Structured claim schemas (subject/predicate/object triples) — those are future adapters
- Contradiction resolution algorithms — that's policy, not substrate
- Semantic reasoning or inference — AIDB is a memory substrate, not a reasoner
- Multi-modal interpretation — adapters handle domain-specific semantics
- Sophisticated confidence propagation — confidence is recorded, not computed
- Full graph-theoretic operations — KnowledgeRelation is a relation, not a full graph DB

## Validation Tests

The epistemic contract is proven by:

1. **Lineage test**: Create A → E → A' → I → K → M, then reconstruct the chain backward.
2. **Contradiction test**: Create K1 and K2 from different evidence, create a contradicts relation, verify both exist simultaneously.
3. **Temporal test**: Create K with status=proposed, change to accepted, verify current state and full history are both available.
4. **Failure test**: Create E with status=failed and zero outputs, verify the chain is intact but incomplete.
5. **Partial test**: Create E with confidence=0.71 and partial outputs, verify downstream claims reference the partial artifact explicitly.

## Design Decisions

**Why unstructured claims?**
Interpretations may be ambiguous, nuanced, or uncertain. Forcing them into fixed schemas prematurely would dictate the evidence rather than let evidence dictate representation.

**Why separate Interpretation and Knowledge?**
Interpretation is "what did this model/human say about this artifact?" Knowledge is "what does the system currently believe?" They are different questions.

**Why are relations separate from Knowledge?**
Relations can link multiple knowledge records in patterns (e.g., K1 contradicts K2, K3 supports K1, K4 refines K3). Embedding relations in Knowledge metadata would create implicit semantics and make queries harder.

**Why is Memory grounded in Knowledge, not Interpretation?**
Memory is about agent state, not epistemic provenance. An agent remembers claims the system has recognized, not raw interpretations.

**Why use WorkflowEvent instead of separate history tables?**
AIDB already has an event system. Using a single event table preserves a single audit trail and avoids competing sources of truth.

**Why are extracted artifacts first-class?**
Because multiple interpretations may use the same extracted material. Making extraction output first-class avoids duplicating work and preserves the artifact DAG.

**Why can an extraction have zero outputs?**
Some transformations fail. Recording the failure is important; pretending the output exists would corrupt the epistemic chain.
