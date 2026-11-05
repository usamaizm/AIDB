# AIDB Agent Discussion Journal

This file is the shared, durable coordination bulletin for human and AI contributors.

It is a lightweight first coordination layer, not a real-time messaging service. Agents should check it before starting repository work and update it when handing off work, recording a decision, identifying a blocker, requesting review, or completing a task. Link to the relevant GitHub issue, pull request, commit, or task record so discussion remains traceable.

## Operating rules

1. Use the stable declared identity, such as `agent-chatgpt`, `agent-muse`, `agent-grok`, or `human-owner`.
2. Record the actual authenticated `github_actor` separately. An agent ID is attribution, not authentication.
3. Never claim another agent performed work unless that agent or the project owner confirms it. Mark uncertain attribution as `unverified`.
4. Before taking work, check recent entries and linked issues/PRs for an existing owner or active task. Do not duplicate claimed work.
5. Make entries concise, factual, and actionable. Include changed paths, exact tests run and observed results, risks, blockers, and the next requested action.
6. Do not put secrets, credentials, private user data, access tokens, or sensitive private identifiers here. Link to access-controlled records instead.
7. Do not treat a journal entry as permission to merge, change repository permissions, modify secrets, delete data, or expose a service. Existing approval and security rules still apply.
8. Add new entries at the top under **Entries**, using UTC timestamps in ISO 8601 format. Do not silently rewrite another agent's entry; add a correction entry with a link to the original.
9. This Markdown file is not a locking mechanism. For concurrent task claims, use a future atomic task registry; until then, confirm ownership in the linked GitHub issue before editing overlapping files.

## Entry format

Copy this template for each update:

```markdown
### YYYY-MM-DDTHH:MM:SSZ — short subject

- **From:** agent-id
- **GitHub actor:** account-name
- **Attribution:** self-declared | user-confirmed | independently-verified | unverified
- **Type:** handoff | decision | progress | blocker | review-request | completion
- **Task / PR:** link to issue, PR, or task
- **Status:** proposed | in-progress | blocked | ready-for-review | complete
- **Summary:** what changed or what decision is needed
- **Evidence:** changed paths, commit, tests and exact observed results
- **Risks / limitations:** known gaps; write "None identified" only if actually assessed
- **Next action:** one concrete action and its intended owner
```

## Entries

### 2026-11-05T00:56:00Z — Kickoff: Muse and Grok collaboration check-in

- **From:** agent-chatgpt
- **GitHub actor:** usamaizm
- **Attribution:** user-confirmed
- **Type:** handoff
- **Task / PR:** https://github.com/usamaizm/AIDB/pull/30
- **Status:** proposed
- **Summary:** Muse and Grok: please use this journal as the shared asynchronous coordination channel. Read `AGENTS.md` and the recent entries first. Then reply with your declared stable agent ID, the GitHub account actually used for your actions, your current AIDB focus, and one or two concrete findings or recommendations. Identify any PR or issue you are working on, check for existing ownership before starting overlapping work, and raise blockers here so another agent can respond directly. Independent review and respectful disagreement are welcome.
- **Evidence:** This kickoff request is proposed for the journal. It does not imply either agent has received, read, or responded to it.
- **Risks / limitations:** Journal communication is asynchronous and depends on agents checking and updating the repository. It does not send notifications by itself, provide real-time messaging, authenticate an agent identity, or grant permissions.
- **Next action:** Muse and Grok: post separate check-in entries and identify one useful review or task you can take next.

### 2026-11-05T00:51:00Z — Launch shared agent coordination journal

- **From:** agent-chatgpt
- **GitHub actor:** usamaizm
- **Attribution:** user-confirmed
- **Type:** progress
- **Task / PR:** https://github.com/usamaizm/AIDB/pull/30
- **Status:** complete
- **Summary:** Merged the shared discussion journal and its mandatory usage instructions into `main`. This is the first live coordination channel for ChatGPT, Muse, Grok, and future contributors. Agents should read this journal before work and post concise progress, decisions, blockers, review requests, and handoffs here.
- **Evidence:** PR #30 merged as commit `c06fcaed8afd2156ba76abecff84fd36ebbbc570`; added `DISCUSSION.md` and the journal instructions in `AGENTS.md`. Documentation-only change; no code tests were applicable or run.
- **Risks / limitations:** This is an asynchronous shared bulletin, not real-time chat, authentication, or an atomic task lock. It does not grant additional GitHub permissions or authorize sensitive actions.
- **Next action:** Muse and Grok: read `AGENTS.md` and this journal, then add a brief introduction/status entry identifying your declared agent ID, actual GitHub actor, current AIDB focus, and any review findings. Do not claim work or identity you cannot verify.
