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

## 2026-11-15 — D1: Per-record digests and canonicalization for aidb-home-v2

Status: accepted
Category: contract / integrity

Summary:
The aidb-home-v2 format will carry a per-record SHA-256 digest for each exported record, computed over a canonical serialization (RFC 8785 / JCS). The canonicalization primitive lives in `aidb/canonical.py`; artifact digests are keyed by D4's stable artifact ID, not by content checksum alone.

Why:
Exported homes need tamper evidence per record, not just per file, and digests are only comparable across nodes if every node canonicalizes identically.

Implications:
- A v2 importer/verifier must check record digests on ingest.
- The digest primitives exist today; wiring them into export/import/verify is follow-on work.
- One canonicalization rule is shared with the distributed manifest (see the 2026-11-05 boundaries entry).

Related:
- GitHub issue #29 (acceptance record)
- aidb/canonical.py

## 2026-11-15 — D2: aidb-home-v1 legacy policy

Status: accepted
Category: contract / compatibility

Summary:
aidb-home-v1 remains a supported legacy format under the terms recorded on issue #29. v1 payloads are never silently reinterpreted as v2: verified-v2 content must be distinguishable from legacy content, and any wrap/migrate/reject choice for a v1 payload is explicit.

Why:
Homes already exported as v1 must keep a defined meaning once v2 exists; silent reinterpretation would corrupt provenance and integrity claims.

Implications:
- The v2 importer must state its v1 behavior explicitly.
- This matches boundary (3) in the 2026-11-05 boundaries entry.

Related:
- GitHub issue #29 (acceptance record)
- docs/evolution-and-compatibility.md

## 2026-11-15 — D3: Artifacts are in the default portable profile

Status: accepted
Category: contract / portability

Summary:
Artifacts and their blobs are part of the default portable profile of the home format (they are `portable` in `aidb/portability.py`), rather than an opt-in extra.

Why:
Artifacts are the substrate's primary content; a default profile that left them behind would export a home missing the material its provenance chain refers to.

Implications:
- Public (filtered) exports still apply visibility rules separately; D3 governs the full profile.
- Blob size and privacy consequences are handled by the profile's visibility rules, not by excluding artifacts by default.

Related:
- GitHub issue #29 (acceptance record)
- aidb/portability.py

## 2026-11-15 — D4: Stable external IDs

Status: accepted
Category: contract / identity

Summary:
Records that cross node or home boundaries carry stable external IDs that do not change across export/import round trips. Internal row IDs are an implementation detail; digests (D1) and cross-references key off the stable external ID.

Why:
Per-record digests, replication, and cross-home references are meaningless if a record's identity changes every time it is imported.

Implications:
- The v2 envelope must define the stable ID for each portable record family.
- Import paths must preserve, not re-mint, external IDs.

Related:
- GitHub issue #29 (acceptance record)

## 2026-11-05 — Distributed-networking decision boundaries (six)

Status: accepted (agent-level consensus 2026-11-05; PR #61 adopted as the proposed distributed architecture, its content on main via commit 3d32b3e)
Category: architecture

Summary:
Six boundaries govern all distributed-networking work:
1. Stable opaque node identity bound to a cryptographic key, with rotation/revocation/bootstrap specified **before** implementation; TLS never implies authorization.
2. One canonicalization rule shared by the integrity work (N4b/D1) and the distributed manifest.
3. No silent reinterpretation of aidb-home-v1 (see D2).
4. Discovery and location records are untrusted, expiring hints.
5. Explicit per-node/per-content partial replication; no implied global consensus. Conflict, tombstone, and deletion semantics are deferred as separate maintainer decisions.
6. PR #49 is treated as the semantic collaboration layer only, not as transport.

Why:
These boundaries keep identity, integrity, and compatibility decisions ahead of implementation, so the data plane is not built on unstated assumptions.

Implications:
- No networking implementation may freeze a wire format that violates a boundary without a new decision recorded here.
- The distributed target direction (next entry) is executed inside these boundaries.

Related:
- DISCUSSION.md entries 2026-11-05T19:48:00Z and 2026-11-05T19:52:00Z
- docs/distributed-networking.md
- docs/evolution-and-compatibility.md

## 2026-11-05 — Target direction: AIDB becomes a distributed system

Status: accepted (maintainer direction)
Category: architecture

Summary:
AIDB's target architecture is distributed: home data is split into chunks scattered and replicated across independently operated nodes; no node must hold the full corpus. The work splits into an interop/control plane (discovery, agent cards, requests — HTTPS first) and a data plane (chunking, content addressing, placement, replication, retrieval, per-chunk privacy). The data plane is the primary design work.

Why:
A single local SQLite file with an HTTP front does not meet the project's goal of a shared substrate across agents and machines.

Implications:
- The current single-node implementation is the foundation and local case, not the end state.
- `aidb/http_client.py` (verified HTTPS document fetch) is an early interop step only; the peer protocol itself is not yet implemented.
- All distributed work stays inside the six boundaries above.

Related:
- docs/distributed-networking.md
- DISCUSSION.md (2026-11-05 entries)

## 2026-11-16 — Maintainer directives: threading, sessions, streaming, best practices

Status: accepted (maintainer instruction, 2026-11-16)
Category: implementation direction

Summary:
The maintainer directed four implementation lanes on the current single-node codebase:
- **Threading:** the store must support real concurrent reads — per-thread connections, WAL mode, and `busy_timeout` — instead of serializing every request behind one connection lock.
- **Sessions:** implement a real session lifecycle (create/participate, session-scoped messages, per-session change cursors) on the existing `sessions`/`session_participants`/`messages` tables. This supersedes the Q26 review's storage-only disposition for the session tables, which had been made because no write paths existed.
- **Streaming:** generator-based streaming export/import, a chunked cursor-resumable change feed over HTTP, and bounded artifact-blob streaming, so whole homes are never materialized in memory.
- **Best practices:** the whole repository is held to best coding practices — clean lint and formatting, honest capability claims, tests asserting true invariants.

Why:
Concurrency, session scoping, and bounded streaming are prerequisites for the distributed data plane and for multi-agent use of a single node today.

Implications:
- Q26's storage-only call remains in force for the other collaboration-facade tables (`tasks`, `message_reads` stay undecided/dead schema) unless separately directed.
- Portability of the session tables is a separate, still-open decision; implementing sessions does not make them portable.

Related:
- docs/current-state.md (lane status)
- aidb/portability.py (registry unchanged by these lanes)
