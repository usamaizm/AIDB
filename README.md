# AIDB

AIDB is a collection of collections of ideas.

AIDB is a durable, local-first SQLite-backed foundation for AI systems. It gives agents a place to store operational memory, session state, shared knowledge, tasks, and workflow events without requiring a central cloud dependency.

AIDB is intentionally model-agnostic and repository-native. It does not run models or call external AI services by itself. Instead, it provides a durable coordination layer for AI workflows, agent memory, and knowledge capture.

## Living structure taxonomy

AIDB should remain able to hold many kinds of structured knowledge, not just documents and rows.

- x: a single scalar value
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

See `docs/idea-taxonomy.md`, `docs/knowledge-transformations.md`, and the encyclopedia for the evolving concept system.

## Core project posture

AIDB is designed around a clear responsibility split:

- GitHub Copilot handles implementation work
- AIDB stores the memory, policy, protocol, and task context
- GitHub provides the public coordination surface and audit trail
- you remain the final reviewer and decision-maker

## Conceptual direction

The project is exploring a recursive, symmetric, and geometric knowledge model. The idea is not to flatten everything into a single database table, but to preserve how ideas branch, recur, transform, and reassemble across scales.

This includes:

- recursive content structures
- repeated local patterns
- global contextual layers
- relation-rich graphs
- abstract geometric organization
- multi-scale concept navigation
- representation transformations for storage and transport
- meaningful scalar and higher-order knowledge units

AIDB is best understood as a living archive of concepts, not a finalized product specification.
