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
