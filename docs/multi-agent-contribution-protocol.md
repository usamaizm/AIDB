# Multi-Agent Contribution Protocol

Status: proposed; experimental; no runtime coordinator is implied by this document.

## 1. Purpose

Allow the project owner to direct ChatGPT, Muse, Grok, and future agents through their existing apps while keeping work attributable, non-conflicting, reviewable, and recoverable. The protocol must not require purchasing a separate GitHub user account for each agent.

This protocol distinguishes **who authenticated to GitHub** from **which agent claims to have produced work**. If multiple apps use the owner's GitHub connection, GitHub will still record the owner as the authenticated actor. Repository metadata improves traceability but does not turn that claim into independently verified identity.

## 2. Operating principles

1. The human owner remains the repository owner and final authority for merges, permissions, secrets, releases, destructive operations, and public deployments.
2. Agents may inspect, plan, implement, test, document, and open pull requests within the permissions actually available to them.
3. No agent may push directly to `main`, force-push shared branches, merge its own PR, change repository security settings, or modify secrets as part of ordinary autonomous work.
4. Every material change must be associated with an agent label, task, branch, commit, evidence, and review state.
5. An agent must not claim that tests, CI, a scheduled run, or an event trigger succeeded unless it observed the result.
6. If identity, task ownership, branch state, or intended behavior is ambiguous, the agent must stop the conflicting action, record the ambiguity, and choose a non-destructive task.
7. Agents must read the current `AGENTS.md`, `.aidb/session-context.yml`, and relevant source/tests before changing code. Current repository state outranks chat history and model memory.

## 3. Agent identifiers

Use stable, human-readable identifiers:

| Contributor | Canonical ID |
| --- | --- |
| Repository owner | `human-owner` |
| ChatGPT | `agent-chatgpt` |
| Muse | `agent-muse` |
| Grok | `agent-grok` |

Identifiers are labels, not credentials. An agent must state its canonical ID in task records and PR metadata. AIDB must not treat a self-declared ID as cryptographic proof of origin.

Do not share personal access tokens between agents or place credentials in the repository, commits, issues, PRs, logs, or this protocol. Do not create paid GitHub accounts merely to obtain labels.

## 4. Phone-first interaction model

The owner may continue to give instructions conversationally in the ChatGPT, Muse, and Grok apps. The apps are the human control surfaces; the repository is the durable shared record.

When an owner gives an instruction in any app, the agent should:

1. Convert it into a concise task with an acceptance condition.
2. Read the current repository handoff and inspect open work before editing.
3. Record or update the task in the shared task register before implementation.
4. Claim only work that is not already actively owned.
5. Work in an isolated branch and report a PR or a clear blocker in the app conversation.

The owner should not need to manually coordinate every file edit. Agents are expected to discover existing work, choose an unclaimed task from the approved backlog when no direct task is pending, and leave a concise handoff. They must not invent product requirements or expand scope silently.

## 5. Task lifecycle and collision avoidance

Each task has one active owner at a time. Use these states:

- `queued`
- `claimed`
- `in_progress`
- `blocked`
- `review`
- `done`
- `abandoned`

A task record should contain:

```yaml
id: AIDB-XXX
title: Short, testable task title
status: queued
owner: null
created_at: YYYY-MM-DDTHH:MM:SSZ
claimed_at: null
lease_expires_at: null
branch: null
related_pr: null
acceptance:
  - Observable condition one
  - Observable condition two
```

For the initial manual protocol, update the shared task register in a small, focused commit or PR. Do not assume a Markdown/YAML edit is an atomic lock: two agents can race. If simultaneous claims are common, implement an atomic claim operation in AIDB storage before relying on task locks for safety.

A future runtime coordinator should use transactional compare-and-set claims and expiring leases. It should reject a second active claim, support heartbeat/lease renewal, and require an explicit recovery check before reassigning work after lease expiry. Lease expiry alone must never authorize overwriting another agent's branch or uncommitted work.

## 6. Branch and pull-request rules

Use one branch per task, named:

```text
agent/<agent-id>/<short-task-slug>
```

Examples:

- `agent/agent-chatgpt/audit-export-privacy`
- `agent/agent-muse/add-regression-tests`
- `agent/agent-grok/review-http-boundary`

Rules:

1. Branch from the latest appropriate base after checking the current branch and related PRs.
2. Do not share a working branch between agents.
3. Do not edit another agent's active branch unless the owner explicitly coordinates a handoff.
4. Keep PRs small and task-scoped. State the base branch and any dependency on another PR.
5. Do not merge automatically. The owner controls merge policy; required CI and review checks must pass first.
6. If branch protection is unavailable on the repository plan/settings, agents must still follow the no-direct-main-push rule by procedure. Document that this is a convention, not an enforced control.

## 7. Required contribution metadata

Every PR description must include:

```yaml
aidb_contribution:
  protocol: "1"
  agent_id: "agent-muse"
  task_id: "AIDB-XXX"
  base_branch: "main"
  summary: "What changed and why"
  files_or_components:
    - "path/to/file"
  tests:
    - command: "python -m pytest -q"
      result: "passed | failed | not_run"
      evidence: "link or concise output reference"
  risks:
    - "Known limitation, or 'none identified'"
  handoff: "What the next reviewer/agent should do"
```

Use commit trailers when practical:

```text
Agent: agent-muse
Task: AIDB-XXX
Protocol: 1
```

Commit author/committer names and email fields may be set to descriptive values only when the app/tool permits and repository policy allows. They are editable metadata and must not be presented as verified identity. The GitHub account shown as the pusher/PR actor remains the account that authenticated the operation.

## 8. Review and merge

- A different agent should review the change when available; the authoring agent must not describe its own review as independent.
- Reviewers check correctness, security/privacy, compatibility, tests, scope, and whether the PR duplicates existing work.
- Conflicting architectural proposals must be recorded as alternatives with evidence; do not silently overwrite a decision.
- The owner approves merges and any exception to the safety rules.
- A merge is complete only after GitHub confirms it. A green local test is not a green CI run.

## 9. Scheduling, events, and autonomy boundaries

Polling and event triggers may be configured in an AI platform, GitHub Actions, or another service. These are separate mechanisms and must be inventoried individually.

- AIDB does not, by itself, wake an app, keep a model running, or guarantee that a platform schedule/event trigger executes.
- A schedule such as every 30 or 60 minutes is an intended cadence, not proof of execution. Record actual last-run time and outcome where available.
- Event-driven agents must filter events to relevant repository, branch, action, and workflow types; ignore their own non-actionable updates to prevent loops.
- Every automation must be idempotent where possible, bounded in runtime, and safe to retry.
- GitHub Actions permissions must be least-privilege. Prefer read-only permissions by default; grant only the specific write permissions required by a reviewed workflow.
- Never expose secrets to pull-request code from untrusted branches. Do not run privileged workflows on untrusted PR code with write tokens or secrets.
- Do not add model-provider API keys to the repository. Calling an external model from GitHub Actions may incur separate usage charges and must not be assumed to be included in an app subscription.

## 10. Usage limits and graceful degradation

AIDB cannot bypass an AI provider's free-tier quota, rate limits, or app usage cap. When an agent is unavailable:

1. Mark its assigned task `blocked` or leave it queued with the reason and retry condition.
2. Other available agents may claim different, non-overlapping tasks.
3. Do not impersonate the unavailable agent or claim it performed work.
4. Resume the task when that agent becomes available, or explicitly reassign it while preserving the original history.

The protocol should make useful progress possible with one or two available agents; it must not require all agents to be online simultaneously.

## 11. Audit record and trust levels

The contribution ledger should preserve task ID, declared agent ID, timestamps, branch, commit SHA, PR URL, review decisions, test/CI evidence, and final disposition.

Use explicit trust labels:

- `self_declared`: agent identity supplied in PR/commit metadata.
- `session_authenticated`: identity bound to a distinct agent credential verified by an AIDB service.
- `github_app_authenticated`: GitHub operation performed through a dedicated GitHub App identity.

Only use the stronger labels after implementing and verifying the corresponding authentication. With all apps using the owner's GitHub login, contributions remain `self_declared` even if their metadata is consistent.

## 12. Rollout plan

### Phase 0 — Inventory and stop the highest-risk behavior
- List all workflow files and inspect triggers, permissions, secrets, and write operations.
- Check branch protection/rulesets and current open PRs.
- Do not disable existing schedules blindly; document what each one does first.
- Adopt the no-direct-main-push and PR metadata rules immediately as contributor instructions.

### Phase 1 — Documentation and manual ledger
- Add this protocol and stable agent IDs.
- Add a minimal task register only after choosing its canonical format and location.
- Have each agent include the required metadata in new PRs.

### Phase 2 — Reliable coordination
- Implement atomic task claims, leases, event deduplication, and contribution records using existing AIDB persistence.
- Add tests for concurrent claims, lease expiry, retries, duplicate events, and crash recovery.
- Keep the coordinator optional; ordinary repository work must remain possible without it.

### Phase 3 — Stronger identity (optional)
- If agent platforms can securely call an AIDB endpoint, issue separate revocable agent credentials and bind each credential to one canonical ID.
- If a dedicated GitHub App is later useful, use one app identity for the gateway and preserve the originating agent in AIDB's audit record.
- Do not promise that separate app identities can be selected from the existing mobile apps unless those apps actually support that integration.

## 13. Definition of done for this protocol

The protocol is adopted only when:
- Contributors can identify the owner versus each AI agent.
- Every new task has one recorded owner and acceptance criteria.
- Every agent change is isolated on a task branch and submitted for review.
- PRs carry the required attribution and verification metadata.
- The limits of self-declared attribution are documented.
- Workflow permissions and branch protections have been inspected rather than assumed.
- Tests demonstrate any automated claim/lease/event behavior before it is relied upon.

Until the runtime coordination phases are implemented, this document defines a contributor procedure, not an already-running autonomous coordinator.
