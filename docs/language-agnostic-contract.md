# AIDB Language-Neutral Contract (Draft)

Status: proposed contract for review; not yet a frozen protocol.

## 1. Goal

AIDB is defined by observable data semantics and compatibility rules, not by a programming language, class hierarchy, database engine, or transport. Python/SQLite is one reference implementation. Another implementation is compatible when it passes the same language-neutral conformance tests.

This document proposes a small first contract. It does not claim every capability is implemented today.

## 2. Normative terms

The words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY express requirements for implementations of this draft.

## 3. Canonical data model

The contract operates on resources, relationships, changes, specifications, and portable snapshots.

Every resource MUST have:
- `id`: stable opaque string identifier, unique within a node;
- `type`: non-empty namespaced or registered type string;
- `revision`: positive integer, increased on every accepted mutation;
- `content`: JSON value or explicit null;
- `metadata`: JSON object;
- `created_at` and `updated_at`: RFC 3339 timestamps in UTC when available;
- `provenance`: optional structured record identifying the actor and source of a change.

Identifiers MUST be treated as opaque. Consumers MUST NOT assume that an identifier is numeric, sequential, a database primary key, or meaningful outside its declared scope. Implementations SHOULD use globally unique string identifiers for new resources.

Relationships MUST identify source, target, relation type, and optional metadata. A relationship MUST NOT silently imply authorization or trust.

Unknown fields MUST be preserved when round-tripping where practical. Unknown optional fields and extensions MUST be safely ignorable. Required extensions MUST be explicitly declared.

## 4. Representation and encoding

The initial interoperable representation is UTF-8 JSON. This is a representation choice, not a requirement to use a JSON library or a particular in-memory object model.

Implementations MUST define JSON field names and semantics rather than exposing native-language property names. Object member order MUST NOT carry meaning. Arrays are ordered only where the field definition says they are ordered. Absence and explicit `null` MUST be distinguished where the field contract says they differ.

Timestamps MUST use RFC 3339 UTC form. Binary content MUST be carried as an external artifact reference or an explicitly defined encoded payload, never silently coerced into text.

Canonical JSON bytes, signatures, and content-addressing rules are not finalized here and MUST NOT be assumed for security-sensitive hashing until a dedicated canonicalization profile is adopted.

## 5. Core operations

Every conforming implementation MUST define equivalent semantics for these operations, regardless of transport:

- `discover`: identify the node and provide a reference to its current specification;
- `get_specification`: return the authoritative current versioned specification;
- `get_resource(id)`: return a resource or a typed not-found error;
- `create_resource(resource)`: create a resource and return its assigned identity and initial revision;
- `update_resource(id, patch, expected_revision)`: mutate a resource only if the expected revision matches;
- `delete_resource(id, expected_revision)`: delete or tombstone according to the declared retention policy, with revision conflict detection;
- `relate(source, target, type, metadata)`: create or confirm a relationship;
- `list_changes(cursor, limit, filter)`: return ordered changes and a continuation cursor;
- `export_snapshot(options)`: produce a portable snapshot;
- `import_snapshot(snapshot, mode)`: validate and restore a portable snapshot.

Transport adapters MAY add convenience operations but MUST NOT change these semantics.

## 6. Mutation, concurrency, and idempotency

Mutations MUST be atomic: either the operation is accepted as a whole or it has no effect.

Updates and deletes MUST support optimistic concurrency through an expected revision or an equivalent precondition. A mismatch MUST return a conflict error and MUST NOT overwrite newer state.

Operations that may be retried across unreliable transports SHOULD accept an idempotency key. Repeating the same key with the same request MUST NOT duplicate the mutation. Reusing a key with a different request MUST return a conflict.

A change record MUST identify the change, operation, affected resource when applicable, actor when known, timestamp, and resulting revision when applicable. A change feed MUST have stable continuation semantics. Transport-specific cursors MUST be opaque to clients.

## 7. Errors

Errors MUST be machine-readable and have a stable code, human-readable message, and optional structured details. At minimum, implementations MUST distinguish:
- `invalid_argument`
- `not_found`
- `already_exists`
- `revision_conflict`
- `unauthenticated`
- `permission_denied`
- `unsupported_version`
- `unsupported_capability`
- `integrity_failure`
- `temporarily_unavailable`
- `internal_error`

Clients MUST branch on error codes, not parse human-readable messages.

## 8. Identity, authority, and provenance

Node identity, actor identity, authentication, authorization, provenance, and trust are separate concepts.

A capability advertised by a node MUST NOT grant permission. A transport connection MUST NOT by itself authorize a write. Implementations MUST enforce authorization at the operation boundary and SHOULD record the actor and provenance for accepted mutations.

Untrusted imported data MUST be validated before it is allowed to affect live state. Snapshot integrity checks MUST be separate from claims about the trustworthiness of the snapshot's author.

## 9. Versioning and capability negotiation

The node specification MUST identify the contract version and supported capabilities. A client MUST discover the specification before relying on optional behavior.

Backward-compatible additions SHOULD be additive and optional. Breaking changes MUST increment the contract's major version or be isolated behind a separately negotiated version. A node MUST reject unsupported required features clearly rather than silently misinterpreting them.

The specification describes current behavior; it is not itself an authorization token.

## 10. Portable snapshots

A portable snapshot MUST declare its format identifier and version. It SHOULD preserve resource identities, relationships, provenance, revision information, relevant change history, and schema/contract versions.

Import MUST validate the format and all references before committing changes. The import mode MUST state whether it merges, replaces, or restores into an empty node. Implementations MUST NOT silently overwrite conflicting records. A failed import MUST leave the target unchanged.

A database engine's native file is not, by itself, the portable interchange format.

## 11. Transport independence

HTTP, local IPC, command-line interfaces, MCP, A2A, queues, and language SDKs are adapters. Each adapter MUST map to the same operation semantics, errors, authorization checks, revisions, and change history.

A transport MUST NOT become the source of truth for data semantics. AIDB MUST remain usable locally without a cloud account or a particular agent framework.

## 12. Conformance

A shared, language-neutral conformance suite MUST test behavior through the public contract, not private implementation details. The suite SHOULD use JSON fixtures and black-box operation scenarios so the same tests can be run against Python, Rust, Go, TypeScript, or other implementations.

Minimum conformance scenarios:
1. create, read, update, and delete a resource;
2. reject an update with a stale revision;
3. preserve resource and relationship identity across export/import;
4. validate change ordering and cursor continuation;
5. return stable error codes for invalid and unauthorized requests;
6. reject a corrupt or incompatible snapshot without partial import;
7. ignore unknown optional fields while rejecting unknown required capabilities;
8. prove that two different transport adapters produce equivalent results.

## 13. Implementation sequence

1. Review and approve this contract's semantics before calling it stable.
2. Add versioned JSON Schemas and canonical example fixtures.
3. Implement a contract facade over the existing Python/SQLite store.
4. Write black-box conformance tests against that facade.
5. Separate persistence behind an adapter so a different storage engine can implement the same contract.
6. Add a second-language client or implementation to prove the contract is genuinely language-neutral.
7. Freeze version 1 only after interoperability, migration, authorization, and recovery tests pass.

## 14. Current limitations

This document is a proposal, not evidence that the existing code already conforms. The current Python package contains implementation-specific dataclasses, integer IDs in several domain models, and SQLite-backed storage. Those details must remain internal or be translated at the contract boundary. Before production use, the project still needs tested authorization semantics, transaction boundaries, conflict behavior, portable import guarantees, and compatibility tests.
