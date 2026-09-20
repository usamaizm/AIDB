# Request evaluation rubric

This document defines the evaluation rubric for requests submitted to AIDB or associated with the repository.

## Purpose

The goal is to avoid silent acceptance of low-quality, unsafe, or high-risk proposals while still preserving a lightweight and practical review process.

## Evaluation criteria

Requests should be evaluated using the following dimensions.

### 1. Clarity

- Is the request understandable?
- Are the stated goals and constraints clear?
- Are the required fields present?

### 2. Scope and fit

- Is the request aligned with the repository purpose?
- Is the request within project scope, or does it expand beyond the project’s intended boundaries?
- Does it fit the current architecture and maintenance model?

### 3. Risk

- Does the request involve code changes, workflow changes, permissions, or secrets?
- Could it affect security, repository integrity, or operational stability?
- Is the change reversible or easy to audit?

### 4. Priority

- Is there an immediate need?
- Does the request support an active project goal or a known gap?
- Does it help maintain project clarity, safety, or repeatability?

### 5. Evidence and provenance

- Is the request grounded in a concrete issue, requirement, or prior decision?
- Is there enough evidence to justify the proposal?
- Is the request transparent about uncertainty or assumptions?

### 6. Compliance and governance

- Does the request respect repo protocols, permissions, and human review requirements?
- Is it aligned with the project’s knowledge and authority order?
- Does it avoid bypassing explicit review gates?

## Recommended decision outcomes

### Accept

Use when the request is clear, relevant, low-risk, and appropriately scoped.

### Ask for clarification

Use when key details are missing or ambiguity is high.

### Route or create a task

Use when the request is valid but requires a specific workstream or agent.

### Reject or defer

Use when the request is off-scope, risky, unclear, or incompatible with project governance.

## Review expectations

- Human review is required for code or workflow changes.
- Requests that touch security, secrets, or permissions should be treated as high risk.
- Proposed content should be visibly distinguished from accepted project knowledge.

## Final rule

If evidence is weak, the request should not be promoted automatically. Uncertainty should be reported rather than hidden.
