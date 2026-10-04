"""
tests/test_fleet_live_sync_and_antigravity_assurance_suite.py — Live UI Fleet State Sync & Antigravity Fallback Assurance.

Lead Architect: Hamza Bukhari
Project: ZEZO (Autonomous Desktop AI Operating System v2)
"""

import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from core.fleet_manager import FleetManager
from core.task_manager import TaskContext, TaskManager, TaskStatus


def test_fleet_manager_event_broadcast_and_status_lifecycle():
    """Verify that dispatching a task updates agent state to working and broadcast events fire."""
    fm = FleetManager()
    ali = fm.get_agent("ALI")
    assert ali is not None
    initial_completed = ali.completed_tasks

    broadcast_mock = MagicMock()
    with patch.object(fm, "_broadcast_event", side_effect=broadcast_mock):
        with patch("core.task_manager.TaskManager.submit") as mock_submit:
            # Fake task submission
            mock_submit.return_value = "task_abc123"
            res = fm.dispatch_task("ALI", "Build modern fitness gym single page application")
            assert res["success"] is True
            assert res["task_id"] == "task_abc123"
            assert ali.status == "working"
            assert ali.current_task_id == "task_abc123"
            assert any("TASK STARTED" in log for log in ali.recent_logs)

            # Check broadcast calls
            event_names = [call.args[0] for call in broadcast_mock.call_args_list]
            assert "agent_task_started" in event_names
            assert "fleet_updated" in event_names

            # Complete task
            comp_res = fm.complete_task("ALI", "task_abc123")
            assert comp_res["success"] is True
            assert ali.status == "idle"
            assert ali.current_task_id is None
            assert ali.completed_tasks == initial_completed + 1
            assert any("COMPLETED" in log for log in ali.recent_logs)


def test_fleet_worker_fn_progress_and_completion_lifecycle():
    """Test that _worker_fn execution updates progress, logs, and triggers complete_task."""
    fm = FleetManager()
    ali = fm.get_agent("ALI")
    assert ali is not None

    with tempfile.TemporaryDirectory() as tmpdir:
        tm = TaskManager()

        # Mock action runner to report progress and succeed
        def mock_run(tool_name, params):
            ctx = params.get("task_ctx")
            if ctx:
                ctx.report(45, "Synthesizing Hero Section CSS")
                ctx.report(85, "Adding Glassmorphism animations")
            return "SUCCESS"

        with patch("core.task_manager.get_task_manager", return_value=tm):
            with patch("core.action_loader.discover_actions") as mock_discover:
                mock_reg = MagicMock()
                mock_reg.run = mock_run
                mock_discover.return_value = mock_reg

                res = fm.dispatch_task("ALI", "Build luxury villa showcase", path=tmpdir)
                task_id = res["task_id"]
                assert ali.status == "working"

                # Wait for task thread to finish
                for _ in range(50):
                    time.sleep(0.05)
                    st = tm.status(task_id)
                    if st and st.get("status") in ("done", "completed"):
                        break

                assert ali.status == "idle"
                assert ali.task_progress in (0, 100)
                # Verify intermediate progress was recorded in recent_logs
                assert any("45%" in log or "85%" in log for log in ali.recent_logs)


def test_antigravity_fallback_when_cli_produces_no_deliverables():
    """Verify that if CLI exits without creating index.html or code files, Antigravity falls back to REST."""
    from actions.antigravity_agent import _run_worker

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Simulate CLI creating only .gitignore or DESIGN_BLUEPRINT.html
        (repo_path / ".gitignore").write_text("node_modules/\n")
        (repo_path / "DESIGN_BLUEPRINT.html").write_text("<h1>Spec</h1>")

        mock_proc = MagicMock()
        mock_proc.pid = 1234
        mock_proc.poll.side_effect = [None, 0]
        mock_proc.wait.return_value = 0
        mock_proc.stdout.readline.side_effect = [b"", b""]

        mock_ctx = MagicMock()
        mock_ctx.cancelled.return_value = False
        mock_ctx.report = MagicMock()
        mock_ctx.on_complete = MagicMock()

        # REST pipeline mock that produces the real index.html
        fake_plan = {
            "project_name": "fitness-landing",
            "files": [{"path": "index.html", "purpose": "Main landing page"}],
            "summary": "Built fitness landing page",
            "entry_point": "index.html"
        }

        def fake_write_file(f_info, task, files, repo, written, design_context=None):
            (repo / "index.html").write_text("<!DOCTYPE html><html><body><h1>FitLife Gym</h1></body></html>")
            return "<!DOCTYPE html>..."

        with patch("actions.antigravity_agent._find_antigravity_bin", return_value="C:\\fake\\agy.exe"):
            with patch("subprocess.Popen", return_value=mock_proc):
                with patch("actions.antigravity_agent.plan_antigravity_project", return_value=fake_plan):
                    with patch("actions.antigravity_agent.write_antigravity_file", side_effect=fake_write_file):
                        with patch("webbrowser.open"):
                            res = _run_worker({"task": "Build Fitness Gym website", "repo": str(repo_path)}, mock_ctx)

                            assert res["status"] == "success"
                            assert (repo_path / "index.html").exists()
                            # Blueprint should be cleaned up
                            assert not (repo_path / "DESIGN_BLUEPRINT.html").exists()
                            assert "index.html" in res["files"]
