# Agent Maintenance Notes

This file is a durable handoff for human and AI contributors working on AIDB.

## What currently works

- AIDB has a Python reference implementation with SQLite-backed durable state.
- The epistemic model tracks artifact, extraction, interpretation, knowledge, and memory provenance.
- Artifact lineage and extraction-output provenance are validated rather than inferred silently.
- The agent-home foundation provides resources/notes, ownership and visibility, relationships, optimistic concurrency, durable cursorable changes, checkpoints, portable export/import, runtime specification, discovery, and explicit authorization for network writes.
- The architecture is intentionally language-, model-, transport-, network-, cloud-, and database-engine agnostic at the contract level.
- Node specifications are versioned runtime data rather than mutable history.
- Home export/import preserves relationships, change history, and snapshots.

## What has caused problems

- Setuptools package discovery can accidentally treat repository-level directories as packages. Keep discovery explicitly constrained to the implementation package.
- Provenance must never label an artifact as derived without real extraction lineage.
- Extraction outputs must agree with the extraction's input artifact when parent lineage is asserted.
- Lineage cycle tests must not be blocked by artifact immutability triggers before the lineage invariant can be exercised.
- Home import must cover every table exported by export_home(), restore in dependency order, validate the payload schema, and roll back on any failure.
- Snapshot tests must exercise restore_snapshot() directly; dead conditional test paths are not coverage.
- Do not assume an HTTP/cloud deployment is required; AIDB is self-hostable and transport-adapter based.
- Do not claim CI/tests are green unless a current run has actually been observed.
- Review stacked PRs against the current main; old PRs may be based on superseded commits.

## Contributor workflow

1. Inspect current main before starting work.
2. Identify whether an existing PR already contains the intended change.
3. Prefer small, coherent branches and PRs over speculative feature accumulation.
4. Run the relevant tests when execution is available and record the result accurately.
5. Preserve provenance, privacy, portability, and compatibility invariants.
6. Update this file when a bug, invariant, architectural decision, or contributor workflow lesson is important enough to help the next agent.

## Known status

As of October 4, 2026, PRs #11 and #12 are merged into main. PR #13 contains the atomic, schema-safe home-import hardening pass. The repository remains experimental; treat architecture and protocol details as evolving unless explicitly frozen.
## Agent and file-format compatibility

- Keep `AGENTS.md` as repository-level contributor instructions; keep `README.md` human-facing and `docs/` authoritative for architecture and contracts.
- Default to Markdown for instructions and prose, but support plain text and other file formats as artifacts. Do not infer semantics from file extensions alone.
- Follow `docs/agent-compatibility-and-file-formats.md` for the proposed artifact metadata, capability discovery, format adapters, and ingestion rules.
- Follow `docs/binary-and-assembly.md` for the proposed binary and assembly artifact rules.
- Preserve original bytes; treat extraction/conversion as explicit, provenance-tracked transformations. Never execute imported artifacts as a side effect of ingest, indexing, preview, or export.
- Do not claim a format or agent protocol is implemented until capability discovery and relevant conformance tests demonstrate it.
## Modularity

- Treat `docs/modular-architecture.md` as the proposed guide for module boundaries, dependency direction, adapter/plugin contracts, and incremental refactoring.
- Keep the core independent of concrete storage engines, transports, language bindings, agent frameworks, model providers, and file-format parsers.
- Prefer documented interfaces and conformance tests over directory-only separation. Do not split modules into services/packages prematurely.
- New optional capabilities must declare their contract version, dependencies, capabilities, configuration, and permissions; unsupported capabilities should return stable errors.
- Refactor incrementally after inspecting current dependencies and tests. Do not claim the architecture is implemented or tests pass without evidence.
## Product direction: one-stop substrate for agents

- Treat `docs/one-stop-agent-substrate.md` as the product-scope proposal: shared agent data/memory/artifacts with a small stable core and optional modules.
- Prioritize reliable shared primitives and conformance tests before accumulating integrations or specialized features.
- Keep search, embeddings, parsing, OCR, model providers, and agent-framework integrations optional; advertise support through capability discovery.
- Preserve access control, provenance, byte-safe artifacts, portability, revision checks, and explicit side-effect boundaries.
- Avoid describing AIDB as a replacement for every database or specialized system. Integrate through explicit adapters when that is more appropriate.
- Treat the document as intended direction, not a statement that all listed features are already implemented.
