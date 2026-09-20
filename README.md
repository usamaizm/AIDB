# AIDB

AIDB is a durable, local-first SQLite-backed foundation for AI systems. It gives agents a place to store operational memory, session state, shared knowledge, tasks, and workflow events without requiring a separate database service or a deployed runtime.

AIDB is intentionally model-agnostic and repository-native. It does not run models or call external AI services by itself. Instead, it provides a durable coordination layer for AI workflows, agent memory, and reviewable project knowledge.

## What AIDB is

AIDB is both:

- a lightweight state layer for AI agents and multi-agent systems
- a protocol and knowledge model for repository-native AI coordination

The project is designed to support:
- agent registration and identity
- session-based communication
- message history and read tracking
- private memory and shared knowledge
- task creation, priority, and dependency handling
- tool call logging and workflow auditing
- local semantic retrieval using token-based similarity
- orchestrated task execution via a simple workflow engine

## Why AIDB

A lot of AI systems fail not because the model is weak, but because the system has no durable memory, no task coordination layer, and no clear review boundary.

AIDB solves that by giving AI systems:
- a persistent local store
- a stable task model
- shared knowledge records
- session history
- workflow event traceability
- a clear separation between proposal, acceptance, and implementation

## Core features

- agent registration with roles, permissions, and capabilities
- durable session-based communication
- message inbox, unread tracking, and transcript retrieval
- per-agent memory and shared knowledge storage
- document ingestion and local retrieval
- keyword and lightweight semantic search
- task scheduling with dependencies and priority
- workflow event logging
- tool call audit trails
- a simple orchestration layer via `WorkflowEngine`

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

## Core model

AIDB is structured around these core concepts:

- Agent: identity, role, permissions, capabilities
- Session: durable conversation or workflow stream
- Message: ordered communication event in a session
- Memory: per-agent facts, preferences, and private recall state
- KnowledgeRecord: shared searchable content
- Task: unit of work with status, dependency, and priority
- Tool: registered callable or capability
- ToolCall: execution trace for tool use
- WorkflowEvent: orchestration and operational history
- WorkflowEngine: task lifecycle coordination

## Knowledge storage and retrieval

AIDB can store project or domain knowledge and search it locally.

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

AIDB supports:
- keyword-based lookup via `search()`
- lightweight semantic comparison via `semantic_search()`
- durable storage for documents and knowledge records
- local-first indexing without external services

## Messaging and sessions

AIDB supports durable agent-to-agent or human-to-agent communication by session.

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

## Task orchestration

AIDB supports simple coordination for work assignments and workflow readiness.

```python
from aidb import AIDB, WorkflowEngine

with AIDB("workflow.sqlite3") as db:
    worker = db.register_agent("Worker", permissions=["read_task", "write_memory"])
    task = db.create_task("Draft summary", assigned_to=worker.id, priority=5)

    engine = WorkflowEngine(db)
    ready = engine.next_ready_tasks(worker.id)
    print(ready)

    engine.run_task(task.id, worker.id)
    engine.complete_task(task.id, worker.id, result={"status": "done"})
```

## Repository-native AI request and review model

AIDB is also designed for repository-native AI coordination on GitHub.

The repository acts as:

- a request intake surface
- a review queue
- a durable knowledge base
- a source-of-truth for accepted decisions

The governing principle is:

- proposals are not authority
- reviewed documentation and merged code are authority
- implementation requires review and approval
- AI agents do not get unchecked repo mutation rights

This means:

- GitHub Issues can be used as AI request intake
- Discussions can host broader design proposals
- Pull Requests represent implementation proposals
- Docs and code become the trusted knowledge layer
- human review remains the approval boundary

## Source-of-truth order

When there is ambiguity, AIDB should resolve it in this order:

1. README
2. protocol and design docs
3. accepted decision log
4. reviewed code and tests
5. merged pull requests
6. accepted discussions
7. external proposals
8. unreviewed AI output

In short: proposals are provisional; accepted knowledge is authoritative.

## Permission model

The default policy is intentionally strict.

- external AIs may submit requests
- external AIs may not directly edit code
- external AIs may not merge pull requests
- external AIs may not modify workflows or repo settings
- external AIs may not access secrets
- implementation requires explicit human approval

This is necessary to keep the project safe while still enabling AI participation in a reviewable way.

## Repository structure

- `aidb/`: core package
- `docs/`: protocol, evaluation, knowledge, and governance documents
- `examples/`: runnable examples
- `tests/`: verification for package behavior
- `.aidb/`: machine-readable protocol and knowledge definitions
- `.github/`: issue templates and workflow automation
- `LICENSE`: Apache 2.0 license

## AI request protocol

The project includes a structured AI request flow:

- request issues are created using a standard template
- triage automation labels and acknowledges them
- maintainer review determines acceptance, rejection, or clarification
- accepted requests become actionable tasks
- implementation happens via reviewed PRs only

This gives other AI systems a stable pathway to participate without bypassing the repo’s trust boundaries.

## Shared knowledge base

AIDB is also a knowledge base for participating AIs. The repo is treated as durable memory for:

- project goals
- architecture and protocol
- accepted decisions
- examples and patterns
- limitations and constraints
- operational rules

Unreviewed external AI output is not treated as project truth. It is only a proposal until reviewed and accepted.

## Example lifecycle

```text
AI submits request
  -> request is structured and labeled
  -> evaluator reviews it
  -> accepted / rejected / needs clarification
  -> accepted request becomes a task
  -> implementation is proposed
  -> reviewed PR is merged
  -> accepted docs and code become the knowledge base
```

## Installation

From a local clone:

```bash
git clone https://github.com/usamaizm/AIDB.git
cd AIDB
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Optional dev dependencies:

```bash
pip install -e .[dev]
```

## License

This project is licensed under the Apache License 2.0. See the `LICENSE` file for details.

## Project status

AIDB is a lightweight foundation for local-first AI state management, agent coordination, and repository-native AI knowledge. It is designed for experiments, prototypes, embedded agent systems, and review-first AI collaboration in GitHub-based workflows.

The project aims to keep things simple:
- local by default
- review-first by design
- portable across AI systems
- safe by policy
- durable by repository and SQLite
