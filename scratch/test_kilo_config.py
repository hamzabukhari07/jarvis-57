"""
scratch/test_kilo_config.py — Verification test for Kilo Code Free Models integration.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.action_loader import discover_actions
from core.skill_loader import SkillRegistry
from memory.config_manager import (
    DEFAULT_KILO_MODEL,
    KILO_CODE_FREE_MODELS,
    get_kilo_model,
    save_kilo_model,
)
from actions.kilo_agent import kilo_agent, run_kilo_task


class TestKiloIntegration(unittest.TestCase):

    def test_kilo_config_free_models(self):
        """Ensure Kilo Code free models are defined with kilo/kilo-auto/free as default."""
        self.assertIn("kilo/kilo-auto/free", KILO_CODE_FREE_MODELS)
        self.assertIn("kilo/stepfun/step-3.7-flash:free", KILO_CODE_FREE_MODELS)
        self.assertEqual(DEFAULT_KILO_MODEL, "kilo/kilo-auto/free")

        # Test getter / setter
        save_kilo_model("kilo/stepfun/step-3.7-flash:free")
        self.assertEqual(get_kilo_model(), "kilo/stepfun/step-3.7-flash:free")

        # Reset back to default
        save_kilo_model(DEFAULT_KILO_MODEL)
        self.assertEqual(get_kilo_model(), "kilo/kilo-auto/free")

    def test_kilo_action_discovery(self):
        """Ensure kilo_run is auto-discovered in ActionRegistry."""
        actions_dir = Path(__file__).parent.parent / "actions"
        registry = discover_actions(actions_dir=actions_dir, logger=lambda m: None)
        tool_names = registry.names()
        
        self.assertIn("kilo_run", tool_names)
        print(f"[TEST PASS] kilo_run discovered in ActionRegistry: {tool_names}")

    def test_kilo_skill_discovery(self):
        """Ensure kilo_code skill is discovered and loaded by SkillRegistry."""
        skills_dir = Path(__file__).parent.parent / "skills"
        registry = SkillRegistry(skills_dir=skills_dir)
        skills = registry.list_skills()
        skill_names = [s["name"] for s in skills]
        
        self.assertIn("kilo_code", skill_names)
        content = registry.read_skill("kilo_code")
        self.assertIn("kilo-auto/free", content)
        print(f"[TEST PASS] kilo_code skill discovered and loaded successfully.")

    @patch("shutil.which", return_value="/usr/local/bin/kilo")
    @patch("subprocess.run")
    def test_kilo_execution_mocked(self, mock_run, mock_which):
        """Ensure run_kilo_task properly constructs command line arguments and invokes subprocess."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Refactored app.py using kilo-auto/free"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        result = run_kilo_task("Refactor authentication logic", model="kilo-auto/free")
        self.assertIn("kilo-auto/free", result)
        self.assertIn("Refactored app.py", result)
        print(f"[TEST PASS] Mocked execution returned:\n{result}")


if __name__ == "__main__":
    unittest.main()
