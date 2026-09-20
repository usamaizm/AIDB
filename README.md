# AIDB

AIDB is a collection of collections of ideas.

AIDB is a durable, local-first SQLite-backed foundation for AI systems. It gives agents a place to store operational memory, session state, shared knowledge, tasks, and workflow events without requiring a central cloud dependency.

AIDB is intentionally model-agnostic and repository-native. It does not run models or call external AI services by itself. Instead, it provides a durable coordination layer for AI workflows, agent memory, and knowledge capture.

## Living structure taxonomy

AIDB should remain able to hold many kinds of structured knowledge, not just documents and rows. Some useful categories include:

- x: a single value, anchor, or scalar idea
- x,y: a pair, coordinate, relationship, or correlation
- x,y,z: a triad, positional relation, or spatial/causal structure
- x,y,z,t: a spacetime state, trajectory, process, or event record
- world map: a geospatial layer assembled from coordinates and trajectories
- dictionary: named fields or key-value memory
- list: ordered sequence
- set: unordered collection of related ideas
- graph: nodes and edges
- tree: hierarchy or ancestry
- matrix: rows and columns of structured data
- document: prose, notes, or narrative knowledge
- event: something that happened at a point in time
- workflow: ordered actions and transitions
- conversation: messages, turns, and transcript state

The important distinction is:

- shape / category = how the information is structured
- meaning / tags = what the information is about

A single item may be represented in multiple ways. For example, a migration record may be a point, a route, a geospatial event, or a map layer depending on context.

This makes AIDB usable as both:

- a conceptual archive for ideas and proposals
- a spatial-temporal memory model for connected knowledge

See `docs/idea-taxonomy.md` for a deeper treatment of this structure system.

## The final operating model

AIDB is designed around a clear responsibility split:

- GitHub Copilot handles implementation work
- AIDB stores the memory, policy, protocol, and task context
- GitHub provides the public coordination surface and audit trail
- you remain the final reviewer and decision-maker
