# AIDB v1.0 Design

Status: design proposal only; no implementation changes yet.

## 1. Design objective

AIDB v1.0 should preserve and harden the existing epistemic core already present in the repository:

Artifact -> Extraction -> Interpretation -> Knowledge -> Memory

The first v1.0 goal is not to expand the ontology. The goal is to make the existing chain durable, testable, queryable, and reviewable.

The design below is driven by the code audit of the current repository and intentionally favors the actual implemented primitives over the broader conceptual taxonomy in the README and encyclopedia.

## 2. Current-state findings that the design preserves

The repository currently includes the following operational primitives:

- agents
- sessions
- tasks
- messages
- tool calls
- artifacts
- extractions
- extraction_outputs
- interpretations
- epistemic_knowledge
- epistemic_knowledge_relations
- epistemic_memory
- workflow_events

The strongest implemented chain is:

Memory
  -> epistemic_memory.knowledge_id
  -> epistemic_knowledge
  -> interpretation_id
  -> interpretations
  -> output_artifact_id
  -> artifact
  -> optional extraction via extraction_outputs
  -> source artifact

This is validated by `AIDB.trace_memory_to_source()` in `aidb/store.py` and tested in `tests/test_epistemic_chain.py`.

The design keeps this core and makes it canonical.

## 3. Canonical v1.0 principle

AIDB v1.0 should have a single canonical epistemic model:

- `epistemic_knowledge` is canonical knowledge storage
- `epistemic_memory` is canonical agent-memory storage
- `workflow_events` is canonical immutable history stream
- `artifacts` are canonical evidence objects with checksum and provenance
- `interpretations` are canonical evidence-to-claim transformations
- `extractions` are optional, but valid, transforms from raw artifact to derived artifact

Legacy tables must be treated as compatibility or migration layers, not parallel conceptual models.

## 4. Canonical schema

### 4.1 `agents`

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT UNIQUE NOT NULL | |
| description | TEXT | |
| model | TEXT | |
| role | TEXT DEFAULT 'agent' | |
| permissions | TEXT JSON | capability or policy list |
| capabilities | TEXT JSON | real access capabilities |
| metadata | TEXT JSON | |

### 4.2 `sessions`

| Column | Type | Notes |
|---|---|---|
| session_id | TEXT PK | |
| title | TEXT | |
| description | TEXT | |
| metadata | TEXT JSON | |
| created_by | INTEGER FK -> agents.id | nullable |
| created_at | TEXT | |
| status | TEXT | active, archived, closed |

### 4.3 `tasks`

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| title | TEXT | |
| description | TEXT | |
| assigned_to | INTEGER FK -> agents.id | nullable |
| status | TEXT | queued, running, done, failed |
| metadata | TEXT JSON | |
| created_at | TEXT | |
| updated_at | TEXT | |
| depends_on | INTEGER FK -> tasks.id | nullable |
| priority | INTEGER | |

### 4.4 `artifacts`

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT | |
| media_type | TEXT | MIME type |
| filename | TEXT | optional |
| size_bytes | INTEGER | |
| checksum | TEXT | |
| checksum_algorithm | TEXT DEFAULT 'sha-256' | |
| provenance | TEXT JSON | source and chain info |
| status | TEXT DEFAULT 'raw' | raw, derived, processed, archived |
| encoding | TEXT | optional |
| parent_artifact_id | INTEGER FK -> artifacts.id | nullable |
| transformation_history | TEXT JSON | list of steps |
| metadata | TEXT JSON | |
| created_at | TEXT | |

### 4.5 `extractions`

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| input_artifact_id | INTEGER FK -> artifacts.id | required |
| method | TEXT | OCR, text_extraction, parser, ... |
| status | TEXT | pending, success, partial, failed |
| confidence | REAL 0..1 | |
| created_at | TEXT | |
| metadata | TEXT JSON | |

### 4.6 `extraction_outputs`

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| extraction_id | INTEGER FK -> extractions.id | |
| output_artifact_id | INTEGER FK -> artifacts.id | |
| sequence | INTEGER | |
| UNIQUE(extraction_id, output_artifact_id) | | |
| UNIQUE(extraction_id, sequence) | | |

### 4.7 `interpretations`

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| output_artifact_id | INTEGER FK -> artifacts.id | required |
| claim | TEXT | free-form or structured claim |
| interpreter | TEXT | model name/version or human |
| confidence | REAL 0..1 | |
| created_at | TEXT | |
| metadata | TEXT JSON | |

### 4.8 `epistemic_knowledge`

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| interpretation_id | INTEGER FK -> interpretations.id | required |
| status | TEXT | proposed, accepted, rejected, deprecated |
| confidence | REAL 0..1 | |
| created_at | TEXT | |
| metadata | TEXT JSON | |

### 4.9 `knowledge_relations`

Canonical relation table, replacing the current `epistemic_knowledge_relations` name if desired.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| source_knowledge_id | INTEGER FK -> epistemic_knowledge.id | |
| target_knowledge_id | INTEGER FK -> epistemic_knowledge.id | |
| relation | TEXT | contradicts, supports, refines, supersedes, derived_from, duplicates |
| confidence | REAL 0..1 | |
| evidence_artifact_id | INTEGER FK -> artifacts.id | nullable |
| created_by | TEXT | actor or source |
| created_at | TEXT | |
| metadata | TEXT JSON | |
| UNIQUE(source_knowledge_id, target_knowledge_id, relation) | | |

### 4.10 `epistemic_memory`

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| agent_id | INTEGER FK -> agents.id | |
| knowledge_id | INTEGER FK -> epistemic_knowledge.id | |
| kind | TEXT | fact, belief, observation, hypothesis, rule |
| confidence | REAL 0..1 | agent-subjective confidence |
| status | TEXT | active, dormant, forgotten |
| context | TEXT JSON | when/how encountered |
| created_at | TEXT | |
| metadata | TEXT JSON | |

### 4.11 `workflow_events`

Canonical immutable history stream.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| event_type | TEXT | e.g. KnowledgeProposed |
| entity_type | TEXT | artifact, extraction, interpretation, knowledge, memory |
| entity_id | INTEGER | |
| timestamp | TEXT | |
| actor_id | INTEGER FK -> agents.id | nullable |
| payload | TEXT JSON | event data |
| schema_version | TEXT | version of event shape |
| correlation_id | TEXT | relates related events |
| causation_id | TEXT | cause of this event |

This is the canonical event stream and may replace the existing loose `workflow_events` semantics without needing a separate table per entity type.

## 5. Canonical enums

The current system already has free-form strings for statuses and relations. v1.0 should define them as actable enums, validated at the app layer and preferably constrained by the DB when possible.

### 5.1 Knowledge status

- proposed
- accepted
- rejected
- deprecated
- superseded

### 5.2 Memory status

- active
- dormant
- forgotten
- reactivated

### 5.3 Artifact status

- raw
- derived
- processed
- archived
- failed

### 5.4 Extraction status

- pending
- success
- partial
- failed

### 5.5 Relation types

- contradicts
- supports
- refines
- supersedes
- derived_from
- duplicates

## 6. Canonical lineage invariant

This is the first-class guarantee:

Interpretation
  -> direct source artifact OR extraction_output -> artifact
  -> Knowledge
  -> Memory

The invariant should be expressed as:

- Memory must reference a valid `epistemic_knowledge` row.
- Knowledge must reference a valid `interpretation` row.
- Interpretation must reference a valid `artifact` row.
- If the interpretation is derived from an extraction, it must reference an artifact that is a valid extraction output from some extraction.
- If the interpretation is direct from an artifact, the artifact must be the source artifact and no extraction is required.

This is the rule to test and enforce.

## 7. State transition rules

### 7.1 Knowledge state transitions

`proposed -> accepted -> deprecated/superseded` or `proposed -> rejected`.

Every transition appends an immutable event to `workflow_events` with payload containing:

- old_status
- new_status
- reason
- actor_id
- timestamp
- schema_version

### 7.2 Memory state transitions

`active -> dormant -> forgotten` or `forgotten -> reactivated`. 

Memory is an agent-state projection, not evidence. It is mutable but its acquisition and updates remain historical.

### 7.3 Artifact lifecycle

`raw -> derived -> processed -> archived`.

Artifacts are versioned by identity and provenance, not by mutation in-place.

## 8. Event sourcing model

AIDB v1.0 should treat `workflow_events` as the authoritative history stream.

### 8.1 Event schema

Each event should contain:

- id
- event_type
- entity_type
- entity_id
- timestamp
- actor_id
- payload
- schema_version
- correlation_id
- causation_id

### 8.2 Event examples

- KnowledgeProposed
- KnowledgeAccepted
- KnowledgeRejected
- KnowledgeDeprecated
- KnowledgeSuperseded
- MemoryCreated
- MemoryUpdated
- MemoryForgotten
- RelationCreated
- RelationRemoved
- ArtifactCreated
- ArtifactDerived
- InterpretationCreated
- ExtractionCreated

This preserves the notion that current tables are materialized state, while the event stream gives history and replayability.

## 9. Canonical API

### 9.1 Dataclasses

The current dataclasses in `aidb/core.py` are close to the correct model and should remain the public API. v1.0 should align them with the canonical tables.

Proposed structure:

- Agent
- Artifact
- Extraction
- ExtractionOutput
- Interpretation
- Knowledge
- KnowledgeRelation
- Memory
- Session
- Task
- Tool
- ToolCall
- WorkflowEvent
- Message

### 9.2 Core methods

```
register_agent(...)
create_session(...)
create_task(...)
register_artifact(...)
register_artifact_from_bytes(...)
derive_artifact(...)
create_extraction(...)
record_extraction_output(...)
create_interpretation(...)
create_knowledge(...)
create_knowledge_relation(...)
remember_knowledge(...)
trace_memory_to_source(memory_id)
trace_artifact_lineage(artifact_id)
add_event(...)
retrieve(query, ...) -> RetrievalResult
```

### 9.3 Retrieval API

The retrieval result should not be a bare list of chunks. It should return evidence bundles.

```
RetrievalResult(
    memory: Memory,
    knowledge: Knowledge,
    interpretation: Interpretation,
    artifact: Artifact,
    relevance: float,
    confidence: float,
    provenance_strength: float,
    recency: float,
    supporting_relations: list[KnowledgeRelation],
    contradicting_relations: list[KnowledgeRelation],
    lineage: list[Artifact | Interpretation | Knowledge | Memory],
)
```

This object should support downstream reasoning and present contradictory evidence cleanly.

## 10. Retrieval model

v1.0 should not introduce a vector database by default.

The retrieval model should be multi-dimensional and evidence-aware.

### Retrieval score should combine:

- semantic_similarity
- entity_relevance
- temporal_relevance
- provenance_strength
- confidence
- recency
- task_relevance
- relationship_relevance

The API should never return just one collapsed number without context. It should return the bundle and sub-scores.

### Retrieval result should distinguish:

- supporting evidence
- contradicting claims
- explanation of why this memory was chosen
- lineage / source paths

## 11. Contradiction handling

Contradiction handling is a differentiator for AIDB and should be first-class.

Example:

- Claim A: PostgreSQL, confidence 0.82, evidence deployment.yaml
- Claim B: SQLite, confidence 0.71, evidence architecture.md
- Relation: Claim A contradicts Claim B
- State: unresolved

This should be visible in retrieval results and searchable via relation queries.

## 12. Capability model

The prototype fields `permissions` and `capabilities` already exist, but they are not enforced. v1.0 should make them real.

### Capability examples

- memory.read
- memory.write
- knowledge.propose
- knowledge.accept
- knowledge.reject
- artifact.read
- artifact.write
- workflow.execute
- repository.modify

These are checked at the API layer, not just stored as metadata.

This turns governance from advisory policy into enforceable boundaries.

## 13. Migration plan from 0.9.0

### 13.1 Goal

Keep the current database readable while switching to canonical schema and semantics.

### 13.2 Migration strategy

1. Add schema version table.
2. Detect database version.
3. Initialize `schema_migrations` table.
4. Migrate legacy `knowledge` table to `epistemic_knowledge` semantics where possible.
5. Migrate legacy `memories` table to `epistemic_memory` semantics where possible.
6. Keep compatibility views or adapters for older code.
7. Alert on ambiguous or orphaned records.

### 13.3 Compatibility rule

- `epistemic_knowledge` becomes canonical; `knowledge` is a compatibility table.
- `epistemic_memory` becomes canonical; `memories` is a compatibility table.
- `workflow_events` remains canonical event history stream.
- `legacy` helpers are wrappers, not competing models.

## 14. Transaction and concurrency rules

The database should establish a clear transaction boundary for any operation that updates epistemic state.

### Example transaction groups

- artifact creation + extraction linkage + interpretation creation
- knowledge creation + relation creation + event insertion
- memory creation + event insertion

Rule: all writes that are semantically linked must be committed in a single transaction.

### Concurrency

- No mutation of state should occur without an event append.
- Use SQLite transactions with write locks.
- Keep single-writer semantics by default for the v1.0 API.
- Multi-agent concurrency should be supported by correlation_id and causation_id.

## 15. Public error model

v1.0 should make errors explicit and typed.

Suggested exceptions:

- `ValidationError`
- `LineageError`
- `ConstraintViolationError`
- `PermissionDeniedError`
- `MigrationError`
- `ConcurrencyError`

This is more usable than relying only on generic `ValueError`.

## 16. Test matrix

The test suite should focus on invariants rather than CRUD only.

### Required invariant tests

- Every Memory traces to valid Knowledge.
- Every Knowledge traces to valid Interpretation.
- Every Interpretation traces to a valid Artifact.
- If derived, the artifact must have a parent and transformation history.
- If an extraction exists, it must map to a valid source artifact.
- All knowledge status transitions are logged as events.
- All memory status transitions are logged as events.
- Contradicting claims are retained and queryable.
- Retrieval returns supporting and contradicting relations.
- Orphans are rejected or explicitly flagged.
- Historical reconstruction from events is possible.
- Migration from legacy schema works.
- Capability enforcement blocks unauthorized actions.

### Test priority

1. lineage
2. contradiction
3. status transitions
4. artifact derivation
5. migration
6. capability checks
7. concurrency/transaction consistency

## 17. Recommended implementation sequence

### Phase 1: Freeze current behavior

- document current schema and supported behavior
- add `schema_version` and compatibility notes
- establish baseline tests

### Phase 2: Resolve legacy/current schema

- designate canonical tables
- create migration scaffolding
- mark legacy tables as compatibility tables

### Phase 3: Define canonical enums + invariants

- statuses
- relations
- event types
- lineage rules

### Phase 4: Add migrations

- schema migration framework
- compatibility wrappers
- upgrade path from 0.9.0

### Phase 5: Make lineage enforceable

- validate every write chain
- reject orphaned memory or knowledge
- explicit event append on failed lineage detection

### Phase 6: Make state transitions historical

- event stream as authoritative source
- payload-based transitions
- replay support

### Phase 7: Formalize relations

- relation enum enforcement
- contradiction support in retrieval
- query by relation type and evidence artifact

### Phase 8: Build provenance-aware retrieval

- evidence bundle results
- ranking by provenance, confidence, and recency
- contradictory claim handling

### Phase 9: Enforce capabilities

- permission checks in API methods
- capability-driven policy checks

### Phase 10: Harden concurrency / transactions

- atomic writes
- transaction boundaries
- lock policy
- correlation IDs for multi-step updates

### Phase 11: Expand invariant + property tests

- property-based tests for lineage and state changes
- history replay validation
- migration verification

## 18. De-scoping for v1.0

The following should be explicitly deferred for later versions:

- geometric ontology as database schema
- fractal or lattice storage models
- custom vector database implementation
- elaborate multi-node distributed architecture
- full graph database engine
- extra ontology taxonomy beyond the minimal epistemic primitives

AIDB v1.0 should prove the durable epistemic substrate first.

## 19. Final recommendation

AIDB v1.0 should not become a general-purpose semantic graph or a new vector DB.

It should become a small, durable epistemic substrate whose core guarantees are:

- exact provenance
- lineage validation
- event-sourced history
- contradiction visibility
- capability-based access
- evidence-aware retrieval

That is a much smaller and more defensible v1.0 than the broader geometry-first vision described in the README.

## 20. Success criteria for v1.0

The project is ready to move from concept to implementation when all of the following are true:

- there is one canonical epistemic model
- lineage is enforced
- status transitions are historical
- contradictory claims are visible and queryable
- retrieval returns evidence bundles, not just chunks
- capability checks are enforced
- migration path exists from 0.9.0
- invariant tests pass consistently

This design is intentionally conservative and implementation-ready without changing the conceptual ambition of the repository.
