# AIDB Request Review Checklist

Use this checklist when evaluating an issue submitted through the AI request intake form.

## Before evaluation

- [ ] The request contains a supported request type.
- [ ] The source AI and version are identified where available.
- [ ] The request is not asking for secrets, permissions, or direct merging.
- [ ] Related issues, discussions, and existing documentation were searched.

## Evaluate

- [ ] Relevant to AIDB's goals and current scope.
- [ ] Specific enough to act on.
- [ ] Technically feasible with the stated constraints.
- [ ] Not a duplicate or contradiction of accepted knowledge.
- [ ] Security and permission impact is understood.
- [ ] Scope and implementation cost are reasonable.
- [ ] Expected outcome and success criteria are clear.

## Record a decision

Choose exactly one outcome:

- `status:accepted`: convert into an actionable task.
- `status:rejected`: explain why it will not be pursued.
- `status:needs-clarification`: ask focused follow-up questions.
- route to architecture, security, or maintainer review when specialist input is required.

An accepted request is still not permission to merge. Implementation must happen through a reviewed pull request.
