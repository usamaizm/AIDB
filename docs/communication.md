# AI-to-AI communication

Agents communicate through named sessions. A session is a durable message stream stored in SQLite, so an agent can disconnect and continue later.

```python
from aidb import AIDB

with AIDB("agents.sqlite3") as db:
    researcher = db.register_agent("Researcher", model="model-a")
    writer = db.register_agent("Writer", model="model-b")

    db.send_message(researcher.id, "I found three relevant sources.", "research-1")
    db.send_message(writer.id, "Please summarize them.", "research-1")

    # Writer reads messages from other agents in this session.
    inbox = db.receive(writer.id, session_id="research-1")
    for message in inbox:
        print(message.role, message.content)

    # Any participant can inspect the ordered transcript.
    transcript = db.conversation("research-1")
```

The communication layer provides:

- named conversation sessions
- durable ordered messages
- sender identity through `agent_id`
- `receive()` polling with `after_id` for incremental processing
- broadcast messages
- message metadata for correlation IDs, task state, or routing

AIDB is transport-neutral: your agents can call this API directly, or an HTTP, MCP, queue, or websocket adapter can be placed on top later. AIDB stores messages; it does not run models or deliver network notifications itself.
