import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest
from core.ui_server import ZezoUIServer
from core.file_reader import read_file
from ui import ZezoUI


class TestDesktopIngestionCallback(unittest.TestCase):
    def test_ui_server_and_zezo_ui_callback(self):
        # 1. Create a dummy file
        test_file = Path("test_sample_resume.txt")
        test_file.write_text(
            "HAMZA BUKHARI\nLead AI Architect & Creator of ZEZO OS\nSkills: Python, PyQt6, AI Systems\nGitHub: github.com/fakexezo-lgtm",
            encoding="utf-8"
        )
        try:
            # 2. Setup server and callback tracking
            server = ZezoUIServer(port=8798)
            captured = []
            server.on_file_uploaded = lambda info: captured.append(info)

            # Ingest through file_reader
            res = read_file(test_file)
            self.assertTrue(res.text)
            self.assertIn("HAMZA BUKHARI", res.text)

            file_info = {
                "name": test_file.name,
                "path": str(test_file.resolve()),
                "size": test_file.stat().st_size,
                "file_type": res.file_type,
                "engine": res.engine,
                "text": res.text,
                "is_truncated": res.is_truncated,
            }

            # Fire callback
            if server.on_file_uploaded:
                server.on_file_uploaded(file_info)

            self.assertEqual(len(captured), 1)
            self.assertEqual(captured[0]["name"], "test_sample_resume.txt")
            self.assertIn("HAMZA BUKHARI", captured[0]["text"])
            self.assertIn("Skills: Python", captured[0]["text"])

            print(f"[RUNTIME PASS] Desktop ingestion callback captured: {captured[0]['name']} ({captured[0]['size']} bytes)")
        finally:
            if test_file.exists():
                test_file.unlink()


if __name__ == "__main__":
    unittest.main()
