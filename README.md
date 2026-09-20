# AIDB

AIDB is a collection of collections of ideas.

Status: experimental, concept-first, standards-aware, and reviewable.

AIDB is a local-first knowledge and memory substrate for AI systems. It gives agents a durable place to store operational memory, session state, shared knowledge, workflow events, and project context without depending on a central cloud service.

AIDB is intentionally model-agnostic and repository-native. It does not run models or call external AI services by itself. Instead, it provides a durable coordination layer for AI workflows, knowledge capture, task tracking, and reviewable provenance.

AIDB is also file-format agnostic at the protocol layer: it is designed to handle text, PDFs, images, binary payloads, archives, and other artifact types through metadata-driven identity, provenance, and transformation tracking rather than file-extension assumptions.

## At a glance

- Local-first memory and knowledge storage
- SQLite-backed operational state layer
- Session and task orchestration
- Reviewable provenance and source hierarchy
- Concept-first, geometry-aware knowledge modeling
- Standards-aware serialization, integrity, and security practices
- Format-agnostic artifact handling for mixed media

## Core principles

1. Preserve provenance and source hierarchy.
2. Distinguish proposals from accepted knowledge.
3. Keep the concept system expressive without sacrificing reviewability.
4. Prefer known-good standards over ad hoc formats where practical.
5. Treat the system as a living archive, not a frozen product specification.
6. Treat artifacts as content objects first and file extensions second.

## Living structure taxonomy

AIDB should remain able to hold many kinds of structured knowledge, not just documents and rows.

- scalar: a single atomic value
- super-scalar: a value with identity, metadata, provenance, and structure
- array: an indexed sequence of values
- matrix: a 2D array or tabular structure
- tensor: an N-dimensional array
- x,y: a pair, coordinate, relationship, or correlation
- x,y,z: a triad, positional relation, or spatial/causal structure
- x,y,z,t: a spacetime state, trajectory, process, or event record
- dictionary: named key-value memory
- list: ordered sequence
- set: unordered collection
- graph: nodes and edges
- tree: hierarchy
- document: prose or narrative knowledge
- world map: geospatial layer
- event: time-based record
- workflow: process or action stream
- diamond lattice: branching and convergence
- cube: orthogonal dimensional structure
- tetrahedron: minimal four-way stability
- sphere: bounded or global context
- hex: local neighborhood and resilient clustering
- fractal: recursive self-similarity across scales
- symmetry: invariance under transformation
- super-symmetry: higher-order relations across layers and domains
- encoding / decoding: representation conversion
- compression / decompression: size reduction and restoration
- encryption / decryption: confidentiality and access control
- serialization / deserialization: object-to-format conversion
- hashing / verification: integrity and identity checks

The distinction matters:

- shape / category = how the information is structured
- meaning / tags = what the information is about

A single item may be represented in multiple ways. For example, a migration record may be a point, a route, a geospatial event, or a map layer depending on context.

This makes AIDB usable as both:

- a conceptual archive for ideas and proposals
- a geometric and topological memory model for connected knowledge
- a transformation-aware knowledge system for representation, storage, and access

## Conceptual direction

The project is exploring a recursive, symmetric, and geometric knowledge model. The idea is not to flatten everything into a single database table, but to preserve how ideas branch, recur, transform, and reassemble across scales.

This includes:

- recursive content structures
- repeated local patterns
- global contextual layers
- relation-rich graphs
- abstract geometric organization
- multi-scale concept navigation
- representation transformations for storage and transfer
- meaningful scalar and higher-order knowledge units

AIDB is best understood as a living archive of concepts, not a finalized product specification.

## Standards and interoperability

AIDB prefers known-good standards over ad hoc formats where possible.

- Storage and interchange: JSON, YAML, TOML, and CBOR where appropriate
- Integrity: SHA-256 and related standard hash functions
- Serialization: standard JSON/YAML rules and versioned schemas
- Transport: standard HTTP and TLS patterns where used externally
- Provenance: explicit timestamps, source references, and version metadata
- Encryption: standard strong encryption with key management
- Compression: standard codecs for storage or transfer efficiency

Conceptual flexibility remains important, but actual implementation formats should align with established interoperability conventions wherever practical.

## Governance and review model

AIDB is designed around a clear responsibility split:

- GitHub Copilot handles implementation work
- AIDB stores the memory, policy, protocol, and task context
- GitHub provides the public coordination surface and audit trail
- you remain the final reviewer and decision-maker

The repository also includes a structured governance model under `.aidb/` and `docs/` to keep proposals, accepted decisions, and unreviewed material separated.

## Documentation map

- `README.md` — project overview and framing
- `brainstorms/` — open, provisional ideas and notes
- `encyclopedia/` — concept vocabulary and structured knowledge model
- `docs/` — governance, protocol, standards, and review guidance
- `.aidb/` — repository-level policy and authority model
- `aidb/` — Python package and operational state layer
- `examples/` — sample request and workflow structures

## What AIDB is not

AIDB is not a claim that one ontology or one schema solves all knowledge representation. It is not an autonomous execution environment by default. It is not a replacement for human review. It is a durable, reviewable substrate for AI memory, workflow state, and concept formation.

## In one sentence

AIDB is an experimental, reviewable, local-first memory and knowledge system for AI agents, designed to preserve provenance, structure, and concept continuity across evolving project work.

See `docs/idea-taxonomy.md`, `docs/knowledge-transformations.md`, `docs/protocol.md`, `docs/request-evaluation.md`, `docs/artifact-protocol.md`, and `docs/standards.md` for the evolving concept system, artifact model, and governance model.
