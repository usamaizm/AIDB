# Repository Audit and Launch Readiness

Audit snapshot: 2026-11-05, refreshed after the full-repository evaluation on issue #18. This is a living triage record, not a claim that every file has had a line-by-line security review.

## Current verified baseline

- The default branch is `main`; the repository is experimental.
- The Python reference implementation uses SQLite. The C ABI header remains a draft and is not a functioning implementation.
- Main head `3de365d36f3f5bd353a24c8fa8a0bb01921b0ba1` was verified by CI run [41974601882](https://github.com/usamaizm/AIDB/actions/runs/41974601882) on 2026-11-05: Python 3.10, 3.11, and 3.12 passed compile, Ruff, and pytest (128 passed, 3 skipped, 1 xfailed; the xfail is E1 N4b). Draft remediation PR [#55](https://github.com/usamaizm/AIDB/pull/55) has a passing matrix at run [42089972938](https://github.com/usamaizm/AIDB/actions/runs/42089972938) (129 passed, 3 skipped, 1 xfailed); it is not merged.
- CI then exposed an HTTP integration failure: a threaded request used an SQLite connection created on another thread. The connection now permits cross-thread access, and HTTP handler database work is serialized with an instance lock.
- CI also exposed stale HTTP test expectations: a configured auth token means an unauthenticated write should receive 401, and the valid request must use the configured token. These assertions were corrected.
- The initial Ruff pass found a duplicate `Memory` class definition in `aidb/epistemic.py`; the legacy payload was renamed `LegacyMemoryRecord` so `Memory` refers to the canonical epistemic model. Regression tests cover both.
- `import_home` previously accepted caller-supplied SQL column identifiers and did not roll back all changes on failure. It now validates the payload, tables, columns, and scalar values before writing, then uses a savepoint so a constraint failure rolls back the import. Regression tests cover invalid columns and a foreign-key failure.

## CI and quality gate

The CI workflow installs development dependencies, compiles source and tests, runs Ruff correctness checks, and runs pytest on Python 3.10, 3.11, and 3.12.

Latest run at time of this snapshot: [GitHub Actions CI](https://github.com/usamaizm/AIDB/actions/workflows/ci.yml). Recheck the newest run before treating the baseline as green. Ruff currently selects import/syntax correctness and common runtime errors (`E4`, `E9`, `F`); style rules such as one-line compound statements are not yet enforced.

## Open pull-request triage

Verified against the live GitHub API on 2026-11-05. Open PRs: #14, #15, #16, #24, #25, #45, #49, #50, and draft #55. Do not merge stale or overlapping branches without reviewing their current diff and CI.

- [#55 — audit remediation](https://github.com/usamaizm/AIDB/pull/55): draft first tranche. It removes the broken package-level WorkflowEngine export, validates artifact registration, consolidates duplicate epistemic models, and corrects README/authority claims. CI run #42089972938 passed the 3-version matrix. Remaining audit items are explicitly not complete.
- [#49 — durable agent discovery and collaboration](https://github.com/usamaizm/AIDB/pull/49) and [#50 — E1 companion](https://github.com/usamaizm/AIDB/pull/50): review as a stack. #50 must merge with or after #49, never before. #49's test_cli_surface backing-table mapping was the verified blocker in the latest review.
- [#14 — agent discovery](https://github.com/usamaizm/AIDB/pull/14) and [#15 — executable agent network](https://github.com/usamaizm/AIDB/pull/15): overlap with #49; do not merge blindly.
- [#16 — living context and agent identity](https://github.com/usamaizm/AIDB/pull/16): disposition pending.
- [#24 — agent onboarding](https://github.com/usamaizm/AIDB/pull/24) and [#45 — progressive onboarding](https://github.com/usamaizm/AIDB/pull/45): reconcile overlapping onboarding changes.
- [#25 — phone-first contribution protocol](https://github.com/usamaizm/AIDB/pull/25): parked pending attribution and scope review.

Closed PRs #8, #13, #26, #28, #33, #38, and #41 remain closed; do not reapply their changes without identifying a still-missing behavior.

## Launch boundary

AIDB can be described as a local experimental reference implementation. It should not be described as a production-ready public agent platform, operating-system kernel, universal emulator, or stable C ABI until those capabilities exist, are tested, and have an explicit support/security boundary.


## 2026-11-05 remediation update — draft PR #55

The following audit items have been addressed on [draft PR #55](https://github.com/usamaizm/AIDB/pull/55), not merged to main:

- The nonfunctional WorkflowEngine package export and its implementation module have both been removed.
- Artifact registration and portable import validate algorithm/digest shape, size, status, JSON metadata, and blob-to-metadata checksum agreement.
- Portable import no longer silently ignores non-primary-key SQLite constraint failures. Identical rows with matching primary keys remain idempotent; conflicting rows still reject atomically.
- Duplicate epistemic dataclasses are replaced by compatibility exports of the canonical `aidb.core` classes.
- Common Python API validation, missing-reference, import-conflict, and integrity failures now have stable error classes/codes. Resource creation, publication, and relationship writes use savepoints so compound mutations roll back atomically, including inside an outer transaction. JSON-backed resource inputs reject non-finite and non-serializable values. The HTTP adapter includes structured details, maps the contract error taxonomy to HTTP statuses, and returns a generic non-leaking `internal_error` envelope for unexpected handler exceptions.
- HTTP upload bodies are authenticated/read before acquiring the store's public connection guard; response serialization/writes happen after releasing it; and the production server sets a 10-second socket timeout with daemonized request threads and a bounded listen backlog.
- README capability claims and project orientation/handoff documents were refreshed.

**Observed verification:** CI run [42092557120](https://github.com/usamaizm/AIDB/actions/runs/42092557120) passed on Python 3.10, 3.11, and 3.12. Each job passed compile and Ruff; pytest reported 138 passed, 3 skipped, 1 xfailed. The remaining xfail is E1 N4b. This run predates the latest error-taxonomy, JSON-input validation, connection-guard, and HTTP error-envelope commits. No CI run has yet been observed for the latest PR head, so those changes remain unverified by CI. The latest branch head recorded here is `b85a14055552a9e4b2794a258d522d6aa27184ec`; comparison is 40 commits ahead / 1 behind `main`, and GitHub currently reports the PR not mergeable. Independent review and latest-head CI are still pending.

**Still blocked or in parallel:**
- N4b per-record tamper detection needs a versioned integrity and canonicalization profile; the current draft contract explicitly says canonical JSON hashing is not finalized.
- Resource deletion/tombstone behavior needs a retention and reference policy.
- Portable external IDs, default artifact inclusion, and the `aidb-home-v1` compatibility/migration rule need maintainer decisions.
- Import-ID validation and the phantom CLI session/task/message surface are claimed in a parallel contributor lane; do not duplicate or overwrite that work.
- HTTP multi-tenant/per-agent authorization and rate limiting remain beyond the current single-token local/self-hosted server model.

PR #55 remains a draft and is not merged. Its last passing CI is evidence for an earlier branch head only; it does not verify the latest commits or make the outstanding decisions complete. The `aidb.engine` module has since been removed; update this disposition if a replacement orchestration design is accepted.

