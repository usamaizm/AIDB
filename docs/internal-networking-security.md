# Internal networking security architecture

Status: proposed security baseline; not a frozen wire protocol.

This document defines security requirements for communication between AIDB nodes and trusted services. It does not claim that peer networking, replication, mutual TLS, or per-node authorization is implemented today.

## 1. Scope and threat model

Internal networking means node-to-node or service-to-node communication across a process, host, container, private subnet, VPN, or service mesh. "Internal" is a routing description, not a trust boundary. Any reachable peer is potentially compromised or hostile.

Assume an attacker may:
- observe, inject, modify, replay, delay, or drop network traffic;
- connect from an untrusted or compromised host on a private network;
- steal a node credential or gain access to one node;
- send malformed, oversized, deeply nested, or expensive requests;
- exploit retries, concurrent updates, stale replicas, and partial failures.

The design must protect confidentiality in transit, peer identity, operation-level authority, data integrity, and availability within stated resource limits. It cannot guarantee availability against a network-level denial of service or protect a fully compromised endpoint.

## 2. Secure defaults

1. Peer networking is disabled unless explicitly configured.
2. Local embedded operation remains available without a network listener.
3. A listener binds to loopback by default. A non-loopback bind requires explicit secure configuration.
4. Plaintext transport is forbidden for remote peers. Do not rely on private IP ranges, firewalls, VPN membership, DNS names, or service discovery as authentication.
5. Unknown peers, unknown protocol versions, and unknown required capabilities fail closed.
6. A transport connection or successful authentication never grants unrestricted database access.

## 3. Transport security and peer identity

The initial interoperable remote transport SHOULD be HTTPS over TLS 1.3. TLS 1.2 MAY be enabled only as an explicit compatibility policy; obsolete protocol versions and weak cipher suites MUST be disabled.

For node-to-node communication, mutual TLS (mTLS) SHOULD be the baseline:
- each node has a distinct certificate and private key;
- both sides validate certificate chains against explicitly configured trust roots;
- the peer identity is derived from a validated certificate identity, not a caller-supplied node ID or IP address;
- certificate identity MUST be bound to the AIDB node identity through a documented identity profile;
- hostname/SAN validation is required when DNS names are used;
- private keys must be protected at rest and never transmitted.

A deployment MAY terminate TLS at a trusted proxy or service mesh only if the proxy-to-AIDB hop is also authenticated and encrypted, and the proxy conveys peer identity through a channel the backend can verify. Unauthenticated forwarded identity headers MUST NOT be trusted.

Bearer tokens may be used for a single trusted client or bootstrap path, but are not equivalent to mTLS and MUST NOT be treated as durable node identity. Tokens MUST be high entropy, scoped, stored as secrets, rotated, revocable, and sent only over TLS.

## 4. Authentication, authorization, and trust

Keep these concepts separate:
- node identity: which AIDB node is connecting;
- authentication: proof that the peer controls its credential;
- authorization: which operations and data the peer may access;
- provenance: who or what originated a stored fact or mutation;
- trust: policy or review state assigned to content or peers.

Every request MUST be authorized at the operation boundary. Authorization SHOULD be deny-by-default and scoped by peer identity, operation, resource namespace/ownership, and visibility. At minimum, read, create, update, delete, relationship, change-feed, snapshot-export, snapshot-import, and administrative capabilities must be separable.

A peer MUST NOT gain write authority merely by being authenticated, discovered, listed in a peer registry, or connected over a private network. Imported content remains untrusted data regardless of the authenticated sender. The sender identity is provenance, not proof that the content is true.

## 5. Request integrity, replay, and retries

TLS protects an active connection, but the application protocol still needs explicit retry and replay semantics.

- Each mutation MUST support an expected revision or equivalent concurrency precondition.
- Retryable mutations SHOULD carry an idempotency key scoped to the authenticated peer and operation.
- Reusing a key with a different request body MUST fail with a conflict.
- Idempotency records MUST be retained for a documented period and committed atomically with the mutation.
- If requests are accepted asynchronously, the response MUST distinguish accepted, completed, and failed states.
- If application-level signatures are introduced for offline queues or store-and-forward relays, define canonical bytes, key identifiers, rotation, revocation, and signature domain separation before implementation. Do not sign ad hoc JSON serialization.

Timestamps and nonces MAY supplement replay defense for signed messages, but MUST NOT replace idempotency and concurrency controls.

## 6. Replication and data integrity

Replication is not trusted merely because transport authentication succeeds.

- Replication peers and permitted directions MUST be explicitly configured.
- Each replicated mutation MUST retain origin node, actor, operation, source revision, and provenance where available.
- Conflicts MUST be surfaced; last-write-wins MUST NOT be silently assumed.
- Snapshot import MUST validate format, references, integrity, and authorization before atomic commit.
- Snapshot integrity and sender authenticity are separate checks.
- No peer may overwrite or delete data outside its granted scope.
- Deletion propagation requires an explicit tombstone, retention, and resurrection policy before replication is enabled.

## 7. Resource limits and operational security

Every network adapter MUST define bounded request sizes, pagination, connection concurrency, timeouts, and limits on expensive operations. It SHOULD support rate limiting and backpressure. Errors MUST avoid leaking credentials, private resource contents, filesystem paths, SQL details, or stack traces.

Security-relevant events SHOULD be auditable: peer authentication success/failure, authorization denial, credential changes, policy changes, snapshot import/export, replication conflicts, and administrative actions. Logs must not contain bearer tokens, private keys, or sensitive payloads.

Credentials need documented provisioning, rotation, revocation, expiry, and recovery procedures. Loss or compromise of a peer credential must have a practical containment path.

## 8. Protocol negotiation

Before exchanging application data, peers MUST establish:
- protocol and contract version;
- stable node identity;
- supported authentication and transport profile;
- required and optional capabilities;
- authorization scope for the session or request.

Negotiation is not authorization. Unsupported required versions or capabilities MUST fail closed with a stable machine-readable error. Optional capabilities may be ignored only when their semantics are not required by the operation.

## 9. Rollout sequence

1. Approve the threat model, node identity profile, and trust-root model.
2. Specify versioned request/response envelopes, operation codes, error codes, canonical identifiers, and capability negotiation.
3. Implement authenticated peer identity and deny-by-default authorization before enabling replication.
4. Add conformance tests for invalid certificates, untrusted roots, revoked credentials, wrong peer identities, unauthorized operations, replayed idempotency keys, stale revisions, malformed/oversized requests, and interrupted transfers.
5. Add replication only after tombstones, conflict resolution, provenance, and snapshot integrity semantics are specified and tested.
6. Conduct an independent security review before recommending untrusted-network or multi-tenant deployment.

## 10. Current implementation boundary

The built-in HTTP adapter documented in [server-security.md](server-security.md) is a small single-node adapter. Its non-loopback mode currently requires TLS and a shared bearer token. It does not implement mTLS peer identity, per-node authorization scopes, credential revocation, protocol negotiation, replication, or multi-tenant isolation. It is not a conforming implementation of this proposed internal-networking profile and must not be described as secure node-to-node networking.

Until those capabilities exist, keep the adapter loopback-only or place it behind a separately secured, carefully configured trusted boundary. Do not expose it directly to an untrusted network.
