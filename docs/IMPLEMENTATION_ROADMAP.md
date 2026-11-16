# AIDB Implementation Roadmap

Last reviewed: 2026-11-16  
Status: living checklist; refresh evidence from current `main` before treating an item as complete.

This is the actionable companion to [the project context](PROJECT_CONTEXT.md) and [the machine-readable session manifest](../.aidb/session-context.yml). It separates shipped behavior from design intent. “Done” requires code, regression tests, and current CI evidence where applicable.

## P0 — Keep the foundation reliable

- [x] Add a fast, durable session bootstrap for new agents.
  - Evidence: `/.aidb/session-context.yml`, `/docs/PROJECT_CONTEXT.md`, `/AGENTS.md`, README onboarding links.
- [x] Keep Python CI matrix on 3.10, 3.11, and 3.12 with compile, Ruff, and pytest.
  - Evidence: [latest previously completed onboarding CI](https://github.com/usamaizm/AIDB/actions/runs/38051323847). Recheck CI after code changes.
- [x] Add configurable bounds to HTTP note/resource list responses and change feeds; support offset pagination.
  - Implementation: `aidb/server.py`, `aidb/store.py`; regression coverage: `tests/test_home_server.py`.
- [x] Reject HTTP request bodies larger than a configurable limit before reading/parsing the body.
  - Default limit: 1 MiB; oversized authorized POST receives HTTP 413. Regression coverage: `tests/test_home_server.py`.
- [ ] Add regression tests for the exposed CLI command contract.
  - Proposed in [PR #106](https://github.com/usamaizm/AIDB/pull/106); CI run [43862813272](https://github.com/usamaizm/AIDB/actions/runs/43862813272) passed Python 3.10/3.11/3.12. Keep unchecked until merged to `main`.

## P0 — Demonstrate the AI development loop

- [ ] Define a repeatable agent task format with explicit scope, acceptance criteria, allowed tools, and risk level.
- [ ] Add a repository-state discovery command or documented tool path that returns branch/commit, project manifest, relevant tests, and active work without dumping the whole repository into context.
- [ ] Demonstrate an agent completing a bounded change from discovery through implementation, tests, and a reviewable handoff using actual tool results.
- [ ] Add a failure-repair exercise: deliberately fail a test, require the agent to diagnose the observed output, fix the cause, and rerun the test.
- [ ] Record what remains manual, unavailable, or permission-gated; do not call the workflow autonomous if a hidden human step is required.
- [ ] Keep external/destructive actions, releases, permission changes, and untrusted-code execution behind explicit safeguards.

Acceptance evidence: reproducible scripts or workflow runs, test results, and a handoff artifact. Documentation alone does not complete this milestone.

## P1 — Close correctness and service-safety gaps

- [ ] Re-audit home export/import and snapshot/restore: atomicity, idempotency, foreign keys, privacy filtering, malformed inputs, and recovery after interruption.
- [ ] Add/verify request timeouts, server lifecycle behavior, consistent error envelopes, and malformed/oversized request handling.
- [ ] Review the public/private visibility rules on every HTTP route, including change-feed cursor behavior and authorization.
- [ ] Verify artifact integrity and provenance invariants against `EPISTEMIC_CONTRACT.md`, `AUDIT_FINDINGS.md`, and `docs/invariants.md`.
- [ ] Add tests for Unicode and mixed-script text, including Simplified/Traditional Chinese, Japanese, Arabic, and mixed RTL/LTR preservation.
- [ ] Reconcile open PRs #8, #13, #14, #15, and #16. Compare current diffs first; do not blind-merge or close them.

## P2 — Deliver measurable speed and efficiency

- [ ] Add reproducible benchmark fixtures for ingest, exact lookup, list pagination, retrieval, export/import, and concurrent access.
- [ ] Capture baseline p50/p95/p99 latency, throughput, peak memory, database size, index size, and context-token cost.
- [ ] Eliminate N+1 read patterns in list endpoints with batched SQL reads; measure before/after.
- [ ] Add keyset/cursor pagination where offset pagination becomes costly, with stable ordering and documented cursor semantics.
- [ ] Add streaming/chunked artifact ingest, export, and restore for large objects.
- [ ] Implement token-budgeted context assembly with source-linked compact summaries and progressive disclosure.
- [ ] Add resource budgets, cancellation, and bounded background work only with tests for cancellation and recovery.
- [ ] Add content-addressed blob storage and optional compression after byte-preservation and privacy constraints are tested.
- [ ] Do not claim petabyte/exabyte capability without representative benchmarks and a clear deployment architecture.

## P3 — Expand the modular substrate safely

- [ ] Specify and implement versioned adapter contracts and capability discovery, then prove them with at least one real adapter.
- [ ] Decide and implement the supported stable C ABI; the current header is a proposal, not a shipped ABI.
- [ ] Add language bindings only after the language-neutral semantics, error model, ownership, and byte/text rules are stable.
- [ ] Add explicit sandboxed toolchain adapters for build/emulation/decompilation; never execute imported content during ingest, indexing, preview, or export.
- [ ] Implement reviewed self-improvement workflows with baselines, isolation, approvals, audit logs, rollback, and recovery before any autonomous structural changes.
- [ ] Consider distributed storage only after local durability, replication semantics, access controls, and recovery have measurable tests.

## Pull-request reconciliation (snapshot 2026-11-16)

There are 47 open PRs. The following are priority review clusters, not merge instructions:

- [#106 — CLI contract tests](https://github.com/usamaizm/AIDB/pull/106): all three CI matrix jobs passed on its head in run [43862813272](https://github.com/usamaizm/AIDB/actions/runs/43862813272); still open and not yet part of main.
- [#88 — HTTP safe 500 responses](https://github.com/usamaizm/AIDB/pull/88): review requested server-side exception logging; keep client error bodies sanitized.
- [#90](https://github.com/usamaizm/AIDB/pull/90), [#92](https://github.com/usamaizm/AIDB/pull/92), [#98](https://github.com/usamaizm/AIDB/pull/98), [#104](https://github.com/usamaizm/AIDB/pull/104): overlapping `verify_home()` integrity lanes; consolidate before merge.
- #70–#105: related validation, schema/versioning, export/import, portability, and documentation-claim work. Review implementation PRs with their paired claim PRs and ensure claims match what actually lands.
- [#14](https://github.com/usamaizm/AIDB/pull/14), [#15](https://github.com/usamaizm/AIDB/pull/15), [#49](https://github.com/usamaizm/AIDB/pull/49), [#61](https://github.com/usamaizm/AIDB/pull/61): overlapping discovery, collaboration, and networking proposals; compare contracts and security boundaries as one family.
- #8, #13, #16, #24, #25, #45, #50, #55, and #64: inspect for unique changes versus current main and newer PRs; do not merge stale branches wholesale.

Before acting on any PR, fetch its current diff, base/head SHAs, review threads, and latest CI. A green CI run on one PR does not validate main or another branch.

## Completion protocol

For each item:
1. Define acceptance criteria and tests before changing code.
2. Make the smallest coherent implementation change.
3. Run focused tests, compile checks, Ruff, and the full CI matrix when possible.
4. Record commit IDs and actual test/CI links; distinguish queued, running, passed, and failed.
5. Update this checklist only when evidence justifies changing status.
6. Record unresolved risks and the single next highest-value task.

**Not a promise:** this roadmap records all known major workstreams from the project discussion; it does not mean all goals can be safely completed in one pass. Preserve correctness and honest evidence over premature completion claims.
