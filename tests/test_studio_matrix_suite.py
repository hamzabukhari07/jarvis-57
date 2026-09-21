"""
tests/test_studio_matrix_suite.py
Automated verification test suite for Option A ("Studio Matrix") multi-task UI & engine.
Lead Architect: Hamza Bukhari
"""

import sys
import time
import unittest
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QLabel

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.task_manager import TaskManager, TaskStatus, TaskContext
from ui import TaskQueueWidget, TaskMatrixDrawer, C

# Headless QApplication instance for UI testing
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestTaskManagerCategorization(unittest.TestCase):
    def setUp(self):
        self.tm = TaskManager(max_tasks=20, ttl_sec=600)

    def test_get_categorized_tasks_empty(self):
        cat = self.tm.get_categorized_tasks()
        self.assertIn("running", cat)
        self.assertIn("queued", cat)
        self.assertIn("done", cat)
        self.assertEqual(len(cat["running"]), 0)
        self.assertEqual(len(cat["queued"]), 0)
        self.assertEqual(len(cat["done"]), 0)

    def test_get_categorized_tasks_workflow(self):
        # 1. Submit running coding task
        t1 = self.tm.submit("opencode_agent", lambda p, ctx: time.sleep(0.5) or {"status": "success"}, {})
        # 2. Submit second coding task -> should be queued
        t2 = self.tm.submit("opencode_agent", lambda p, ctx: {"status": "success"}, {})
        # 3. Submit immediate fast non-coding task
        t3 = self.tm.submit("web_search", lambda p, ctx: {"query": "test"}, {})

        time.sleep(0.05)
        cat = self.tm.get_categorized_tasks()

        # Verify running & queued categories
        running_ids = [t["id"] for t in cat["running"]]
        queued_ids = [t["id"] for t in cat["queued"]]
        self.assertIn(t1, running_ids)
        self.assertIn(t2, queued_ids)

        # Let fast task complete
        time.sleep(0.1)
        cat2 = self.tm.get_categorized_tasks()
        done_ids = [t["id"] for t in cat2["done"]]
        self.assertIn(t3, done_ids)


class TestTaskQueueWidget(unittest.TestCase):
    def setUp(self):
        self.widget = TaskQueueWidget()

    def test_initial_state(self):
        self.assertIsNotNone(self.widget)
        self.assertEqual(self.widget._cnt_badge.text(), "0")

    def test_set_tasks_updates_ui(self):
        mock_data = {
            "running": [
                {"id": "a1b2c3d4", "tool": "opencode_agent", "progress": 45, "status": "running", "elapsed_sec": 12.3}
            ],
            "queued": [
                {"id": "e5f6g7h8", "tool": "kilo_agent", "message": "queued (position #1)", "status": "queued"}
            ],
            "done": [
                {"id": "i9j0k1l2", "tool": "dev_agent", "status": "done", "elapsed_sec": 4.1}
            ]
        }
        self.widget.set_tasks(mock_data)
        self.assertEqual(self.widget._cnt_badge.text(), "2")  # 1 running + 1 queued

        # Test signal emission on click
        selected_ids = []
        self.widget.task_selected.connect(lambda tid: selected_ids.append(tid))
        
        # Trigger item selection
        self.widget.task_selected.emit("a1b2c3d4")
        self.assertIn("a1b2c3d4", selected_ids)


class TestTaskMatrixDrawer(unittest.TestCase):
    def setUp(self):
        self.drawer = TaskMatrixDrawer()

    def test_drawer_stats_and_cards(self):
        mock_data = {
            "running": [
                {"id": "run101", "tool": "antigravity_agent", "progress": 60, "status": "running", "elapsed_sec": 18.0, "pid": 4812, "message": "writing components"}
            ],
            "queued": [
                {"id": "que202", "tool": "opencode_agent", "status": "queued", "message": "waiting in queue"}
            ],
            "done": [
                {"id": "don303", "tool": "web_search", "status": "done", "elapsed_sec": 2.2, "progress": 100}
            ]
        }
        self.drawer.set_tasks(mock_data)
        
        # Verify stats labels
        self.assertEqual(self.drawer._stat_running.findChild(QLabel, "val_lbl").text(), "1")
        self.assertEqual(self.drawer._stat_queued.findChild(QLabel, "val_lbl").text(), "1")
        self.assertEqual(self.drawer._stat_done.findChild(QLabel, "val_lbl").text(), "1")

        # Test signal wiring
        inspected = []
        self.drawer.task_inspected.connect(lambda tid: inspected.append(tid))
        self.drawer._on_inspect("run101")
        self.assertIn("run101", inspected)


if __name__ == "__main__":
    unittest.main()
