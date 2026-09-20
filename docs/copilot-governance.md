# Copilot Governance and Execution Model

This document defines how GitHub Copilot participates in the AIDB workflow without bypassing the repository’s trust boundaries.

## Core rule

GitHub Copilot is the implementation agent. AIDB is the coordination and knowledge layer. The maintainer is the final authority.

## Responsibilities

### GitHub Copilot

GitHub Copilot may:

- read relevant instructions and repository context
- implement accepted tasks
- update code and tests
- draft documentation improvements
- open pull requests
- respond to review feedback

GitHub Copilot must not:

- decide that its own proposal is accepted
- merge its own pull request
- change repository permissions or secrets
- modify protected workflows without approval
- treat unreviewed output as authoritative knowledge
- bypass the request and review policy

### AIDB

AIDB stores and organizes:

- tasks
- requests
- decisions
- protocol rules
- evaluation records
- accepted knowledge
- workflow history

### Maintainer

The maintainer is responsible for:

- approving or rejecting requests
- reviewing implementation proposals
- approving PRs
- deciding when a change becomes authoritative knowledge
- maintaining repository policy and safety boundaries

## Execution flow

```text
proposal or request
  -> triage and validation
  -> review and approval
  -> task creation
  -> Copilot implementation
  -> tests and review
  -> maintainer approval or revision
  -> merge and knowledge update
```

## Task template requirements

Accepted Copilot tasks should include:

- objective
- relevant context
- required behavior
- constraints and out-of-scope items
- acceptance criteria
- review checkpoints
- knowledge update expectations

## Safety boundaries

Copilot should always operate under the following constraints:

- no secret access
- no direct repo admin actions
- no merge without review approval
- no workflow modification without explicit approval
- no automatic promotion of unreviewed output

## Knowledge update rule

AIDB may learn from the outcome of a task, but learning must be reviewable.

Only accepted, reviewed outcomes may become knowledge.

## Result

This separation creates a practical, safe, and scalable workflow:

- proposals can come from humans or AIs
- the repository retains durable memory
- GitHub Copilot executes implementation work
- the maintainer remains the final decision-maker
