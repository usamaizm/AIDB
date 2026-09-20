from __future__ import annotations

from typing import Any

from .store import AIDB


class WorkflowEngine:
    """Light orchestration layer for tasks, sessions, and agent execution flows."""

    def __init__(self, db: AIDB):
        self.db = db

    def next_ready_tasks(self, agent_id: int | None = None) -> list[Any]:
        return self.db.ready_tasks(agent_id)

    def run_task(self, task_id: int, agent_id: int, session_id: str | None = None) -> Any:
        if not self.db.require_permission(agent_id, "read_task"):
            raise PermissionError(f"agent {agent_id} cannot operate on tasks")

        task = self.db.update_task_status(task_id, "in_progress")
        self.db.add_event("task_started", "task started", agent_id=agent_id, task_id=task_id, session_id=session_id)
        return task

    def complete_task(self, task_id: int, agent_id: int, session_id: str | None = None, result: Any | None = None) -> Any:
        if not self.db.require_permission(agent_id, "write_memory"):
            raise PermissionError(f"agent {agent_id} cannot complete tasks")

        task = self.db.update_task_status(task_id, "completed")
        self.db.add_event("task_completed", "task completed", agent_id=agent_id, task_id=task_id, session_id=session_id, metadata={"result": result})
        return task
