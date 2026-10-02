# AIDB Epistemic Kernel Audit: Findings & Proposed Changes

**Date**: 2026-10-02  
**Scope**: Conservative hardening pass on epistemic kernel (Artifact → Extraction → Interpretation → Knowledge → Memory)  
**Goal**: Establish correctness and enforcement before expanding features

---

## I. Canonical Model Assessment

### Current State

The repository has **two competing models** living in the same codebase:

#### 1. Legacy Knowledge-Base Model
- **Tables**: `knowledge` (agent_id, title, content, tags)
- **API**: `add_document()`, `search()`, `remember()`, `recall()`
- **Semantics**: Lightweight keyword store; unstructured
- **Used by**: Legacy APIs

#### 2. Epistemic Model (Canonical)
- **Tables**: 
  - `artifacts` (immutable evidence)
  - `extractions` (transforms)
  - `extraction_outputs` (links)
  - `interpretations` (claims about artifacts)
  - `epistemic_knowledge` (system state)
  - `epistemic_knowledge_relations` (claim relationships)
  - `epistemic_memory` (agent-specific knowledge)
  - `workflow_events` (audit trail)
- **API**: `register_artifact()`, `create_interpretation()`, `create_knowledge()`, `remember_knowledge()`, `trace_memory_to_source()`
- **Semantics**: Rich provenance, full lineage, event-sourced
- **Tested by**: `test_epistemic_chain.py`

### Finding 1.1: Canonical Model Declared but Not Enforced
**Issue**: The epistemic model is documented and partially tested, but the legacy model still coexists without deprecation markers.

**Current behavior**:
- Both models accept writes
- No API discourages legacy usage
- No migration scaffolding exists
- No version tracking

**Files affected**:
- `aidb/core.py` — exports both `KnowledgeRecord` (legacy) and `Knowledge` (canonical)
- `aidb/epistemic.py` — **redefines** `Memory` differently than in `core.py` (line 199-209)
- `aidb/store.py` — has both `knowledge` and `epistemic_knowledge` tables

---

## II. Artifact Integrity Assessment

### Finding 2.1: No Database-Level Immutability

**Issue**: Artifacts are documented as immutable, but SQLite allows direct UPDATE/DELETE.

**Current behavior**:
```python
# aidb/core.py line 74
status: str = "raw"  # No database constraint
```

**Schema** (aidb/store.py):
```sql
CREATE TABLE IF NOT EXISTS artifacts (
    id INTEGER PRIMARY KEY,
    ...
    -- No UNIQUE constraint on (checksum_algorithm, checksum)
    -- No trigger preventing UPDATE/DELETE
);
```

**What's broken**:
1. Same artifact bytes can be registered multiple times (no checksum uniqueness)
2. SQL can directly mutate artifacts (no immutability trigger)
3. Python API doesn't expose mutation, but that's insufficient

**Invariant violated**:
> "Artifacts are immutable once created" (EPISTEMIC_CONTRACT.md line 11)

---

### Finding 2.2: No Content-Address Identity

**Issue**: Checksum exists but is not enforced as unique.

**Current behavior**:
```sql
checksum TEXT NOT NULL,
checksum_algorithm TEXT NOT NULL DEFAULT 'sha-256',
-- Missing: UNIQUE(checksum_algorithm, checksum)
```

This allows:
```
artifact 17 → SHA256 abc123
artifact 42 → SHA256 abc123  ← duplicate content, different ID
artifact 91 → SHA256 abc123  ← triple duplicate
```

**Files affected**:
- `aidb/store.py` lines 92-108 (schema definition)

**Tests that would fail**:
- None currently (gap in test coverage)

---

## III. Provenance & Lineage Assessment

### Finding 3.1: Direct-Origin Fallback Hides Broken Provenance

**Issue**: `trace_memory_to_source()` silently assumes direct-origin when no extraction is found, even if metadata claims derivation.

**Current implementation** (aidb/store.py, `trace_memory_to_source`):
```python
# Hypothetical reconstruction from test behavior
# If interpretation.output_artifact_id has no extraction:
if not extraction:
    # Direct-origin path is valid; no extraction required.
    chain.extraction = None
    chain.source_artifact = artifact  # ← NO VALIDATION
```

**What's broken**:
1. An artifact marked as "derived" in metadata can pass lineage check without an extraction record
2. Test `test_trace_memory_to_source_rejects_corrupt_provenance` expects this to fail but implementation doesn't enforce it
3. Metadata with `"evidence_kind": "extraction"` is ignored during validation

**Test expectation** (tests/test_epistemic_chain.py line 77-98):
```python
def test_trace_memory_to_source_rejects_corrupt_provenance(tmp_path):
    # Creates artifact marked as extraction-derived
    # but with NO extraction record
    interpretation = db.create_interpretation(
        output_artifact_id=orphan.id,
        claim="This is an extraction-derived claim.",
        interpreter="fake-model",
        confidence=0.7,
        metadata={"evidence_kind": "extraction"},  # ← Claims derivation
    )
    # Test expects EpistemicChainBrokenError
    with pytest.raises(EpistemicChainBrokenError):
        db.trace_memory_to_source(memory.id)
```

**Reality**:
- If the implementation doesn't check metadata, this test may pass incorrectly
- OR the implementation checks parent_artifact_id and rejects if present without extraction

**Files affected**:
- `aidb/store.py` — `trace_memory_to_source()` method (needs inspection of full implementation)
- `tests/test_epistemic_chain.py` — test may not be validating the right thing

---

### Finding 3.2: No Explicit Source Vs. Derived Distinction

**Issue**: Artifacts can have `parent_artifact_id` set without an extraction relationship, creating ambiguity.

**Current schema**:
```sql
parent_artifact_id INTEGER,  -- Can be set independently of extractions
FOREIGN KEY(parent_artifact_id) REFERENCES artifacts(id) ON DELETE SET NULL
```

**What's broken**:
1. An artifact can have a parent but no extraction record (missing link)
2. An extraction can exist but not produce output artifacts for its input
3. No invariant: "if parent_artifact_id is NOT NULL, extraction_outputs must exist"

**Invariant violated**:
> "Extraction output is always an artifact" (EPISTEMIC_CONTRACT.md line 14)
> "Complete lineage is reconstructable" (EPISTEMIC_CONTRACT.md lines 79-91)

---

## IV. Event-Sourcing Assessment

### Finding 4.1: Mutations Are Not Atomic With Events

**Issue**: Creating epistemic state does not atomically produce the corresponding WorkflowEvent.

**Current behavior** (inferred from test patterns):
```python
# Caller must do this separately:
knowledge = db.create_knowledge(...)  # INSERT into epistemic_knowledge
db.add_event(...)  # Separate call to workflow_events
```

**What's broken**:
1. If `add_event()` is forgotten, state exists without audit trail
2. If `add_event()` fails but create succeeded, inconsistency remains
3. No database-level guarantee that events and state are synchronized
4. Rollback doesn't guarantee both succeed or both fail

**Invariant violated**:
> "Every creation is an event" (EPISTEMIC_CONTRACT.md line 47)
> "Events form the audit trail" (EPISTEMIC_CONTRACT.md line 48)

---

### Finding 4.2: No Event Payload Schema

**Issue**: `workflow_events` table exists but event shape is unstructured.

**Current schema** (aidb/store.py):
```sql
CREATE TABLE IF NOT EXISTS workflow_events (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,
    message TEXT NOT NULL DEFAULT '',
    agent_id INTEGER,
    task_id INTEGER,
    session_id TEXT,
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- No: event_type, entity_type, entity_id, payload, schema_version, correlation_id, causation_id
);
```

**What's broken**:
1. Cannot distinguish "artifact created" from "memory forgotten" reliably
2. No entity_id linking events to their entities
3. No correlation/causation IDs for multi-step transactions
4. No schema_version for event evolution
5. Cannot replay history from events alone

**Files affected**:
- `aidb/store.py` lines for `workflow_events` schema

---

## V. Knowledge vs Interpretation Assessment

### Finding 5.1: Class Duplication in epistemic.py

**Issue**: `epistemic.py` redefines `Memory` with a different schema than `core.py`.

**In core.py** (lines 156-165):
```python
@dataclass
class Memory:
    agent_id: int
    knowledge_id: int  # ← Links to Knowledge
    kind: str = "fact"
    confidence: float = 0.5
    status: str = "active"
    context: dict[str, Any] = field(default_factory=dict)
```

**In epistemic.py** (lines 199-209):
```python
@dataclass
class Memory:  # ← DUPLICATE NAME
    agent_id: int
    content: str  # ← Different schema!
    kind: str = "fact"
    importance: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)
```

**Problem**:
- `from aidb.core import Memory` and `from aidb.epistemic import Memory` are **different objects**
- Code importing the wrong one will silently fail type-checking
- No deprecation marker on the incorrect one

**Files affected**:
- `aidb/core.py` lines 156-165
- `aidb/epistemic.py` lines 199-209

---

### Finding 5.2: Knowledge/Interpretation Boundary Not Enforced

**Issue**: No validation that Interpretation ≠ Knowledge; both can be created for raw model output.

**Current behavior**:
- An LLM output can become an Interpretation (correct)
- An LLM output can also become Knowledge without an Interpretation (incorrect)

**What's broken**:
1. No constraint preventing direct model output → Knowledge
2. No distinction between "model said X" and "we believe X"
3. EPISTEMIC_CONTRACT.md line 53 warns against this, but code doesn't enforce it

**Invariant violated**:
> "Model outputs are Interpretations or Knowledge, not Artifacts" (EPISTEMIC_CONTRACT.md line 54)
> "A model-generated claim becomes evidence only if explicitly serialized as artifact" (EPISTEMIC_CONTRACT.md line 56)

---

## VI. Retrieval Assessment

### Finding 6.1: No Retrieval Abstraction

**Issue**: Search is hard-coded; retrieval interface is missing.

**Current implementation** (inferred):
- `search()` likely loads all rows and scores in Python
- No abstraction for swapping retrieval backends
- Labeled "_embedding()" and "_cosine_similarity()" but is lexical, not embeddings

**Files affected**:
- `aidb/store.py` — search-related methods

**Invariant violated**:
> "[Retrieval should be pluggable; current implementation is O(N)]" (from technical assessment)

---

## VII. API Coherence Assessment

### Finding 7.1: Duplicate/Overlapping Method Names

**Issue**: Multiple methods do similar things with different names and signatures.

**Inferred from code**:
- `remember()` vs `remember_knowledge()`
- `add_document()` vs `create_knowledge()`
- `knowledge` table vs `epistemic_knowledge` table
- `Memory` vs `EpistemicMemory` concept

**Files affected**:
- `aidb/store.py` — full AIDB class
- `aidb/core.py` — exported symbols

---

## VIII. Test Coverage Assessment

### Current Tests

**test_basic.py**:
- ✅ `test_package_exports()` — validates exports
- ✅ `test_register_artifact_from_bytes()` — basic artifact creation
- ✅ `test_derive_artifact_tracks_transformation_history()` — derivation tracking

**test_epistemic_chain.py**:
- ✅ `test_trace_memory_to_source_direct_origin()` — direct-origin lineage
- ✅ `test_trace_memory_to_source_extraction_origin()` — extraction-based lineage
- ✅ `test_trace_memory_to_source_rejects_corrupt_provenance()` — expects broken provenance rejection (may not be enforced)
- ✅ `test_trace_artifact_lineage()` — artifact derivation chain

### Missing Tests

- ❌ Checksum uniqueness constraint
- ❌ Artifact immutability (attempted mutation rejection)
- ❌ Duplicate artifact detection
- ❌ Atomic state + event creation (rollback scenarios)
- ❌ Knowledge/Interpretation boundary enforcement
- ❌ Event payload schema validation
- ❌ Cycle detection in lineage
- ❌ Extraction without outputs validation
- ❌ Parent artifact without extraction rejection

---

## IX. Schema Issues Summary

### Critical

1. **No UNIQUE constraint on (checksum_algorithm, checksum)** — allows duplicate artifacts
2. **No immutability enforcement** — SQLite allows UPDATE/DELETE on artifacts
3. **No extraction_outputs linkage validation** — parent_artifact_id can exist without extraction
4. **No provenance metadata validation** — "derived" marked artifacts can lack extraction records
5. **Event mutations not atomic** — state and events can desynchronize

### Important

6. **Event schema incomplete** — missing entity_id, correlation_id, schema_version
7. **Memory class duplicate** — two incompatible definitions in core.py vs epistemic.py
8. **No retrieval abstraction** — hard-coded implementation, O(N) search
9. **API method duplication** — remember() vs remember_knowledge(), add_document() vs create_knowledge()

### Moderate

10. **Lexical "embedding" mislabeled** — should be "term-frequency vector"
11. **No cycle detection** — artifact lineage could theoretically loop
12. **Test coverage gaps** — missing invariant tests for immutability, uniqueness, atomicity

---

## X. Proposed Conservative Changes

### Immediate Actions (Phase 1: Foundation)

These changes establish the minimal correct epistemic kernel without redesigning the system.

#### 1.1 Establish Canonical Model
- **File**: `aidb/__init__.py`
- **Change**: Export only canonical types; mark legacy as deprecated
- **Invariant**: Single, unambiguous public API

#### 1.2 Add Checksum Uniqueness
- **File**: `aidb/store.py` — schema definition
- **Change**: Add `UNIQUE(checksum_algorithm, checksum)` to artifacts table
- **Invariant**: Content-address identity (same bytes = same artifact ID)

#### 1.3 Add Artifact Immutability
- **File**: `aidb/store.py` — schema + API
- **Changes**:
  - Remove any update/delete methods for artifacts in AIDB class
  - Add SQLite trigger to prevent UPDATE/DELETE on artifacts table
  - Add test asserting mutation rejection
- **Invariant**: Artifacts cannot be modified once created

#### 1.4 Add Parent-Artifact Validation
- **File**: `aidb/store.py` — constraint or trigger
- **Change**: If `parent_artifact_id IS NOT NULL`, then extraction_outputs must reference this artifact
- **Invariant**: No orphaned parent relationships

#### 1.5 Fix trace_memory_to_source() Provenance Check
- **File**: `aidb/store.py` — `trace_memory_to_source()` method
- **Change**: Before returning direct-origin, check metadata for "evidence_kind": if marked as "extraction", require an extraction record
- **Invariant**: Claimed provenance matches actual lineage

#### 1.6 Resolve Memory Dataclass Duplication
- **File**: `aidb/epistemic.py`
- **Change**: Remove the second Memory definition (lines 199-209); keep the correct one from core.py
- **Invariant**: One canonical Memory class

#### 1.7 Add Event Schema Version
- **File**: `aidb/store.py` — schema definition
- **Change**: Add columns: entity_type (TEXT), entity_id (INTEGER), correlation_id (TEXT), causation_id (TEXT)
- **Invariant**: Events are properly typed and traceable

---

### Phase 2: Enforcement (Atomic Mutations)

#### 2.1 Make create_knowledge() Atomic
- **File**: `aidb/store.py` — `create_knowledge()` method
- **Change**: 
  ```python
  BEGIN TRANSACTION
  INSERT INTO epistemic_knowledge (...)
  INSERT INTO workflow_events (kind='KnowledgeCreated', entity_type='knowledge', entity_id=..., ...)
  COMMIT
  ```
- **Invariant**: Every knowledge creation has a corresponding event

#### 2.2 Make create_interpretation() Atomic
- **File**: `aidb/store.py` — `create_interpretation()` method
- **Change**: Same pattern; insert interpretation + event in single transaction
- **Invariant**: Every interpretation has a corresponding event

#### 2.3 Make remember_knowledge() Atomic
- **File**: `aidb/store.py` — `remember_knowledge()` method
- **Change**: Same pattern; insert memory + event in single transaction
- **Invariant**: Every memory creation has a corresponding event

#### 2.4 Add Rollback Tests
- **File**: `tests/test_epistemic_chain.py`
- **Change**: Add tests that force transaction failures and verify neither state nor event persists
- **Invariant**: All-or-nothing semantics

---

### Phase 3: Validation Tests

#### 3.1 Immutability Tests
- Attempt artifact UPDATE → reject
- Attempt artifact DELETE → reject

#### 3.2 Checksum Uniqueness Tests
- Register same bytes twice → second should fail or return existing
- Verify different checksums don't collide

#### 3.3 Provenance Validation Tests
- Create artifact with parent but no extraction → reject
- Create extraction that produces no outputs → accept (valid failed extraction)

#### 3.4 Event Atomicity Tests
- Create knowledge; transaction fails partway → neither state nor event persists
- Verify every knowledge/memory/interpretation has corresponding event

---

## Ambiguities Requiring Clarification

1. **How should duplicate artifact registration be handled?**
   - Option A: Reject with error (content-address identity)
   - Option B: Return existing artifact ID (deduplication)
   - **Recommendation**: Option A (explicit, fail-fast)

2. **Should parent_artifact_id require an extraction or just indicate lineage?**
   - Option A: Require extraction for non-null parent (strict)
   - Option B: Allow parent without extraction, but mark as "manual" (loose)
   - **Recommendation**: Option A (strict by default)

3. **Should create_extraction() itself create a KnowledgeCreated event?**
   - Option A: Yes, extractions are first-class (many events)
   - Option B: Only interpret + knowledge + memory create events (fewer events)
   - **Recommendation**: Option A (complete audit trail)

4. **Should legacy `knowledge` table be dropped or migrated?**
   - Option A: Deprecate; provide migration path
   - Option B: Keep for compatibility; mark as @deprecated
   - **Recommendation**: Option B (don't break existing code; provide bridge)

---

## Recommended Sequence for Implementation

1. **Fix model duplication** (Memory class) — trivial, unblocks everything
2. **Add schema constraints** (UNIQUE checksum, immutability trigger, parent-extraction validation)
3. **Fix trace_memory_to_source()** provenance check (small logic change)
4. **Make create_knowledge/interpretation/memory atomic** (refactor into transaction-aware methods)
5. **Enhance event schema** (add entity_type, entity_id, correlation_id)
6. **Add test suite** for new invariants
7. **Document deprecation path** for legacy APIs

---

## Files to Modify (In Order)

1. `aidb/epistemic.py` — remove duplicate Memory
2. `aidb/core.py` — potentially align with epistemic.py
3. `aidb/store.py` — schema, constraints, triggers, atomic methods, validation
4. `tests/test_epistemic_chain.py` — add invariant tests
5. `tests/test_basic.py` — add immutability, uniqueness, atomicity tests
6. `EPISTEMIC_CONTRACT.md` — clarify ambiguities and add success criteria
7. `CHANGELOG.md` — document changes

---

## Success Criteria (Go/No-Go)

### Must-Have
- ✅ No data corruption under current test suite
- ✅ Checksum uniqueness enforced
- ✅ Artifacts are immutable through API and schema
- ✅ Parent-artifact requires extraction or is rejected
- ✅ Provenance validation in trace_memory_to_source()
- ✅ All Memory mutations are atomic with events

### Should-Have
- ✅ Event schema includes entity tracking
- ✅ Test suite validates invariants
- ✅ Deprecation path for legacy APIs

### Nice-to-Have
- ✅ Retrieval abstraction defined (but not yet implemented)
- ✅ API method consolidation documented

---

**End of Audit**

