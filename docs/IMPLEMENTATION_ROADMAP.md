# AIDB Implementation Roadmap

Last reviewed: 2026-10-10  
Status: living checklist; refresh evidence from current `main` before treating an item as complete.

This is the actionable companion to [the project context](PROJECT_CONTEXT.md) and [the machine-readable session manifest](../.aidb/session-context.yml). It separates shipped behavior from design intent. “Done” requires code, regression tests, and current CI evidence where applicable.

## P0 — Keep the foundation reliable

- [x] Add a fast, durable session bootstrap for new agents.
  - Evidence: `/.aidb/session-context.yml`, `/docs/PROJECT_CONTEXT.md`, `/AGENTS.md`, README onboarding links.
- [x] Keep Python CI matrix on 3.10, 3.11, and 3.12 with compile, Ruff, and pytest.
  - Evidence: [latest previously completed onboarding CI](https://github.com/usamaizm/AIDB/actions/runs/38051323847). Recheck CI after code changes.
- [x] Add configurable bounds to HTTP note/resource list responses and change feeds; support offset pagination.
  - Implementation: `aidb/server.py`, `aidb/store.py`.
  - Tests: `tests/test_home_server.py`.
  - This item is pending CI verification for the current code commits until the new workflow run succeeds.
- [x] Reject HTTP request bodies larger than a configurable limit before reading/parsing the body.
  - Default limit: 1 MiB; oversized authorized POST receives HTTP 413.
  - Tests: `tests/test_home_server.py`.
  - This item is pending CI verification for the current code commits until the new workflow run succeeds.

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

## Pull-request reconciliation

- [ ] [#8 — online service](https://github.com/usamaizm/AIDB/pull/8): compare unique service changes against the server already on main; deployment must not be public by default.
- [ ] [#13 — atomic import](https://github.com/usamaizm/AIDB/pull/13): compare with the main-branch atomic/schema-safe import implementation and preserve any unique tests.
- [ ] [#14 — agent discovery](https://github.com/usamaizm/AIDB/pull/14) and [#15 — agent network](https://github.com/usamaizm/AIDB/pull/15): review together and consolidate overlapping files and contracts.
- [ ] [#16 — living context](https://github.com/usamaizm/AIDB/pull/16): compare remaining unique changes against the now-existing session manifest and handoff.

## Completion protocol

For each item:
1. Define acceptance criteria and tests before changing code.
2. Make the smallest coherent implementation change.
3. Run focused tests, compile checks, Ruff, and the full CI matrix when possible.
4. Record commit IDs and actual test/CI links; distinguish queued, running, passed, and failed.
5. Update this checklist only when evidence justifies changing status.
6. Record unresolved risks and the single next highest-value task.

**Not a promise:** this roadmap records all known major workstreams from the project discussion; it does not mean all goals can be safely completed in one pass. Preserve correctness and honest evidence over premature completion claims.
