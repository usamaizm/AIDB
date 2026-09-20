# AIDB

AIDB is an open, model-agnostic database for AIs. It provides a shared persistence layer for AI agents, their memories, tools, knowledge, and conversation messages.

## What belongs in an AI database?

- **Agents** — names, models, capabilities, and configuration metadata
- **Memories** — agent-specific facts, preferences, observations, and goals
- **Knowledge** — shared documents and searchable reference material
- **Tools** — tool names, descriptions, JSON schemas, and endpoints
- **Messages** — conversation history associated with an agent or session

AIDB does not execute models or tools and does not require a particular vendor. Any AI application can use it as a local SQLite database.

## Quick start

```bash
python -m pip install -e .
python -m aidb --db demo.sqlite3 agent Archivist --model my-model
python -m aidb --db demo.sqlite3 search memory
```

```python
from aidb import AIDB

with AIDB("agent.sqlite3") as db:
    agent = db.register_agent(
        "Researcher", model="my-model", capabilities=["search", "summarize"]
    )
    db.remember(agent.id, "The user prefers concise answers", kind="preference")
    db.add_document("AIDB", "A shared memory and knowledge store for AI agents", ["ai", "database"])
    memories = db.recall(agent.id, "user preferences")
    knowledge = db.search("AI database")
```

## Design principles

1. **Open access:** use it with any AI framework or model.
2. **Inspectable:** SQLite keeps data portable and easy to back up.
3. **Agent-aware:** private memories are scoped to an agent while knowledge can be shared.
4. **Extensible:** JSON metadata allows applications to add fields without migrations.
5. **Local-first:** no account, cloud service, or API key is required.

## Roadmap

- REST and MCP-compatible adapters
- vector/embedding indexes as optional extensions
- access control and encrypted private memories
- full-text search and retention policies
- import/export formats for common agent frameworks

Apache 2.0
