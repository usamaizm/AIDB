"""The public package surface must not advertise a broken WorkflowEngine.

Until this change, ``aidb`` exported ``WorkflowEngine`` (in ``__all__``)
whose three methods delegated to store methods that do not exist
(``ready_tasks``, ``require_permission``, ``update_task_status``), so every
method raised ``AttributeError`` on first use. The store has no task or
session API and no permission model for the engine to delegate to, so the
engine module and its export are removed rather than repaired by inventing
a subsystem. These tests pin the honest surface: they fail on any tree
that still ships the broken engine.
"""

import importlib

import pytest

import aidb
from aidb import AIDB


def test_workflow_engine_is_not_exported():
    assert "WorkflowEngine" not in aidb.__all__
    assert not hasattr(aidb, "WorkflowEngine")


def test_workflow_engine_import_fails():
    with pytest.raises(ImportError):
        from aidb import WorkflowEngine  # noqa: F401


def test_engine_module_is_gone():
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("aidb.engine")


def test_remaining_exports_are_real():
    for name in aidb.__all__:
        assert hasattr(aidb, name), f"__all__ advertises missing name: {name}"


def test_package_still_works_without_engine(tmp_path):
    db = AIDB(tmp_path / "home.sqlite3")
    agent = db.register_agent("surface-check")
    assert agent.id is not None
    event = db.add_event("surface_check", "package works without the engine", agent_id=agent.id)
    assert event.id is not None
    assert [e.id for e in db.list_events()] == [event.id]
    db.close()
