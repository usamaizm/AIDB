# Agent Collaboration

AIDB is intended to be approachable by independent AI agents, not only by its maintainers.

## Discovery

Agents can inspect `/.well-known/agent-card.json` when a deployment exposes the file through its transport, or inspect `llms.txt` and the repository documentation when discovering AIDB through source control.

The card is deliberately small: it advertises that the node is an AIDB home, its current broad capabilities, and the durable collaboration request concept without forcing a transport or model framework.

## Collaboration requests

A collaboration request is durable state. A request should identify the requesting agent, the requested capability or task, relevant context, provenance, and an expiration or lifecycle policy. Responses should be persisted as well.

Recommended lifecycle: `requested` → `accepted` / `declined` → `active` → `completed` / `cancelled`.

Agents should not assume that discovery implies authorization. A discovered node may still require authentication, authorization, or explicit acceptance before receiving data or writes.

## Agent-to-agent principle

AIDB should make it possible for agents to discover one another, leave durable context, request work, and resume collaboration later without requiring a human to relay every message.

This is a protocol-level goal. Transport adapters may expose the same semantics over HTTP, MCP, A2A, CLI, or other mechanisms as they mature.
