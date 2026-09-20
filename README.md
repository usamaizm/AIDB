# AIDB

AIDB is a durable SQLite-backed foundation for AI systems. It stores the operating memory and coordination state needed for multi-agent workflows in a local-first, model-agnostic way.

## What AIDB supports

- agent registration with roles, permissions, and capabilities
- session creation and participant membership
- message history, reads, and unread inbox tracking
- private memory and shared knowledge records
- task assignment, priorities, and dependency-aware workflow readiness
- tool registry and tool-call audit logging
- workflow event history for orchestration traces
- lightweight semantic retrieval using token-based similarity
- orchestration via WorkflowEngine

## Quick start

```python
from aidb import AIDB, WorkflowEngine

with AIDB("agents.sqlite3") as db:
    planner = db.register_agent(
        "Planner",
        role="manager",
        permissions=["read_task", "create_task", "assign_task"],
        capabilities=["planning", "coordination"],
    )

    researcher = db.register_agent(
        "Researcher",
        role="worker",
        permissions=["read_task", "write_memory"],
    )

    session = db.create_session("benchmark-review", created_by=planner.id)
    db.join_session(session.session_id, researcher.id)

    task = db.create_task(
        "Review benchmark",
        assigned_to=researcher.id,
        status="queued",
        priority=10,
    )

    db.send_message(planner.id, "Please inspect the benchmark dataset.", session.session_id)
    db.add_event("task_assigned", "Task assigned to researcher", agent_id=planner.id, task_id=task.id, session_id=session.session_id)
    db.remember(researcher.id, "The user prefers concise explanations.", kind="preference")
    db.log_tool_call(researcher.id, "search_docs", {"query": "benchmark"}, {"count": 3}, session_id=session.session_id)

    engine = WorkflowEngine(db)
    ready = engine.next_ready_tasks(researcher.id)
    print(ready)
```

## Core model

- Agent: identity, role, permissions, capabilities
- Session: durable conversation stream between agents
- Message: ordered communication event in a session
- Memory: per-agent facts and preferences
- Knowledge: shared searchable content
- Task: unit of work with status, priority, and dependency links
- Tool: registered callable interface
- ToolCall: execution trace for tools
- WorkflowEvent: orchestration and operational timeline
- WorkflowEngine: task scheduling and lifecycle coordination

## Semantic retrieval

AIDB includes a lightweight similarity search built on token frequency vectors. It is local, fast, and dependency-free, making it suitable for prototype agent systems and local experimentation.

## Scope

AIDB is intentionally local-first and model-agnostic. It does not run models or invoke external APIs itself. Instead, it gives AI systems a durable place to store state, coordinate work, and recover after a restart.

## Roadmap

- embeddings and vector memory stores
- authorization boundaries for sensitive operations
- richer dependency graphs and scheduling policies
- API adapters for MCP, REST, or websockets
- persistent orchestration dashboards

Apache 2.0
