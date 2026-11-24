# AIDB Universal File Format — Proposal

**Status:** Proposal for project review; not yet a frozen or implemented standard  
**Proposed file extension:** `.aidb`  
**Name:** AIDB (Artificial Intelligence Database) File Format

## Purpose

The AIDB file format is intended to provide one language-independent, extensible container for representing, storing, and exchanging information across AI systems and other software, regardless of programming language, operating system, storage engine, or network.

The format must be capable of representing ordinary text as well as structured, relational, spatial, temporal, scientific, and multimodal information—including 2D, 3D, and 4D data, and large binary content—without requiring a different AIDB format for each kind of information.

## Foundational principle

**One AIDB format for information; many possible implementations for reading, writing, storing, and transporting it.**

AIDB must not make Python, Rust, C, JavaScript, SQLite, JSON, Markdown, IPFS, or any other implementation technology a prerequisite of the format.

## Requirements

A conforming format design must address:

1. **One canonical file identity:** the `.aidb` extension identifies an AIDB file. The extension alone does not establish that a file is valid; conformance is determined by its specified signature, structure, and version.
2. **Language independence:** implementations in different programming languages must interpret the same file consistently.
3. **Extensibility:** new information types and application-specific extensions can be introduced without corrupting or redefining existing meanings.
4. **Universal structure:** support for atomic values, sequences, maps, records, graphs, relationships, documents, events, and multidimensional arrays/tensors.
5. **Spatial and temporal semantics:** coordinates, dimensions, coordinate reference systems, units, and time must be representable explicitly. A bare number must not be assumed to have a unit or coordinate meaning.
6. **Mixed content:** support readable text and efficient binary payloads in the same overall format, without requiring binary media to be expanded into text.
7. **Identity and references:** resources and contained objects can have stable identifiers and refer to one another.
8. **Provenance and history:** authorship/agent identity, source, timestamps, transformations, and change history can be preserved where applicable.
9. **Integrity and security:** define content integrity checks and leave room for authenticated protection and access-control metadata without confusing encryption with identity or trust.
10. **Versioning and compatibility:** define format versions, extension rules, unknown-field behavior, and safe migration.
11. **Portability:** a file can be copied between compatible systems without depending on a particular database engine or network.
12. **Conformance:** independent implementations must be testable against shared fixtures and must preserve meaning when reading and writing files.

## Boundaries

The AIDB file format is the portable information container and interchange boundary. It is not itself:

- a programming language or execution environment;
- a database engine or query language;
- a network transport or peer-discovery system;
- an ontology that dictates one interpretation for every domain;
- a requirement to use any particular serialization library or storage backend.

AIDB may provide adapters for existing formats and systems. Such adapters do not make those formats the canonical AIDB file format.

## Design work required before version 1.0

This proposal deliberately does **not** select a final byte-level encoding or claim that a complete syntax already exists. Those choices require comparative research and working prototypes. The specification must decide, with evidence:

- the file signature and version header;
- the canonical logical data model and type system;
- the textual representation and its character encoding;
- the binary section/container layout and payload boundaries;
- canonical numeric, coordinate, unit, and time representations;
- identifiers, references, relationships, and provenance;
- extension and unknown-type handling;
- integrity, optional compression, and optional encryption;
- streaming, random access, and large-file behavior;
- conformance tests and interoperability fixtures.

The design must be evaluated against representative text, graph, tabular, tensor, 2D/3D/4D spatial, image, audio, video, and mixed-content examples. It must also be tested with at least two independent language implementations before the project calls the format stable.

## Relationship to the current AIDB architecture

The existing architecture distinguishes storage, interchange, and wire formats. This proposal asks the project to consider standardizing `.aidb` as the canonical **file/container and interchange format**. It does not automatically make the same encoding mandatory for internal database storage or every network message. Any decision to unify those boundaries must be explicit and justified separately.

This proposal is intended to record the project's direction for discussion and review. It does not claim that the format has been implemented, finalized, or adopted as a stable release.
