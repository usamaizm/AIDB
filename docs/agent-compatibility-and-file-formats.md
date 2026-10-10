# Agent Compatibility and File Formats

Status: proposed design; complements the language-neutral contract and binary/assembly proposal. It is not a claim that every format is already implemented.

## Recommendation

Use Markdown (`.md`) as the default format for agent instructions and human-readable project knowledge, but do not make Markdown a requirement for all content. AIDB should treat content format as metadata and capability negotiation, not as a property inferred only from a filename.

Keep the repository-root `AGENTS.md` as the contributor/agent handoff. Keep `README.md` as the human-facing project overview. Put durable architecture and contract rules in `docs/`. Use additional nested `AGENTS.md` files only when a subdirectory needs scoped instructions. Do not create multiple competing instruction files that disagree.

`llms.txt` may be offered as an optional generated discovery/index file, but should not be AIDB's source of truth or a required agent interface. The interoperable source of truth is the AIDB specification, resources, and declared capabilities. Tooling conventions evolve, so adapters should advertise what they support.

## File-format policy

AIDB SHOULD support these categories:

- **Instructions and prose:** Markdown (`text/markdown`), plain text (`text/plain`), and optionally HTML or reStructuredText through adapters.
- **Structured data:** JSON as the initial interoperable representation; YAML, TOML, XML, CSV, and JSON Lines may be supported through format-specific parsers and exporters.
- **Code and technical source:** source files as text with declared language, encoding, and optional toolchain/target metadata; this includes C, C++, assembly, scripts, and configuration files.
- **Documents:** PDF, DOCX, ODT, and other document formats as original artifacts, with extracted text stored as a derived artifact when an extractor is available.
- **Images, audio, and video:** preserve original bytes and media metadata; OCR, transcription, and other interpretations are derived artifacts with provenance.
- **Archives and packages:** preserve original bytes; unpacking is an explicit, resource-limited transformation, not an automatic assumption.
- **Binary artifacts:** object files, executables, libraries, firmware, bytecode, and unknown binary data must be preserved byte-for-byte where possible.

Format support is capability-based. An implementation may store an opaque file even if it cannot parse or preview it. It must not claim semantic search, extraction, conversion, or safe execution unless the relevant adapter exists and reports success.

## Artifact metadata

Every file-like artifact SHOULD record:

- opaque artifact ID;
- original filename, if supplied, kept as metadata rather than identity;
- declared media type and format identifier, if known;
- detected format and detector/version, if detection was attempted;
- byte length and cryptographic digest with named algorithm;
- character encoding and line-ending information when relevant;
- created/modified timestamps when known, without inventing missing values;
- source, owner/visibility, provenance, and transformation history;
- optional language, architecture, ABI, runtime, and toolchain metadata;
- extraction status and the exact adapter/version used, when applicable.

Never trust a filename extension or user-supplied media type as proof of the actual format. Preserve the original bytes even when a normalized or extracted representation is produced.

## Agent interoperability

An agent-compatible AIDB node should expose a versioned machine-readable specification describing:

1. supported resource and artifact types;
2. read/write capabilities and authorization requirements;
3. accepted representations and encodings;
4. available extraction, indexing, and transformation adapters;
5. size limits and pagination/streaming behavior;
6. version and compatibility policy;
7. provenance, error, and concurrency semantics.

Agents should discover capabilities instead of assuming every node supports every format. Unsupported operations must return a stable machine-readable error rather than silently dropping fields or converting bytes to text.

### Suggested conventions

- `AGENTS.md`: instructions for coding agents working in a repository or directory tree.
- `README.md`: project overview, setup, and entry points for people and agents.
- `docs/*.md`: architecture, contracts, design decisions, and operational guidance.
- `*.txt`: plain text content with no Markdown interpretation unless explicitly declared.
- AIDB artifact metadata: authoritative format, provenance, and capability declarations.

These filenames are conventions for discoverability, not special behavior that every AIDB consumer must hard-code.

## Ingestion and transformation rules

- Store original bytes or an explicitly documented lossless representation.
- Make parsing, OCR, transcription, indexing, conversion, and archive extraction explicit transformations.
- Record each transformation's inputs, outputs, adapter name/version, configuration, and timestamp when known.
- Apply configurable limits for file size, expansion ratio, recursion depth, processing time, and memory.
- Treat imported content and archives as untrusted; do not execute files during ingest, indexing, preview, or export.
- Keep extracted text linked to its source artifact so agents can distinguish source content from derived interpretations.
- If a format cannot be parsed, retain it as an opaque artifact and report the limitation.

## Suggested API semantics

The language-neutral contract should eventually define equivalents for:

- `put_artifact(stream, metadata)`;
- `get_artifact(artifact_id, range_or_stream_options)`;
- `get_artifact_metadata(artifact_id)`;
- `list_supported_formats()`;
- `list_capabilities()`;
- `extract_artifact(artifact_id, adapter, options)`;
- `record_transformation(inputs, outputs, adapter, provenance)`.

These are semantic proposals, not existing API symbols. Large artifacts should use streaming or external blob references rather than requiring every language binding to allocate the entire file in memory.

## Conformance tests

At minimum, test that:

- UTF-8 Markdown and plain-text files round-trip without unexpected changes;
- arbitrary binary fixtures round-trip byte-for-byte;
- unknown extensions and unsupported formats are preserved as opaque artifacts;
- incorrect media-type declarations do not cause silent reinterpretation;
- derived text links to its source and records extractor provenance;
- unsupported capabilities return stable errors;
- size/expansion limits are enforced;
- snapshots clearly report whether external blobs are included;
- C, C++, Python, and a later independent binding observe equivalent artifact semantics.

## Implementation order

1. Add artifact and capability schemas to the language-neutral contract.
2. Define streaming blob storage, metadata, digest, and snapshot semantics.
3. Add format capability discovery and an opaque-storage fallback.
4. Implement text/Markdown/plain-text and binary round-trip support first.
5. Add extraction adapters incrementally, each with provenance and conformance tests.
6. Add repository guidance to `AGENTS.md` and keep it aligned with actual implementation status.

## Current status

This is a design proposal. The current repository should not be described as supporting every listed format until the relevant storage, parser/adapter, and conformance tests are implemented.
