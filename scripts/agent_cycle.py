#!/usr/bin/env python3
"""Run bounded, evidence-producing AIDB contributor checks."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

CHECKS = (
    ("compile", (sys.executable, "-m", "compileall", "-q", "aidb", "tests")),
    ("ruff", (sys.executable, "-m", "ruff", "check", "aidb", "tests")),
    ("pytest", (sys.executable, "-m", "pytest", "-q")),
)
CONTEXT_FILES = (".aidb/session-context.yml", "docs/PROJECT_CONTEXT.md", "AGENTS.md", "docs/IMPLEMENTATION_ROADMAP.md")


def run_check(name: str, command: Sequence[str], root: Path, timeout: int) -> dict:
    """Run a fixed check and preserve its actual exit status and bounded output."""
    started = time.monotonic()
    try:
        result = subprocess.run(list(command), cwd=root, capture_output=True, text=True, timeout=timeout, check=False)
        return {"name": name, "command": list(command), "status": "passed" if result.returncode == 0 else "failed",
                "exit_code": result.returncode, "duration_seconds": round(time.monotonic() - started, 3),
                "stdout": result.stdout[-12000:], "stderr": result.stderr[-12000:]}
    except subprocess.TimeoutExpired as exc:
        def decode(value: str | bytes | None) -> str:
            if value is None:
                return ""
            return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value
        return {"name": name, "command": list(command), "status": "timed_out", "exit_code": None,
                "duration_seconds": round(time.monotonic() - started, 3),
                "stdout": decode(exc.stdout)[-12000:], "stderr": decode(exc.stderr)[-12000:], "timeout_seconds": timeout}
    except OSError as exc:
        return {"name": name, "command": list(command), "status": "could_not_run", "exit_code": None,
                "duration_seconds": round(time.monotonic() - started, 3), "stdout": "", "stderr": str(exc)}


def inspect(root: Path) -> dict:
    """Collect compact project state and indicate which handoff files exist."""
    git = subprocess.run(["git", "rev-parse", "--show-toplevel", "--abbrev-ref", "HEAD", "HEAD"],
                         cwd=root, capture_output=True, text=True, check=False)
    lines = git.stdout.splitlines()
    files = []
    for relative in CONTEXT_FILES:
        path = root / relative
        exists = path.is_file()
        files.append({"path": relative, "exists": exists, "bytes": path.stat().st_size if exists else 0})
    return {"repository_root": lines[0] if git.returncode == 0 and lines else str(root),
            "branch": lines[1] if git.returncode == 0 and len(lines) > 1 else None,
            "commit": lines[2] if git.returncode == 0 and len(lines) > 2 else None,
            "git_status": "available" if git.returncode == 0 else "unavailable", "context_files": files}


def verify(root: Path, timeout: int) -> dict:
    """Run the same compile, lint, and test commands used by CI."""
    results = [run_check(name, command, root, timeout) for name, command in CHECKS]
    return {"schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
            "repository": inspect(root), "checks": results,
            "overall_status": "passed" if all(item["status"] == "passed" for item in results) else "failed",
            "limitations": ["Checks do not prove behavioral completeness or security.",
                            "This tool does not edit files, retry failures, merge changes, or execute imported artifacts."]}


def render_handoff(report: dict) -> str:
    lines = ["# AIDB Agent Verification Handoff", "", "Result: **" + report["overall_status"].upper() + "**",
             "Created: " + report["created_at"],
             "Branch: " + str(report["repository"].get("branch") or "unknown"),
             "Commit: " + str(report["repository"].get("commit") or "unknown"), "", "## Check results", ""]
    for item in report["checks"]:
        lines.append("- **" + item["name"] + "**: " + item["status"] + " (exit=" + str(item["exit_code"]) +
                     ", " + str(item["duration_seconds"]) + "s)")
        detail = (item.get("stderr") or item.get("stdout") or "").strip()
        if detail:
            lines.extend(["", "  Output:"])
            lines.extend("  " + line for line in detail.splitlines()[-20:])
    lines.extend(["", "## Limitations", ""])
    lines.extend("- " + item for item in report["limitations"])
    lines.extend(["", "## Next action", ""])
    if any(item["status"] != "passed" for item in report["checks"]):
        lines.append("Inspect failure output, fix the cause in a bounded change, then rerun verification.")
    else:
        lines.append("Review the diff and acceptance criteria; passing checks alone do not approve or merge a change.")
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("inspect", "verify"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--timeout", type=int, default=600, help="timeout per check in seconds")
    parser.add_argument("--report", type=Path, help="optional path for JSON evidence")
    parser.add_argument("--handoff", type=Path, help="optional path for Markdown handoff")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if not root.is_dir():
        parser.error("repository root is not a directory: " + str(root))
    if args.timeout < 1:
        parser.error("--timeout must be positive")
    if args.command == "inspect":
        report = inspect(root)
        print(json.dumps(report, indent=2))
        return 0 if report["git_status"] == "available" else 1
    report = verify(root, args.timeout)
    rendered = json.dumps(report, indent=2)
    print(rendered)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")
    if args.handoff:
        args.handoff.parent.mkdir(parents=True, exist_ok=True)
        args.handoff.write_text(render_handoff(report), encoding="utf-8")
    return 0 if report["overall_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
