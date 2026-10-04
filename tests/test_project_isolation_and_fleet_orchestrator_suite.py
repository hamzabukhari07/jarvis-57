"""
tests/test_project_isolation_and_fleet_orchestrator_suite.py

Verifies:
1. Workspace Project Slug Extraction & Collision-Safe Directory Allocation (REQ-V1-001, REQ-V1-002)
2. Decoupled Sticky Repo in resolve() for Brand-New Projects (REQ-V1-001)
3. In-Place Fleet Worker Execution (Zero Ghost Task Cards in TaskManager) (REQ-V1-006)
4. Haider Fleet Agent Registration & Auto-Capability Routing (REQ-V1-004)
5. Agent Active Task Count & Concurrency Overflow Balancing (Max 3 Tasks) (REQ-V1-005)
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from core.repo_context import (
    extract_project_slug,
    get_unique_project_dir,
    resolve,
    remember_repo,
    get_last_repo,
)
from core.fleet_manager import FleetManager
from core.task_manager import TaskManager, TaskStatus
from actions.antigravity_agent import antigravity_action


def test_extract_project_slug():
    assert "portfolio" in extract_project_slug("Build a modern portfolio website for Hamza")
    assert "real-estate" in extract_project_slug("create a real estate landing page")
    assert "dental" in extract_project_slug("make a dental clinic site")
    assert extract_project_slug("") == "web-project"


def test_get_unique_project_dir_and_collision_increment():
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        dir1 = get_unique_project_dir("build dental clinic website", base_parent=base)
        assert dir1.name == "dental-clinic"
        assert dir1.exists()

        # Simulate files created in dir1
        (dir1 / "index.html").write_text("<html></html>", encoding="utf-8")

        # Second call with same topic must not overwrite; should generate collision-safe suffix
        dir2 = get_unique_project_dir("build dental clinic website", base_parent=base)
        assert dir2.name == "dental-clinic_1"
        assert dir2.exists()
        assert dir1 != dir2


def test_resolve_decouples_sticky_repo_for_new_project():
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        old_repo = base / "old_dental_project"
        old_repo.mkdir()
        remember_repo(str(old_repo))
        assert get_last_repo() == str(old_repo)

        # Standard resolve returns old_repo from memory
        p, src = resolve()
        assert p == old_repo
        assert src == "memory"

        # When is_new_project=True, resolve MUST allocate a fresh unique directory instead of returning old_repo
        fresh_p, fresh_src = resolve(is_new_project=True, task_hint="real estate landing page")
        assert fresh_p != old_repo
        assert fresh_src == "new_project"
        assert "real-estate" in fresh_p.name


def test_haider_registered_in_fleet():
    fm = FleetManager()
    assert "HAIDER" in fm.agents
    haider = fm.get_agent("HAIDER")
    assert haider is not None
    assert haider.name == "Haider"
    assert "Frontend" in haider.role
    assert haider.default_tool == "antigravity_run"
    assert haider.desk_x == 320
    assert haider.desk_y == 280


def test_fleet_auto_capability_routing_and_overflow_to_haider():
    fm = FleetManager()

    # Normal routing (0 active tasks)
    with patch.object(fm, "get_agent_active_task_count", return_value=0):
        agent_fe = fm.resolve_agent_by_mention_or_capability("Design responsive hero landing page")
        assert agent_fe is not None
        assert agent_fe.id == "ALI"

        agent_be = fm.resolve_agent_by_mention_or_capability("Build FastAPI backend API with Postgres models")
        assert agent_be is not None
        assert agent_be.id == "AHMAD"

    # Simulate Ali has >= 3 active tasks -> should auto-route to Haider
    with patch.object(fm, "get_agent_active_task_count", side_effect=lambda aid: 3 if aid == "ALI" else 0):
        overflow_agent = fm.resolve_agent_by_mention_or_capability("Design responsive hero landing page")
        assert overflow_agent is not None
        assert overflow_agent.id == "HAIDER"


def test_antigravity_run_in_place_eliminates_ghost_task():
    # Verify that passing run_in_place=True executes worker directly without calling tm.submit()
    with tempfile.TemporaryDirectory() as tmpdir:
        mock_ctx = MagicMock()
        mock_ctx.report = MagicMock()

        dummy_result = {"status": "success", "repo": tmpdir, "files": ["index.html"]}
        with patch("actions.antigravity_agent._run_worker", return_value=dummy_result) as mock_worker:
            with patch("actions.antigravity_agent.get_task_manager") as mock_get_tm:
                params = {
                    "task": "Build dental clinic site",
                    "project_path": tmpdir,
                    "run_in_place": True,
                    "task_ctx": mock_ctx,
                }
                res = antigravity_action(params)
                # Worker should be called directly
                mock_worker.assert_called_once()
                # tm.submit must NOT be called (zero ghost task cards)
                mock_get_tm.assert_not_called()
                assert "success" in res
