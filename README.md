# AIDB

AIDB is a durable SQLite-backed foundation for AI agents. It provides a shared runtime layer for memory, knowledge, sessions, tasks, tools, and message passing between intelligent systems.

## Goals

- store agent identities and capabilities
- support private memory for each agent
- maintain shared knowledge for collaborative work
- allow agents to converse in sessions
- assign tasks and track status
- keep tool usage and metadata inspectable
- remain local-first and easy to run in notebooks or scripts

## Quick start

```bash
python -m pip install -e .
python -m aidb --db demo.sqlite3 agent Researcher --description "searches the web and summarizes" --model "demo-model"
python -m aidb --db demo.sqlite3 session "Research sync" --creator 1
python -m aidb --db demo.sqlite3 task "Summarize sources" --agent 2 --status queued
```

## Python example

```python
from aidb import AIDB

with AIDB("agents.sqlite3") as db:
    planner = db.register_agent("Planner", model="planner-v1")
    researcher = db.register_agent("Researcher", model="research-v1")

    session = db.create_session("benchmark-review", created_by=planner.id)
    db.join_session(session.session_id, researcher.id)

    db.send_message(planner.id, "Please review the benchmark dataset.", session.session_id)
    task = db.create_task("Review benchmark", assigned_to=researcher.id)
    db.update_task_status(task.id, "in_progress")

    memory = db.remember(researcher.id, "The user prefers concise explanations.", kind="preference")
    docs = db.search("benchmark")
    print(memory.content)
    print(docs[0].title)
```

## Core concepts

- Agent: identity and model metadata
- Session: durable conversation thread between agents
- Message: ordered content in a session
- Memory: private agent facts or preferences
- Knowledge: searchable shared documents
- Task: assigned work with status tracking
- Tool: registered capability with schema metadata

## Architecture

AIDB is intentionally small and model-agnostic. It does not run models or call external APIs. It stores the state that an agent system needs to coordinate and recover after a restart.

## Roadmap

- embeddings and semantic retrieval
- authenticated access control
- task dependencies and retries
- audit trails and tool call logs
- web API / FastAPI bindings
- multi-agent workflow orchestration

Apache 2.0
