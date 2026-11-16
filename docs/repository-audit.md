# Repository Audit and Launch Readiness

Audit snapshot: 2026-11-16 (refreshed after PR #136 merged). This is a point-in-time engineering triage, not a security certification.

## Current verified baseline

- Default branch: `main`, commit `635dca74845803a6820849ff026ace3d2a4e34a7`.
- Runtime: experimental Python reference implementation backed by SQLite. `include/aidb/aidb.h` remains a proposal; no stable compiled C ABI is implemented.
- CLI source exposes `agent`, `search`, and `serve` only. The database path defaults to `aidb.sqlite3`; `serve` defaults to loopback/private visibility. `AIDB_AUTH_TOKEN` is the environment fallback for `--auth-token`, and an explicit CLI token takes precedence.
- CI workflow `.github/workflows/ci.yml` runs compileall, Ruff, and pytest on Python 3.10, 3.11, and 3.12. The merged PRs below passed their own PR-head CI matrix; this is not a claim that a separate push-triggered workflow on the current main SHA was observed.
- There are 7 open PRs at this refresh: #142, #138, #139, #140, #64, #55, and #25. The current queue is limited to two transport hardening PRs, an additive onboarding PR, two blocked legacy code branches, and one documentation proposal.

## Merged implementation evidence

| PR | Merged scope | CI evidence |
|---|---|---|
| #71 | Snapshot contract versioning | Merged |
| #73 | Artifact import-row validation | Merged |
| #80 | Agents-table export/import | Merged |
| #106 | Public CLI contract tests | [43862813272](https://github.com/usamaizm/AIDB/actions/runs/43862813272) |
| #109 | Strict resource/note create and update validation | [43864558782](https://github.com/usamaizm/AIDB/actions/runs/43864558782) |
| #111 | Strict home import row and change-payload validation | [43865913472](https://github.com/usamaizm/AIDB/actions/runs/43865913472) |
| #112 | Read-only home integrity verification | [43866381773](https://github.com/usamaizm/AIDB/actions/runs/43866381773) |
| #113 | Server-side diagnostics for sanitized HTTP 500 responses | [43866856432](https://github.com/usamaizm/AIDB/actions/runs/43866856432) |
| #115 | Explicit v1 export projections and portability registry | [43867824641](https://github.com/usamaizm/AIDB/actions/runs/43867824641) |
| #116 | RFC 8785/JCS canonical JSON and record-digest primitive | [43868111389](https://github.com/usamaizm/AIDB/actions/runs/43868111389) |
| #117 | Restore historical `updated_at` fields in v1 projections | [43868719211](https://github.com/usamaizm/AIDB/actions/runs/43868719211) |
| #119 | Local resource-backed agent discovery/collaboration | [43870081165](https://github.com/usamaizm/AIDB/actions/runs/43870081165) |
| #136 | Consolidated nine Q8–Q16 contribution-claim records (documentation only) | Merged; no runtime code changed |

All listed PR runs passed compileall, Ruff, and pytest on Python 3.10/3.11/3.12.

## Implemented boundaries and remaining limitations

- Home import validates required fields, JSON values, references, and change-payload semantics before writes; the savepoint/rollback path remains in place.
- `verify_home()` is read-only and checks strict JSON shapes, snapshot format/hash/content, artifact blob existence/size/checksum, and change/revision/visibility history.
- Resource and note creation/update reject malformed values and non-strict JSON before persistence.
- HTTP unexpected GET/POST failures retain server-side tracebacks while returning a sanitized `internal_error` response. The server still lacks per-agent authorization scopes, multi-tenant isolation, rate limiting, and comprehensive request/operation timeouts.
- Full/private exports include portable agents-table rows. Public-only exports omit agent rows until the table has an explicit visibility policy; public discovery uses visibility-aware agent-profile resources.
- Export uses explicit per-table v1 projections; `updated_at` is preserved for resources and notes. `home_snapshots` remains storage-only and is not recursively exported.
- `aidb/canonical.py` implements RFC 8785/JCS canonical JSON and per-record SHA-256 digests. This pure library is not yet integrated into a versioned home envelope, import/export digest validation, or `verify_home()`.
- `aidb/network.py` implements local resource-backed agent profiles, offers, requests, collaboration requests, responses, and reviews. It is not peer-to-peer networking.
- No stable C ABI, broad language bindings, autonomous self-evolution, sandboxed code execution, distributed consensus/replication, or extreme-scale performance guarantee is established. Design documents are not implementation evidence.

## Open-work clusters

- **HTTP request safety — PR #142:** current-main branch; adds a 16-worker semaphore cap with 503 overload response, 10-second accepted-socket timeout, bounded backlog, POST-body lock isolation, and a real partial-body timeout test. Its exact-head CI run [43883296685](https://github.com/usamaizm/AIDB/actions/runs/43883296685) passed compileall, Ruff, and pytest on Python 3.10/3.11/3.12. The predecessor #137 passed CI before the worker-cap addition. Independent review remains outstanding. Socket I/O timeout does not bound long-running SQLite work; GET handlers still serialize reads and response writes under the shared lock.
- **HTTPS verification — PR #138:** current-main branch; CI run [43882236199](https://github.com/usamaizm/AIDB/actions/runs/43882236199) passed the same matrix. Independent review remains outstanding. This is inbound TLS and bearer-token verification only, not mTLS, peer identity, or distributed networking. Add a negative test using a trusted certificate with a mismatched hostname to isolate hostname-verification coverage.
- **Progressive onboarding — PR #139:** additive guide/template; CI run [43882238516](https://github.com/usamaizm/AIDB/actions/runs/43882238516) passed the same matrix. Independent review remains outstanding. The older PRs #45/#24 were closed because they were stale and the #45 branch removed mandatory contributor/AI-first safeguards.
- **Audit refresh — PR #140:** this documentation-only PR updates this audit and the session manifest; CI run [43883361499](https://github.com/usamaizm/AIDB/actions/runs/43883361499) passed the Python 3.10/3.11/3.12 matrix for the immediately prior audit head. Recheck the latest head after this refresh.
- **Adapter refactor — PR #64:** not mergeable; 88 commits behind current main and GitHub reports a dirty merge. The extracted service bypasses strict resource validation and the HTTP lock wraps request-body reading, regressing PR #137's slow-upload isolation. Rebuild from current main with shared validators and focused conformance tests; do not merge the existing branch.
- **Broad remediation — PR #55:** not mergeable; 92 commits behind current main and GitHub reports a dirty merge. Last independent exact-head review at `ab2374f79c6801ecd873561f10b2e8c92cddf59a` found Ruff `F821 AIDBError` and two failing tests; no current-head CI is visible. Much of the scope overlaps smaller merged PRs. Extract only unique, revalidated changes into focused PRs.
- **Phone-first contribution protocol — PR #25:** documentation proposal only. Its workflow inventory and branch-protection review are still outstanding; it does not change permissions or automations.
- **Superseded branches closed:** #14/#15 (older discovery/network branches superseded by #119), #24/#45 (onboarding superseded by #139), #74–#87 (claim-only entries consolidated by #136), and #133/#134/#137 (stale transport branches replaced by #138/#142). The earlier #129/#131 branches were also superseded.

No separate push-triggered CI run was observed for the current `main` commit `635dca7`; the green CI evidence above is tied to the exact PR heads, not a claim about a separate main-branch run.

## Launch boundary

AIDB should be described as an experimental local-first Python/SQLite reference implementation with a tested local collaboration layer. Do not describe it as production-ready, distributed, universally format-compatible, a stable C ABI, a secure code-execution environment, or an extreme-scale database until those properties are implemented, tested, and independently reviewed.
