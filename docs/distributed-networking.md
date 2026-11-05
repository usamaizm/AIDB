# AIDB Distributed Networking Architecture

Status: proposed architecture; not yet implemented.

AIDB is intended to become a distributed knowledge substrate. Independent nodes may store, discover, verify, retrieve, and replicate selected portions of a shared knowledge space. No node is required to hold the entire corpus, and no single topology or central service is mandatory.

The logical knowledge model must remain independent of physical placement. A logical resource or artifact may be represented by immutable content chunks, a versioned manifest, and expiring location records. Chunk identifiers are integrity identifiers, not permissions or provenance claims.

## Security

All communication crossing a machine or trust boundary must use authenticated encrypted transport. HTTPS is the initial interoperable request/response transport. TLS 1.2 is the minimum for the existing HTTP adapter; TLS 1.3 is preferred. Clients verify certificates and hostnames by default. Mutual TLS is an option in this design where deployments need certificate-based peer authentication. No network connection silently falls back to plaintext.

AIDB node identity is transport-independent and must not be an IP address, hostname, or certificate serial number. The authenticated transport peer must be bound to a claimed node identity. Agent identity remains distinct from node identity. Authentication does not grant authorization: every discovery, read, write, and replication operation is separately authorized.

Use established cryptographic standards and maintained libraries. Define versioned identity keys, signed key rotation, revocation, canonical manifests, and test vectors before freezing the wire format. Verify content digests and lengths before persisting received chunks. Preserve provenance separately from content identity. Private content is not replicated merely because a peer knows its identifier; replication requires explicit policy and authorization. Application-level encryption may be required when replicas cross trust boundaries.

## Distributed behavior

AIDB should support partial replication. Nodes may store selected chunks according to explicit policy. Discovery may use static peers, DNS, registries, gossip, or other adapters; discovery data is untrusted until the peer is authenticated and its identity claim verified. Location records expire and can be refreshed without changing content identifiers.

The protocol must define idempotent transfer, bounded streaming, retry/backoff, resumable transfer, change cursors, replication policy, deletion/retention, conflict handling, and offline/partition behavior. Do not imply global ACID transactions across disconnected nodes. Prefer verifiable immutable content and explicit eventual synchronization over pretending to provide global strong consistency.

All network operations need bounded payloads, timeouts, concurrency, decompression, query cost, retries, and retained discovery state. Internet-facing nodes additionally need quotas, rate limits, and per-agent authorization. Retrieved artifacts remain inert data and must never be executed as a side effect of retrieval or replication.

## Implementation sequence

1. Freeze node identity, trust, key rotation, and revocation semantics.
2. Define canonical chunk and manifest formats with cross-language test vectors.
3. Define authenticated peer handshake and capability negotiation.
4. Implement read-only remote chunk retrieval with integrity verification.
5. Add explicitly authorized publication, discovery, and expiring location records.
6. Add resumable partial replication and cursor-based synchronization.
7. Define conflicts, deletion, retention, and recovery before claiming production-grade distributed state.

## Current implementation status

The Python implementation currently has an inbound HTTP adapter. Non-loopback binding already requires a bearer token and TLS certificate/key; TLS 1.2 is the minimum. This does not implement outbound peer connections, stable cryptographic node identity, distributed chunk location, or replication. Authorization remains coarse and lacks per-agent scopes and multi-tenant isolation.

AIDB should not be described as having implemented distributed storage until tests demonstrate two independent authenticated nodes, chunk publication/retrieval, integrity verification, partial replication, restart recovery, offline peer handling, deterministic conflict behavior, and language-neutral protocol interoperability.
