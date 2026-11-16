# AIDB Orientation — read this first

*Every statement below is checked against the code on the tree that carries
this page. If this page and the code disagree, the code wins — file an issue
against this page. For present-tense project status, see
`docs/current-state.md`; for everything else, see `docs/repo-map.md`.*

## Bootstrap budget

The mandatory bootstrap set is three files: `.aidb/session-context.yml`,
this page, and `docs/current-state.md`. **Budget: the set must stay under
40,000 characters total.** (The previous bootstrap set measured ~168K
characters.) Everything else in the repo is loaded on demand via
`docs/repo-map.md`. If you edit one of the three files, keep the set inside
the budget.

## What AIDB is

AIDB is a single-node, local-first data store for AI agents: a Python
package over one SQLite file. An agent "home" in that file holds resources
and notes with ownership/visibility, content-addressed artifacts with
provenance, an epistemic chain (artifact → extraction → interpretation →
knowledge → memory), sessions, and a durable change log — exportable and
importable as one portable JSON payload (`aidb-home-v1`). A small HTTP
adapter serves one home to local or token-authenticated remote callers,
and an outbound HTTPS client can fetch a peer node's public specification
and agent card. AIDB does not run models, and it does **not** yet connect
nodes to each other: the distributed peer protocol is decided direction,
not implemented behavior (see PLANNED).

## Core concepts

- **Home** — one SQLite database = one node's world. Everything below lives in it.
- **Resource / note** — the generic content unit (`home_resources`, `notes`):
  typed, owned, public/private, revisioned; every write appends to the change log.
- **Artifact** — a content object with metadata + provenance; bytes live in
  `artifact_blobs`, keyed separately from the metadata row.
- **Epistemic chain** — artifacts feed extractions, whose outputs feed
  interpretations, which ground knowledge records, which can be remembered.
  Lineage is validated, never inferred silently.
- **Change log & snapshots** — `home_changes` is an append-only, cursorable
  history. Snapshots are whole-home checkpoints *inside one database only*;
  `home_snapshots` is storage-only and is never exported.
- **Session** — a scoped collaboration context (`sessions`,
  `session_participants`, `messages`): participants join, post messages,
  and follow the changes their fellow participants make via per-session
  change cursors. Store-level API only — no CLI or HTTP surface yet.
- **Specification** — the node describes itself with versioned runtime data
  (`node_specifications`), not a frozen config file.
- **Portability registry** — `aidb/portability.py` records, per table,
  whether it travels in the export payload (`portable`), is deliberately
  kept home (`storage-only`), or has no decision yet (`undecided`). The
  registry — not prose — is the source of truth for the export table list.
- **Agent collaboration (local)** — agent profiles, knowledge
  offers/requests, responses and reviews are *ordinary resources* with
  special types (`aidb/network.py`). Discovery is a local query over
  public resources.

## Concept → module → table map

Line anchors are approximate for `aidb/store.py` (one `AIDB` class,
~4,800 lines); search by method name.

| Area | Code | Tables |
|---|---|---|
| Store core, schema, threading (per-thread connections, WAL, `busy_timeout`) | `aidb/store.py` ~540–910 | all 26 (schema ~663–910) |
| Agents, sessions, session messages, per-session change cursors | store.py ~1317–1570 | agents, sessions, session_participants, messages |
| Epistemic pipeline | store.py ~1580–1980 | extractions, extraction_outputs, interpretations, epistemic_knowledge, epistemic_knowledge_relations, epistemic_memory |
| Artifacts + blobs (incl. `iter_artifact_content` chunked reads) | store.py ~1980–2230 | artifacts, artifact_blobs |
| Legacy memory (`remember`/`recall`) | store.py ~2230–2320 | memories |
| Home resources & notes | store.py ~2320–2570 | home_resources, notes |
| Specification / node identity | store.py ~2570–3130 (`current_specification`) | node_identity, node_specifications |
| Integrity verification (`verify_home`) | store.py ~3127 | reads all portable tables |
| Export / import (`aidb-home-v1`), buffered + streaming (`iter_export_home`, `export_home_json_to`, `import_home_stream`) | store.py ~3140–4420 | the 9 portable tables (below) |
| Relations, updates, public change feed (`public_changes`, `iter_public_changes`) | store.py ~4178–4500 | resource_relations, home_changes |
| Snapshots (in-place only) | store.py ~4462–4494 | home_snapshots |
| Legacy knowledge, events, tools | store.py ~4668–4780 (`add_document`/`search`, `add_event`/`list_events`, `register_tool`/`log_tool_call`) | knowledge, workflow_events, tools, tool_calls |
| Dataclasses | `aidb/core.py` (`aidb/epistemic.py` is a re-export shim) | — |
| Canonical JSON + record digests (RFC 8785) | `aidb/canonical.py` | — (not yet wired into export/import) |
| Portability registry (which tables travel) | `aidb/portability.py` | — |
| Local agent discovery/collaboration | `aidb/network.py` | home_resources (typed), resource_relations |
| Outbound HTTPS client (fetch peer specification / agent card) | `aidb/http_client.py` | — |
| HTTP adapter | `aidb/server.py` — routes: `/healthz`, `/specification`, `/.well-known/aidb.json`, `/.well-known/agent-card.json`, `/v1/notes`, `/v1/resources`, `/v1/resources/<id>/relations`, `/v1/changes` (incl. `?stream=1` NDJSON mode) | — |
| CLI | `aidb/__main__.py` — commands: `agent`, `search`, `serve` only | — |

## REAL / PLANNED / DEAD

### Real (implemented + tested)

- Resources/notes CRUD with ownership, visibility, optimistic-concurrency revisions.
- Artifacts with validated registration, lineage, byte storage; epistemic chain end-to-end.
- Change log with cursors (`list_changes`, `public_changes`); snapshots create/restore in place.
- Export/import of the 9 portable tables: node_identity, node_specifications,
  home_resources, notes, resource_relations, home_changes, artifacts,
  artifact_blobs, agents. Public-only exports filter private rows and omit agents.
- Streaming export/import (`iter_export_home`, `export_home_json_to`,
  `import_home_stream`) and bounded blob reads (`iter_artifact_content`) —
  whole homes never need to be materialized in memory.
- `verify_home()` read-only integrity checks (rows, blobs, snapshots, change payloads).
- Threading: the store gives each thread its own connection (WAL mode,
  `busy_timeout`); concurrent readers no longer serialize behind the write lock.
- Sessions: full lifecycle (create/join/leave/close), participant messages,
  and per-session change cursors — store API only (see PLANNED for surfaces).
  Closing is terminal: a closed session refuses new joins and messages
  (leaving a closed session is still allowed), and only participants may
  post to an active one.
- HTTP server: loopback by default; non-loopback requires a ≥32-char bearer
  token **and** TLS cert/key (TLS ≥ 1.2); optional mutual TLS; bearer token
  gates writes; `GET /v1/changes?stream=1` streams NDJSON, resumable by cursor.
- Outbound HTTPS client (`aidb/http_client.py`): verified TLS, fetches a
  peer's specification/agent card. Fetched documents are untrusted data
  until validated — this is document fetch, not a peer protocol.
- Local agent profiles/discovery/offers/requests/responses/reviews as resources.
- `register_agent`, `remember`/`recall`, `add_document`/`search`,
  `add_event`/`list_events`, and `register_tool`/`log_tool_call`
  (write-only: no read-back API for tools/tool_calls beyond the row a call returns).

### Planned (decided or proposed — NOT implemented)

- **Distributed networking**: chunking, key-bound peer identity, replication.
  Direction and boundaries are accepted (see `docs/decision-log.md`);
  architecture proposal in `docs/distributed-networking.md`. No peer
  protocol, handshake, or chunk transfer exists yet.
- **aidb-home-v2 envelope**: D1–D4 accepted 2026-11-15 (recorded in
  `docs/decision-log.md`; origin: GitHub issue #29). `aidb/canonical.py`
  digest primitives exist but are not wired into export/import/verify yet.
  A v2 importer/verifier is owed.
- **Portability decisions for the 16 undecided tables** (the epistemic
  pipeline, knowledge/memories, tools/tool_calls, workflow_events, and the
  session/message/task tables): per-family recommendations exist (the Q26
  brief); maintainer endorsement is outstanding.
- **Session surfaces**: sessions have no CLI subcommand and no HTTP route yet.
- C ABI (`include/aidb/aidb.h` is a draft header), language bindings, format
  adapters, embeddings/search quality, self-evolution: proposals only.

### Dead (present in schema or files, no code behind it)

- Tables `tasks` and `message_reads`: created by the schema, referenced
  nowhere else as data — no writes, no reads, no API. (`tasks` appears
  only as a foreign-key target from `workflow_events`.) The store methods
  `create_task` and `send_message` do not exist; the CLI exposes no
  session/message/task subcommands (pinned in `tests/test_cli_surface.py`).
- `.aidb/collaboration-log.md`: superseded by DISCUSSION.md; history only.

## Working rules that bite

1. **Attribution is enforced by a checker, not by prose.** Every PR body needs
   the contributors table from `.github/pull_request_template.md`.
   Accepted statuses: `user_confirmed`, `self_declared`, `maintainer_verified`,
   `unknown`. Accepted roles: `primary`, `co_author`, `reviewer`,
   `maintainer_assisted`. Header exactly:
   `agent_id | github_actor | attribution_status | contribution_role | provenance`
   (provenance ≥ 8 chars, factual). The PR author's GitHub login must be a row.
   `scripts/check_pr_attribution.py` is authoritative;
   `docs/CONTRIBUTOR_PROTOCOL.md` matches it.
2. **DISCUSSION.md is append-only at the top.** New entries go directly under
   `## Entries`, newest first, using the template in that file's header.
   Never rewrite, retitle, or "restore" another entry from memory —
   restorations come from git history only. Coordinate in DISCUSSION.md
   (structured) and CHAT.md (informal) *before* PR-thread comments.
3. **Never edit another agent's branch.** Hand over a patch or a comment; the
   branch's author applies it. If a journal PR conflicts, rebuild it as a fresh
   branch from current main — do not force-merge an old one.
4. **Merges, closures, deletions, and workflow-file changes are the
   maintainer's call** — never implied by a green check or a review.
   Evidence-linked dispositions only: no closing a PR/issue without stating
   where its content landed or why it is superseded.
5. **Never put a closing keyword next to another PR's number** in a PR body
   ("…does not resolve #55" still auto-closes #55). Refer to other PRs without
   resolve/fix/close verbs.
6. **Claims need evidence.** State the intended behavior and acceptance
   criterion before editing; run the narrow tests, then the full suite;
   report exact counts. Design docs are not proof of implementation —
   check the code.
7. **Byte-verify anything you publish** against the locally tested tree before
   calling it done.

## Canonical doc per topic

| Topic | Canonical source |
|---|---|
| Getting oriented | this page + `docs/current-state.md` |
| Everything else in the repo | `docs/repo-map.md` |
| Contributor + attribution rules | `docs/CONTRIBUTOR_PROTOCOL.md` + `.github/pull_request_template.md` (checker: `scripts/check_pr_attribution.py`) |
| Current project state | `docs/current-state.md` |
| Coordination | `DISCUSSION.md` (header rules), `CHAT.md` |
| Which tables are portable | `aidb/portability.py` (the registry) |
| HTTP deployment security | `docs/server-security.md` |
| Distributed direction | `docs/decision-log.md` (decisions) + `docs/distributed-networking.md` (proposal) |
| Accepted decisions | `docs/decision-log.md` |
| Epistemic invariants | `EPISTEMIC_CONTRACT.md`, `docs/invariants.md` |
| Agent identities | `.aidb/agent-profiles.yml` |
