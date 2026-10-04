# AIDB Architecture

Status: proposed architecture reset

AIDB is intended to be an accessible, simple, vibrant, live database for AI systems.

This document deliberately precedes implementation. The current Python package is an implementation and source of evidence, not the definition of the architecture.

## 1. Product boundary

AIDB is a database for AI-accessible state.

It stores:

- durable data and artifacts
- relationships and knowledge
- provenance
- changes and history
- live activity
- agent/session context

AIDB does not require a particular model, agent framework, programming language, cloud provider, or database engine.

## 2. Language neutrality

The architecture is language agnostic.

The canonical contract is defined by:

1. data semantics
2. wire semantics
3. serialization rules
4. identity and provenance rules
5. versioning and compatibility rules

Python, Rust, Go, TypeScript, or another language may implement the contract. No language-specific object model is normative.

## 3. The primary primitive: state plus change

AIDB must preserve both current state and its evolution.

A mutation is not merely an overwrite. A meaningful change has an identity, time, actor, affected resource, previous/new state or operation, and provenance where applicable.

The database therefore exposes two complementary views:

- **state:** efficient access to what exists now
- **changes:** ordered access to what happened

Live subscriptions are a projection of the change stream, not a separate source of truth.

This makes questions such as these first-class:

- What changed since I last connected?
- Who changed it?
- When did it change?
- What did it replace?
- What else changed because of it?
- What is changing now?

## 4. Node model

An AIDB node is the smallest independently usable deployment unit.

A node contains:

- durable state
- identity/configuration
- protocol endpoint(s), when enabled
- change history
- portability/recovery metadata

A node can run locally, inside a container, or on a network.

The container is disposable; the state is not.

## 5. Access model

AIDB should have one conceptual database interface with multiple transports.

Access must support:

- inspect/discover
- read/query
- create/write
- relate
- observe changes
- recover/export/import

HTTP, MCP, A2A, CLI, and language SDKs are adapters to the same semantics. They must not create independent data models.

## 6. Data model

The current Artifact -> Extraction -> Interpretation -> Knowledge -> Memory chain is retained as a candidate epistemic model, not declared the universal ontology.

Before implementation expands, the project must determine:

- the minimum canonical entities
- entity identity rules
- relationship semantics
- provenance requirements
- temporal semantics
- deletion/retention semantics
- confidence and uncertainty semantics

The architecture must permit additional structures without forcing every use case into one ontology.

## 7. Portability

AIDB state must be movable between compatible implementations.

A portable state package should be able to preserve:

- data
- relationships
- provenance
- change history
- identities/references
- schema/version information

Portability is a compatibility contract, not a promise that an internal SQLite file is itself the universal interchange format.

## 8. Survivability

The system should remain useful through:

- process failure
- machine replacement
- container replacement
- offline operation
- network partitions
- software upgrades
- schema migrations
- implementation changes

Recovery must be testable and verifiable.

## 9. Simplicity

The minimum useful node should be small.

No model runtime, GPU stack, vector database, cloud account, or agent framework should be required for the core.

Optional capabilities can be added without making the base node dependent on them.

## 10. Vibrancy

Vibrancy means the database is understandable as a living system.

Humans and agents should be able to see:

- current state
- recent changes
- active sessions
- connected actors
- provenance
- health
- capability information

The interface should make change visible without requiring users to reconstruct it from opaque logs.

## 11. Internet cohesion

Internet connectivity is an access property, not the identity of the product.

A node may be:

- completely local
- privately networked
- publicly reachable

When networked, discovery, authentication, authorization, protocol negotiation, and interoperability must be explicit.

## 12. Architecture questions still open

This document intentionally leaves major questions unresolved until they are researched and tested:

- What exactly constitutes a canonical AIDB resource?
- Is the change log append-only, mutable, or hybrid?
- Are state and history physically separate or one storage model?
- What temporal query semantics are required?
- How should concurrent writes and conflicts work?
- What is the identity model for nodes, agents, and resources?
- What does replication mean?
- Which protocol should be normative at the wire level?
- What are the minimum discovery and capability requirements?
- Which parts belong in the core versus adapters?
- What is the smallest viable portable interchange package?

## 13. Architectural rule

Do not add a feature merely because a protocol, framework, or trend makes it possible.

First establish its semantics in the AIDB model. Then expose those semantics through the appropriate adapter.

AIDB should be a database first, a protocol participant second, and a framework dependency never.
