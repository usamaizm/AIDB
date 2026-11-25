# AIDB Repo Map — load on demand

*The bootstrap set (`.aidb/session-context.yml`, `docs/orientation.md`,
`docs/current-state.md`) is all an agent needs to start. Load anything
below only when the task touches it. "Proposal" means the document
describes intended direction, not implemented behavior — verify against
the code before quoting it as state.*

## Start here

| Path | Purpose | Load when |
|---|---|---|
| `.aidb/session-context.yml` | Machine-readable bootstrap manifest and canonical pointers | Always (bootstrap) |
| `docs/orientation.md` | What AIDB is; REAL/PLANNED/DEAD; concept→module→table map; rules that bite | Always (bootstrap) |
| `docs/current-state.md` | Present-tense project status, landing lanes, open decisions | Always (bootstrap) |
| `AGENTS.md` | Contributor rules, invariants, repo-specific lessons | Before any change |
| `README.md` | Human-facing overview and quick start | When docs or onboarding change |
| `docs/PROJECT_CONTEXT.md` | Longer project handoff and vision (snapshot — status may lag `docs/current-state.md`) | When you need background reasoning, not status |

## Coordination

| Path | Purpose | Load when |
|---|---|---|
| `DISCUSSION.md` | Structured coordination journal (claims, handoffs, decisions, blockers) | Before starting work; when claiming/handing off |
| `CHAT.md` | Informal agent chat | For questions and exploratory discussion |
| `ISSUES.md` | Issue register; declares GitHub Issues canonical | When filing or triaging work |
| `.aidb/agent-profiles.yml` | Stable agent IDs, aliases, roles | When attributing work |
| `.aidb/collaboration-log.md` | **Superseded** pre-DISCUSSION coordination log — history only | Never for current state |
| `.aidb/protocol.yml` | External-request intake protocol | When handling external AI requests |
| `.aidb/knowledge.yml` | Knowledge index | When looking up recorded project knowledge |
| `.aidb/agent-task-template.yml`, `.aidb/tasks/` | Task templates | When structuring a new task |

## Contributor workflow

| Path | Purpose | Load when |
|---|---|---|
| `docs/CONTRIBUTOR_PROTOCOL.md` | Attribution + workflow entry point (matches the checker) | Before opening a PR |
| `.github/pull_request_template.md` | PR body template incl. contributor table | Before opening a PR |
| `scripts/check_pr_attribution.py` | CI-enforced attribution validation — the authority on statuses/roles | When attribution values are in doubt |
| `CONTRIBUTING.md` | Engineering standards (testing, security, review) | Before implementation work |
| `docs/maintainer-review.md` | Request review checklist | When reviewing requests/PRs |
| `docs/request-evaluation.md` | Rubric for evaluating external requests | With `.aidb/protocol.yml` |
| `docs/iteration-guide.md` | How work is iterated in this repo | When planning a work cycle |
| `docs/copilot-governance.md` | Copilot's role and execution model | Only for Copilot-related work |
| `docs/AI_CONTRIBUTORS.md` | Notes on independent AI contributors | Background on contributor setup |
| `docs/CONTRIBUTION_ATTRIBUTION_AUDIT.md` | Historical attribution audit | History only |
| `docs/decision-log.md` | Accepted architectural decisions — authoritative over proposals | Before any design or contract change |
| `docs/repository-audit.md` | Point-in-time audit snapshot (ages quickly) | For audit history, not current status |

## Code areas

| Path | Purpose | Load when |
|---|---|---|
| `aidb/store.py` | The store: schema, all persistence, export/import, sessions, verification | Any behavior change |
| `aidb/server.py` | HTTP adapter (routes, bind security, TLS) | HTTP work |
| `aidb/http_client.py` | Outbound verified-HTTPS client (peer document fetch) | Transport work |
| `aidb/network.py` | Local agent discovery/collaboration as typed resources | Collaboration work |
| `aidb/canonical.py` | RFC 8785 canonical JSON + record digests (v2 primitives) | Integrity/v2 work |
| `aidb/portability.py` | Per-table portability registry — source of truth for export tables | Export/import work |
| `aidb/core.py` | Dataclasses (`aidb/epistemic.py` re-exports it) | Model changes |
| `aidb/__main__.py` | CLI (`agent`, `search`, `serve`) | CLI work |
| `tests/` | Pytest suite; `test_cli_surface.py` pins the advertised surface | Always, for the area you touch |
| `include/aidb/aidb.h` | Draft C ABI header — not an implemented API | Only for ABI proposal work |

## Contracts and invariants

| Path | Purpose | Load when |
|---|---|---|
| `EPISTEMIC_CONTRACT.md` | Normative epistemic invariants | Epistemic pipeline work |
| `docs/invariants.md` | Boundary invariants (artifact → extraction → …) | Epistemic pipeline work |
| `docs/specification.md`, `docs/specification.example.json` | The dynamic node specification | Specification work |
| `docs/home.md` | The agent-home concept | Home-model questions |
| `docs/knowledge-base.md`, `docs/agent-memory-and-knowledge-entries.md`, `docs/knowledge-transformations.md` | Knowledge/memory model notes | Knowledge-area work |
| `docs/idea-taxonomy.md` | Taxonomy of idea records | Knowledge-area work |
| `docs/communication.md` | Communication model between agents | Collaboration design |
| `docs/agent-network.md` | Durable agent network (semantic layer) | Collaboration design |
| `AUDIT_FINDINGS.md` | Epistemic kernel audit, 2026-10-02 — point-in-time | History; pre-dates the Nov remediation lanes |

## Architecture and direction (proposals unless noted)

| Path | Purpose | Load when |
|---|---|---|
| `docs/distributed-networking.md` | Distributed networking architecture (direction accepted; not implemented) | Distributed design work |
| `docs/evolution-and-compatibility.md` | Evolution/compatibility boundaries | Format/version changes |
| `docs/architecture.md` | Architecture overview (precedes implementation in places) | Background |
| `AIDB_V1_DESIGN.md` | V1 design proposal | History/background |
| `docs/one-stop-agent-substrate.md` | Product-scope proposal | Scope questions |
| `docs/modular-architecture.md` | Proposed module boundaries | Refactor planning |
| `docs/IMPLEMENTATION_ROADMAP.md` | Implementation roadmap | Planning |
| `docs/schema-proposal.md` | Proposed schema additions | Schema design |
| `docs/protocol.md` | AIDB protocol description | Protocol questions |
| `docs/artifact-protocol.md` | Artifact protocol and format neutrality | Artifact design |
| `docs/api-design-principles.md` | Public API design principles | API changes |
| `docs/language-agnostic-contract.md` | Language-neutral contract (draft) | Binding/contract work |
| `docs/c-first-api.md` | C-first API proposal | ABI work |
| `docs/agent-compatibility-and-file-formats.md` | Format adapters / ingestion proposal | Format work |
| `docs/format-registry-platform-compatibility.md` | Format registry proposal | Format work |
| `docs/binary-and-assembly.md` | Binary/assembly artifact proposal | Artifact work |
| `docs/multilingual-and-language-agnostic.md` | Language-agnosticism design | I18n work |
| `docs/performance-context-and-scale.md` | Performance/scale goals and proposed designs | Performance work |
| `docs/storage-efficiency-and-numeric-data.md` | Storage-efficiency proposal | Storage work |
| `docs/self-evolving-architecture.md` | Self-evolution proposal | Background only |
| `docs/autonomous-kaizen.md` | Operational contract and phased implementation sequence for autonomous continuous improvement | Kaizen/autonomy work |
| `docs/live-build-and-emulation.md` | Live build/emulation runtime proposal | Background only |
| `docs/standards.md` | Standards and interoperability notes | Interop questions |

## Operations and security

| Path | Purpose | Load when |
|---|---|---|
| `SECURITY.md` | Security policy | Security questions |
| `docs/server-security.md` | Operational server security: bind rules, token, TLS | Deploying or changing the server |
| `CHANGELOG.md` | Change history | Release/history questions |
| `examples/`, `data/`, `encyclopedia/`, `brainstorms/` | Examples, sample data, reference material, idea drafts | Only when a task names them |
