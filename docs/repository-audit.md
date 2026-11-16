# Repository Audit and Launch Readiness

Audit snapshot: 2026-11-16. This is a point-in-time engineering triage, not a line-by-line security certification.

## Current verified baseline

- Default branch: `main`, commit `ae8196aac1491c20cfbf35aa7481dbc74cf2e9f5` at the time of this audit. The repository remains experimental.
- Runtime: Python reference implementation backed by SQLite. `include/aidb/aidb.h` remains a draft; no stable compiled C ABI is implemented.
- CLI source currently exposes only `agent`, `search`, and `serve` subcommands in `aidb/__main__.py`. The database path defaults to `aidb.sqlite3`; `serve` defaults to loopback/private visibility. `AIDB_AUTH_TOKEN` is used when `--auth-token` is not supplied, and an explicit CLI token takes precedence. Do not document unsupported session/message/task CLI commands.
- CI workflow `.github/workflows/ci.yml` runs compileall, Ruff, and pytest on Python 3.10, 3.11, and 3.12.
- PR [#106](https://github.com/usamaizm/AIDB/pull/106), head `66b87198d507238118db96010d49ed09b83742f3`, passed all three matrix jobs in [run 43862813272](https://github.com/usamaizm/AIDB/actions/runs/43862813272) and was merged as `721e20bb159a861570320d9cdadf3147b7dc0d59`. The merge includes the CLI contract tests.
- The merged CLI-test change was verified on its PR head before merge; a separate push-triggered CI run for the resulting merge commit was not observed in this audit.
- The open PR search returned 42 pull requests at the latest snapshot. This backlog includes overlapping correctness work and paired documentation claims; it must be reconciled by diff and evidence, not bulk-merged.

## Implemented boundaries and known limitations

- Main contains SQLite-backed persistence, core epistemic/provenance models, artifact lineage, agent-home resources/notes, relationships, revisions/change feeds/checkpoints, home export/import, node specification, discovery foundations, and an HTTP server. Inspect current source/tests for exact semantics of each operation.
- Resource and note creation/update boundaries now reject invalid field types, non-strict JSON values, non-finite numbers, and invalid metadata before writing; regression coverage is in `tests/test_resource_creation_validation.py` and `tests/test_update_resource_validation.py`.
- The current package is not a production-ready public agent platform. Public deployment still needs a complete reviewed policy for authentication/authorization, TLS termination, timeouts, rate limiting, operational logging, and lifecycle management.
- The project does not yet establish universal file-format support, broad language bindings, a stable C ABI, autonomous self-evolution, distributed consensus/replication, sandboxed code execution, or petabyte/exabyte performance. Design documents are not implementation evidence.
- The currently exposed CLI is intentionally small: `agent`, `search`, and `serve`. The CLI contract regression suite landed in PR #106.

## CI and quality gate

The workflow installs `.[dev]`, compiles `aidb` and `tests`, runs Ruff, and executes pytest on Python 3.10/3.11/3.12. Ruff currently selects `E4`, `E9`, and `F`; it is a correctness-focused baseline, not a comprehensive style, type, or security scan. Always tie CI claims to the exact commit SHA and run URL.

## High-priority open PR clusters

There were 42 open PRs at audit time. Key clusters:

- [#106 — CLI contract tests](https://github.com/usamaizm/AIDB/pull/106): merged after its three-version CI matrix passed.
- [#71 — snapshot-contract versioning](https://github.com/usamaizm/AIDB/pull/71): merged; legacy snapshot stamps remain readable and new snapshots use `aidb-snapshot-v1`.
- [#109 — resource/note validation](https://github.com/usamaizm/AIDB/pull/109): merged with all three CI jobs green; the older duplicate PRs #100 and #102 were closed.
- [#73 — artifact import validation](https://github.com/usamaizm/AIDB/pull/73): remains open for review.
- [#88 — HTTP safe 500 responses](https://github.com/usamaizm/AIDB/pull/88): unexpected handler errors return sanitized JSON 500. A review requested server-side exception logging (for example `logger.exception`) and a corresponding test; without diagnostics, the catch-all risks hiding operational failures.
- [#90](https://github.com/usamaizm/AIDB/pull/90), [#92](https://github.com/usamaizm/AIDB/pull/92), [#98](https://github.com/usamaizm/AIDB/pull/98), [#104](https://github.com/usamaizm/AIDB/pull/104): overlapping `verify_home()` checks for artifact blobs, change payload/revision chains, snapshots, and stored-row JSON. Consolidate into one coherent function and test suite before merge; avoid four independent rewrites.
- #70–#105: additional artifact registration/import validation, agents-table export/import, explicit export projections, portability registry, canonical JSON/digests, schema/versioning, dataclass consolidation, and paired documentation claims. PR #71 snapshot versioning is merged; PR #109 now covers resource/note validation and supersedes #100/#102. Validate each remaining PR against current main and its paired claim.
- [#14](https://github.com/usamaizm/AIDB/pull/14), [#15](https://github.com/usamaizm/AIDB/pull/15), [#49](https://github.com/usamaizm/AIDB/pull/49), [#61](https://github.com/usamaizm/AIDB/pull/61): discovery, collaboration, and distributed networking overlap. Resolve identity, trust, authorization, canonicalization, compatibility, replication, and conflict semantics before implementation claims.
- #8, #13, #16, #24, #25, #45, #50, #55, and #64: older service, import, context, workflow, runtime-spec, artifact, and modularity proposals; compare unique deltas to main and newer PRs.

The discussion journal also records unpushed work claims. Check for branch/PR creation and respect claimed overlap before editing the same code.

## Priority order

1. Keep CI green on all supported Python versions and add regression coverage for actual defects.
2. Consolidate and review import/export/snapshot verification, strict input validation, and artifact/provenance integrity.
3. Fix HTTP error handling with both sanitized client responses and server-side diagnostics; verify authorization on every route before public exposure.
4. Reconcile the overlapping PR families above; do not bulk-merge or close without diff review.
5. Add Unicode/mixed-script preservation tests and measurable performance/storage benchmarks.
6. Demonstrate a bounded AI development loop with actual discovery, implementation, failure repair, verification, and handoff evidence.
7. Only then expand adapter, language-binding, distributed, and execution capabilities behind explicit contracts and isolation.

## Launch boundary

AIDB should be described as an experimental local-first Python/SQLite reference implementation. Do not describe it as production-ready, universally format-compatible, distributed-consistent, a stable C ABI, a secure code-execution environment, or an extreme-scale database until those properties are implemented, tested, and independently reviewed.
