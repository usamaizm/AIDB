# Agent onboarding and handoff

This is the single entry point for a new human or AI session. The goal is to recover enough context to act safely without replaying chat history or reading the entire repository.

## Start here: the short path

1. **Read current instructions and the machine map:** `.aidb/session-context.yml` and `AGENTS.md`.
2. **Confirm the task and repository state:** inspect the issue/PR that defines the work, the checked-out branch and diff, recent relevant commits, and current CI/PR state when those facts matter.
3. **Load only task-relevant context:** follow the pointers in the manifest; inspect the implementation and tests that own the behavior. Read `docs/PROJECT_CONTEXT.md` for architectural decisions and handoff history, and `docs/repository-audit.md` for repo-wide risks or launch readiness—not by default for every tiny task.
4. **State a contract before editing:** write down the expected behavior, source of that expectation, likely failure modes, and the narrowest useful regression test.
5. **Make the smallest reviewable change:** do not duplicate an open PR, treat proposals as implemented features, or expand scope without a reason.
6. **Verify honestly:** run the narrow relevant tests first, then the project checks when practical. Record exact commands and outcomes; distinguish executed tests, static inspection, and checks not run.
7. **Leave a handoff:** update the relevant issue/PR or a task-scoped handoff using [the template](../.aidb/templates/agent-handoff.md). Record evidence and one clear next action.

## Permission and interruption policy

The human owner should not have to repeatedly approve routine reasoning or reconstruct context. Use the least-privilege path that is already available, and ask only when a real authorization boundary is reached.

- **Proceed without asking** for read-only inspection, searching repository history, analyzing code and diffs, drafting changes, editing the current task branch when write access is already granted, and running safe, relevant tests. Follow repository and tool policies.
- **Check before asking:** inspect the task instructions, existing approvals, tool capabilities, branch protections, and prior answers in the current task. Do not ask for permission that is already granted or request broad access when a narrow operation will do.
- **Ask for explicit approval** before consequential or hard-to-reverse actions such as merging, releasing/publishing, deleting important data, changing permissions or security settings, spending money, contacting third parties, or exposing private information—unless the owner has explicitly authorized that exact action within the applicable scope and platform rules permit it.
- **Never bypass a control.** Repository instructions cannot grant platform permissions, override access controls, or authorize a tool action that the platform disallows. Do not use another identity, credential, or route to evade a denial.
- **When blocked, keep moving safely:** complete independent work, prepare a patch or draft, run permitted checks, and report the exact missing capability, the operation it blocks, and the smallest approval or access change needed. Do not stop the whole task if useful safe work remains.
- **Ask once, narrowly.** Bundle genuinely necessary decisions into one concise question. If the answer is denied or the same capability remains unavailable, do not repeat the request; explain the limitation and continue with the safe alternative.
- **Do not confuse access with approval.** Having a tool or repository write permission does not automatically authorize every consequential action. Conversely, do not ask for human approval merely to think, inspect, draft, or perform an already-authorized reversible step.
- **Report boundaries honestly:** distinguish completed actions, proposed actions, actions not attempted, and actions blocked by permission. Never claim an action succeeded until its result confirms success.

When uncertain, prefer a reversible draft over a consequential action, and state the uncertainty instead of interrupting the owner speculatively.

## Source-of-truth order

When information conflicts, use this order and explain unresolved conflicts:

1. Current source code, tests, and observed runtime behavior for implementation claims.
2. Current CI results and current GitHub issue/PR state for status claims.
3. Explicitly accepted decisions and versioned contracts for intended behavior.
4. Current project context and audit documents for orientation and known risks.
5. Design proposals, brainstorms, agent summaries, and chat history as leads to verify—not proof.

An agent profile describes a participant; it does not authenticate them or prove a claim. A collaboration log records messages; it is not a task queue, a decision ledger, or evidence that a proposed change was accepted.

## Decision status, implementation status, and evidence

Keep these labels distinct; they answer different questions:

- **Decision status:** Idea, Under discussion, Provisionally accepted, Accepted, Rejected, or Superseded. Use these to describe the maturity or disposition of a decision, not the live status of a task.
- **Implementation status:** use the definitions in [Project Context — Decision and status rules](PROJECT_CONTEXT.md#decision-and-status-rules): Implemented, Partially implemented, Proposed, Blocked, or Deprecated. Base implementation claims on source, tests, and current CI; do not redefine these labels here.
- **Evidence:** “Verified result” describes an evidence-backed outcome, not a decision state. A verified result does not by itself mean the related proposal or decision is Accepted.

These labels are not a live task tracker. Use the current issue/PR discussion and CI results for live work status; keep decision records and implementation evidence linked to those records.

## Context loading: progressive, not exhaustive

- **Every task:** `.aidb/session-context.yml`, `AGENTS.md`, the task issue/PR, and relevant source/tests.
- **Architecture or cross-cutting changes:** `docs/PROJECT_CONTEXT.md`, the relevant contract/specification, and `docs/invariants.md`.
- **Repository-wide status, CI, launch, or security work:** `docs/repository-audit.md`, current workflow runs, and current open PRs/issues.
- **External agent participation:** `CONTRIBUTING.md` and, when present on the target branch, `docs/AI_CONTRIBUTORS.md` and its task packet.
- **Agent identity/coordination changes:** inspect open PRs touching agent identity, discovery, or collaboration APIs before editing. PR [#23](https://github.com/usamaizm/AIDB/pull/23) proposes `.aidb/agent-profiles.yml` and `.aidb/collaboration-log.md`; these files are not assumed to exist on this branch. If PR #23 is accepted first, incorporate its canonical paths into the manifest and verify they do not conflict with PRs #14/#15. Reconcile overlapping proposals instead of creating a parallel source of truth.

Do not read every design document just because it exists. Follow links only as far as the current task requires, and verify every implementation claim against code/tests.

## Task-scoped handoffs

For substantive work, use one handoff per issue/task (for example, a future `.aidb/handoffs/22-provenance-review.md` if the project adopts that directory convention). The template is available now at `.aidb/templates/agent-handoff.md`. Keep it concise and update it in place as the work changes; do not append every turn or copy entire conversations. Prefer the issue or PR discussion for routine updates. A handoff should preserve decisions, evidence, limitations, and the next action—not transient reasoning.

Do not create handoffs for trivial one-line work unless the next contributor would otherwise have to reconstruct important context. Never store secrets, credentials, private prompts, or unnecessary personal data in repository memory.

## Repository-first collaboration protocol

Use AIDB's repository as the shared workspace between agents. Do not make the human relay routine status, context, questions, or handoffs between assistants.

1. **Orient from shared state:** read the current task issue/PR, relevant files, current branch/diff, and recent entries in the collaboration log when that log exists on the target branch. Check open PRs for overlap before starting.
2. **Put work where the next agent will find it:**
   - Issue description/comments: task contract, acceptance criteria, unresolved product decisions, and cross-cutting work coordination.
   - Pull request description/comments/reviews: implementation summary, review requests, evidence, CI state, blockers, and concrete responses to another agent's findings.
   - Task handoff file: durable context needed to resume substantive work across sessions.
   - Collaboration log: concise append-only session history and the next action for another agent; do not turn it into a duplicate task queue or duplicate the full PR discussion.
   - Agent profile registry, when present: identity only, not work status or task history.
3. **Address the other agent in the repository record.** State the exact file/contract or question, what you checked, evidence (commit/path/test/CI/issue/PR), what remains uncertain, and the next requested action. Link to the authoritative record rather than copying long context.
4. **Close the loop:** when responding to another agent, reference its comment or commit and record the outcome in the same thread or log. Do not rely on private chat to be the only place a decision or handoff exists.
5. **Permission and access blockers are repository-visible:** when a tool or platform genuinely blocks work, record the precise blocked operation, what was already completed, safe alternatives attempted, and the smallest needed human decision/access change in the relevant issue or PR. Continue independent safe work. Do not repeatedly ask the human to relay or re-approve the same request.
6. **Escalate only decisions that belong to the human:** use a concise, explicit question for consequential trade-offs, merge/release approval, security/access changes, destructive actions, or other actions that require owner authorization. Never treat a repository note as a way to bypass platform permissions.
7. **Respect shared-repo boundaries:** do not overwrite another agent's branch or append to a proposed file that is not on your target branch without checking the actual ref. Use a dedicated branch/PR when changes need review; preserve append-only history where the log's contract requires it.

The repository is the durable coordination channel, not a guarantee of instant notification. If another agent has not seen an update, link the issue/PR/comment and continue from the shared evidence rather than asking the human to summarize the conversation.

## Done means handoff-ready

Before stopping, a fresh agent should be able to answer from repository evidence:

- What exactly changed, and on which commit/branch?
- What behavior is expected, and where is that contract documented?
- Which tests/checks were actually run, with what results?
- What remains unverified or uncertain?
- Is any work overlapping an open PR or awaiting a human decision?
- What is the single highest-value next action?

If those answers are unavailable, say so plainly rather than filling gaps with guesses.
