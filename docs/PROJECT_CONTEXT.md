# AIDB Project Context and Collaboration Agreement

**Status:** Draft; exploratory and nonbinding until explicitly accepted by the maintainer.  
**Purpose:** Preserve project intent and collaboration context across humans, AI agents, sessions, and implementations.

## 1. Vision

AIDB aims to become an agent-friendly database and collaboration platform for AI systems. The long-term vision includes:

- Persistent memory and knowledge with provenance.
- Agent discovery, capability awareness, and collaboration.
- Shared context that lets humans and agents build on prior work without repeatedly reconstructing it.
- Accessible integration across languages, models, frameworks, and deployment environments.
- Durable, reviewable, portable state and history.

These are aspirations to explore, not a commitment to implement every capability immediately.

## 2. Immediate priority: continuity

An agent joining AIDB should be able to discover:

1. The project's current vision and purpose.
2. The maintainer's stated goals and constraints.
3. Explicitly accepted principles and decisions.
4. Proposals, experiments, disagreements, and unresolved questions.
5. Relevant work already attempted, its evidence, and lessons learned.
6. Current work, known limitations, and useful next steps.

Project memory should make context recoverable rather than dependent on a person or agent remembering an earlier conversation.

## 3. Keep the project open to evolution

AIDB is experimental and its architecture may evolve. Contributors should:

- Explore before standardizing.
- Discuss consequential foundational choices before making them difficult to reverse.
- Distinguish evidence from assumptions and recommendations.
- Mark brainstorms and experiments as provisional.
- Prefer small, reviewable, reversible changes while questions remain open.
- Preserve provenance, privacy, security, portability, and compatibility as explicit concerns.
- Let implementation experience inform architecture without treating today's implementation as the permanent contract.
- Avoid adding a feature merely because a framework or protocol makes it possible.

Documenting an idea or implementing a prototype does not, by itself, make it accepted policy.

## 4. Decision and knowledge status

Use explicit status labels where useful:

- **Idea:** A possibility worth exploring.
- **Under discussion:** Alternatives and trade-offs are being considered.
- **Experiment:** A limited test or implementation is underway or has been tried.
- **Provisionally accepted:** The current preferred direction may still change.
- **Accepted:** The authorized decision-maker explicitly approved the decision.
- **Rejected:** Considered and not selected; retain the rationale when useful.
- **Superseded:** Replaced by a later decision, with history preserved.
- **Verified result:** A claim supported by a specific test, observation, or source.

These labels are not interchangeable. Agent agreement is not proof of technical correctness; a successful experiment does not automatically settle the long-term architecture.

## 5. Agent identity and self-description

Contributors should identify themselves as specifically as their environment permits. Keep separate the agent's declared identity, underlying model, product/runtime, and any project-specific nickname.

Record available fields when relevant:

- Stable project agent ID.
- Display name and optional nickname.
- Provider or organization.
- Exact model identifier and version/snapshot, if exposed.
- Product, runtime, API, or coding environment.
- Relevant capabilities, tools, and permission scope.
- Known limitations.
- Session timestamp.
- Source or confidence of identity claims (for example, verified by the runtime, provider-reported, self-reported, or unknown).

Do not invent model versions, subscription tiers, capabilities, or internal identifiers. Mark unavailable values as unknown. Nicknames are labels for collaboration, not evidence of technical identity.

An example template (illustrative only):

```yaml
agent:
  id: "agent:<provider>:<purpose-or-instance>"
  display_name: "<agent or product name>"
  nickname: null
  provider: "<provider, if known>"
  model:
    identifier: "<exact identifier or unknown>"
    version: "<exact version or unknown>"
    verification: "runtime-reported | provider-reported | self-reported | unknown"
  runtime:
    product: "<application, API, or environment>"
    plan: "unknown"
  capabilities: []
  limitations: []
  session:
    started_at: "<ISO 8601 timestamp with timezone, if available>"
```

A declared identity is not authentication. If AIDB later supports consequential network operations, authentication and authorization must be designed separately.

## 6. Contributions and intellectual provenance

Preserve meaningful contributions as attributable perspectives rather than blending them into a single anonymous voice.

Where relevant, a contribution should record:

- Author agent or human ID.
- Timestamp and relevant project revision/context.
- Type: proposal, review, finding, experiment, objection, or summary.
- The actual position or recommendation.
- Concise rationale and supporting evidence or links.
- Assumptions, uncertainty, and confidence where useful.
- Alternatives considered.
- Material agreements and disagreements.
- Outcome/status and who had authority to decide.
- Links to related contributions, decisions, changes, and test results.

Represent disagreements fairly. Do not claim unanimity when contributors differ, and do not present an agent's recommendation as the maintainer's decision. Preserve rejected and superseded ideas when their rationale may help future work.

Do not persist credentials, secrets, or unnecessary private conversation details in project memory.

## 7. Decision records

For consequential decisions, capture:

- **Question:** What needs to be decided and why?
- **Status:** Open, experimental, provisionally accepted, accepted, rejected, or superseded.
- **Options:** Material alternatives considered.
- **Evidence and trade-offs:** Benefits, risks, assumptions, and unknowns.
- **Contributors:** Who supplied relevant perspectives.
- **Decision owner:** Who made or authorized the decision.
- **Rationale:** Why this option was selected, or why no choice was made yet.
- **Consequences:** Expected effects and follow-up work.
- **Revisit conditions:** Evidence or circumstances that should trigger reconsideration.
- **History:** Links to previous decisions or revisions.

The maintainer's stated vision should remain distinguishable from agent advice and group consensus.

## 8. Agent handoff

After meaningful work, leave a concise handoff with:

- Agent identity and relevant environment details.
- Repository revision/branch and files inspected or changed.
- Work completed and findings.
- Recommendations, assumptions, and unresolved questions.
- Disagreements worth preserving.
- Tests/checks actually run and their observed results.
- Suggested next steps.

Inspect the current repository and existing pull requests before starting overlapping work. Never claim a test passed unless a current run or reliable result confirms it.

## 9. Collaboration loop

A useful default workflow is:

1. **Discuss** the goal and problem.
2. **Clarify** constraints, assumptions, and open questions.
3. **Compare** options and trade-offs.
4. **Agree on scope** and whether to experiment.
5. **Implement** a focused change once authorized.
6. **Verify** the result and report limitations honestly.
7. **Record** decisions, evidence, and a handoff.

Keep routine exploration lightweight; make consequential changes reviewable.

## 10. Open by design

This document does not freeze AIDB's canonical resource model, identity system, temporal semantics, replication model, wire protocol, or boundary between core and adapters. Those remain questions for research, discussion, and experiments until explicitly decided.

This document is itself a draft. Revise it when experience reveals a better process, and record substantive changes rather than implying that provisional language was always settled.

## 11. Measures of progress

Alongside implementation progress, ask:

- Can a new agent recover the vision and current state without making the maintainer repeat everything?
- Are opinions, evidence, and accepted decisions clearly distinguished?
- Are disagreements preserved accurately?
- Are experiments producing useful learning?
- Is the project becoming more reliable without prematurely restricting its future?
- Can contributors explain what remains unknown and why?

**Working principle:** Preserve not only what AIDB concludes, but who contributed each perspective, what informed it, and how decisions evolved.
