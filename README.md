# AIDB

AIDB (Artificial Intelligence Data Base) is a lightweight, local-first SQLite-backed memory and coordination layer for AI agents and workflows. It gives applications a durable place to store agent state, session history, shared knowledge, task work, and execution traces without requiring a separate database service or model runtime.

AIDB is intentionally model-agnostic: it stores state and supports retrieval, but it does not call external AI services or manage LLM execution itself.

## Why AIDB?

- Local-first and portable: data lives in SQLite files you control.
- Durable agent state: agents, sessions, messages, memory, and workflow events persist across runs.
- Searchable knowledge: add documents and search by keyword or semantic similarity.
- Task orchestration: create tasks, assign owners, and resolve dependency-aware readiness.
- Tool and workflow auditing: track tool usage and orchestration events for debugging and observability.
- Minimal dependencies: built for Python 3.10+ using the standard library and SQLite.

## Features

- Agent registration with roles, permissions, capabilities, and metadata
- Session-based communication with durable message history
- Message inbox and read tracking for AI-to-AI or human-to-AI workflows
- Per-agent memory and shared knowledge records
- Keyword search and lightweight cosine-similarity semantic search
- Task management with priorities, dependencies, and status updates
- Workflow events and task execution tracking
- Tool call logging for auditing and introspection
- Workflow orchestration via `WorkflowEngine`

## Installation

From the repository root:

```bash
git clone https://github.com/usamaizm/AIDB.git
cd AIDB
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

For development/test dependencies:

```bash
pip install -e .[dev]
```

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

    db.send_message(
        planner.id,
        "Please inspect the benchmark dataset.",
        session.session_id,
    )

    db.add_event(
        "task_assigned",
        "Task assigned to researcher",
        agent_id=planner.id,
        task_id=task.id,
        session_id=session.session_id,
    )

    db.remember(
        researcher.id,
        "The user prefers concise explanations.",
        kind="preference",
    )

    db.log_tool_call(
        researcher.id,
        "search_docs",
        {"query": "benchmark"},
        {"count": 3},
        session_id=session.session_id,
    )

    engine = WorkflowEngine(db)
    ready = engine.next_ready_tasks(researcher.id)
    print(ready)
```

## Core concepts

AIDB is organized around a few core entities:

- Agent: a participant with a name, role, permissions, and capabilities
- Session: a durable conversation or workflow stream
- Message: an ordered communication event tied to a session
- Memory: private fact or preference storage for one agent
- KnowledgeRecord: shared searchable document-like content
- Task: a unit of work with status, priority, and dependency tracking
- Tool: a registered callable or external capability
- ToolCall: execution trace for tool use
- WorkflowEvent: operational or orchestration events
- WorkflowEngine: scheduling and task lifecycle coordination

## Knowledge storage and retrieval

AIDB can store structured knowledge and search it locally:

```python
from aidb import AIDB

with AIDB("knowledge.sqlite3") as db:
    db.add_document(
        "Model selection",
        "Use the smallest model that meets the quality requirement.",
        tags=["modeling", "decision"],
    )

    hits = db.search("smallest model quality")
    print(hits[0].title)

    semantic_hits = db.semantic_search("workflow optimization", threshold=0.1)
    print(semantic_hits)
```

`search()` performs simple term-based matching, while `semantic_search()` computes a lightweight token-frequency cosine similarity score for more flexible relevance matching.

## Messaging and sessions

AIDB supports durable communication between agents:

```python
from aidb import AIDB

with AIDB("agents.sqlite3") as db:
    researcher = db.register_agent("Researcher")
    writer = db.register_agent("Writer")

    db.send_message(researcher.id, "I found three sources.", "research-1")
    db.send_message(writer.id, "Please summarize them.", "research-1")

    inbox = db.receive(writer.id, session_id="research-1")
    print(inbox)

    transcript = db.conversation("research-1")
    print(transcript)
```

You can inspect unread messages, mark messages as read, and maintain separate conversation threads per session.

## Task orchestration

AIDB can help model workflow coordination:

```python
from aidb import AIDB, WorkflowEngine

with AIDB("workflow.sqlite3") as db:
    agent = db.register_agent("Worker", permissions=["read_task", "write_memory"])
    task = db.create_task("Draft summary", assigned_to=agent.id, priority=5)

    engine = WorkflowEngine(db)
    ready = engine.next_ready_tasks(agent.id)
    print(ready)

    engine.run_task(task.id, agent.id)
    engine.complete_task(task.id, agent.id, result={"status": "done"})
```

The engine provides a simple coordination layer over tasks, permissions, and workflow events.

## Repository layout

- `aidb/`: core Python package
- `docs/`: design and usage notes
- `examples/`: runnable sample scripts
- `tests/`: project tests
- `pyproject.toml`: package metadata and optional dev dependency config

## Examples and docs

- `examples/demo.py` demonstrates document ingestion and search
- `docs/communication.md` describes session-based communication patterns
- `tests/` contains basic verification for the public package API

## License

This project is licensed under the Apache License 2.0. See the [`LICENSE`](LICENSE) file for details.

## Project status

AIDB is a lightweight foundation for local agent memory and workflow state. It is designed for experimentation, prototypes, embedded agent systems, and local orchestration layers.

