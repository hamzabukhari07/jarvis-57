"""
Tests for Non-Blocking Daemon Commands in quick_snippet
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import actions.quick_snippet as quick_snippet


class TestDaemonAndScaffoldFixes(unittest.TestCase):

    @patch("subprocess.Popen")
    def test_uvicorn_command_starts_non_blocking_daemon(self, mock_popen):
        mock_proc = MagicMock()
        mock_proc.pid = 9999
        mock_proc.poll.return_value = None  # Process is running
        mock_popen.return_value = mock_proc

        result = quick_snippet._execute_command("uvicorn main:app --reload --port 8000")
        self.assertIn("running in background", result)
        self.assertIn("9999", result)
        mock_popen.assert_called_once()


if __name__ == "__main__":
    unittest.main()
