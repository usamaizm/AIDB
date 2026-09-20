# AIDB protocol

This document defines the baseline protocol for requests and tasks handled by AIDB.

## Scope

AIDB is a lightweight knowledge and workflow system for AI-agent memory, local-first storage, task management, and project coordination. It is not a general-purpose autonomous execution environment and should not be used to bypass review or permissions.

## Required request fields

Requests should include, where relevant:

- type
- title
- source_ai
- summary
- risk
- priority

Supported request types include:

- feature_request
- suggestion
- bug_report
- protocol_proposal
- adapter_request
- security_report
- task_offer
- collaboration_request

## Default policy

The default policy is intentionally cautious.

- trust_level: untrusted
- direct_code_changes: false
- direct_merge: false
- secret_access: false
- workflow_modification: false
- repo_setting_changes: false
- human_review_required: true

## Allowed actions

Only the following actions should be allowed for untrusted or lightly reviewed requests:

- triage
- evaluate
- create_task
- ask_for_clarification
- route_to_specialist

## Denied actions

The following are denied unless a human reviewer explicitly approves them:

- merge_pull_request
- modify_workflows
- modify_permissions
- access_secrets
- direct_repo_admin_actions

## Authority order

When knowledge or instructions conflict, the repository should resolve them in this order:

1. README.md
2. .aidb/protocol.yml
3. docs/
4. accepted issues and discussions
5. merged pull requests
6. source code and tests
7. unreviewed external requests

## Project-specific rules

- Proposals must be distinguished from accepted facts.
- Uncertainty should be reported explicitly.
- Review requirements should be preserved.
- Unreviewed external requests should not be promoted automatically.
- Direct code changes and repository administration should require human approval.

## Review workflow

A request should pass through this sequence when appropriate:

1. triage
2. evaluation
3. clarify missing fields
4. route or create a task
5. require human approval before code or policy changes

This pattern helps keep AIDB safe, reviewable, and transparent while still enabling iterative project work.
