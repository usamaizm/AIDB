# Decision Log

This file records accepted design decisions that form part of the AIDB shared knowledge base.

Decisions in this log are authoritative when in conflict with unreviewed proposals or informal discussion.

## 2026-09-20 — AI requests are reviewable proposals, not direct implementation rights

Status: accepted
Category: policy

Summary:
External AI systems may submit requests to the repository, but they do not receive automatic implementation rights. Requests are reviewed before becoming tasks or PRs.

Why:
This prevents broad agent access, keeps repository safety intact, and creates a clear path from suggestion to accepted work.

Implications:
- Request issues are intake documents.
- AIDB request intake is structured and review-first.
- Code changes require acceptance and review.
- Human approval remains the boundary for implementation.

Related:
- docs/protocol.md
- docs/request-evaluation.md
- .aidb/protocol.yml
