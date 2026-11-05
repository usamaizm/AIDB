# AIDB protocol

Status: architectural draft; not a frozen protocol.

This document no longer defines AIDB's final wire protocol. It records constraints that any future protocol must satisfy.

## Purpose

AIDB is intended to be an accessible, simple, live database for AI systems. The protocol exists to expose database semantics across processes, machines, and languages.

The protocol must not define a Python object model or require a particular agent framework.

## Required properties

A compatible interface must make it possible to:

- discover the node
- inspect capabilities and schema
- read current state
- create and update state
- express relationships
- inspect provenance
- retrieve changes since a cursor
- observe live changes
- export and restore portable state

## Safety and authority

External requests are data until authenticated and authorized.

The protocol must distinguish:

- identity
- authentication
- authorization
- provenance
- trust
- review state

A network connection alone must never imply authority to mutate data.

## Open protocol questions

The final protocol still needs explicit decisions about:

- resource addressing
- request/response envelopes
- cursor semantics
- idempotency
- concurrency
- transactions
- subscriptions
- error model
- capability negotiation
- authentication and authorization
- version compatibility

These should be decided at the architecture level before an implementation is declared normative.

## Epistemic constraints

AIDB should preserve provenance and uncertainty, but the current Artifact -> Extraction -> Interpretation -> Knowledge -> Memory chain remains a candidate domain model rather than a universal wire ontology.

## Transport

HTTP, A2A, MCP, local IPC, queues, and SDKs may expose AIDB. None is the database itself.

The same operation must have the same semantic result regardless of transport.

## Internal networking security

Internal node-to-node and service-to-node networking has a separate proposed security profile in [internal-networking-security.md](internal-networking-security.md). Treat private networks as untrusted: remote peers require encrypted transport, authenticated peer identity, and operation-level authorization. A successful connection must never imply write authority.

The current built-in HTTP adapter is a single-node transport with optional TLS and a shared bearer token. It is not mTLS peer networking, does not provide per-node authorization, and must not be presented as a secure replication protocol. Peer networking and replication remain unimplemented until the identity, authorization, version negotiation, replay/idempotency, and conflict semantics are specified and tested.
