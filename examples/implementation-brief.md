# Copilot implementation brief

This is the implementation brief that GitHub Copilot should follow for the accepted task.

## Objective
Add a basic decision-log capability to AIDB to support durable, reviewable project decisions.

## Context
AIDB already has a protocol and knowledge model, but no first-class API for accepted project decisions. This makes it harder to capture reviewed lessons and design outcomes during iterative improvement.

## Requirements

- Add a data model for a decision record
- Include fields for title, summary, rationale, status, related references, and timestamps
- Allow records to be created and retrieved through the AIDB API
- Keep the feature small and explicit
- Do not automatically promote a record to accepted status without a review workflow

## Out of scope

- adding a full external search service
- changing repo permissions
- granting Copilot direct merge rights
- allowing unreviewed proposals to become knowledge without review

## Acceptance criteria

- Decision records can be created and read through AIDB
- records include rationale and status
- docs mention how accepted decisions differ from proposals
- the feature is covered by tests or validation examples

## Review checkpoints

- validate naming and API fit with existing AIDB patterns
- confirm record status semantics are clear
- confirm design remains safe and local-first
