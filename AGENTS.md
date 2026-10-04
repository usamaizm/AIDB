# Agent Maintenance Notes

This file is a durable handoff for human and AI contributors working on AIDB.

## What currently works

- AIDB has a Python reference implementation with SQLite-backed durable state.
- The epistemic model tracks artifact, extraction, interpretation, knowledge, and memory provenance.
- Artifact lineage and extraction-output provenance are validated rather than inferred silently.
- The agent-home foundation provides resources/notes, ownership and visibility, relationships, optimistic concurrency, durable cursorable changes, checkpoints, portable export/import, runtime specification, discovery, and explicit authorization for network writes.
- The architecture is intentionally language-, model-, transport-, network-, cloud-, and database-engine agnostic at the contract level.
- Node specifications are versioned runtime data rather than mutable history.
- Home export/import now preserves the complete home table set, including relationships, change history, and snapshots.

## What has caused problems

- Setuptools package discovery can accidentally treat repository-level directories as packages. Keep discovery explicitly constrained to the implementation package.
- Provenance must never label an artifact as derived without real extraction lineage.
- Extraction outputs must agree with the extraction's input artifact when parent lineage is asserted.
- Lineage cycle tests must not be blocked by artifact immutability triggers before the lineage invariant can be exercised.
- Home import can silently lose state if its table list diverges from export_home(). Keep export/import table coverage synchronized and restore in foreign-key dependency order.
- Home import must be atomic: validate rows/columns and roll back on any failure rather than leaving partial restored state.
- Snapshot tests previously contained dead conditional code and did not exercise restore_snapshot(). Tests must call the real recovery path.
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

As of October 4, 2026, the agent-home foundation PR (#11) and home export/import fix PR (#12) have been merged into main. PR #13 contains the next hardening pass for atomic, schema-safe home imports. The repository remains experimental; treat architecture and protocol details as evolving unless explicitly frozen.
