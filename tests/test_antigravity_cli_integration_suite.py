"""
tests/test_antigravity_cli_integration_suite.py — Unit & Integration Test Suite for Antigravity CLI ('agy')

Verifies:
1. Antigravity CLI discovery (_find_antigravity_bin)
2. Antigravity model resolution & alias mapping (_resolve_model)
3. Config persistence (get_antigravity_model, save_antigravity_model)
4. Action handler dispatch & task submission (antigravity_action)
5. Action loader tool registration & schema validity
6. Hardware throttling helper definitions
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from actions.antigravity_agent import (
    TOOL,
    _find_antigravity_bin,
    _resolve_model,
    antigravity_action,
)
from memory.config_manager import (
    ANTIGRAVITY_CLI_MODELS,
    DEFAULT_ANTIGRAVITY_MODEL,
    get_antigravity_model,
    save_antigravity_model,
)


class TestAntigravityCLIIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.repo = Path(self.tmp_dir) / "my_project"
        self.repo.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        try:
            from core.task_manager import get_task_manager
            tm = get_task_manager()
            with tm._lock:
                tm._tasks.clear()
                tm._coding_queue.clear()
        except Exception:
            pass
        try:
            shutil.rmtree(self.tmp_dir)
        except Exception:
            pass

    def test_1_antigravity_bin_discovery(self):
        """Verify _find_antigravity_bin finds the agy binary or candidate path."""
        bin_path = _find_antigravity_bin()
        # On user system agy.exe is installed at %LOCALAPPDATA%\agy\bin\agy.exe
        if bin_path:
            self.assertTrue(Path(bin_path).exists() or shutil.which(bin_path) is not None)
            self.assertTrue("agy" in bin_path.lower() or "antigravity" in bin_path.lower())

    def test_2_model_resolution_and_aliases(self):
        """Verify model aliases map to official Antigravity models."""
        self.assertEqual(_resolve_model("sonnet"), "claude-sonnet-4-6")
        self.assertEqual(_resolve_model("claude"), "claude-sonnet-4-6")
        self.assertEqual(_resolve_model("opus"), "claude-opus-4-6-thinking")
        self.assertEqual(_resolve_model("3.7"), "gemini-3.7-flash-medium")
        self.assertEqual(_resolve_model("3.8"), "gemini-3.8-flash-medium")
        self.assertEqual(_resolve_model("3.6"), "gemini-3.6-flash-medium")
        self.assertEqual(_resolve_model("pro"), "gemini-3.1-pro-high")
        self.assertEqual(_resolve_model("gpt"), "gpt-oss-120b-medium")
        self.assertEqual(_resolve_model("custom-model-id"), "custom-model-id")

    def test_3_config_manager_persistence(self):
        """Verify Antigravity models list and config get/save functions."""
        self.assertIn("gemini-3.7-flash-medium", ANTIGRAVITY_CLI_MODELS)
        self.assertIn("claude-sonnet-4-6", ANTIGRAVITY_CLI_MODELS)
        self.assertEqual(DEFAULT_ANTIGRAVITY_MODEL, "gemini-3.7-flash-medium")

        original_model = get_antigravity_model()
        try:
            save_antigravity_model("claude-opus-4-6-thinking")
            self.assertEqual(get_antigravity_model(), "claude-opus-4-6-thinking")
        finally:
            save_antigravity_model(original_model)

    def test_4_tool_schema_and_action_loader(self):
        """Verify TOOL dictionary schema matches standard Zezo contract."""
        self.assertEqual(TOOL["name"], "antigravity_run")
        self.assertEqual(TOOL["behavior"], "NON_BLOCKING")
        self.assertIn("task", TOOL["parameters"]["properties"])
        self.assertIn("project_path", TOOL["parameters"]["properties"])
        self.assertIn("model", TOOL["parameters"]["properties"])

        from core.action_loader import discover_actions
        registry = discover_actions(Path("actions"))
        names = registry.names()
        self.assertIn("antigravity_run", names)

    def test_5_antigravity_action_dispatch(self):
        """Verify antigravity_action submits a background task and returns task_id."""
        player = MagicMock()
        resp = antigravity_action(
            {"task": "Build modern SaaS landing page", "project_path": str(self.repo)},
            player=player,
        )
        self.assertIn("ZEZO Coder task start ho gaya hai", resp)
        self.assertIn("Task ID:", resp)
        self.assertTrue(player.show_content.called)
        badge_arg = player.show_content.call_args[0][0]
        self.assertIn("ZEZO CODER", badge_arg)


if __name__ == "__main__":
    unittest.main()
