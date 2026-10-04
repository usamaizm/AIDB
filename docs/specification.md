# AIDB Dynamic Specification

Status: proposed architecture

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

- `id`: stable identifier for the specification resource
- `version`: semantic version of the specification document
- `issued_at`: publication time
- `node`: node identity
- `contract`: protocol/data-contract identity
- `capabilities`: current advertised capabilities
- `resources`: currently exposed resource types
- `transports`: currently available access transports
- `extensions`: optional negotiated extensions
- `constraints`: operational or compatibility constraints
- `supersedes`: prior specification identifier when applicable

A consumer must be able to determine which specification is currently authoritative.

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

Unknown capabilities and extensions must be safely ignorable unless explicitly marked required.

## Endpoint abstraction

An endpoint identifies a way to access a capability. It is not an IP address.

Endpoint metadata may contain transport, protocol, address/reference, serialization, authentication mechanisms, capabilities served, priority, and validity.

The specification must not require IPv4, IPv6, DNS, HTTP, or any particular network topology.

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

The architecture does not yet freeze a single serialization. A canonical representation must eventually define deterministic field semantics, stable identifiers, explicit null/absence behavior, version compatibility, extension rules, and integrity/signature representation where required.

JSON is a practical initial representation. CBOR or other representations may be adapters over the same semantics.

## Design rule

The specification describes the node. It must not become a second, competing architecture.

If database semantics change, the specification changes with them. If a transport changes, the specification advertises the new transport without changing the underlying data model.

The node remains the authority for its current operational description, while its history preserves how that description evolved.
