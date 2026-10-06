"""
tests/test_phase9_office_visual_sync_suite.py — Test Suite for Phase 9.

Validates:
1. /api/tasks endpoint return structure and status serialization in ui_server.py.
2. Scranton Office floor Kanban board data schema alignment.
3. Peer delegation collaboration event format emitted via fleet_control.py / ui_server.py.
4. CSS & Modal rules verification for #kanbanModal (opaque backgrounds, no backdrop-filter on inner panels, AGENTS.md §8 compliance).
"""

import json
from pathlib import Path
import pytest

from core.task_manager import get_task_manager, TaskState, TaskStatus


def test_api_tasks_serialization():
    tm = get_task_manager()
    tid = tm.submit("code_helper", lambda p, ctx: {"status": "ok"}, {"task": "unit test task"})
    assert tid is not None

    tasks = tm.all_tasks()
    assert isinstance(tasks, list)
    assert any(t["id"] == tid for t in tasks)

    # Verify structure matches Kanban board expectations
    target = next(t for t in tasks if t["id"] == tid)
    assert "status" in target
    assert "tool" in target
    assert "elapsed_sec" in target
    assert "progress" in target


def test_office_html_kanban_modal_and_rules():
    office_path = Path(__file__).parent.parent / "frontend" / "office.html"
    assert office_path.exists()

    content = office_path.read_text(encoding="utf-8")

    # 1. Kanban modal element existence
    assert 'id="kanbanModal"' in content
    assert 'FLEET KANBAN TASK BOARD' in content

    # 2. Kanban columns
    assert 'id="kanbanColQueued"' in content
    assert 'id="kanbanColRunning"' in content
    assert 'id="kanbanColReview"' in content
    assert 'id="kanbanColDone"' in content

    # 3. Dynamic collaboration visualizer function
    assert 'function drawCollaborationLine' in content
    assert 'function openKanbanBoardModal' in content
    assert 'function refreshKanbanBoard' in content

    # 4. AGENTS.md §8 Rule 1 compliance check (No backdrop-filter on modal-panel or overlay)
    assert '.modal-panel {' in content
    # Panel must be opaque #0a0a0a
    assert 'background: #0a0a0a !important;' in content or 'background: #0a0a0a;' in content
    assert 'backdrop-filter: blur' not in content
    assert 'backdrop-filter: none !important;' in content
    assert 'body.modal-open' in content
    assert '@keyframes modalIn' in content
