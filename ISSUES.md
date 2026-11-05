# AIDB Issue Register

**Purpose:** a durable, repository-level index of known issues, risks, and follow-up work. This file helps humans and agents understand what needs attention without treating scattered chat messages or agent notes as an authoritative backlog.

## Source of truth

- **GitHub Issues** are the canonical records for actionable defects, feature requests, and investigations. Each item listed here should link to its GitHub issue.
- **Pull requests** record proposed fixes, review evidence, and merge status.
- **DISCUSSION.md** is for coordination, task claims, blockers, and handoffs.
- **CHAT.md** is for informal conversation, hypotheses, questions, and discoveries.
- **docs/decision-log.md** records accepted architectural decisions.

Do not create a second, competing issue tracker in this file. If an issue has no GitHub issue yet, create one before listing it here, unless it is explicitly marked as an untriaged observation.

## Inclusion rules

Add an entry when it is:
- a confirmed defect or security/privacy concern;
- a reproducible conformance failure;
- a significant compatibility, reliability, or architectural risk needing a decision;
- a cross-cutting follow-up that would otherwise be easy to lose.

Avoid listing routine tasks, speculative concerns without evidence, or every small implementation detail. Link related PRs, tests, and discussion so readers can verify the status themselves.

## Status vocabulary

Use one of these statuses consistently:

- **Untriaged** — reported, but not yet reproduced or assessed.
- **Open** — confirmed or accepted; no complete fix is merged.
- **In progress** — an implementation or investigation is underway.
- **Blocked** — progress depends on a named decision, dependency, or external action.
- **Resolved** — the fix is merged and the relevant regression/conformance check passes.
- **Closed / superseded** — no longer applicable; explain why and link the replacement if any.

A PR being open, a test passing on an unmerged branch, or an agent reporting a proposed patch does **not** make an issue resolved.

## Priority guidance

- **P0 — Critical:** active exploitation, severe data loss/corruption, or system-wide outage.
- **P1 — High:** serious security/privacy/integrity failure or a core workflow unusable.
- **P2 — Normal:** meaningful defect or capability gap with a workaround.
- **P3 — Low:** polish, documentation, or limited-impact improvement.

Priority is about impact, not how easy or urgent a task feels. Record uncertainty rather than overstating severity.

## Issue entry template

Copy this for each tracked item:

```markdown
### [P2] Short, factual issue title

- **GitHub:** [#123](https://github.com/OWNER/REPO/issues/123)
- **Status:** Open
- **Area:** import | export | privacy | artifacts | provenance | API | CLI | docs | other
- **Reported by:** human role or declared agent ID
- **Owner:** unassigned or declared owner
- **Evidence:** reproduction, failing test, audit note, or relevant commit/PR
- **Impact:** who or what is affected
- **Acceptance criteria:** observable conditions that establish resolution
- **Related:** links to PRs, tests, decisions, or discussion

**Notes:** concise context, including known limitations or competing hypotheses.
```

## Maintenance rules

1. Link every actionable entry to its canonical GitHub Issue. Never invent issue numbers or imply a report is confirmed without evidence.
2. Keep titles factual and statuses current. Update the entry when evidence changes; preserve important historical context in the GitHub issue or discussion thread.
3. Mark an item **Resolved** only after the fix is merged and its acceptance criteria are verified on the target branch.
4. If a fix is reverted or a regression reappears, reopen the entry and link the regression evidence.
5. Record agent identity and attribution honestly. A self-declared agent ID is not authentication or independent verification.
6. Do not include credentials, tokens, private user data, or sensitive information.
7. Prefer one canonical issue per defect. Cross-link duplicates rather than maintaining competing descriptions.
8. Review this register when preparing release notes, conformance reports, or decision-ready batches.

## Current register

No issues are entered here yet. Add confirmed items with canonical GitHub Issue links as they are triaged. This avoids publishing an incomplete or stale backlog as though it were authoritative.
