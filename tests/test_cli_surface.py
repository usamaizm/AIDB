"""Conformance smoke tests for the advertised surface.

The node specification and the CLI must only advertise what the store
actually implements: every CLI subcommand must dispatch to store methods
that exist, and every advertised capability / resource type must map to
at least one public store method. Sessions, messages, and tasks were
removed from both surfaces because the store has schema for them but no
API (route (b): remove the dead surface now; reimplement as resources
later if the capability is wanted).
"""

import ast
import subprocess
import sys
from pathlib import Path

from aidb import AIDB

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI_SOURCE = (REPO_ROOT / "aidb" / "__main__.py").read_text(encoding="utf-8")

# Methods the store never implemented; the CLI must never call them again.
PHANTOM_METHODS = {"create_session", "send_message", "create_task"}

# Advertised capability -> public store methods that back the claim.
CAPABILITY_METHODS = {
    "resources": ["create_resource", "get_resource", "list_resources"],
    "notes": ["create_note", "get_note", "list_notes"],
    "artifacts": ["register_artifact", "get_artifact", "list_artifacts"],
    "knowledge": ["create_knowledge", "remember_knowledge"],
    "changes": ["list_changes", "public_changes"],
    "export": ["export_home"],
    "restore": ["restore_snapshot", "import_home"],
    "public_private": ["publish_resource"],
    "ownership": ["update_resource"],
}

# Advertised resource type -> public store methods that back the claim.
RESOURCE_TYPE_METHODS = {
    "resource": ["create_resource"],
    "note": ["create_note"],
    "artifact": ["register_artifact"],
    "knowledge": ["create_knowledge"],
    "memory": ["remember", "trace_memory_to_source"],
}


def _public_store_method(name):
    method = getattr(AIDB, name, None)
    return method is not None and not name.startswith("_") and callable(method)


def test_cli_dispatches_only_to_existing_store_methods():
    tree = ast.parse(CLI_SOURCE)
    called = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "db"
    }
    assert called, "expected the CLI to call at least one store method"
    assert not (called & PHANTOM_METHODS)
    for name in sorted(called):
        assert _public_store_method(name), f"CLI calls missing store method: {name}"


def test_cli_registers_exactly_the_dispatched_subcommands():
    tree = ast.parse(CLI_SOURCE)
    registered = {
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "add_parser"
        and node.args
        and isinstance(node.args[0], ast.Constant)
    }
    dispatched = {
        comparator.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Compare)
        and isinstance(node.left, ast.Attribute)
        and node.left.attr == "command"
        and isinstance(node.left.value, ast.Name)
        and node.left.value.id == "args"
        for comparator in node.comparators
        if isinstance(comparator, ast.Constant)
    }
    assert registered == dispatched
    assert not ({"session", "message", "task"} & registered)


def test_cli_source_has_no_phantom_method_references():
    for name in sorted(PHANTOM_METHODS):
        assert name not in CLI_SOURCE


def test_advertised_capabilities_are_backed_by_store_methods():
    db = AIDB(":memory:")
    payload = db.specification_dict()
    assert payload["capabilities"], "expected a non-empty capability list"
    for capability in payload["capabilities"]:
        assert capability in CAPABILITY_METHODS, (
            f"advertised capability has no recorded backing: {capability}"
        )
        for method in CAPABILITY_METHODS[capability]:
            assert _public_store_method(method), (
                f"capability {capability!r} names missing store method: {method}"
            )


def test_advertised_resource_types_are_backed_by_store_methods():
    db = AIDB(":memory:")
    payload = db.specification_dict()
    assert payload["resources"], "expected a non-empty resource type list"
    for resource_type in payload["resources"]:
        assert resource_type in RESOURCE_TYPE_METHODS, (
            f"advertised resource type has no recorded backing: {resource_type}"
        )
        for method in RESOURCE_TYPE_METHODS[resource_type]:
            assert _public_store_method(method), (
                f"resource type {resource_type!r} names missing store method: {method}"
            )


def test_cli_help_exits_zero():
    result = subprocess.run(
        [sys.executable, "-m", "aidb", "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "usage" in result.stdout.lower()
