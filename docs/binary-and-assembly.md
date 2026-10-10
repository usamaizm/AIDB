# Binary and Assembly Support

Status: proposed design; not yet implemented.

## Goal

AIDB should be able to store, identify, move, inspect, and preserve binary and assembly-related artifacts without assuming that every artifact is text or that every host can execute it. This is an extension of the language-neutral contract, not a change that makes AIDB itself an execution engine.

## 1. Binary artifacts

Binary data MUST be represented as bytes or as a reference to an artifact blob. It MUST NOT be silently decoded as UTF-8 text. Each binary artifact SHOULD include:

- opaque artifact ID;
- media type and format identifier;
- byte length;
- cryptographic digest plus named algorithm;
- optional filename and encoding metadata;
- provenance and transformation history;
- optional platform, architecture, ABI, and endianness metadata when relevant.

Large blobs SHOULD be stored through a blob-storage adapter, separate from metadata records. The contract must define whether a reference is local, portable, content-addressed, or remote. A portable export must include the blob or clearly declare that the blob is external and unavailable in that export.

## 2. Assembly artifacts

Assembly source MUST be stored as a text artifact with an explicit character encoding and an explicit target description. The target description SHOULD identify:

- instruction-set architecture (for example x86-64, AArch64, or RISC-V);
- syntax/dialect (for example Intel or AT&T syntax, where applicable);
- assembler and relevant version, if known;
- object format and ABI, where applicable;
- operating system or execution environment, if relevant.

Assembly is not portable merely because it is text. Instructions, calling conventions, system calls, relocation rules, and object formats depend on the target.

## 3. Executable and object files

Object files, libraries, firmware images, bytecode, and executables MUST be treated as opaque artifacts unless a format-specific parser is explicitly enabled. Format detection MUST be based on validated bytes, not just a filename or claimed MIME type.

Metadata inspection SHOULD be read-only by default. AIDB MUST NOT execute an artifact as a side effect of storing, indexing, previewing, importing, exporting, or hashing it.

## 4. Optional tooling adapters

Assembly, disassembly, compilation, emulation, and debugging belong in optional adapters, not in the core storage contract. Each adapter should declare:

- tool name and version;
- supported architectures and formats;
- inputs and outputs;
- required permissions;
- resource limits and timeout;
- whether the operation is deterministic;
- provenance linking outputs to inputs and tool configuration.

Adapters MUST treat artifacts as untrusted input. If execution or emulation is supported, it MUST be opt-in and isolated with explicit resource limits and access controls. The default installation should not execute imported binaries.

## 5. Integrity and safety

- Enforce configurable maximum artifact sizes and streaming limits.
- Compute and verify digests when blobs are ingested or exported.
- Avoid parsing untrusted files in a privileged process where possible.
- Never infer trust or permission from a file extension, signature field, or successful format parse alone.
- Keep artifact provenance separate from claims about the artifact's safety or authenticity.
- Validate snapshot references and blob availability before committing an import.

## 6. Contract-level operations

The language-neutral contract should eventually define operations equivalent to:

- `put_blob(bytes, metadata)` and `get_blob(artifact_id)`;
- `get_artifact_metadata(artifact_id)`;
- `verify_artifact(artifact_id, expected_digest)`;
- `export_artifact(artifact_id, options)` and `import_artifact(package)`;
- `record_transformation(input_ids, output_ids, tool, parameters, provenance)`.

These are proposed semantic operations, not current API symbols.

## 7. Suggested artifact categories

- `application/octet-stream` — unknown or generic binary;
- architecture-specific object/executable formats — declared with a format identifier;
- assembly source — text plus an explicit architecture and dialect;
- bytecode — declared runtime/VM and version;
- firmware or disk images — explicit format and target metadata.

Do not rely on media type alone to determine the binary's actual format.

## 8. Implementation plan

1. Extend the language-neutral contract with an artifact resource and blob-storage semantics.
2. Add JSON schemas and fixtures for binary metadata, assembly targets, and transformation provenance.
3. Implement streaming blob storage with size limits and digest verification.
4. Add C ABI operations for binary buffers and artifact metadata, using explicit buffer ownership.
5. Add round-trip tests proving binary bytes survive import/export unchanged.
6. Add assembly/disassembly support as optional adapters with declared tool versions and target architectures.
7. Keep execution, emulation, and debugging disabled by default; add separate threat-model and sandbox tests before enabling them.

## Current status

This document records the proposed design only. The current C header and Python implementation do not yet provide a verified, end-to-end binary/assembly API. Do not claim support until binary round-trip, integrity, format-validation, and adapter-isolation tests pass.
