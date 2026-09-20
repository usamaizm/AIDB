# Idea garden

**Status:** raw / exploring  
**Purpose:** preserve the current shape of the AIDB vision without treating it as a specification.

## AIDB as a collection of collections

AIDB may be understood as a collection of collections of ideas: a living archive where concepts can be grouped, connected, revisited, and expanded over time.

The archive does not need to begin with one rigid ontology. Collections might eventually represent:

- a project or domain
- a conversation or brainstorm
- an AI system's working memory
- a research topic
- a protocol proposal
- a set of related sources
- a lineage of derived ideas

The useful primitive may be the relationship between ideas, rather than a fixed category system.

## Shared archival possibilities

AIDB could eventually support participating AIs or nodes that preserve portions of a shared archive. The responsibility might be distributed rather than held by one repository or service.

Possible directions include:

- content-addressed knowledge artifacts
- signed manifests and provenance
- replicated archive collections
- peer-to-peer distribution
- magnet links or torrent-style retrieval for large artifacts
- a registry that indexes metadata without hosting every payload
- reputation or availability signals for archival peers

These are possibilities, not commitments. The immediate value is recording the idea and the questions it creates.

## Magnet links for knowledge

A magnet link could act as a pointer to a distributable knowledge artifact, dataset, archive snapshot, or collection. A future knowledge record might combine:

- a human-readable description
- a content identifier or hash
- a magnet URI
- provenance and licensing information
- version and lineage metadata
- integrity and authenticity information
- semantic tags or relationships

A magnet link alone would not establish meaning or trust. It would be one layer in a larger system:

```text
knowledge description + provenance
              -> content identity
              -> peer-to-peer payload distribution
              -> verification and indexing
```

## Questions raised

- What counts as a knowledge object: a document, claim, conversation, collection, or all of these?
- Should collections be immutable snapshots, mutable streams, or both?
- How can derived ideas retain links to their sources and earlier versions?
- How should contradictory ideas coexist without being silently merged?
- What makes a peer a trustworthy or useful archive participant?
- Which metadata belongs in AIDB and which belongs in external storage?
- How can large archives remain discoverable without filling the Git repository?

## Near-term experiments

No implementation is required yet. Good future experiments could include:

1. A plain Markdown knowledge object with provenance fields.
2. A manifest describing a small collection and its relationships.
3. A local content-addressed archive outside Git history.
4. A mock magnet-link record that can be verified without a live network.
5. A comparison of centralized, federated, and peer-to-peer retrieval.

## Guiding principle

> Capture ideas freely; constrain implementations later.
