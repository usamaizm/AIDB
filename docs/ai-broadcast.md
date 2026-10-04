# AI broadcast protocol

AIDB's durable message stream can be used as a transport-neutral AI-to-AI broadcast primitive. Broadcast messages are persisted in the same session transcript as ordinary messages and are marked with `role: "broadcast"` and `metadata.audience: "*"`.

## Envelope

The recommended machine-readable metadata is:

```json
{
  "protocol": "aidb.ai-broadcast/v1",
  "type": "capability_announcement",
  "audience": "*",
  "correlation_id": "optional-id"
}
```

The message body remains application-defined. AIDB does not treat a broadcast as trusted knowledge: receiving an announcement or claim does **not** promote it into the epistemic knowledge chain.

## Python

```python
message = db.broadcast_message(
    agent_id=agent.id,
    content='I can analyze PDF artifacts.',
    session_id='agent-network',
    metadata={
        'protocol': 'aidb.ai-broadcast/v1',
        'type': 'capability_announcement',
    },
)

inbox = db.receive(other_agent.id, 'agent-network', after_id=cursor)
```

This is intentionally local and durable. Network delivery remains the responsibility of an adapter (for example HTTP, MCP, queue, or WebSocket), while AIDB provides the persistent protocol record and provenance boundary.
