# AIDB Project Context and Agent Handoff

Last reconciled: 2026-11-16
Status: living handoff; experimental project; update this file when material decisions, implementation status, or priorities change.

## Read this first

For any new human or AI session:

1. Read [`.aidb/session-context.yml`](../.aidb/session-context.yml) for a machine-readable orientation and canonical pointers, then read this file for the human-readable handoff. Neither is a substitute for source code or tests.
2. Read `AGENTS.md` for contributor rules and safety invariants.
3. Read `README.md` for the user-facing project overview and quick start.
4. Read `.aidb/protocol.yml` before interpreting or processing external AI requests; read `.aidb/knowledge.yml` for the knowledge index and authority rules.
5. Read `docs/repository-audit.md` for current risks, CI baseline, open PR triage, and launch blockers.
6. For the task at hand, read the relevant linked contract/design docs below and inspect current source/tests. Do not assume a design document means a feature is implemented.
7. Verify current branch, recent commits, CI, issues, and PRs before making status claims. Update this handoff and the audit when the verified state materially changes.

When a user supplies this repository URL in a fresh session, begin with this file and `AGENTS.md`, then fetch the current versions from the default branch. Do not rely on model memory or an old transcript as the source of truth.

## Mission

AIDB is an experimental, local-first, model-agnostic knowledge, memory, artifact, and coordination substrate for AI systems. It aims to let agents preserve durable information, provenance, project context, workflow state, and artifacts instead of starting from scratch in every session. It is not itself a model and does not automatically call external AI services.

The long-term goal is a modular, interoperable substrate that can serve constrained devices and very large deployments, with stable contracts and replaceable implementations. This is a direction, not a claim of production readiness or extreme-scale performance.

## AI-first development principle

AIDB is intended to be built and maintained primarily through capable AI agents, with human collaboration welcome. Routine progress should not depend on a human manually performing work an agent can safely and reliably complete. This is a project requirement, not a claim that autonomous development is already fully implemented.

Agents should be able to discover the current project state, understand contracts and constraints, plan bounded work, inspect and modify code, run checks, interpret actual tool output, repair failures, and leave a reviewable handoff. The repository is the durable source of truth; chat history and model-generated claims are not evidence.

Autonomy must remain evidence-driven and bounded. Agents must not bypass access controls, tests, provenance, review requirements, or execution isolation. Changes to persistent data, public interfaces, security boundaries, release state, or untrusted-code execution require the safeguards defined by the relevant contracts. Human review remains available for collaboration and higher-risk decisions; it should not be a substitute for automating routine, verifiable work.

Progress is measured by demonstrated workflows, not labels. A capability counts as implemented only when a repeatable test or recorded execution proves it. Track discovery, implementation, validation, failure recovery, and handoff separately; state what remains manual and why.

## Product and architecture requirements discussed so far

### 1. Language and API neutrality
- Keep contracts independent of any one programming language, model, agent framework, transport, cloud, or database engine.
- C is a candidate stable low-level ABI; `include/aidb/aidb.h` is a draft, not a functioning implementation. Idiomatic language bindings should preserve contract semantics.
- UTF-8 interoperable text boundaries, explicit byte lengths/ownership, stable machine-readable errors, and Unicode-safe storage are required design principles.
- Human-language neutrality includes Simplified/Traditional Chinese, Japanese, Arabic, mixed RTL/LTR, and preserving original content. Do not claim multilingual search quality without analyzers and tests.

### 2. Artifacts and provenance
- Treat artifacts as content objects, not merely filename extensions. Support text, documents, images, audio/video, code, assembly, archives, and opaque binary data through optional adapters and capability discovery.
- Preserve original bytes. Parsing, OCR, translation, normalization, decompilation, and other transformations must be explicit derived artifacts with provenance.
- Never execute imported content as a side effect of ingest, indexing, preview, inspection, or export.
- Preserve source identity, checksums, lineage, ownership, permissions, revisions, and uncertainty honestly.

### 3. Modularity and evolution
- Keep a small reliable core and optional modules behind versioned contracts with declared capabilities, dependencies, configuration, limits, and permissions.
- AIDB should improve as it accumulates data and feedback. The intended loop is observe → diagnose → propose → isolate/experiment → evaluate against a baseline → approve/promote → monitor/recover → learn.
- Knowledge organization, indexes, ranking, caches, adapters, schemas, and even core architecture may evolve through reviewed, tested, versioned migrations.
- Stable invariants include data integrity, identity, authorization, provenance, version/revision semantics, auditability, and recoverability. No unreviewed self-modification should bypass these invariants.
- Agents may submit competing proposals and evidence; preserve attribution and disagreement. Unreviewed content is not automatically accepted knowledge.

### 4. Speed, storage, and context efficiency
- Design for constrained and high-end environments using configurable resource budgets, not assumptions that all available resources should be consumed.
- Bound query work and response sizes; support pagination/cursors, cancellation, and streaming large objects.
- Prefer selective indexes, incremental processing, bounded caches, backpressure, and resumable background work.
- Keep canonical data separate from rebuildable derived data such as indexes, embeddings, summaries, and caches.
- Use compression and content-addressed deduplication where appropriate, while preserving original bytes and avoiding cross-tenant existence leaks.
- Return the smallest sufficient, evidence-backed context first; support token budgets, progressive disclosure, source-linked summaries, and compact task handoffs. Never dump the whole knowledge base into an agent context by default.
- Measure latency percentiles, throughput, memory, disk amplification, index size, and token use across representative workloads. Do not promise petabyte/exabyte performance without evidence.

### 5. Numeric/scientific and large data
- Preserve exact integer/decimal values when required; record array/tensor dtype, byte order, shape, strides, units, missing-value conventions, and precision/error metadata.
- Use chunked/range-accessible data for large artifacts where practical. Derived embeddings/visualizations remain versioned and rebuildable.
- Distinguish logical deletion, tombstones, and physical erasure; garbage collection must be reference-safe and observable.

## Current verified implementation boundary

The default branch has a Python reference implementation backed by SQLite. Existing source and tests cover core persistence, epistemic/provenance models, artifact lineage, agent-home resources and notes, relationships, concurrency/revisions, changes/checkpoints, home export/import, and an HTTP server. See current source and tests for exact behavior.

Known limitations:
- The project is experimental, not production-ready.
- The C header is a draft ABI; no implemented stable C ABI should be claimed.
- Proposed format adapters, universal agent compatibility, broad language bindings, autonomous self-evolution, adaptive resource profiles, distributed storage, and extreme-scale performance are not established runtime capabilities merely because design documents exist.
- The design documents below are proposals unless source code, tests, capability discovery, and CI prove implementation.
- The latest CI must be rechecked at task time; do not treat an old green run as proof the current HEAD passes.

## Architecture and contract index

- [Implementation roadmap](IMPLEMENTATION_ROADMAP.md) — evidence-driven P0–P3 checklist, explicit acceptance workflow, and PR reconciliation.
- [Repository audit and launch readiness](repository-audit.md) — verified baseline, known bugs, CI, open PRs, launch blockers.
- [One-stop agent substrate](one-stop-agent-substrate.md) — product scope and shared primitives.
- [Self-evolving architecture](self-evolving-architecture.md) — controlled continuous improvement, risk tiers, migration and recovery.
- [Performance, context efficiency, and scale](performance-context-and-scale.md) — bounded work, token budgets, resource profiles, benchmarks.
- [Storage efficiency and numeric data](storage-efficiency-and-numeric-data.md) — blob/metadata separation, compression, deduplication, chunked arrays and integrity.
- [Modular architecture](modular-architecture.md) — module boundaries, adapters, contracts.
- [Language-agnostic contract](language-agnostic-contract.md) and [C-first API proposal](c-first-api.md) — API semantics and draft ABI direction.
- [API design principles](api-design-principles.md) — ownership, errors, versioning, safety.
- [Multilingual and language-agnostic design](multilingual-and-language-agnostic.md) — Unicode, RTL, binding parity, language tests.
- [Agent compatibility and file formats](agent-compatibility-and-file-formats.md), [binary and assembly](binary-and-assembly.md), and [artifact protocol](artifact-protocol.md) — format-neutral artifacts and safe transformation.
- [Agent memory and knowledge entries](agent-memory-and-knowledge-entries.md) — durable memory and typed knowledge.
- [Live build and emulation](live-build-and-emulation.md) — proposed runtime/toolchain adapter boundaries; do not execute untrusted artifacts.
- [Invariants](invariants.md), [epistemic contract](../EPISTEMIC_CONTRACT.md), and [audit findings](../AUDIT_FINDINGS.md) — integrity and provenance requirements.
- [Contributor guide](../CONTRIBUTING.md) and [security policy](../SECURITY.md) — review and security workflow.

## Current work queue

Verified snapshot on 2026-11-16:

- Default branch: `main`, commit `721e20bb159a861570320d9cdadf3147b7dc0d59`.
- Open pull requests: 47. This is a live queue, not a merge plan; inspect each current diff, base/head SHA, review, and CI before taking action.
- PR [#106](https://github.com/usamaizm/AIDB/pull/106) adds CLI contract tests and was merged to `main` after all three CI jobs passed (Python 3.10, 3.11, 3.12), including compileall, Ruff, and pytest in run [43862813272](https://github.com/usamaizm/AIDB/actions/runs/43862813272). Merge commit: `721e20bb159a861570320d9cdadf3147b7dc0d59`.
- PR [#88](https://github.com/usamaizm/AIDB/pull/88) proposes stable JSON 500 responses for unexpected HTTP handler errors. Its review requested server-side exception logging while keeping client responses sanitized; do not treat it as approved or merged.
- PRs [#90](https://github.com/usamaizm/AIDB/pull/90), [#92](https://github.com/usamaizm/AIDB/pull/92), [#98](https://github.com/usamaizm/AIDB/pull/98), and [#104](https://github.com/usamaizm/AIDB/pull/104) overlap in `verify_home()`. Consolidate artifact blobs, change payload/revision-chain checks, snapshot content, and stored-row JSON validation before merging a coherent implementation.
- PRs #70–#105 include related artifact validation, import validation, export projection/portability, agents-table coverage, dataclass consolidation, schema/snapshot versioning, and paired documentation-claim PRs. Review code and its paired claim entry together; do not merge a claim-only PR as proof that its implementation landed.
- Older open proposals #8, #13–#16, #24–#25, #45, #49–#50, #55, #61, and #64 still need individual freshness/overlap review. The agent-discovery/network proposals #14, #15, #49, and #61 must be compared as a family rather than merged independently.
- The shared journal contains additional unpushed work claims from other contributors. Respect their stated ownership and verify whether branches/PRs have appeared before editing overlapping files.

Next priorities:
1. Reconcile and land high-confidence correctness fixes in small, tested, non-overlapping batches.
2. Close the remaining HTTP error-handling and deployment-safety gaps without leaking internals or silently swallowing diagnostics.
3. Complete import/export/snapshot verification, rollback, privacy, and idempotency coverage.
4. Add reproducible benchmarks before performance or scale claims.
5. Demonstrate the AI development loop with repeatable evidence, including failure repair and handoff; documentation alone is insufficient.

This queue is a point-in-time snapshot. Refresh GitHub state before acting. No PR merge, public deployment, permission change, release, or destructive operation is authorized by this handoff.

## Decision and status rules

For every material feature or design:
- Label it **implemented**, **partially implemented**, **proposed**, **blocked**, or **deprecated** based on source/tests and current CI.
- Link evidence: source paths, tests, commits, CI runs, and relevant decisions.
- Record trade-offs and unresolved questions instead of silently presenting opinions as accepted policy.
- Do not claim full-repository security certification from a file-tree scan or documentation audit.
- Prefer incremental changes with regression tests. Update this handoff, `AGENTS.md`, the knowledge index, and repository audit when their respective information changes.

## Session handoff template

At the end of substantive work, leave:
- **Changed:** paths and behavior changed.
- **Verified:** commands/tests and exact CI run or commit evidence.
- **Not verified:** what could not be run or inspected.
- **Open decisions/risks:** unresolved choices and security/compatibility concerns.
- **Next step:** the single highest-value next action.

The repository is the durable source of truth. A fresh agent should be able to get oriented from this handoff without replaying a prior conversation, while still verifying live code and project state.
