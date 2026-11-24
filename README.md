# AIDB

AIDB is a collection of collections of ideas.

Status: experimental, concept-first, standards-aware, and reviewable.


## For AI agents and fresh sessions

Fast path for a fresh agent session: read the machine-readable [session context manifest](.aidb/session-context.yml), then [project handoff](docs/PROJECT_CONTEXT.md), [`AGENTS.md`](AGENTS.md), and the [repository audit](docs/repository-audit.md). These point to the right code, tests, architecture contracts, known limitations, and next priorities. Fetch current `main` and verify live CI/PR state before acting; do not rediscover the project from chat history or treat proposals as shipped features.

AIDB is a local-first knowledge and memory substrate for AI systems. It gives agents a durable place to store operational memory, shared knowledge, workflow events, and project context without depending on a central cloud service.

AIDB is intentionally model-agnostic and repository-native. It does not run models or call external AI services by itself. Instead, it provides a durable coordination layer for AI workflows, knowledge capture, agent collaboration, and reviewable provenance.

## Quick start (Python reference implementation)

The currently exposed CLI commands are `agent`, `search`, and `serve`. From a checkout:

```bash
python -m pip install -e .
python -m aidb --db aidb.sqlite3 agent my-agent --description "Local worker"
python -m aidb --db aidb.sqlite3 search "project context"
python -m aidb --db aidb.sqlite3 serve --host 127.0.0.1 --port 8765
```

The database path defaults to `aidb.sqlite3`. For `serve`, the default visibility is private and the default bind is loopback. The CLI accepts `AIDB_AUTH_TOKEN` as an environment fallback for `--auth-token`; an explicit CLI token takes precedence. Do not expose a non-loopback listener publicly without a reviewed authentication, authorization, TLS, and deployment configuration. The current CLI does not expose session/message/task subcommands.

## Implementation status

The Python/SQLite package is an experimental reference implementation. The architecture, format, distributed-network, modular-adapter, self-evolution, C ABI, and extreme-scale material elsewhere in this README describes goals or proposals unless the relevant source, tests, and capability checks demonstrate otherwise. The current `main` branch has not yet absorbed every open pull request. See the [live-state audit](docs/repository-audit.md) for the verified branch/CI snapshot and open-work reconciliation.

AIDB is also file-format agnostic at the protocol layer: it is designed to handle text, PDFs, images, binary payloads, archives, and other artifact types through metadata-driven identity, provenance, and transformation tracking rather than file-extension assumptions.

## Contributing agents

All human and AI contributors follow the [contributor protocol](docs/CONTRIBUTOR_PROTOCOL.md). PRs record stable agent identities separately from authenticated GitHub accounts, with attribution status and factual provenance.

## Architecture

AIDB is being redesigned as a language-agnostic, portable, live database for AI systems. The Python package is an implementation, not the architectural contract. The node describes its current contract dynamically through a versioned specification. See `docs/architecture.md` and `docs/specification.md`.

AIDB does not assume IPv4, IPv6, DNS, HTTP, a cloud provider, or any particular network topology. Endpoints are capabilities with transport metadata; networking remains infrastructure.

## Dynamic specification

An AIDB node publishes a current machine-readable specification describing its identity, contract, capabilities, resources, transports, extensions, and constraints. The specification is versioned and changes are part of node history.

This lets agents discover what a node **is and can currently do** rather than relying on a frozen list of assumptions.

## At a glance

- Local-first memory and knowledge storage
- Language-neutral node contract
- Dynamic discovery and capability advertisement
- Durable state plus change history
- Agent discovery and collaboration records
- Reviewable provenance and source hierarchy
- Format-agnostic artifact handling for mixed media
- Portable recovery as a first-class concern

## Core principles

1. Preserve provenance and source hierarchy.
2. Distinguish proposals from accepted knowledge.
3. Keep the concept system expressive without sacrificing reviewability.
4. Prefer known-good standards over ad hoc formats where practical.
5. Treat the system as a living archive, not a frozen product specification.
6. Treat artifacts as content objects first and file extensions second.
7. Keep transport and networking details out of the core data model.

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

## Standards and interoperability

AIDB prefers known-good standards over ad hoc formats where possible. Concrete transport and serialization choices remain adapters until the architecture freezes their semantics.

## Documentation map

- `README.md` — project overview and framing
- `docs/architecture.md` — architectural reset
- `docs/specification.md` — dynamic node specification
- `docs/protocol.md` — protocol constraints and open questions
- `docs/server-security.md` — safe local and remote HTTP deployment
- `docs/distributed-networking.md` — proposed secure distributed knowledge-network architecture
- `docs/evolution-and-compatibility.md` — independent contract versioning, adapters, migration, and conformance requirements
- `docs/AI_CONTRIBUTORS.md` — invitation and starter task for independent AI contributors
- `brainstorms/` — open, provisional ideas and notes
- `encyclopedia/` — concept vocabulary and structured knowledge model
- `aidb/` — reference implementation

## What AIDB is not

AIDB is not a claim that one ontology or one schema solves all knowledge representation. It is not an autonomous execution environment by default. It is not a replacement for human review. It is a durable, reviewable substrate for AI memory, workflow events, and concept formation.

## In one sentence

AIDB is an experimental, reviewable, language-agnostic live database for AI systems, designed to preserve provenance, structure, and concept continuity across evolving project work.

## Independent AI contributors

Independent AI agents are welcome to inspect, challenge, test, and improve AIDB. Start with the [independent AI contributor guide](docs/AI_CONTRIBUTORS.md) and its bounded [first-review task](.aidb/tasks/first-independent-agent-review.yml). Contributions are judged by evidence and the same review standards regardless of their source.


## Durable agent discovery and collaboration

AIDB provides local, resource-backed agent profiles, provisional knowledge offers, knowledge requests, collaboration requests, durable responses, and independent reviews. These records inherit resource visibility, ownership, relationships, revisions, and provenance. See [the agent-network guide](docs/agent-network.md) and [the runnable example](examples/agent_loop.py).

This is a local semantic collaboration layer, not peer-to-peer networking. It does not provide cryptographic agent identity, outbound node connections, federation, chunk replication, notifications, or autonomous model execution. The separate distributed networking architecture remains a proposal until those capabilities are implemented and tested.


## Ecosystem integration

See the [ecosystem status snapshot](docs/ECOSYSTEM_STATUS.md) for verified implementation and CI status across all ten projects.


AIDB is part of a set of independent, interoperable projects. See the [ecosystem integration contract](docs/ECOSYSTEM_INTEGRATION.md) for project responsibilities, dependency boundaries, and the proposed integration sequence.


## AIID interoperability

AIDB includes an optional, conservative [AIID descriptor ingestion adapter](docs/aiid-integration.md). It stores descriptors as untrusted metadata and does not fetch or execute described resources.
