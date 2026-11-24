# AI agent contribution record

**Prepared:** 2026-11-24  
**Scope:** AIDB pull requests and agent profile records visible on the repository's current `main`.  
**Purpose:** Make existing agent attribution and the difference between code contributions and coordination-only claims easy to review.

This is an evidence-based summary of repository records, not cryptographic proof of model identity or an independent quality certification. GitHub authenticated the account `usamaizm`; the logical agent identities below are self-declarations recorded in the repository's contributor tables and agent profile.

## Recorded agent identities

| Agent ID | Display name | Self-declared model | GitHub actor | Attribution status |
|---|---|---|---|---|
| `agent-muse` | Muse | Muse Spark 1.3 (Meta) | `usamaizm` | `self_declared` |
| `agent-chatgpt` | ChatGPT | GPT-6; specific version unknown | `usamaizm` | `self_declared` |
| `agent-grok` | Grok Bot | Grok Bot; provider/version unknown | `usamaizm` | `self_declared` |

The source of truth for these declarations is [`.aidb/agent-profiles.yml`](../.aidb/agent-profiles.yml). The profile explicitly separates logical agent identity from the authenticated GitHub actor and says not to infer undisclosed model details.

## Muse — verified merged code contributions

The following pull requests are merged into `main` and explicitly attribute primary authorship to `agent-muse`:

| PR | Merged change | Evidence in PR |
|---|---|---|
| [#70](https://github.com/usamaizm/AIDB/pull/70) | Strict validation of artifact provenance and metadata JSON | `aidb/store.py` plus dedicated regression tests |
| [#71](https://github.com/usamaizm/AIDB/pull/71) | Version snapshot contract separately from the home envelope | Store change plus snapshot-contract tests |
| [#72](https://github.com/usamaizm/AIDB/pull/72) | Persist schema version and add a migration runner | Store change plus schema-version/migration tests |
| [#73](https://github.com/usamaizm/AIDB/pull/73) | Validate artifact rows on home import | Store change plus import-validation tests |
| [#78](https://github.com/usamaizm/AIDB/pull/78) | Consolidate duplicate epistemic dataclasses onto `aidb.core` | Epistemic module refactor plus consolidation tests |
| [#80](https://github.com/usamaizm/AIDB/pull/80) | Fail-closed export/import of the agents table | Store change plus agents export/import tests |

These PRs include contributor tables that identify `agent-muse` as `primary`, `self_declared`, with the authenticated actor `usamaizm`.

## Shared implementation and integration work

Several later merged PRs explicitly distinguish Muse's primary design/test contribution from ChatGPT's integration role:

| PR | Merged scope | Recorded roles |
|---|---|---|
| [#111](https://github.com/usamaizm/AIDB/pull/111) | Validate imported home rows and change history | Muse: primary design and regression suites; ChatGPT: integrator |
| [#112](https://github.com/usamaizm/AIDB/pull/112) | Complete `verify_home()` integrity coverage | Muse: primary design and regression suites; ChatGPT: integrator |
| [#113](https://github.com/usamaizm/AIDB/pull/113) | Log unexpected HTTP handler failures | Muse: primary behavior and original tests; ChatGPT: logging and integration tests |
| [#115](https://github.com/usamaizm/AIDB/pull/115) | Portability registry and explicit export projections | Muse: primary design/tests; ChatGPT: integrator |
| [#116](https://github.com/usamaizm/AIDB/pull/116) | RFC 8785 canonical JSON and record-digest primitives | Muse: primary canonicalization implementation/tests; ChatGPT: integration and agent-projection coverage |

The contributor tables in these PRs are the detailed provenance record. The summary here does not reassign primary authorship.

## Coordination-only claim PRs

A number of PRs with `docs/agent-muse-*` branches add entries to `DISCUSSION.md` to record task ownership, evidence, and handoffs. Some original claim PRs were closed as superseded by rebuilt versions after the main branch advanced. Examples include [#122–#136](https://github.com/usamaizm/AIDB/pulls?q=is%3Apr+is%3Amerged+agent-muse).

These journal-only PRs are useful coordination/provenance records, but they are **not additional code changes** and must not be counted as separate implementations. PR #136 explicitly maps the Q8–Q16 claim lanes back to the code PRs listed above.

## Verification boundary

The AIDB repository's Python CI matrix has passed on Python 3.10, 3.11, and 3.12 in the observed run [45389139164](https://github.com/usamaizm/AIDB/actions/runs/45389139164). This verifies the configured compile, Ruff, and pytest checks on that revision. It does not prove every architectural proposal is implemented, nor does it independently authenticate the model behind a self-declaration.

## Attribution rules going forward

1. Preserve `agent_id` and `github_actor` as separate fields.
2. Keep `self_declared`, `user_confirmed`, `maintainer_verified`, and `unknown` distinct.
3. Do not infer agent identity from account names, commit style, timestamps, or model behavior.
4. Do not count a coordination-only claim PR as a code implementation.
5. Keep contributor tables on every material PR, including integrator and reviewer roles.
6. Never rewrite historical attribution to make later contributions appear to have been authored by a different agent.
