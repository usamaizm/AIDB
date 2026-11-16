# AIDB — Current State

*Present-tense status, derived from the code. Snapshot: 2026-11-16, on the
Q30–Q33 landing stack (built on main `aa42b28`). Point-in-time: re-verify
before quoting. This page supersedes the status snapshots in
`docs/PROJECT_CONTEXT.md`, `docs/repository-audit.md`, and older sections
of `AGENTS.md`.*

## On the tree right now

- **Suite:** 643 passed, 3 skipped, 1 xfailed; `ruff check` and
  `ruff format --check` clean (run locally on this tree).
- **Package:** `aidb/` — 10 modules; `store.py` is a ~4,800-line
  single-class store over SQLite; 26 schema tables.
- **CLI:** `agent`, `search`, `serve` only — no session/message/task
  subcommands.
- **Coordination:** DISCUSSION.md is the structured journal, CHAT.md the
  informal channel; `.aidb/collaboration-log.md` is superseded history.

## Subsystem status (from code, not docs)

| Subsystem | Status |
|---|---|
| Home resources/notes, relations, revisions | Implemented, validated, tested |
| Artifacts + epistemic chain | Implemented; strict provenance/metadata validation on register + import paths |
| Export/import (`aidb-home-v1`) | Implemented for 9 portable tables; import validates rows before writes, atomic; streaming variants (`iter_export_home`, `export_home_json_to`, `import_home_stream`) implemented |
| `verify_home()` | Implemented: row JSON, blobs, snapshots, change/revision chains |
| Snapshots | Implemented **in place only** — `home_snapshots` is storage-only, never exported |
| Threading | Implemented: per-thread connections, WAL mode, `busy_timeout`; readers no longer serialize behind the write lock |
| Sessions | Implemented in the store: lifecycle, participants, session messages, per-session change cursors. **Not** exposed via CLI or HTTP |
| Change feed | `list_changes`/`public_changes` cursors + `GET /v1/changes?stream=1` NDJSON streaming, resumable via `after_id` |
| HTTP server | Implemented: bearer-token writes, inbound TLS ≥ 1.2, optional mutual TLS, bounded workers; non-loopback requires token + TLS |
| Outbound HTTPS client | Implemented (`aidb/http_client.py`): verified-TLS fetch of a peer's specification/agent card. No peer protocol behind it yet |
| Local agent collaboration (network.py) | Implemented as typed resources: profiles, offers, requests, responses, reviews |
| Canonical digests (canonical.py) | Primitives implemented; **not** wired into export/import/verify |
| Distributed networking | **Not implemented** — direction and boundaries accepted (see Decisions in force); no chunking, replication, or peer identity |
| Portability decisions | 9 portable / 1 storage-only / **16 undecided** (`aidb/portability.py`) |

## Lanes landing (Q30–Q33)

Built and verified locally; landing as pull requests in order. Status is
"landing" until each merge is observed on main.

- **Q30 — threading:** per-thread store connections, WAL, `busy_timeout`.
- **Q31 — sessions:** real lifecycle on the existing session schema,
  session messages, per-session change cursors.
- **Q32 — streaming:** generator-based export/import, NDJSON change feed,
  bounded artifact-blob streaming.
- **Q33 — legibility:** orientation/current-state/repo-map pages (this
  page is part of it), decision-log backfill, contradiction fixes,
  slimmed bootstrap.

## Decisions in force

- **D1–D4 accepted** (per-record digests + canonicalization; v1 legacy
  policy; artifacts in the default portable profile; stable external
  IDs) — now recorded in `docs/decision-log.md` (origin: GitHub
  issue #29). The v2 importer/verifier they unblock is not yet in the tree.
- **Distributed direction**: AIDB is to become a distributed system —
  data split into chunks scattered/replicated across nodes, data plane
  primary. Six consensus boundaries (key-bound identity first, one
  canonicalization rule, no silent v1 reinterpretation, discovery records
  as untrusted expiring hints, explicit partial replication, PR #49 as
  semantic layer only) are recorded in `docs/decision-log.md`.
- **Attribution**: checker-enforced values live in
  `scripts/check_pr_attribution.py`; `AGENTS.md` prose now matches it.

## Standing decisions awaiting the maintainer

- **CI format enforcement:** whether CI should run
  `ruff format --check` (the tree is format-clean; CI currently enforces
  `ruff check` only). This is a workflow-file change.
- **The errors.py envelope:** whether to adopt a structured error
  taxonomy (an `aidb/errors.py` module + an HTTP `{code, error, details}`
  envelope) in place of the current error style.
- **Q26 portability endorsement:** per-family dispositions for the 16
  undecided tables (epistemic pipeline portable-as-direction, deferred;
  collaboration-facade and node-local operational tables storage-only)
  await endorsement, and a venue (issue #29 or #18) for recording them.

## Known open (repo-derivable)

- 16 tables have no portability decision, incl. the whole epistemic
  pipeline (`aidb/portability.py`).
- `tasks` and `message_reads` are dead schema (no code paths);
  `tools`/`tool_calls` are write-only (no read-back API).
- The v2 home envelope (D1) has digest primitives but no importer/verifier.
- `docs/PROJECT_CONTEXT.md` and `docs/repository-audit.md` are snapshots
  that age quickly; for status, this page wins.
