# Modular Architecture

Status: proposed architecture; implementation status must be verified feature by feature.

## Goal

AIDB should be modular from the inside out: a small stable core defines data semantics and contracts, while storage engines, format handlers, transports, language bindings, agent integrations, and optional processing tools plug in through explicit interfaces. Modularity must not mean a collection of tightly coupled packages that only happen to live in separate directories.

## Architectural rules

1. **Contract before implementation.** Define observable behavior in the language-neutral specification. Every implementation and adapter follows that contract.
2. **Small core, optional capabilities.** Core identity, resource semantics, revisions, relationships, provenance, authorization decisions, and errors must not depend on a specific database, programming language, model, file format, or transport.
3. **Ports and adapters.** The core calls interfaces; adapters implement those interfaces. Core modules must not import concrete optional adapters.
4. **Explicit dependencies.** Each module declares what it provides, what it requires, its version, and compatibility constraints. Detect missing or incompatible dependencies during startup or configuration validation.
5. **Capability discovery.** Agents and clients query supported operations, artifact formats, storage features, and processing adapters instead of inferring support from installed packages or file extensions.
6. **Replaceable implementations.** A storage engine or transport adapter can be replaced without changing resource semantics or client-facing contract behavior.
7. **No hidden side effects.** Ingesting, indexing, previewing, or exporting an artifact must not execute it. Network access, writes, external tool invocation, and destructive transformations require explicit capability and policy decisions.
8. **Provenance and observability.** Adapter operations report stable errors and record relevant version, inputs, outputs, and provenance. Logs must not leak secrets or private content by default.
9. **Versioned interfaces.** Version public interfaces independently where possible. Define compatibility rules, deprecation windows, and migration paths before freezing an API.
10. **Conformance tests.** Contract tests verify behavior across adapters and language bindings. A module is not interchangeable merely because it has the same function names.

## Proposed module map

### Core modules

- **contract/specification:** versioned schemas, operation semantics, compatibility rules, and conformance fixtures.
- **identity:** node/resource identifiers and identity scope.
- **resource model:** resources, relationships, revisions, and lifecycle semantics.
- **change log:** ordered change records, cursors, checkpoints, and snapshot boundaries.
- **provenance:** source/derived relationships and transformation lineage.
- **policy:** authorization interfaces and capability checks; concrete identity providers remain adapters.
- **errors:** stable machine-readable error codes and details.

### Pluggable adapters

- **storage:** SQLite initially; other databases or filesystem/object stores later.
- **artifact/blob storage:** byte-safe streaming, metadata, digests, and large-object references.
- **format handlers:** text, Markdown, JSON, source code, documents, media, archives, and unknown opaque formats.
- **processing:** extraction, OCR, transcription, parsing, indexing, embedding, compilation, disassembly, and other opt-in operations.
- **transport:** in-process C ABI, command-line interface, local IPC, HTTP, or other transports.
- **language bindings:** C as the stable low-level ABI; optional C++ and other bindings over the same semantics.
- **agent integrations:** adapters for agent frameworks and tools, without making any one framework mandatory.
- **observability:** logging, metrics, tracing, and health checks.

These are logical boundaries, not a requirement to create a separate package or process for every item immediately.

## Dependency direction

Allowed direction:

`client / agent integration -> public API or transport -> core contracts -> module interfaces <- adapters`

Core code must not depend directly on optional frameworks, model SDKs, specific document parsers, or concrete network services. Shared schemas and stable types belong in a small contract layer; avoid a large generic utility module that becomes a hidden dependency hub.

## Plugin contract

Each plugin/adapter should declare:

- stable plugin identifier and version;
- interface/contract version range;
- capabilities provided;
- required dependencies and optional dependencies;
- supported input/output media types and size limits, where relevant;
- configuration schema with safe defaults;
- permissions required for file, network, process, or external-service access;
- health/validation behavior;
- failure and retry semantics;
- provenance fields emitted for transformations.

Plugins must fail closed when required permissions are missing, reject incompatible contract versions, and return typed errors for unsupported operations. Plugin discovery must not automatically execute arbitrary code from imported artifacts or untrusted repositories.

## Suggested repository layout

Prefer a layout that reflects real boundaries while keeping the early project simple. Adapt to existing code rather than moving everything at once:

```text
include/aidb/             # stable C ABI headers
src/core/                 # contract-independent core logic
src/adapters/storage/     # SQLite and future storage backends
src/adapters/artifacts/   # blob storage and format adapters
src/adapters/transport/   # CLI, IPC, HTTP, etc.
src/bindings/cpp/         # optional C++ convenience wrapper
schemas/                  # versioned schemas and fixtures
tests/contract/           # adapter-independent conformance tests
tests/adapters/           # backend/adapter integration tests
docs/                     # architecture, decisions, compatibility
AGENTS.md                 # contributor and coding-agent guidance
```

This is a target layout, not a claim that these directories currently exist or that the C implementation is complete. Avoid a disruptive repository-wide move until interfaces and tests are in place.

## Testing strategy

- Core unit tests cover invariants without requiring a database, model SDK, or network.
- Contract tests run against every storage backend and public binding.
- Adapter integration tests use deterministic fixtures and explicitly identify external dependencies.
- Failure tests cover missing plugins, incompatible versions, timeouts, permission denial, partial I/O, and rollback.
- Artifact tests verify byte-for-byte round trips, digest checks, streaming, size limits, and provenance.
- Optional capabilities must be skippable without making the core test suite fail; required contract tests must never be silently skipped.
- CI should test the minimum supported interface versions and the current versions, and should report which optional adapters were actually tested.

## Implementation sequence

1. Map current code and tests to logical modules; document current dependencies before refactoring.
2. Freeze a small initial contract subset and build reusable conformance tests.
3. Define internal interfaces for storage, artifacts, policy, and change log; keep current SQLite behavior behind the storage interface.
4. Add byte-safe artifact storage and capability discovery.
5. Separate transport and language bindings from core semantics; keep C as the stable ABI goal.
6. Add plugin registration/configuration with explicit permissions and version checks.
7. Add one alternative adapter to prove replaceability before adding many more.
8. Refactor incrementally, with compatibility tests and migration notes for every behavior change.

## Avoid these failure modes

- Splitting everything into microservices or separate packages before the interfaces stabilize.
- Making the core depend on one database, programming language, agent framework, model provider, or transport.
- Treating plugins as trusted merely because they are installed.
- Allowing plugins to silently redefine resource, revision, or provenance semantics.
- Using file extensions as the only format detector.
- Claiming a modularity boundary exists because code is in a different folder when dependencies still cross it directly.
- Marking compatibility or test status green without an observed test run.

## Acceptance criteria

AIDB is meaningfully modular when a developer can add or replace a storage backend, format adapter, transport, or language binding by implementing a documented interface and passing the relevant conformance tests—without rewriting the core data model or changing the behavior of existing clients.
