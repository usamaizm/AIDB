# Iteration guide

AIDB is intentionally evolving. This guide describes how ideas can move through the project without prematurely becoming commitments.

```text
brainstorm -> exploration -> experiment -> proposal -> decision -> implementation -> review
```

## 1. Capture

Write the idea down in `brainstorms/`. Include why it is interesting, possible interpretations, risks, and questions. Do not require a complete solution.

## 2. Explore

Connect the idea to existing notes, compare alternatives, and record what would make it useful or unsuitable.

## 3. Experiment

Use the smallest reversible prototype or example that can teach us something. Keep generated data and large artifacts outside the Git repository.

## 4. Propose

When an idea has a clear purpose and scope, create a focused proposal. State what is intentionally out of scope.

## 5. Decide

Only deliberate, reviewed choices belong in `docs/decision-log.md` or machine-readable protocol files. A decision should include its rationale and what would cause it to be revisited.

## 6. Implement and review

Implementation should happen through normal tasks, tests, and pull requests. Update the relevant knowledge record after the result is known.

## Lightweight note template

```markdown
# Title

**Status:** raw | exploring | promising | parked | revisited | resolved
**Captured:** YYYY-MM-DD

## Idea

## Why it is interesting

## Possible directions

## Risks and tensions

## Open questions

## Related notes
```

The repository is a durable memory for the thinking process, not a demand that every early idea become a feature.
