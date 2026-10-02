"""
tests/test_website_cloner_suite.py — Automated Regression Suite for Website Cloner.

Covers:
1. TOOL Schema & Action Discovery
2. URL Normalization & Domain Extraction
3. TaskManager submit_after Chaining
4. Repo Context get_unique_clone_dir & register_clone
5. Undo register_clone_snapshot Execution
6. Ephemeral Local HTTP Preview Server
7. Fault-Tolerant Asset Downloader & Partial Success Guard
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from actions.website_cloner import (
    TOOL,
    _extract_domain,
    _normalize_url,
    _sanitize_filename,
    localize_and_download_assets,
    start_local_preview_server,
)
from core.action_loader import discover_actions
from core.repo_context import get_unique_clone_dir, register_clone
from core.task_manager import TaskManager, TaskStatus
from core.undo import can_undo, clear as clear_undo, push_undo, register_clone_snapshot, undo_last


class TestWebsiteClonerSuite(unittest.TestCase):

    def setUp(self):
        clear_undo()
        self.temp_dir = Path(tempfile.mkdtemp(prefix="zezo_test_clone_"))

    def tearDown(self):
        if self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass
        clear_undo()

    def test_1_tool_schema_and_discovery(self):
        """Verify TOOL schema complies with action contracts and is auto-discovered."""
        self.assertEqual(TOOL["name"], "clone_website")
        self.assertIn("url", TOOL["parameters"]["required"])
        self.assertIn("mode", TOOL["parameters"]["properties"])
        self.assertIn("output_format", TOOL["parameters"]["properties"])
        self.assertIn("target_dir", TOOL["parameters"]["properties"])

        reg = discover_actions(Path("actions"))
        self.assertIn("clone_website", reg._actions)
        record = reg._actions["clone_website"]
        self.assertEqual(record.name, "clone_website")
        self.assertTrue(callable(record.handler))

    def test_2_url_normalization_and_domain_extraction(self):
        """Verify clean extraction of domain and sanitization of filenames."""
        self.assertEqual(_normalize_url("apple.com"), "https://apple.com")
        self.assertEqual(_normalize_url("http://test.org/page"), "http://test.org/page")
        self.assertEqual(_normalize_url("https://sub.domain.co.uk/test?q=1"), "https://sub.domain.co.uk/test?q=1")

        self.assertEqual(_extract_domain("https://www.apple.com/iphone"), "apple_com")
        self.assertEqual(_extract_domain("tailwindcss.com"), "tailwindcss_com")
        self.assertEqual(_extract_domain("http://localhost:8080/test"), "localhost")

        self.assertEqual(_sanitize_filename("main:style?.css"), "main_style_.css")
        self.assertEqual(_sanitize_filename("valid_image.png"), "valid_image.png")

    def test_3_task_manager_submit_after(self):
        """Verify submit_after chains child task execution strictly after parent completes."""
        tm = TaskManager()

        parent_ran = []
        child_ran = []

        def parent_fn(params, ctx):
            time.sleep(0.2)
            parent_ran.append(True)
            return {"status": "parent_done"}

        def child_fn(params, ctx):
            self.assertTrue(parent_ran, "Parent must complete before child runs")
            child_ran.append(True)
            return {"status": "child_done"}

        parent_id = tm.submit("parent_tool", parent_fn, {})
        child_id = tm.submit_after(parent_id, "child_tool", child_fn, {})

        self.assertIsNotNone(parent_id)
        self.assertIsNotNone(child_id)

        # Wait for both to complete
        start = time.time()
        while time.time() - start < 5.0:
            p_status = tm.status(parent_id)
            c_status = tm.status(child_id)
            if p_status and c_status:
                if p_status.get("status") == TaskStatus.DONE.value and c_status.get("status") == TaskStatus.DONE.value:
                    break
            time.sleep(0.1)

        self.assertEqual(len(parent_ran), 1)
        self.assertEqual(len(child_ran), 1)
        self.assertEqual(tm.status(child_id).get("status"), TaskStatus.DONE.value)

    def test_4_repo_context_register_clone_and_unique_dir(self):
        """Verify get_unique_clone_dir generates unique paths and register_clone activates workspace."""
        dir1 = get_unique_clone_dir("testsite")
        self.assertTrue(str(dir1).endswith("testsite_clone"))

        # Create dummy directory to test collision increment
        dir1.mkdir(parents=True, exist_ok=True)
        try:
            dir2 = get_unique_clone_dir("testsite")
            self.assertTrue(str(dir2).endswith("testsite_clone_1"))
        finally:
            if dir1.exists():
                shutil.rmtree(dir1)

        # Test register_clone
        test_workspace = self.temp_dir / "my_cloned_app"
        resolved = register_clone(test_workspace)
        self.assertTrue(resolved.exists())
        self.assertEqual(resolved, test_workspace.resolve())

    def test_5_undo_register_clone_snapshot(self):
        """Verify register_clone_snapshot pushes an undoable action that cleans up the folder."""
        clone_folder = self.temp_dir / "apple_clone"
        clone_folder.mkdir(parents=True, exist_ok=True)
        (clone_folder / "index.html").write_text("<h1>Apple Clone</h1>", encoding="utf-8")

        register_clone_snapshot(clone_folder, tool_label="Clone of Apple")
        self.assertTrue(can_undo())

        msg = undo_last()
        self.assertIn("Removed cloned directory apple_clone", msg)
        self.assertFalse(clone_folder.exists())

    def test_6_ephemeral_preview_server(self):
        """Verify start_local_preview_server serves local HTML over HTTP loopback."""
        (self.temp_dir / "index.html").write_text("<html><body><h1>Preview Test</h1></body></html>", encoding="utf-8")

        preview_url, port = start_local_preview_server(self.temp_dir)
        self.assertTrue(preview_url.startswith(f"http://127.0.0.1:{port}"))

        # Make HTTP request to verify server is active and serving content
        req = urllib.request.Request(preview_url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            content = resp.read().decode("utf-8")
            self.assertEqual(resp.status, 200)
            self.assertIn("Preview Test", content)

    def test_7_asset_downloader_and_partial_success(self):
        """Verify asset localization parses HTML, handles partial failures, and writes relative paths."""
        mock_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Page</title>
            <link rel="stylesheet" href="https://example.com/nonexistent_style.css">
        </head>
        <body>
            <h1>Hello World</h1>
            <img src="https://example.com/missing_image.png" alt="Test">
        </body>
        </html>
        """

        class MockTaskContext:
            def report(self, pct, msg=""):
                pass

        localized_html, downloaded, failed = localize_and_download_assets(
            base_url="https://example.com",
            html=mock_html,
            output_dir=self.temp_dir,
            ctx=MockTaskContext(),
        )

        # Partial success guard: failed assets remain with original URL rather than crashing
        self.assertIn("https://example.com/missing_image.png", localized_html)
        self.assertEqual(downloaded, 0)
        self.assertGreaterEqual(failed, 1)


    def test_8_multi_directory_preview_server_isolation(self):
        """Verify multiple cloned directories receive isolated ports and serve distinct content."""
        dir_apple = self.temp_dir / "apple_clone"
        dir_tailwind = self.temp_dir / "tailwind_clone"
        dir_apple.mkdir(parents=True, exist_ok=True)
        dir_tailwind.mkdir(parents=True, exist_ok=True)

        (dir_apple / "index.html").write_text("<html><body><h1>Apple Page</h1></body></html>", encoding="utf-8")
        (dir_tailwind / "index.html").write_text("<html><body><h1>Tailwind Page</h1></body></html>", encoding="utf-8")

        url_apple, port_apple = start_local_preview_server(dir_apple)
        url_tailwind, port_tailwind = start_local_preview_server(dir_tailwind)

        self.assertNotEqual(port_apple, port_tailwind, "Different directories must receive distinct ports")

        # Verify Apple server serves Apple content
        req_apple = urllib.request.Request(url_apple)
        with urllib.request.urlopen(req_apple, timeout=5) as resp:
            content = resp.read().decode("utf-8")
            self.assertIn("Apple Page", content)
            self.assertNotIn("Tailwind Page", content)

        # Verify Tailwind server serves Tailwind content
        req_tailwind = urllib.request.Request(url_tailwind)
        with urllib.request.urlopen(req_tailwind, timeout=5) as resp:
            content = resp.read().decode("utf-8")
            self.assertIn("Tailwind Page", content)
            self.assertNotIn("Apple Page", content)


    def test_9_dom_sanitization_and_chunk_purging(self):
        """Verify _sanitize_and_clean_dom purges minified Next.js/Turbopack chunks and hydration blobs."""
        dirty_html = """
        <!DOCTYPE html>
        <html data-reactroot="">
        <head>
            <title>Next.js Page</title>
            <script src="https://example.com/_next/static/chunks/turbopack-12345.js"></script>
            <script src="https://www.googletagmanager.com/gtag/js?id=G-123"></script>
            <script id="__NEXT_DATA__">{"props":{"pageProps":{}}}</script>
        </head>
        <body data-server-rendered="true">
            <div id="__next">
                <h1>Clean Title</h1>
            </div>
            <next-route-announcer></next-route-announcer>
        </body>
        </html>
        """
        class MockCtx:
            def report(self, p, m=""): pass

        clean_html, downloaded, failed = localize_and_download_assets(
            base_url="https://example.com",
            html=dirty_html,
            output_dir=self.temp_dir,
            ctx=MockCtx(),
        )

        self.assertNotIn("turbopack", clean_html)
        self.assertNotIn("googletagmanager", clean_html)
        self.assertNotIn("__NEXT_DATA__", clean_html)
        self.assertNotIn("data-reactroot", clean_html)
        self.assertNotIn("next-route-announcer", clean_html)
        self.assertIn("Clean Title", clean_html)
        self.assertTrue((self.temp_dir / "assets" / "js" / "app.js").exists())


if __name__ == "__main__":
    unittest.main()
