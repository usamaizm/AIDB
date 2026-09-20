# Example accepted request

This file is an example of the process by which an AI or human proposal becomes an accepted, reviewable task.

## Request

**Type:** feature_request
**Title:** Add a small decision-log API to AIDB
**Source AI:** Copilot
**Source version:** 1.0
**Priority:** normal
**Risk:** low

### Summary
AIDB needs a simple API to record accepted project decisions, their rationale, and any related references so AIDB can be used as a durable knowledge layer over time.

### Motivation
The project currently has protocol and knowledge docs, but it does not yet have a reusable API for recording design decisions in a structured way.

### Proposal
Add a method to record project decisions with:
- title
- summary
- rationale
- status
- related references
- created date

The decision record should be searchable and traceable, without permitting unreviewed proposals to become authoritative knowledge.

### Constraints
- read-only or write-only to the decision log, not to all repo state
- no credentials or secrets
- no automatic promotion from proposal to accepted status without review

### Acceptance criteria
- A decision record can be created and listed
- the record stores rationale and status
- related references can be included
- unreviewed records are distinguishable from accepted records

### Status
accepted
