# AIDB communication

Status: architectural draft.

Communication is one capability of a live AIDB database, not the definition of the database.

## Durable messages

AIDB may store messages as durable resources associated with actors and sessions.

Messages should be queryable as state and represented in the change history so that communication is recoverable rather than dependent on a continuously connected process.

## Live observation

Polling and subscriptions are two access patterns over the same ordered change semantics.

An agent should be able to reconnect and ask:

> Give me everything that changed after cursor X.

A continuously connected agent may instead subscribe to new changes.

The two paths must not produce incompatible semantics.

## Actors

The architecture distinguishes:

- node: a database deployment
- agent: an actor using the database
- human: an actor with potentially higher authority
- service: an external system

Identity and authorization remain open architectural work.

## Sessions

Sessions are useful for grouping interactions, but they must not become the only way to represent relationships or history.

A database resource may participate in multiple sessions and may exist independently of any session.

## Transport neutrality

The existing Python methods are implementation details.

Future HTTP, A2A, MCP, CLI, SDK, queue, and other adapters must map onto the same language-neutral database semantics.
