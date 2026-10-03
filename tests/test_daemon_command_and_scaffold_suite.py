"""
Tests for Non-Blocking Daemon Commands in code_helper and Package Scaffolding in dev_agent
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import actions.code_helper as code_helper
import actions.dev_agent as dev_agent


class TestDaemonAndScaffoldFixes(unittest.TestCase):

    @patch("subprocess.Popen")
    def test_uvicorn_command_starts_non_blocking_daemon(self, mock_popen):
        mock_proc = MagicMock()
        mock_proc.pid = 9999
        mock_proc.poll.return_value = None  # Process is running
        mock_popen.return_value = mock_proc

        result = code_helper._execute_command("uvicorn main:app --reload --port 8000")
        self.assertIn("running in background", result)
        self.assertIn("9999", result)
        mock_popen.assert_called_once()

    def test_dev_agent_auto_creates_init_py_in_subfolders(self):
        import tempfile
        import shutil

        temp_dir = Path(tempfile.mkdtemp())
        try:
            # Simulate writing app/auth.py and tests/client.py
            with patch.object(dev_agent, "_get_model") as mock_model:
                mock_inst = MagicMock()
                mock_inst.generate_content.return_value = MagicMock(text="def foo(): pass")
                mock_model.return_value = mock_inst

                dev_agent._write_file(
                    {"path": "app/auth.py", "description": "Auth module", "imports": []},
                    "test",
                    [],
                    "python",
                    temp_dir,
                    {}
                )
                dev_agent._write_file(
                    {"path": "tests/client.py", "description": "Client test", "imports": []},
                    "test",
                    [],
                    "python",
                    temp_dir,
                    {}
                )

                # Check __init__.py creation
                self.assertTrue((temp_dir / "app" / "__init__.py").exists(), "app/__init__.py must be created")
                self.assertTrue((temp_dir / "tests" / "__init__.py").exists(), "tests/__init__.py must be created")
                self.assertTrue((temp_dir / "app" / "auth.py").exists())
                self.assertTrue((temp_dir / "tests" / "client.py").exists())

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
