# Evolution and Compatibility Architecture

Status: proposed architectural requirement; implementation must be assessed boundary by boundary.

## Purpose

AIDB must be able to change its internal architecture, data representations, storage engines, transports, and optional capabilities without forcing every consumer and stored object to change in lockstep.

Compatibility is a capability of the architecture, not a veto over architectural improvement. Conversely, evolvability is not permission for silent breakage or data loss. AIDB manages change through explicit contracts, adapters, negotiation, migrations, conformance tests, and recoverable transitions.

This document defines the intended evolution model. It does not claim that the current Python/SQLite implementation already satisfies it.

## 1. Stable invariants versus replaceable choices

The following invariants are cross-cutting and must survive implementation changes:

- identity and namespace integrity;
- authorization and least privilege;
- content integrity and safe handling of untrusted bytes;
- provenance and truthful attribution;
- resource ownership, visibility, and lifecycle semantics;
- revision/concurrency guarantees where promised;
- auditability, portability, and recoverability;
- explicit side effects and bounded resource use.

The following are replaceable choices unless a specific contract explicitly makes one normative:

- internal database schema and storage engine;
- on-disk serialization and envelope layout;
- chunking, indexing, caching, and placement strategy;
- network transport and endpoint discovery mechanism;
- optional parsers, processors, and model/agent integrations;
- implementation language, package layout, and deployment topology.

A replaceable choice may still have a versioned public contract. Replaceability means that the contract can be implemented by alternatives; it does not mean implementations may behave differently.

## 2. Contract boundaries and independent versioning

Version these boundaries independently where they evolve for different reasons:

1. logical resource and operation semantics;
2. portable interchange representation;
3. persisted storage representation;
4. wire protocol and transport binding;
5. module/adapter interface;
6. optional extension or capability;
7. runtime specification document.

A product release number must not be used as a substitute for these contract versions. A storage format change must not automatically imply a wire protocol change; a transport change must not redefine resource semantics.

Each versioned contract must define its identifier, version, required and optional features, compatibility rules, unknown-field behavior, error behavior, and deprecation or migration policy. Capabilities describe actual implementation support, not aspirations.

## 3. Evolution paths

Choose the least disruptive path that preserves correctness:

- **Additive evolution:** add optional fields or operations with safe defaults and defined unknown-field behavior.
- **Adapter:** translate an old or external contract at a boundary while keeping the core model independent of it.
- **Migration:** transform persisted data explicitly, with validation, provenance, resumability, and recovery.
- **Parallel implementation:** run competing implementations against the same contract/conformance suite before selecting one.
- **Breaking version:** introduce a new contract version when semantics genuinely change; provide a documented transition where feasible.

Do not retain a flawed internal architecture merely to avoid a version boundary. Do not silently reinterpret old bytes or claim stronger guarantees for legacy data than can be verified.

## 4. Compatibility is explicit and negotiated

Compatibility is evaluated between named contract versions and capabilities, not inferred from package versions or endpoint reachability.

A consumer should discover the peer's current specification, identify required semantics, select a mutually supported contract version, negotiate optional extensions, and fail with a stable machine-readable error when no safe intersection exists.

Unknown optional extensions should be safely ignorable only when the contract says so. Unknown required features must cause a clear incompatibility result. Capability advertisement must be generated from the implementation's actual enabled operations and constraints.

Compatibility may be directional: an implementation may read a prior representation without being able to write it, or may import it only through a migration adapter. The specification must state these distinctions.

## 5. Storage, interchange, and wire formats are different boundaries

Do not assume that the internal SQLite schema, home-file envelope, portable export format, chunk encoding, manifest representation, and network wire representation must be identical.

- **Storage representation** is optimized for a backend and may change through migrations.
- **Interchange representation** is a deliberate portability contract between implementations.
- **Wire representation** is a transport-facing contract and may have multiple encodings over the same semantics.
- **Content-addressed objects** hash the exact canonical bytes defined by their own versioned contract; identity and authorization are not inferred from a digest.

Reuse well-defined primitives when useful, but do not couple independent formats merely because they currently share code. In particular, distributed manifests must not accidentally inherit every constraint of the current home-file format.

Canonicalization is required wherever deterministic cross-implementation hashing or signatures depend on it. Its scope, version, normalization rules, and test vectors must be explicit. Hash raw opaque binary content as exact bytes.

## 6. Adapter and module contract

Every replaceable module declares:

- stable module identifier and module version;
- interface/contract identifier and supported version range;
- capabilities provided and required;
- configuration schema and operational limits;
- permissions and trust assumptions;
- supported representations and conversion behavior;
- stable errors, retry/idempotency behavior, and failure semantics;
- provenance emitted for transformations;
- health and conformance-test status.

The core depends on interfaces, not concrete adapters. An adapter must not silently redefine core identity, authorization, resource, revision, or provenance semantics. Missing, disabled, or incompatible optional modules must not prevent unrelated core functionality from operating.

Module discovery is not module trust. Installing or discovering an adapter must not automatically execute imported content or grant permissions.

## 7. Migration and recovery requirements

Every persisted-format or schema migration must specify:

- source and target contract versions;
- preconditions and compatibility detection;
- deterministic transformation rules;
- validation before committing;
- atomicity or checkpoint/resume behavior;
- idempotency and duplicate/retry handling;
- provenance and audit record;
- backup, rollback, or forward-recovery strategy;
- behavior for unknown fields and partially understood records;
- resource limits and interruption behavior.

Never silently upgrade data merely because it was read. Never discard unknown or unsupported content unless the user/policy explicitly authorizes that loss. A migration must not label legacy content as integrity-verified unless it has actually verified the required bytes and metadata.

Where feasible, test old-reader/new-writer, new-reader/old-writer, mixed-version peers, interrupted migrations, corrupted inputs, and rollback/recovery. State when a direction is intentionally unsupported.

## 8. Conformance and replaceability proof

A module boundary is real only when independent implementations can pass the same observable contract tests.

Maintain versioned golden fixtures and language-neutral test vectors for serialization, hashing, errors, authorization outcomes, and migration behavior. Test positive and negative cases, including malformed and unknown fields, unsupported versions, permission denial, partial I/O, restart, and recovery.

Before replacing an implementation, run the same conformance suite against both the old and new adapters. Compare semantics and externally visible behavior, not internal table layouts. Keep performance tests separate from correctness conformance.

## 9. Experimental evolution

Allow experimental schemas, adapters, and implementations to coexist under explicit experimental identifiers or namespaces. Experimental work must not silently become normative or overwrite accepted data.

Promote an experiment only after its contract, security assumptions, migration/compatibility impact, conformance evidence, and operational limits have been reviewed. Preserve competing proposals and their evidence until a decision is recorded.

## 10. Change decision record

For every material contract change, record:

- problem and reason the current boundary is insufficient;
- affected contracts, modules, data, and consumers;
- invariant(s) that must remain unchanged;
- selected evolution path and alternatives considered;
- compatibility directions supported and intentionally unsupported;
- migration, rollback, and data-loss behavior;
- security and provenance implications;
- conformance fixtures and acceptance criteria;
- decision owner, status (proposed/accepted/deprecated), and review evidence.

A proposal is not an accepted decision. A document is not implementation evidence.

## 11. Application to current AIDB work

- **N4b/home formats:** treat home-file envelopes and persisted schemas as versioned storage/interchange boundaries. Do not let v1 dictate the internal architecture. Define v2 semantics independently; preserve v1 through an explicit reader or migration adapter only if it can be done safely. Keep legacy and verified-v2 assurance distinguishable.
- **Distributed chunks/manifests:** define a separately versioned content and manifest contract. Reuse canonicalization and digest primitives where appropriate, but do not assume the home envelope and distributed manifest are the same format.
- **PR #49 collaboration resources:** keep agent offers, requests, responses, and reviews as semantic resources. Their persistence adapter and transport exposure are separate concerns.
- **PR #61 distributed placement:** keep node identity, peer transport, discovery, chunk placement, and replication behind explicit contracts. A transport or registry must not become the authority for logical identity or authorization.
- **Runtime specification:** advertise only implemented capabilities and negotiate contract versions independently from software release versions.

These are architectural directions, not a freeze of the outstanding N4b, identity, serialization, or replication decisions.

## Acceptance criteria

AIDB demonstrates this architecture when:

1. at least two implementations of a meaningful contract pass the same conformance suite;
2. a storage or transport adapter can be replaced without changing logical resource semantics;
3. old representations are handled only through explicit, tested compatibility or migration paths;
4. mixed-version capability negotiation succeeds when compatible and fails clearly when incompatible;
5. interrupted and failed migrations preserve recoverability and provenance;
6. experimental implementations can be evaluated without silently changing accepted data or contracts.

Until demonstrated, describe each boundary as proposed, partial, or implemented with evidence rather than calling the whole system modular or evolvable.
