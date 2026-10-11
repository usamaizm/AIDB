from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

from scripts.agent_cycle import inspect, render_handoff, run_check, verify


def test_inspect_reports_context_files(tmp_path: Path) -> None:
    (tmp_path / ".aidb").mkdir()
    (tmp_path / ".aidb" / "session-context.yml").write_text("project: aidb\n", encoding="utf-8")
    with patch("scripts.agent_cycle.subprocess.run") as mocked:
        mocked.return_value = subprocess.CompletedProcess(args=["git"], returncode=0,
            stdout=f"{tmp_path}\nmain\nabc123\n", stderr="")
        result = inspect(tmp_path)
    assert result["branch"] == "main"
    assert result["commit"] == "abc123"
    assert result["context_files"][0]["exists"] is True
    assert result["context_files"][1]["exists"] is False


def test_run_check_records_failure_output(tmp_path: Path) -> None:
    completed = subprocess.CompletedProcess(args=["fake"], returncode=2, stdout="out", stderr="failure detail")
    with patch("scripts.agent_cycle.subprocess.run", return_value=completed):
        result = run_check("test", ["fake"], tmp_path, 5)
    assert result["status"] == "failed"
    assert result["exit_code"] == 2
    assert result["stderr"] == "failure detail"


def test_verify_handoff_points_to_repair(tmp_path: Path) -> None:
    with (patch("scripts.agent_cycle.inspect", return_value={"branch": "work", "commit": "abc"}),
          patch("scripts.agent_cycle.run_check", side_effect=[
              {"name": "compile", "status": "passed", "exit_code": 0, "duration_seconds": 0},
              {"name": "ruff", "status": "failed", "exit_code": 1, "duration_seconds": 0, "stderr": "lint issue"},
              {"name": "pytest", "status": "passed", "exit_code": 0, "duration_seconds": 0}])):
        report = verify(tmp_path, 10)
    assert report["overall_status"] == "failed"
    assert "lint issue" in render_handoff(report)
    assert "fix the cause" in render_handoff(report)
