# AIDB

AIDB is a durable SQLite-backed foundation for AI systems. It is designed to hold the shared state needed for multi-agent coordination: identities, memory, knowledge, sessions, tasks, tool calls, and workflow events.

## What AIDB now supports

- agent registration with roles and permissions
- private memory and shared knowledge records
- named communication sessions with participants
- message history and unread tracking
- task assignment, priority, and dependency edges
- tool registry and tool-call auditing
- workflow event logs for orchestration traces

## Why this matters

AIDB is not just a document database. It is a persistence layer for AI operating memory. It lets agents coordinate, recover state, continue conversations, and leave an auditable trail of work.

## Quick start

```bash
python -m pip install -e .
```

```python
from aidb import AIDB

with AIDB("agents.sqlite3") as db:
    planner = db.register_agent(
        "Planner",
        role="manager",
        permissions=["create_task", "assign_task"],
        capabilities=["planning", "coordination"],
    )

    researcher = db.register_agent(
        "Researcher",
        role="worker",
        permissions=["read_task", "write_memory"],
    )

    session = db.create_session("benchmark-review", created_by=planner.id)
    db.join_session(session.session_id, researcher.id)

    db.send_message(planner.id, "Please inspect the benchmark dataset.", session.session_id)
    task = db.create_task(
        "Review benchmark",
        assigned_to=researcher.id,
        status="queued",
        priority=10,
    )

    db.add_event("task_assigned", "Task assigned to researcher", agent_id=planner.id, task_id=task.id, session_id=session.session_id)
    db.remember(researcher.id, "The user prefers concise explanations.", kind="preference")
    db.log_tool_call(researcher.id, "search_docs", {"query": "benchmark"}, {"count": 3}, session_id=session.session_id)
```

## Core model

- Agent: identity, role, permissions, capabilities
- Session: conversation stream between agents
- Message: ordered communication event in a session
- Memory: per-agent facts and preferences
- Knowledge: searchable shared content
- Task: unit of work with status, priority, and dependency links
- Tool: registered callable interface
- ToolCall: execution audit trail
- WorkflowEvent: orchestration and operational timeline

## Scope

AIDB is intentionally local-first and model-agnostic. It does not run models or invoke external APIs itself. Instead, it gives AI systems a durable place to store state and coordinate activity.

## Roadmap

- semantic search via embeddings
- role-based authorization and policies
- richer task dependency graphs
- message delivery acknowledgements and scheduling
- FastAPI or MCP adapters
- persistent agent runtime orchestration

Apache 2.0
