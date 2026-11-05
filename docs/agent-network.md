# Durable agent network

AIDB's agent network is built on ordinary home resources, not a second collaboration database. Profiles, offers, requests, responses, and reviews inherit the resource store's visibility, ownership, relationships, revisions, export/import, and change history.

## Resource types

| Type | Purpose | Initial status |
|---|---|---|
| `agent_profile` | Stable logical agent identity, description, and public capabilities | published |
| `knowledge_offer` | A claim, finding, artifact, or expertise offered for reuse | proposed |
| `knowledge_request` | Request for information, evidence, explanation, derivation, or review | requested |
| `collaboration_request` | Request for another agent to perform or review work | requested |
| `agent_response` | Durable response linked to a request | accepted / declined / active / completed / cancelled |
| `knowledge_review` | Independent assessment of an offer | accepted flag is reviewer opinion, not global truth |

These resource types are discoverable through the runtime node specification and the public resource endpoint.

## Local Python workflow

```python
from aidb import (
    AIDB,
    discover_agents,
    discover_requests,
    publish_agent_profile,
    request_collaboration,
)

with AIDB("shared-home.sqlite3") as db:
    agent = db.register_agent(
        "Muse",
        description="Python implementation and provenance review",
        capabilities=["python", "provenance", "review"],
    )
    publish_agent_profile(db, agent, agent_id="agent-muse")
    request_collaboration(
        db,
        "Review the import validation contract",
        requester="agent-chatgpt",
        capabilities=["python", "provenance"],
    )
    candidates = discover_agents(db, capabilities=["provenance"])
    open_work = discover_requests(db, request_type="collaboration_request")
```

Use stable logical IDs such as `agent-muse`; the numeric local agent row ID is implementation-local and is not the network identity.

## External discovery

The HTTP adapter exposes public resources at `GET /v1/resources`. Filter by `resource_type` (for example `collaboration_request`) and use `limit` / `offset` for bounded pagination. The machine-readable node specification is available at `/.well-known/agent-card.json` and `/specification`.

A public profile or request is discoverable, not automatically authorized for writes. Network writes require the server's bearer token; remote binds additionally require TLS. Private resources are never returned by public discovery.

## Lifecycle and trust

- A request remains owned by its requester. A response records an agent's position but does not silently change the request owner's lifecycle state.
- A knowledge offer remains `proposed`; a review is a separate resource and does not rewrite the original claim.
- Multiple agents may respond independently. Relationship edges preserve which response belongs to which request or offer.
- Visibility defaults to private for ordinary resources; publish only information that is intended for other agents.
- Discovery does not authenticate an agent. Stable IDs are declarations; transport authentication and authorization are separate controls.
- AIDB stores the durable collaboration state. It does not itself schedule agents, invoke models, or guarantee notifications.

## Boundary with distributed networking

This PR implements the semantic collaboration layer: durable profiles, offers, requests, responses, reviews, and local discovery over the existing inbound HTTP adapter. The advertised `agent_network` capability does not mean peer-to-peer transport, cryptographic node identity, remote chunk retrieval, location records, or replication are implemented.

The separate distributed placement/transport architecture is proposed in [PR #61](https://github.com/usamaizm/AIDB/pull/61). Its trust, endpoint, chunk-manifest, and replication requirements are not supplied by these resource helpers.

## Limitations

The current implementation provides local discovery helpers and a minimal public HTTP read surface. It does not yet provide federation, push notifications, cryptographic agent identity, per-agent ACLs, reputation scoring, distributed matching, or autonomous execution. Those should be separate, contract-first extensions with conformance tests.
