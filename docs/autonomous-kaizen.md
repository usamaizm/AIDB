# Autonomous Kaizen — Operating Contract

**Status:** proposed operating contract. This document turns AIDB's existing self-evolution principles into an implementation sequence. It does not claim that autonomous repository discovery, experimentation, promotion, or self-evolution is already implemented.

## Purpose

Build a system that continuously improves the software ecosystem it is responsible for, without requiring a person to coordinate every routine step.

The system must be able to observe, identify opportunities, formulate and compare hypotheses, run bounded experiments, evaluate evidence, deliver verified changes, learn from outcomes, and repeat. It must also improve the quality of this process over time.

**Kaizen autonomously** means that continuous improvement is a normal operating capability, not an occasional human-initiated coding session.

Autonomy is bounded by explicit authority, evidence, resource, privacy, and recovery constraints. It never means unrestricted access or permission to change everything.

## System boundary

Treat the repositories in the ecosystem as related but independently versioned projects.

- **AIDB** is the candidate shared substrate for durable knowledge, provenance, task coordination, and evidence. Its current implementation is a local-first Python/SQLite reference system; it does not yet provide a complete autonomous improvement service.
- **Each repository** remains authoritative for its source, tests, contracts, release process, and accepted decisions.
- **Agents** are replaceable workers. Their declared identity is attribution, not authentication. Their outputs are proposals until checked.
- **GitHub** is currently the practical review and change-delivery boundary. A task record or journal entry is not a lock, approval, or proof of execution.

Cross-repository work must record dependencies and coordinate one owner per overlapping change. A shared memory system must not erase repository boundaries or silently turn one project's decisions into another project's policy.

## The improvement cycle

Every cycle produces a durable record. A cycle may stop at any stage; incomplete work is not reported as complete.

1. **Observe** — inspect authorized repository state, CI, open work, test failures, user feedback, operational metrics, and known gaps. Record the exact commit/ref and observation time.
2. **Detect** — identify a concrete opportunity or regression. Separate measured facts from inferred causes and speculative ideas.
3. **Prioritize** — rank candidates by expected verified benefit, urgency, confidence, cost, risk, dependencies, and reversibility. Keep competing candidates visible.
4. **Contract** — create a bounded task with objective, scope, exclusions, risk tier, permitted actions, acceptance criteria, resource budget, required evidence, and recovery plan.
5. **Investigate** — inspect relevant implementation, history, contracts, tests, and existing tasks. Check for overlapping ownership before editing.
6. **Hypothesize** — state the suspected cause, expected outcome, alternatives, and a falsifiable prediction. Prefer the smallest experiment that can distinguish competing explanations.
7. **Experiment** — work in an isolated branch/worktree or disposable test environment. Never use valuable user data or production state as an experiment without explicit authorization.
8. **Evaluate** — run relevant correctness, security, compatibility, and quality checks against a recorded baseline. An independent verifier should challenge the result where feasible.
9. **Deliver** — produce a reviewable commit/PR and a complete evidence-based handoff. Promotion or merge is a separate authorization decision.
10. **Monitor** — after an authorized rollout, observe regressions and expected effects. Stop or roll back when hard invariants fail or agreed guardrails are breached.
11. **Learn** — record successes, failures, rejected hypotheses, evaluation gaps, and reusable findings with provenance. Do not rewrite canonical facts based on a failed experiment.
12. **Improve the loop** — periodically evaluate whether detection, prioritization, experimentation, verification, and recovery themselves are becoming more effective.

A failed experiment is a valid outcome when it is safely contained, accurately recorded, and used to update future decisions. Repeating an experiment without checking prior evidence is a system failure.

## Task contract

Every autonomous unit of work must be representable as a durable, machine-readable task. AIDB's existing `.aidb/agent-task-template.yml` is the starting point; extend it only when concrete implementation needs are established.

At minimum, a task records:

- Stable task ID, title, objective, and status.
- Target repository, base commit, relevant contracts, and related issues/PRs.
- One accountable agent/owner and any collaborators.
- Included and excluded scope.
- Risk tier, allowed actions, prohibited actions, and approval requirements.
- Acceptance criteria that can be observed and tested.
- Baseline measurements and expected benefit.
- Hypothesis, alternatives, and experiment plan.
- Time/token/compute/test budgets and cancellation conditions.
- Required checks, actual exit codes, artifacts, and evidence links.
- Result: improved, unchanged, regressed, inconclusive, or blocked.
- Changed paths/commits, rollback or recovery instructions, and next action.

Task claiming must eventually be atomic and lease-based, with expiry, heartbeat, idempotency, conflict detection, and abandoned-task recovery. Until that exists, GitHub issues/PRs remain the coordination source of truth; a journal entry alone does not reserve work.

## Evidence and evaluation

A proposed change is not an improvement merely because an agent says it is better or because a test passes.

Each experiment should compare a candidate against a named baseline and preserve:

- Source revision and environment/tool versions.
- Input fixture or authorized workload description.
- Expected and observed behavior.
- Exact commands, exit codes, test counts, and CI run links.
- Before/after measurements and evaluation method.
- Known blind spots, uncertainty, and dissenting results.
- Decision, authorization, rollout state, and recovery path.

Correctness, authorization, privacy, provenance, data integrity, and recoverability are **hard gates**, not weighted preferences. A candidate that violates one is rejected regardless of speed or convenience.

For quality and efficiency, use task-appropriate measures rather than one universal score. Examples include defect rate, regression rate, retrieval relevance, evidence fidelity, latency percentiles, throughput, memory/disk use, migration/restore success, and human review burden.

Guard against Goodhart's law: retain fixed evaluation sets, periodically refresh held-out cases, test adversarial and negative cases, and use more than one evaluator for high-impact claims. A metric improvement that degrades unmeasured user outcomes is not accepted as a net improvement.

## Authority and risk

Use the risk tiers already described in [Self-Evolving Architecture](self-evolving-architecture.md). Enforce them in executable policy and permissions, not only in agent instructions.

- Read-only discovery and proposal generation may be autonomous within granted access.
- Reversible work in isolated branches and disposable fixtures may proceed within a bounded task contract.
- Repository changes should normally be delivered as reviewable branches/PRs, not pushed to protected default branches.
- Human/designated maintainer approval remains required for merges/releases, permission or secret changes, destructive operations, public exposure, production migrations, new network access, and unresolved security-sensitive decisions.
- No agent may disable audit, access control, integrity checks, resource limits, isolation, or recovery to make a task easier.
- Untrusted artifacts must not be executed unless a verified isolated runtime and explicit permission exist.

Approval must be explicit and scoped to the action. A broad statement of project ambition is not blanket authorization for every future high-impact operation.

## Shared learning across repositories

The ecosystem should learn across repository boundaries without creating a single undifferentiated knowledge pool.

- Store findings with source repository, commit, time, author/agent, scope, confidence, and evidence.
- Distinguish observations, hypotheses, accepted decisions, implementation facts, and proposals.
- Preserve contradictory evidence and rejected alternatives.
- Reuse a lesson only after checking that its assumptions apply to the target repository.
- Keep private or access-restricted material within its authorization boundary.
- Track dependencies between repositories so a shared contract change can trigger relevant downstream checks without silently editing every dependent project.

## Implementation sequence

Build this capability incrementally. Do not start with an unrestricted agent that can modify every repository.

### Phase 0 — Make the loop observable

1. Reconcile this contract with the existing self-evolution design, roadmap, task template, and collaboration issue.
2. Define a small set of machine-readable task states and evidence fields.
3. Create a read-only ecosystem inventory: repositories, default branches/commits, project instructions, CI state, open issues/PRs, and declared dependencies.
4. Produce a prioritized improvement queue with evidence and no automatic edits.
5. Demonstrate that a second agent can resume a task from its durable handoff without private conversational context.

### Phase 1 — Execute bounded work

1. Validate task contracts before work begins.
2. Add durable task claims/leases and conflict handling, building on the existing multi-agent collaboration work.
3. Run agents in isolated branches/worktrees with explicit file/repository scope and resource budgets.
4. Capture commands, outputs, artifacts, and exact verification evidence.
5. Exercise failure diagnosis and repair using observed failures, including a deliberately failing regression test in a disposable fixture.
6. Open reviewable PRs and leave complete handoffs; do not auto-merge.

### Phase 2 — Evaluate improvements

1. Add repeatable baseline benchmarks and task-specific evaluation fixtures.
2. Add independent review/verification and negative controls for important claims.
3. Compare candidate changes with baselines and reject regressions in hard invariants.
4. Record outcomes, failed hypotheses, and evaluation blind spots.
5. Measure end-to-end cycle time, success rate, regression rate, review burden, and recovery success.

### Phase 3 — Carefully increase autonomy

1. Identify low-risk, reversible actions that have demonstrated reliable policy enforcement.
2. Allow automatic execution only for explicitly allowlisted actions with bounded scope and budgets.
3. Add canary/monitor/rollback mechanisms before any production promotion.
4. Keep structural, destructive, security-sensitive, and externally visible actions approval-gated.
5. Use measured outcomes to improve the task selector, experiment design, evaluator, and recovery process.

## Definition of demonstrated autonomy

Do not call the system autonomously self-improving until repeatable evidence shows that it can:

1. Discover a real opportunity from current repository evidence.
2. Prioritize it against alternatives and explain the trade-off.
3. Create and claim a bounded task without overlapping another active owner.
4. Resume from durable state in a separate agent session.
5. Implement a change in isolation and repair a failure using observed output.
6. Verify the candidate against baseline tests and relevant negative/security cases.
7. Deliver a reviewable result with exact evidence and truthful attribution.
8. Recover safely from a failed experiment.
9. Learn from both success and failure without contaminating canonical knowledge.
10. Improve at least one measurable property of its own improvement process over repeated cycles.

The first milestone is not self-modifying code. It is a reliable, repeatable, evidence-producing improvement loop.

## Relationship to existing AIDB work

- [Self-Evolving Architecture](self-evolving-architecture.md) defines the evolution layers and risk tiers.
- [Implementation Roadmap](IMPLEMENTATION_ROADMAP.md) tracks the engineering work, including the P0 AI development loop and P3 reviewed self-improvement.
- [Multi-agent collaboration issue #29](https://github.com/usamaizm/AIDB/issues/29) tracks GitHub-native coordination, durable task claims, and messaging.
- `.aidb/agent-task-template.yml` is the existing task-contract seed.
- `AGENTS.md` and the session manifest remain the authoritative repository-specific workflow and safety instructions.

This document is an operating proposal. Implementation status must continue to be established by source, regression tests, and current CI—not by this document.
