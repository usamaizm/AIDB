# Repository Audit and Launch Readiness

Audit snapshot: 2026-10-10. This is a living triage record, not a claim that every file has had a line-by-line security review.

## Current verified baseline

- The default branch is `main`; the repository is experimental.
- The Python reference implementation uses SQLite. The C ABI header remains a draft and is not a functioning implementation.
- Before adding the Ruff gate, CI passed on Python 3.10, 3.11, and 3.12 with 24 tests.
- CI then exposed an HTTP integration failure: a threaded request used an SQLite connection created on another thread. The connection now permits cross-thread access, and HTTP handler database work is serialized with an instance lock.
- CI also exposed stale HTTP test expectations: a configured auth token means an unauthenticated write should receive 401, and the valid request must use the configured token. These assertions were corrected.
- The initial Ruff pass found a duplicate `Memory` class definition in `aidb/epistemic.py`; the legacy payload was renamed `LegacyMemoryRecord` so `Memory` refers to the canonical epistemic model. Regression tests cover both.
- `import_home` previously accepted caller-supplied SQL column identifiers and did not roll back all changes on failure. It now validates the payload, tables, columns, and scalar values before writing, then uses a savepoint so a constraint failure rolls back the import. Regression tests cover invalid columns and a foreign-key failure.

## CI and quality gate

The CI workflow installs development dependencies, compiles source and tests, runs Ruff correctness checks, and runs pytest on Python 3.10, 3.11, and 3.12.

Latest run at time of this snapshot: [GitHub Actions CI](https://github.com/usamaizm/AIDB/actions/workflows/ci.yml). Recheck the newest run before treating the baseline as green. Ruff currently selects import/syntax correctness and common runtime errors (`E4`, `E9`, `F`); style rules such as one-line compound statements are not yet enforced.

## Open pull-request triage

The following PRs were open when checked. GitHub reported `mergeable: false` for the sampled PRs; recheck each branch and its checks before merge. Do not merge solely to clear the queue.

- [#8 — online agent service](https://github.com/usamaizm/AIDB/pull/8): the basic HTTP server and `serve` CLI are already present on `main`. Compare the branch for unique changes instead of merging the entire stale branch. Public deployment still needs a reviewed TLS/reverse-proxy and authentication/authorization plan.
- [#13 — atomic, schema-safe home imports](https://github.com/usamaizm/AIDB/pull/13): its central safety fix has now been implemented directly on `main`, with additional validation and rollback tests. Reconcile or close the now-duplicated PR after confirming the branch diff.
- [#14 — agent discovery and contract-first evolution](https://github.com/usamaizm/AIDB/pull/14): introduces discovery/compatibility documentation and a manifest.
- [#15 — durable agent network loop](https://github.com/usamaizm/AIDB/pull/15): adds network/collaboration APIs and tests, and overlaps with #14 on the agent card, docs, seed knowledge, and discovery files. Review #14 and #15 together and consolidate shared files before merging either.
- [#16 — living project context and agent identity](https://github.com/usamaizm/AIDB/pull/16): documentation-only context proposal. Its file is not yet on `main`; review the proposal and merge only after the maintainer's intent is clear.

Closed PRs should remain part of the history; do not reopen or reapply their changes without identifying what is still missing from `main`.

## Priority order to reach a useful online alpha

1. Keep CI green on all supported Python versions and retain regression tests for each discovered bug.
2. Finish reviewing home import/export and snapshot/restore behavior, including idempotency, rollback, foreign keys, and privacy filtering.
3. Review provenance invariants and database-level artifact integrity against `EPISTEMIC_CONTRACT.md` and `AUDIT_FINDINGS.md`; convert historical/speculative findings into verified tests before changing schema.
4. Reconcile PR #8, #13, #14, #15, and #16. In particular, consolidate the overlapping agent-discovery/network work.
5. Harden the HTTP deployment boundary before public exposure: token handling, explicit authorization policy, TLS termination, request size limits, timeouts, rate limiting, and deployment documentation.
6. Add a minimal runnable agent job contract only after core persistence and service behavior are reliable. Compilation/emulation/decompilation remain proposed adapters, not implemented capabilities.
7. Add broader style/type checks gradually after current code has a clean baseline; avoid mass reformatting unrelated files.

## Launch boundary

AIDB can be described as a local experimental reference implementation. It should not be described as a production-ready public agent platform, operating-system kernel, universal emulator, or stable C ABI until those capabilities exist, are tested, and have an explicit support/security boundary.
