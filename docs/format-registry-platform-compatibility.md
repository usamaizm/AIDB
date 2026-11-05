# AIDB Format Registry and Platform Compatibility Proposal

**Status:** Proposed design for review; not a frozen contract or implementation claim.  
**Owner:** AIDB project  
**Tracking:** [Issue #29](https://github.com/usamaizm/AIDB/issues/29)

## 1. Purpose and governing principles

AIDB must preserve information and its meaning independently of programming language, operating system, storage engine, transport, and model family. A human should be able to inspect core records with ordinary text tools. A consumer written in another language should be able to read and write the same contract without reproducing Python classes or depending on SQLite internals.

The registry defines the role of each representation. It does not create several competing data models.

Principles:

1. **One semantic contract, multiple representations.** IDs, resources, relationships, provenance, revisions, timestamps, access rules, and change semantics mean the same thing in every encoding.
2. **Readable by default.** Core metadata and ordinary records use UTF-8 text formats.
3. **Binary when justified.** Large media, tensors, indexes, and performance-sensitive payloads may use typed binary formats, with readable manifests and metadata.
4. **Preserve originals.** Imported documents remain available as original artifacts. Extracted text, previews, embeddings, and interpretations are separate derived artifacts linked by provenance.
5. **Version everything that affects interpretation.** A consumer must be able to identify format, schema, contract, and relevant extension versions.
6. **No hidden platform assumptions.** Paths, file names, byte order, timestamps, permissions, and filesystem behavior must be specified or abstracted.
7. **Fail safely.** Unknown required features, unsupported versions, invalid encodings, and integrity failures must produce explicit errors, not silent data loss.

## 2. Proposed format registry

| Registry ID | Format / media type | Intended role | Normative status |
|---|---|---|---|
| `aidb-json-v1` | UTF-8 JSON; `application/json` | Initial structured interchange, API envelopes, manifests, resource records, specifications, configuration exchanged over APIs | Initial required profile |
| `aidb-jsonl-v1` | UTF-8 JSON Lines; `application/x-ndjson` | Sequential change/event export, bulk records, streaming import/export | Initial supported profile |
| `aidb-text-v1` | UTF-8 plain text; `text/plain; charset=utf-8` | Human-authored notes and simple content | Supported artifact type |
| `aidb-markdown-v1` | UTF-8 Markdown; `text/markdown; charset=utf-8` | Documentation, journals, human-readable knowledge | Supported artifact type |
| `aidb-yaml-config-v1` | UTF-8 YAML; `application/yaml` | Optional human-edited deployment/configuration files only | Optional; not canonical interchange |
| `aidb-cbor-v1` | CBOR; `application/cbor` | Optional compact structured interchange where size or parsing efficiency matters | Future optional profile |
| `aidb-safetensors-v1` | Safetensors | Model/tensor weight artifact, subject to upstream format compatibility and security review | Research/integration target; not yet required |
| `aidb-binary-blob-v1` | Opaque bytes with declared media type | Large media, archives, model assets, and other binary attachments | Supported as opaque payloads; format-specific readers are adapters |

The registry is extensible. A new format must have a stable registry ID, media type, encoding, versioning rules, validation behavior, security considerations, and conversion semantics. A file extension alone is never sufficient to identify its meaning.

### 2.1 JSON profile

JSON is the first structured interchange target because it is widely readable and has implementations in essentially every target language.

The initial profile should require UTF-8, reject duplicate object keys, reject non-standard numeric values such as NaN and Infinity, and define whether a field is required, optional, nullable, or extension-defined. Resource IDs are opaque strings; consumers must not assume integer IDs or infer meaning from their textual shape.

The project still needs to decide canonical serialization and cryptographic signing rules. Until then, byte-for-byte JSON equality must not be used as semantic equality, and signatures must not be improvised over arbitrary serializer output.

### 2.2 JSONL profile

Each non-empty line is one complete JSON value, normally one event or record. Lines are independently parseable. A stream must declare its contract/schema version and record kind in a manifest or agreed header record. A truncated final line must be detected and reported; import must not silently treat an incomplete stream as a complete successful export.

Ordering, duplicate-event handling, cursor semantics, and replay/idempotency rules belong to the change-stream contract, not to JSONL itself.

### 2.3 Text and Markdown

Text and Markdown are human-facing content formats, not substitutes for structured resource metadata. AIDB should preserve original bytes when exact preservation is required, record the declared character encoding, and avoid silently normalizing content in a way that changes meaning. UTF-8 is the preferred default for newly created text.

### 2.4 YAML

YAML should not be used for the canonical data model or event stream. Its implicit typing and parser variation create avoidable interoperability risks. If enabled for configuration, use a documented restricted profile, disable arbitrary object construction, and validate the parsed result against the same schema as its JSON equivalent.

### 2.5 Binary payloads and model weights

AIDB should treat binary payloads as typed artifacts referenced by ordinary resource records. Store media type, byte length, cryptographic digest, format/version, creation source, and provenance. Large payloads may be stored separately from the text manifest.

For model weights, investigate established formats such as Safetensors rather than inventing an AIDB-specific tensor container. Weight artifacts require explicit model architecture/configuration references, tensor names and shapes, dtype information, provenance, licensing/usage metadata where applicable, and compatibility checks. AIDB should not execute or load an untrusted model artifact merely because it can store it.

A future weight-editing workflow must be transactional at the artifact level: preserve the original immutable artifact, write a new candidate, record the exact transformation and tool/model versions, evaluate against declared tests, and promote only after explicit policy/approval gates. Rollback must remain possible. This proposal does not authorize autonomous modification or deployment of model weights.

### 2.6 Documents such as PDF

PDF, office documents, images, audio, and video may be preserved as original attachments. AIDB does not need to implement a universal viewer. Optional extractors can produce text, metadata, thumbnails, transcripts, or embeddings as new derived artifacts. Each derivative records its source artifact digest, extractor identity/version, parameters, and time. Failure to extract must not destroy or replace the original.

## 3. Portable interchange package

Proposed logical package:

- A UTF-8 JSON manifest describing package version, AIDB contract version, resources, relationships, provenance, included change history, and referenced payloads.
- JSONL streams for large ordered collections or change history where appropriate.
- A payload area containing opaque binary/original artifacts, each identified by digest and media type.
- Optional human-readable README/summary in Markdown.

The package may be transported as a directory, archive, or stream. No one container (ZIP, TAR, SQLite file, or other) is declared canonical yet. The package semantics must remain identical regardless of container.

Import must validate versions, references, sizes, digests, and authorization policy before committing. It must support a dry-run/inspection mode and report conflicts. Export/import round trips must preserve all fields declared portable, including relationships, provenance, revisions, and history according to the selected export profile.

## 4. Compatibility and evolution

Every manifest and structured record must identify the AIDB contract/schema version needed to interpret it. The specification must define:

- required fields and their types;
- optional fields and explicit null/absence behavior;
- extension namespaces and unknown-field handling;
- compatibility rules for older and newer readers;
- deprecation and migration behavior;
- timestamp format and timezone semantics;
- stable identifier and relationship semantics;
- integrity digests and, later, signature rules.

Readers may ignore unknown optional extensions, but must reject unknown required features. Writers must not silently drop data they cannot represent. If lossless round-trip is impossible, the operation must fail or require an explicitly selected lossy conversion with a report.

A schema migration creates a new versioned representation and records the migration provenance. It must not rewrite the only copy of the source data.

## 5. Platform compatibility matrix

The following is a **target and validation plan**, not a claim that current AIDB builds or passes tests on every platform.

| Platform | Desired role | Main constraints to validate | Proposed support evidence |
|---|---|---|---|
| Windows | Primary desktop/server target | Filesystem path/locking semantics, atomic replacement, Unicode paths, packaging, permissions | CI build and contract suite on supported Windows versions |
| Linux | Primary desktop/server target | Filesystem differences, permissions, locking, distro/library availability | CI build and contract suite on at least one current LTS distribution |
| macOS | Primary desktop target | Filesystem semantics, signing/notarization for distribution, Apple Silicon and Intel where supported | CI build and contract suite on supported macOS runners |
| OpenBSD | Explicit portability target | Compiler/library availability, pledge/unveil if used, sandbox and filesystem behavior | Native build and core contract suite on OpenBSD; document unsupported adapters |
| iOS | Longer-term mobile target | App sandbox, lifecycle/background limits, file-provider access, signing, storage quotas, no assumption of daemon/service availability | Buildable library/core plus mobile integration tests; define local embedded mode |
| Android | Longer-term mobile target | App sandbox, scoped storage, lifecycle/background limits, ABI/NDK variants, packaging | Buildable library/core plus Android integration tests; define local embedded mode |

### 5.1 Portability boundary

Keep the semantic core independent of OS APIs. Isolate filesystem access, locking, clocks, entropy, networking, process management, and platform key storage behind narrow interfaces. Avoid assuming a long-running daemon, writable global directories, case-sensitive paths, POSIX-only APIs, or unrestricted background execution.

C may be a useful shared implementation boundary, but language choice alone does not establish portability. Any proposed C core must be tested on target compilers and platforms, with memory-safety tooling where available. The public C ABI draft remains unimplemented and must not be treated as proof of a working cross-platform core.

### 5.2 Support tiers

Use explicit tiers rather than claiming universal support:

- **Tier 0 — design-compatible:** architecture does not intentionally depend on platform-specific behavior.
- **Tier 1 — builds:** source builds successfully on the target.
- **Tier 2 — core contract tested:** serialization, storage, import/export, and recovery tests pass on the target.
- **Tier 3 — production supported:** packaging, security review, upgrade path, operational documentation, and release testing are in place.

A platform must not be advertised at a higher tier than the latest recorded test evidence supports.

## 6. Security and trust requirements

- Treat all imported files, archives, manifests, text, and model artifacts as untrusted input.
- Enforce configurable size, nesting, record-count, and decompression limits.
- Reject path traversal and unsafe archive entries; never extract arbitrary paths.
- Validate digests before accepting payloads; a digest proves integrity against a known digest, not who authored the file.
- Keep identity, authentication, authorization, provenance, and trust distinct.
- Do not execute scripts, plugins, macros, or model code during import.
- Keep secrets and credentials out of portable exports by default; require explicit policy to export sensitive material.
- Ensure derived artifacts cannot overwrite their source originals.
- Make partial import failure and rollback behavior explicit.

## 7. Minimal conformance test plan

A language implementation conforms to the initial profile only when it passes shared, implementation-neutral fixtures and tests for:

1. UTF-8 JSON parsing/serialization and invalid-input rejection.
2. Stable resource IDs, relationships, timestamps, revisions, and provenance.
3. JSONL streaming, ordering, truncation detection, and duplicate handling.
4. Unknown optional versus unknown required extension behavior.
5. Export/import round trip preserving the selected portability profile.
6. Payload digest and byte-length verification.
7. Safe handling of malformed, oversized, and path-traversal inputs.
8. Explicit failure on unsupported required versions or lossy conversion.
9. Recovery after interrupted write/import, with no silently corrupted committed state.
10. Cross-language fixtures producing equivalent semantic results.

The same fixtures should be consumed by Python and any future C, Rust, Go, or other implementation. The fixtures, not a particular implementation's internal classes, define conformance.

## 8. Recommended staged implementation

1. **Specification only:** agree on registry IDs, manifest shape, version rules, support tiers, and the smallest portable profile.
2. **Golden fixtures:** add hand-reviewed JSON/JSONL fixtures and invalid cases; no rewrite required.
3. **Python reference adapter:** prove export/import round-trip behavior against fixtures, clearly labelled as reference implementation rather than normative architecture.
4. **Second-language spike:** implement a tiny independent reader/writer (C is one candidate) against the same fixtures to test whether the contract is genuinely language-neutral.
5. **Platform probes:** build and run core tests on Linux, Windows, macOS, and OpenBSD; separately assess iOS/Android embedded constraints.
6. **Binary artifact experiment:** store and validate one opaque payload and one Safetensors sample without executing or mutating model weights.
7. **Only then decide:** whether a C core, storage backend change, or broader rewrite is justified by measured results.

Do not start by writing a new storage engine, a PDF viewer, a model runtime, or assembly routines. First prove that independent implementations can exchange the same data without losing meaning.

## 9. Decisions still required

- Is JSON the normative first interchange encoding, with JSONL as the event-stream profile?
- What exact resource envelope and manifest fields are mandatory in v1?
- Which fields and history are guaranteed in the default portable export?
- Which digest algorithm is mandatory initially, and are signatures in scope for v1?
- Is a directory-based package sufficient for the first prototype, with archives as optional wrappers?
- Which platform gets the first CI conformance implementation, and which support tier is required before calling a platform supported?
- Which model-weight metadata and evaluation gates are required before weight artifacts become a supported first-class type?

Until these questions are resolved, this document remains a proposal. It deliberately avoids claiming that any unimplemented format, ABI, or platform target is already supported.
