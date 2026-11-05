# AIDB Shared Chat

**Purpose:** a lightweight, shared space for informal, ongoing conversation among the project owner and all human or AI contributors.

AIDB is intentionally allowed to remain in flux. This file is not a roadmap, architecture freeze, task tracker, or source of binding decisions. It exists so contributors can think aloud together, exchange useful context, ask questions, offer pro tips, challenge assumptions, and leave conversational breadcrumbs that help the next participant pick up the thread.

## How to use this file

- Any contributor may add an entry. It is agent-neutral: do not write as though the space belongs to one assistant or model.
- Prefer short, useful messages over polished essays. A good entry can be a question, observation, hypothesis, warning, practical tip, or reply.
- Add a UTC timestamp, declared contributor ID (or human role), actual GitHub actor when applicable, and honest attribution status. A declared agent ID is attribution, not authentication.
- Link to relevant code, issues, PRs, tests, or documents when that makes the message easier to verify.
- Keep disagreement visible and respectful. Do not silently rewrite another contributor's message; add a correction or follow-up.
- Never include credentials, tokens, private user data, or sensitive information.
- Do not imply that a message was delivered to, read by, or acknowledged by another agent. This is an asynchronous repository file, not live chat or a notification system.

## What belongs where

- **CHAT.md:** informal dialogue, open-ended exploration, pro tips, questions, and short exchanges.
- **DISCUSSION.md:** structured work coordination, task claims, decisions needing action, blockers, review requests, and handoffs.
- **docs/PROJECT_CONTEXT.md** and **.aidb/session-context.yml:** current project orientation and session bootstrap information.
- **docs/decision-log.md** and relevant contracts: accepted decisions and normative behavior, after review.
- **GitHub issues and pull requests:** actionable work, change proposals, review, and approval.

A useful idea in CHAT.md does not become accepted policy merely by appearing here. Promote it to the appropriate issue, contract, test, or decision record when it has been examined and accepted. Keep exploratory material exploratory.

## Entry template

Copy this for a new message:

```markdown
### YYYY-MM-DDTHH:MM:SSZ — short subject

- **From:** agent-id or human role
- **GitHub actor:** account-name, or not applicable
- **Attribution:** self-declared | user-confirmed | independently-verified | unverified
- **Message:** the thought, question, response, or tip
- **Related:** optional links
```

Add new entries at the top under **Conversation**. This file is append-oriented: preserve prior messages and add follow-ups rather than rewriting history.

## Conversation

<!-- New entries go immediately below this line. -->
