"""
tests/test_zezo_coder_drawer_suite.py — Test Suite for ZEZO Coder Facade & Telemetry Drawer.
"""

import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QApplication

# Ensure QApplication exists for UI tests
app = QApplication.instance() or QApplication(sys.argv)

from ui import (
    TaskQueueWidget,
    TaskMatrixDrawer,
    _open_project_preview,
    _open_project_folder,
    _get_process_telemetry,
)


class TestZezoCoderDrawerSuite(unittest.TestCase):

    def setUp(self):
        self.sample_data = {
            "running": [
                {
                    "id": "abc12345",
                    "tool": "antigravity_agent",
                    "status": "running",
                    "progress": 45,
                    "elapsed_sec": 12.5,
                    "pid": 9999,
                    "message": "Writing index.html and stylesheets...",
                    "started_at": time.time() - 12.5,
                    "params": {
                        "task": "Build modern dark SaaS landing page",
                        "project_path": "D:/Desktop/website",
                        "model": "gemini-2.5-flash",
                    },
                }
            ],
            "queued": [
                {
                    "id": "def67890",
                    "tool": "opencode_agent",
                    "status": "queued",
                    "progress": 0,
                    "elapsed_sec": 0.0,
                    "message": "queued (position #1)",
                    "started_at": time.time(),
                    "params": {
                        "task": "Add contact form to website",
                        "project_path": "D:/Desktop/website",
                    },
                }
            ],
            "done": [
                {
                    "id": "ghi11223",
                    "tool": "kilo_agent",
                    "status": "done",
                    "progress": 100,
                    "elapsed_sec": 18.2,
                    "message": "completed",
                    "started_at": time.time() - 30.0,
                    "finished_at": time.time() - 11.8,
                    "params": {
                        "task": "Extract design tokens and update colors",
                        "project_path": "D:/Desktop/website",
                    },
                }
            ],
        }

    def test_1_task_queue_widget_renders_zezo_coder_cards(self):
        """Verify TaskQueueWidget renders cards with ZEZO Coder branding and metadata."""
        w = TaskQueueWidget()
        w.set_tasks(self.sample_data)

        # Check badge count
        self.assertEqual(w._cnt_badge.text(), "2")  # 1 running + 1 queued

        # Find all labels inside the container
        from PyQt6.QtWidgets import QLabel
        labels = [lbl.text() for lbl in w._container.findChildren(QLabel)]
        all_text = " ".join(labels)

        # Must contain ZEZO Coder branding
        self.assertIn("⚡ ZEZO Coder", all_text)
        self.assertIn("ZEZO Coder", all_text)

        # Must display task titles
        self.assertIn("Build modern dark SaaS landing page", all_text)
        self.assertIn("Add contact form to website", all_text)

        # Must display progress and ETA
        self.assertIn("45%", all_text)
        self.assertIn("ETA ~", all_text)

        # Must display queue position
        self.assertIn("Position #1", all_text)

    def test_2_task_matrix_drawer_renders_internal_telemetry(self):
        """Verify TaskMatrixDrawer renders internal details, recent log, and action buttons."""
        drawer = TaskMatrixDrawer()
        drawer.set_tasks(self.sample_data)

        from PyQt6.QtWidgets import QLabel, QPushButton
        self.assertEqual(drawer._stat_running.findChild(QLabel, "val_lbl").text(), "1")
        self.assertEqual(drawer._stat_queued.findChild(QLabel, "val_lbl").text(), "1")
        self.assertEqual(drawer._stat_done.findChild(QLabel, "val_lbl").text(), "1")
        labels = [lbl.text() for lbl in drawer._container.findChildren(QLabel)]
        all_text = " ".join(labels)

        # Internal details sections
        self.assertIn("── INTERNAL DETAILS ──", all_text)
        self.assertIn("Engine:", all_text)
        self.assertIn("Model:", all_text)
        self.assertIn("PID:", all_text)
        self.assertIn("Affinity:", all_text)
        self.assertIn("Children:", all_text)
        self.assertIn("Started:", all_text)
        self.assertIn("── RECENT LOG ──", all_text)

        # Action buttons
        buttons = [btn.text() for btn in drawer._container.findChildren(QPushButton)]
        self.assertTrue(any("PREVIEW" in b for b in buttons))
        self.assertTrue(any("OPEN FOLDER" in b for b in buttons))
        self.assertTrue(any("INSPECT" in b for b in buttons))
        self.assertTrue(any("CANCEL" in b for b in buttons))
        self.assertTrue(any("FULL LOG" in b for b in buttons))

    def test_3_telemetry_helper_structure(self):
        """Verify _get_process_telemetry returns required structure."""
        info = _get_process_telemetry(None)
        self.assertIn("affinity", info)
        self.assertIn("job_object", info)
        self.assertIn("children", info)

    def test_4_prompt_contains_zezo_coder_rules(self):
        """Verify core/prompt.txt contains ZEZO Coder persona and domain-aware routing."""
        prompt_path = Path("core/prompt.txt")
        self.assertTrue(prompt_path.exists())
        text = prompt_path.read_text(encoding="utf-8")

        self.assertIn("CODING DELEGATION — ZEZO CODER", text)
        self.assertIn("UNIFIED PERSONA DIRECTIVE", text)
        self.assertIn("ZEZO Coder", text)
        self.assertIn("DEFAULT: `antigravity_run`", text)
        self.assertIn("DEFAULT: `opencode_run`", text)

    def test_5_action_return_messages_use_zezo_coder(self):
        """Verify actions/*.py return clean ZEZO Coder strings."""
        from actions import antigravity_agent, opencode_agent, kilo_agent
        
        ag_src = Path("actions/antigravity_agent.py").read_text(encoding="utf-8")
        op_src = Path("actions/opencode_agent.py").read_text(encoding="utf-8")
        kl_src = Path("actions/kilo_agent.py").read_text(encoding="utf-8")

        self.assertIn("ZEZO Coder", ag_src)
        self.assertIn("ZEZO Coder", op_src)
        self.assertIn("ZEZO Coder", kl_src)


    def test_6_task_manager_renders_file_processor_and_social_intel(self):
        """Verify TaskMatrixDrawer and TaskQueueWidget render accurate dynamic tool cards for file_processor and social intel."""
        mixed_data = {
            "running": [
                {
                    "id": "fp001",
                    "tool": "file_processor",
                    "status": "running",
                    "progress": 50,
                    "elapsed_sec": 2.5,
                    "pid": 1234,
                    "message": "Extracting text from resume",
                    "started_at": time.time() - 2.5,
                    "params": {
                        "action": "extract_text",
                        "file_path": "D:/Documents/Hamza_Bukhari_Resume.pdf",
                    },
                }
            ],
            "queued": [
                {
                    "id": "sr002",
                    "tool": "agent_reach",
                    "status": "queued",
                    "progress": 0,
                    "elapsed_sec": 0.0,
                    "message": "queued",
                    "started_at": time.time(),
                    "params": {
                        "platform": "github",
                        "username": "hamzabukhari07",
                    },
                }
            ],
            "done": [
                {
                    "id": "ag003",
                    "tool": "antigravity_agent",
                    "status": "done",
                    "progress": 100,
                    "elapsed_sec": 14.0,
                    "message": "completed",
                    "started_at": time.time() - 20.0,
                    "params": {
                        "task": "Build modern dashboard",
                        "project_path": "D:/Desktop/project",
                    },
                }
            ],
        }

        # Test TaskMatrixDrawer
        drawer = TaskMatrixDrawer()
        drawer.set_tasks(mixed_data)

        from PyQt6.QtWidgets import QLabel
        drawer_labels = [lbl.text() for lbl in drawer._container.findChildren(QLabel)]
        drawer_text = " ".join(drawer_labels)

        self.assertIn("📄 File Processor", drawer_text)
        self.assertIn("🌐 Social Intelligence", drawer_text)
        self.assertIn("⚡ ZEZO Coder", drawer_text)
        self.assertIn("Extract_text: Hamza_Bukhari_Resume.pdf", drawer_text)
        self.assertIn("GITHUB: hamzabukhari07", drawer_text)
        self.assertIn("Universal File Processor (OCR / Summarize / Parse)", drawer_text)
        self.assertIn("Agent-Reach Social Engine", drawer_text)

        # Test TaskQueueWidget
        queue = TaskQueueWidget()
        queue.set_tasks(mixed_data)
        queue_labels = [lbl.text() for lbl in queue._container.findChildren(QLabel)]
        queue_text = " ".join(queue_labels)

        self.assertIn("📄 File Processor", queue_text)
        self.assertIn("🌐 Social Intelligence", queue_text)
        self.assertIn("ZEZO Coder", queue_text)


if __name__ == "__main__":
    unittest.main()

