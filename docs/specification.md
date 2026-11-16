# AIDB Dynamic Specification

Status: draft contract 0.1.0; implemented subset in the Python/SQLite reference server

AIDB nodes describe themselves through a versioned, inspectable specification. The specification is runtime data, not a static assumption about the implementation.

## Purpose

A node specification answers, at minimum:

- who this node is
- what it currently supports
- which protocol and representation versions it understands
- which resources and operations it exposes
- which optional extensions are enabled
- how another system can discover or reach those capabilities
- what constraints apply
- where to obtain the authoritative current specification

The specification is descriptive and discoverable. It is not, by itself, authorization.

## Self-description

AIDB must expose its current specification through the same language-neutral interface used to inspect the node.

A conceptual resource is `/specification`.

The concrete transport is not normative. HTTP is one possible adapter; local IPC, embedded APIs, queues, or other transports may expose the same resource.

## Specification identity

Every published specification has:

- `id`: stable identifier for this published specification revision
- `version`: monotonically increasing integer revision for this node
- `contract`: object containing the stable contract `id` and semantic `version`
- `supersedes`: identifier of the immediately preceding specification revision, or `null` for the first revision
- `issued_at`: publication time
- `node`: stable node identity
- `capabilities`: capabilities implemented by the node, independent of a particular adapter
- `resources`: resource types implemented by the node
- `transports`: structured descriptions of adapters currently configured by the reference server
- `extensions`: optional extension identifiers
- `constraints`: operational or compatibility constraints

A consumer must be able to determine which specification is currently authoritative. The Python reference implementation uses contract identifier `org.aidb.node-specification` at semantic contract version `0.1.0`. The top-level `version` is a per-node revision counter, not a semantic version. Each new revision links to the prior revision through `supersedes`; the first revision has `supersedes: null`.

## Dynamic means versioned, not mutable history

The current specification may change. Previous specifications remain identifiable through node history or an exported record when the survivability contract requires it.

A consumer must never have to guess whether two specifications describe the same node or whether a capability appeared, disappeared, or changed.

## Capability negotiation

Capabilities are assertions about what the node currently exposes, not promises about every future deployment.

A consumer should:

1. discover the node
2. retrieve the current specification
3. select a compatible contract/version
4. inspect required resource and operation capabilities
5. negotiate optional extensions
6. perform operations
7. use the change stream to detect relevant subsequent changes

Unknown optional capabilities and extensions must be safely ignorable unless explicitly marked required. The current reference server advertises capabilities but does not yet implement a required/optional capability-negotiation endpoint. A client must therefore verify that every required capability appears in the returned specification before attempting an operation; absence is not consent or implicit support.

## Endpoint abstraction

An endpoint identifies a way to access a capability. It is not an IP address.

A transport descriptor identifies the adapter and the operations it actually serves. The current reference server emits descriptors shaped like `{id, protocol, capabilities, authentication}`. The top-level `capabilities` list describes node-level functionality; `transports[].capabilities` is the subset reachable through that adapter. The current HTTP adapter advertises health/specification reads, notes/resources/changes reads, and—only when a bearer token is configured—note creation, resource creation, and relationship creation. The HTTPS adapter uses the same operation set over TLS. Legacy string transport names remain accepted when importing older home records.

The specification must not require IPv4, IPv6, DNS, HTTP, or any particular network topology. A distributed deployment may advertise multiple independently authenticated endpoints and capabilities for chunk retrieval, publication, discovery, and replication. Endpoint discovery is not authorization; clients must authenticate the peer and bind it to the advertised node identity before trusting its claims.

## Identity, authorization, provenance, trust

These are separate concerns:

- **identity**: who claims to be the node or actor
- **specification**: what the node says it can do
- **authorization**: what this caller is permitted to do
- **provenance**: what happened and why
- **trust**: how a consumer evaluates the claims

A discovered capability must never be treated as permission.

## Relationship to change history

A specification change is itself a meaningful node change. The node should therefore be able to answer when a capability appeared, when it was removed, which specification introduced it, and what superseded it.

This connects dynamic discovery directly to survivability and provenance.

## Canonical representation

The current reference endpoint returns UTF-8 JSON under contract version 0.1.0. This draft does not freeze canonical bytes, signatures, or content-addressing. A stable cross-language profile must still define deterministic field semantics, explicit null/absence behavior, compatibility rules, extension rules, and integrity/signature representation where required. CBOR or other representations may be adapters over the same semantics.

## Distributed endpoint and trust requirements

A node specification may advertise endpoint transport, protocol version, address/reference, serialization, authentication mechanisms, capabilities served, priority, and validity. Remote endpoint metadata must describe supported authenticated transport and peer identity mechanisms without exposing credentials or implying that possession of an endpoint grants access.

Node identity must remain stable across IP address, hostname, and certificate changes. Agent identity is separate. Capabilities describe what a node offers; authorization is evaluated independently for every operation.


## Runtime implementation boundary

The reference server exposes the same specification payload at `/specification` and `/.well-known/agent-card.json`; these are aliases, not separate schemas or capability vocabularies. The current built-in adapter is HTTP/1.1, or HTTPS/1.1 when TLS is configured. A handler created without a bearer token advertises read operations only. Configuring a bearer token adds the write operations actually implemented by the handler; this remains authentication, not per-agent authorization.

The persisted specification history creates a new revision whenever capabilities, resource types, transports, extensions, or constraints change. A repeated read with unchanged fields does not create a revision. The `supersedes` link is derived from the immediately preceding retained history record.

Capability negotiation, peer identity binding, mutual TLS, certificate lifecycle management, remote discovery, replication, and non-HTTP adapters remain future work. Their presence in this architecture document is not a claim that the reference implementation ships them.

## Design rule

The specification describes the node. It must not become a second, competing architecture.

If database semantics change, the specification changes with them. If a transport changes, the specification advertises the new transport without changing the underlying data model.

The node remains the authority for its current operational description, while its history preserves how that description evolved.
