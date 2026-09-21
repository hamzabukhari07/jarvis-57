"""
tests/test_ui_and_task_suite.py

Automated test suite verifying:
1. Multi-file upload, selection, removal, clearing, and MainWindow handlers in PyQt6.
2. ANSI code stripping in TaskManager and Task Inspector.
3. TaskState.params propagation and task completion watcher compatibility.
4. Task cancellation via task_status(action='cancel') and process termination.
"""

import sys
import unittest
import time
from pathlib import Path
from unittest.mock import MagicMock

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPainter, QImage

# Ensure QApplication singleton exists for UI tests
_app = QApplication.instance() or QApplication(sys.argv)

from core.task_manager import TaskManager, TaskState, TaskStatus, strip_ansi, get_task_manager
from actions.task_status import task_status
import ui


class TestFileUploadAndUI(unittest.TestCase):
    def setUp(self):
        self.win = ui.MainWindow("face.png")

    def test_file_drop_zone_multi_file_handling(self):
        dz = self.win._drop_zone
        test_files = [str(Path("main.py").resolve()), str(Path("ui.py").resolve()), str(Path("decisions.md").resolve())]
        
        # Test setting files
        dz._set_files(test_files)
        self.assertEqual(len(dz.current_files()), 3)
        self.assertEqual(dz.current_file(), test_files[0])

        # Test single file removal
        dz.remove_file(test_files[1])
        self.assertEqual(len(dz.current_files()), 2)
        self.assertNotIn(test_files[1], dz.current_files())

        # Test clear all
        dz.clear_all()
        self.assertEqual(len(dz.current_files()), 0)
        self.assertIsNone(dz.current_file())

    def test_uploaded_files_bar_actions(self):
        bar = self.win._file_bar
        dz = self.win._drop_zone
        test_files = [str(Path("main.py").resolve()), str(Path("ui.py").resolve())]
        
        dz._set_files(test_files)
        bar.set_files(test_files)
        self.assertEqual(len(bar._item_widgets), 2)

        # Test individual remove callback
        bar._on_remove(test_files[0])
        self.assertEqual(len(dz.current_files()), 1)
        self.assertEqual(dz.current_files()[0], test_files[1])

        # Test select all
        bar._on_select_all()
        self.assertTrue(len(bar._item_widgets) > 0)

        # Test send all signal
        sent_mock = MagicMock()
        bar.files_sent.connect(sent_mock)
        bar._on_send_all()
        sent_mock.assert_called_once_with(dz.current_files())

    def test_main_window_on_file_selected_no_attribute_error(self):
        test_files = [str(Path("main.py").resolve()), str(Path("ui.py").resolve())]
        # Should execute cleanly without AttributeError: 'str' object has no attribute 'name'
        self.win._on_file_selected(test_files)
        self.assertEqual(self.win.current_file, test_files[0])
        self.assertEqual(len(self.win._file_bar._item_widgets), 2)

    def test_drop_canvas_paint_no_crash(self):
        dz = self.win._drop_zone
        test_files = [str(Path("main.py").resolve()), str(Path("ui.py").resolve())]
        dz._set_files(test_files)
        img = QImage(300, 100, QImage.Format.Format_ARGB32)
        p = QPainter(img)
        # Verify paintEvent executes without coordinate or rendering errors
        dz._canvas._paint_files(p, 300, 100)
        p.end()


class TestTaskManagerAndCancellation(unittest.TestCase):
    def test_strip_ansi_sequences(self):
        raw = "\x1b[0m • \x1b[0mExplore landing page structure \x1b[90m Explore Agent \x1b[0m"
        clean = strip_ansi(raw)
        self.assertNotIn("\x1b", clean)
        self.assertIn("Explore landing page structure", clean)
        self.assertIn("Explore Agent", clean)

    def test_task_state_params_propagation(self):
        tm = TaskManager()
        params = {"task": "Build hero section", "repo": "Desktop/my_project", "model": "antigravity"}
        tid = tm.submit("dev_agent", lambda p, ctx: {"status": "success"}, params)
        state = tm.status(tid)
        self.assertIsNotNone(state)
        self.assertEqual(state["params"]["task"], "Build hero section")
        self.assertEqual(state["params"]["repo"], "Desktop/my_project")

    def test_task_cancellation_action(self):
        tm = get_task_manager()
        def slow_job(p, ctx):
            for _ in range(30):
                if ctx.cancelled():
                    return {"status": "cancelled"}
                time.sleep(0.05)
            return {"status": "success"}

        tid = tm.submit("dev_agent", slow_job, {"task": "slow test"})
        res = task_status({"action": "cancel", "task_id": tid})
        self.assertIn("cancelled", res.lower())
        st = tm.status(tid)
        self.assertEqual(st["status"], TaskStatus.CANCELLED.value)


if __name__ == "__main__":
    unittest.main()
