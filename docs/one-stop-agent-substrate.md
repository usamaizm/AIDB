# AIDB: One-Stop Data and Memory Substrate for Agents

Status: product direction and proposed architecture. This document describes the intended scope; it does not claim every capability is implemented.

## Product goal

AIDB aims to be a dependable, local-first, self-hostable data and memory substrate that agents can use as a common place to discover, store, retrieve, relate, update, and exchange the information needed to do work. It should reduce the need for every agent or framework to build its own disconnected memory store, document index, artifact repository, event log, and integration layer.

AIDB should be a **one-stop data substrate**, not a monolithic AI agent and not a requirement to use one model, database, cloud, or framework.

## What belongs in AIDB

### Core, required capabilities

- **Resources and knowledge:** typed resources, notes, records, structured data, and metadata.
- **Agent memory:** durable project and task context, with ownership, visibility, provenance, and lifecycle controls.
- **Relationships and lineage:** explicit links between resources, artifacts, facts, interpretations, and derived outputs.
- **Change history:** revisions, optimistic concurrency, ordered changes, cursors, and checkpoints.
- **Artifact store:** text, Markdown, source code, documents, media, archives, assembly, and opaque binary files, preserving original bytes.
- **Portable data exchange:** validated export/import and snapshot semantics, with clear handling of external blobs.
- **Discovery and specification:** machine-readable node identity, schema versions, operations, and capability discovery.
- **Access control:** explicit authorization boundaries and safe defaults for sensitive or shared information.
- **Stable APIs:** a language-neutral contract and C-first ABI, with optional C++ and other language bindings.

### Optional modules

- Keyword/full-text search and metadata filters.
- Vector embeddings and semantic retrieval.
- Parsing, OCR, transcription, document extraction, and code indexing.
- Graph queries and relationship traversal.
- Task/session memory helpers, retrieval policies, and context assembly.
- Import/export connectors for files, repositories, and external data systems.
- Agent-framework adapters and tool interfaces.
- Transport adapters such as in-process calls, CLI, local IPC, and HTTP.
- Specialized tooling for assembly, compilation, disassembly, and other technical artifacts.

These modules should be independently installable or replaceable where practical. The core should remain useful without any model provider, embedding service, network connection, or optional parser.

## What 'one-stop' must not mean

- It must not force all agents to use the same model, framework, or prompting convention.
- It must not require every deployment to run every plugin.
- It must not pretend opaque storage means a file has been parsed or understood.
- It must not silently execute code or binaries while ingesting, indexing, previewing, or exporting.
- It must not turn unverified extracted text or agent-generated claims into trusted facts without provenance.
- It must not weaken access control by making all memory globally visible to every agent.
- It must not promise exactly-once external side effects; mutation idempotency and adapter retry semantics must be explicit.

## Core object model

Use a small set of composable primitives rather than a separate database design for every feature:

- **Resource:** a typed, revisioned entity with content and metadata.
- **Artifact:** byte-preserving content with media type, size, digest, and provenance metadata.
- **Relationship:** a typed edge between resources or artifacts.
- **Change:** an immutable record of an accepted state transition.
- **Transformation:** a provenance-linked operation that produces derived artifacts or resources from inputs.
- **Specification/capability:** a versioned declaration of supported schemas, operations, adapters, and limits.
- **Snapshot:** a portable, validated view of state and the declared history/blob scope.

Specialized concepts such as agent sessions, tasks, documents, code symbols, embeddings, or memories should generally be represented as resource types or optional modules over these primitives unless their semantics require a separate contract.

## Agent-facing workflow

An agent should be able to:

1. Discover an AIDB node and inspect its versioned specification and permissions.
2. Query capabilities and schemas before using optional features.
3. Store or retrieve resources and byte-safe artifacts.
4. Search or traverse relationships when those modules are available.
5. Attach provenance to observations, extracted content, and generated interpretations.
6. Update resources with revision checks and idempotency keys where supported.
7. Follow a stable change cursor to learn what changed since its last checkpoint.
8. Export or import portable data under explicit authorization and validation rules.

Agent frameworks should call the same contract through adapters; no framework-specific object model should become the canonical data model.

## Modularity and implementation priorities

1. **Contract and conformance:** define stable resource, artifact, relationship, change, provenance, authorization, error, and snapshot semantics.
2. **Reliable core:** ensure existing state, concurrency, change history, import/export, and access-control invariants are tested.
3. **Universal artifacts:** add streaming, byte-safe storage, metadata, digest verification, opaque fallback, and round-trip tests.
4. **Capability discovery:** agents can determine which operations and adapters a node supports.
5. **Retrieval interfaces:** define a common search/retrieval contract; implement basic keyword/metadata retrieval before optional vector search.
6. **C ABI and bindings:** make C a stable low-level boundary, with wrappers over the same contract.
7. **Connectors and agent adapters:** add incrementally based on actual user demand and conformance tests.
8. **Operational hardening:** backup/restore, migrations, resource limits, observability, permission testing, and documented deployment profiles.

Do not implement every proposed feature at once. Build the shared substrate first and add capabilities as replaceable modules.

## Acceptance criteria

AIDB is approaching the one-stop goal when:

- multiple agents can share permitted state without sharing a framework or model;
- data and artifact semantics remain consistent across supported language bindings and transports;
- original binary artifacts survive import/export byte-for-byte;
- clients can discover available capabilities and receive stable errors for unsupported operations;
- changes can be consumed incrementally and mutations are protected against stale revisions;
- provenance distinguishes source material from extracted or agent-generated interpretations;
- access policies prevent unauthorized agents from reading or mutating data;
- optional search, embeddings, parsers, and connectors can be replaced without rewriting the core;
- portability and restore behavior are covered by automated conformance tests.

## Scope statement

Prefer describing AIDB as an **agent-oriented data, memory, and artifact substrate**. It can host or connect to many agent workflows, but it is not inherently a universal replacement for every operational database, search engine, vector database, filesystem, or specialized analytics system. Integration should be capability-driven and avoid duplicating data unnecessarily.

## Structured agent memory

Knowledge entries should use progressive disclosure: a concise abstract or preface at the top, followed by key points, detailed content, typed metadata, provenance, history, and relationships to supporting or conflicting material. See [Agent Memory and Knowledge Entries](agent-memory-and-knowledge-entries.md) for the proposed schema and retrieval model.
