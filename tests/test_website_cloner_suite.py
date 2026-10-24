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
import re
import shutil
import sys
import tempfile
import threading
import time
import unittest
import unittest.mock
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import actions.website_cloner as cloner
from actions.fleet_control import fleet_control
from actions.website_cloner import (
    CAPTURE_ONLY_FORMATS,
    DEFAULT_OUTPUT_FORMAT,
    MAX_CRAWL_TIMEOUT_SEC,
    RE_ARTIFACT_APP_DIR,
    RE_ARTIFACT_SINGLE,
    RE_ARTIFACT_SPECS,
    RE_OUTPUT_CLAUSES,
    RE_REBUILD_FAILURE_PREFIX,
    SINGLE_PAGE_TIMEOUT_SEC,
    TOOL,
    UNCAGE_NO_PURGE,
    UNCAGE_PAGE_TIMEOUT_CRAWL_MS,
    UNCAGE_PAGE_TIMEOUT_SINGLE_MS,
    _extract_domain,
    _new_html_files,
    _normalize_url,
    _re_output_clause,
    _run_reverse_engineer,
    _run_uncage_process,
    _sanitize_filename,
    _uncage_page_timeout_ms,
    _uncage_result_ok,
    _verify_re_artifact,
    clone_website_action,
    crawl_timeout_budget,
    localize_and_download_assets,
    rebuild_failure_message,
    reverse_engineer_prompt,
    run_uncage_exporter,
    start_local_preview_server,
    verify_local_assets,
)
from core.action_loader import discover_actions
from core.repo_context import expand_user_dir, get_unique_clone_dir, register_clone
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


class _StubCtx:
    """Minimal TaskContext stand-in for helpers that only report progress."""

    def __init__(self):
        self.reports = []

    def report(self, pct, msg=""):
        self.reports.append((pct, msg))

    def set_pid(self, pid):
        pass

    def on_complete(self, payload=None):
        pass

    def on_fail(self, error):
        pass

    def cancelled(self):
        return False

    def is_cancelled(self):
        return False


class TestCloneCompletionGuard(unittest.TestCase):
    """Phase 1: a half-extracted bundle must never be reported as a successful clone."""

    REPO_ROOT = Path(__file__).resolve().parent.parent
    FIXTURES = REPO_ROOT / "tools" / "uncage" / "output"

    def test_linear_app_fixture_is_rejected(self):
        """The real broken export (captured-raw.html only) is the permanent regression fixture."""
        fixture = self.FIXTURES / "linear_app"
        if not fixture.exists():
            self.skipTest("fixture export missing")
        ok, why = _uncage_result_ok(fixture, 0)
        self.assertFalse(ok)
        self.assertIn("captured-raw", why)

    def test_complete_fixture_is_accepted(self):
        fixture = self.FIXTURES / "stripe_com"
        if not fixture.exists():
            self.skipTest("fixture export missing")
        self.assertEqual(_uncage_result_ok(fixture, 0), (True, ""))

    def test_missing_asset_map_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "index.html").write_text("<html></html>", encoding="utf-8")
            ok, why = _uncage_result_ok(d, 0)
            self.assertFalse(ok)
            self.assertIn("asset-map.json", why)

    def test_nonzero_exit_code_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "index.html").write_text("<html></html>", encoding="utf-8")
            (d / "asset-map.json").write_text("{}", encoding="utf-8")
            self.assertFalse(_uncage_result_ok(d, 1)[0])
            self.assertTrue(_uncage_result_ok(d, 0)[0])

    def test_missing_directory_is_rejected(self):
        ok, why = _uncage_result_ok(Path("does/not/exist"), 0)
        self.assertFalse(ok)
        self.assertTrue(why)

    def test_surviving_raw_snapshot_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "index.html").write_text("<html></html>", encoding="utf-8")
            (d / "asset-map.json").write_text("{}", encoding="utf-8")
            (d / "captured-raw.html").write_text("<html></html>", encoding="utf-8")
            ok, why = _uncage_result_ok(d, 0)
            self.assertFalse(ok)
            self.assertIn("captured-raw", why)

    def test_timeout_budgets_are_scope_derived(self):
        self.assertEqual(crawl_timeout_budget(1), SINGLE_PAGE_TIMEOUT_SEC)
        self.assertEqual(crawl_timeout_budget(25), MAX_CRAWL_TIMEOUT_SEC)
        self.assertLessEqual(crawl_timeout_budget(999), 600)
        self.assertEqual(_uncage_page_timeout_ms(1), UNCAGE_PAGE_TIMEOUT_SINGLE_MS)
        self.assertEqual(_uncage_page_timeout_ms(25), UNCAGE_PAGE_TIMEOUT_CRAWL_MS)


class TestIntegrityGate(unittest.TestCase):
    """Phase 3: a clone whose local assets 404 must fail, not open a preview."""

    def _page(self, root: Path, head: str) -> Path:
        (root / "assets").mkdir(parents=True, exist_ok=True)
        (root / "index.html").write_text(f"<html><head>{head}</head></html>", encoding="utf-8")
        return root

    def test_present_asset_passes(self):
        with tempfile.TemporaryDirectory() as td:
            root = self._page(Path(td), '<link href="assets/css/style.css" rel="stylesheet">')
            (root / "assets" / "css").mkdir(parents=True)
            (root / "assets" / "css" / "style.css").write_text("body{}", encoding="utf-8")
            ok, msg = verify_local_assets(root)
            self.assertTrue(ok, msg)

    def test_missing_asset_fails_with_count(self):
        with tempfile.TemporaryDirectory() as td:
            root = self._page(Path(td), '<link href="assets/css/gone.css" rel="stylesheet">')
            ok, msg = verify_local_assets(root)
            self.assertFalse(ok)
            self.assertIn("gone.css", msg)

    def test_remote_and_data_refs_are_ignored(self):
        with tempfile.TemporaryDirectory() as td:
            root = self._page(
                Path(td),
                '<link href="https://cdn.example.com/x.css" rel="stylesheet">'
                '<img src="data:image/png;base64,AAAA">'
                '<a href="mailto:a@b.com">m</a><a href="#top">t</a>'
                '<script src="https://cdn.example.com/x.js"></script>',
            )
            ok, msg = verify_local_assets(root)
            self.assertTrue(ok, msg)

    def test_absent_favicon_is_not_a_failure(self):
        """False-positive guard: files outside assets/ are not this gate's business."""
        with tempfile.TemporaryDirectory() as td:
            root = self._page(Path(td), '<link rel="icon" href="/favicon.ico"><a href="robots.txt">r</a>')
            ok, msg = verify_local_assets(root)
            self.assertTrue(ok, msg)

    def test_missing_video_is_a_caveat_not_a_failure(self):
        """uncage never downloads <video> sources, so failing here would block every video-bearing site."""
        with tempfile.TemporaryDirectory() as td:
            root = self._page(
                Path(td),
                '<link href="assets/css/style.css" rel="stylesheet">'
                '<video src="./assets/hero.mp4"></video>',
            )
            (root / "assets" / "css").mkdir(parents=True)
            (root / "assets" / "css" / "style.css").write_text("body{}", encoding="utf-8")
            ok, msg = verify_local_assets(root)
            self.assertTrue(ok, msg)
            self.assertIn("hero.mp4", msg)
            self.assertIn("were not downloaded", msg)

    def test_missing_image_still_fails(self):
        """Images are localised by uncage, so a missing one is a real breakage."""
        with tempfile.TemporaryDirectory() as td:
            root = self._page(Path(td), '<img src="./assets/hero.avif">')
            ok, msg = verify_local_assets(root)
            self.assertFalse(ok)
            self.assertIn("hero.avif", msg)

    def test_missing_script_still_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = self._page(Path(td), '<script src="./assets/js/app.js"></script>')
            ok, msg = verify_local_assets(root)
            self.assertFalse(ok)
            self.assertIn("app.js", msg)

    def test_one_missing_stylesheet_among_many_still_renders(self):
        """A small shortfall is a caveat: the page still renders with the stylesheets that did arrive."""
        with tempfile.TemporaryDirectory() as td:
            refs, body = [], []
            for i in range(10):
                refs.append(f'<link href="assets/css/s{i}.css" rel="stylesheet">')
                (Path(td) / "assets" / "css").mkdir(parents=True, exist_ok=True)
                if i:  # s0 never arrives
                    (Path(td) / "assets" / "css" / f"s{i}.css").write_text("body{}", encoding="utf-8")
            root = self._page(Path(td), "".join(refs))
            ok, msg = verify_local_assets(root)
            self.assertTrue(ok, msg)
            self.assertIn("could not be saved", msg)

    def test_wholesale_asset_loss_fails(self):
        """The reported defect: the served page referenced assets/ that did not exist at all."""
        with tempfile.TemporaryDirectory() as td:
            root = self._page(
                Path(td),
                '<link href="assets/css/a.css" rel="stylesheet">'
                '<script src="assets/js/b.js"></script>',
            )
            ok, msg = verify_local_assets(root)
            self.assertFalse(ok)
            self.assertIn("missing locally", msg)


class TestUncageAutoTuning(unittest.TestCase):
    """Phase 2: the flags ZEZO chooses for the user, and the ones it must never choose."""

    FIXTURE_URL = "https://zezo-autotune-fixture.invalid/"
    FIXTURE_NAME = "zezo_autotune_fixture_invalid"

    def setUp(self):
        self.calls = []

    def tearDown(self):
        stale = Path(__file__).resolve().parent.parent / "tools" / "uncage" / "output" / self.FIXTURE_NAME
        shutil.rmtree(stale, ignore_errors=True)

    def _recorder(self, ctx=None, write_bundle=True, killed=False, on_second=None):
        """Fake _run_uncage_process that records cmd and materialises an export when asked."""
        def _fake(cmd, cwd, _ctx, timeout_sec):
            self.calls.append(list(cmd))
            if killed and len(self.calls) == 1:
                return 0, True, [], []
            if write_bundle:
                out = Path(cwd) / "output" / cmd[cmd.index("-o") + 1]
                out.mkdir(parents=True, exist_ok=True)
                (out / "index.html").write_text("<html><body>ok</body></html>", encoding="utf-8")
                (out / "asset-map.json").write_text("{}", encoding="utf-8")
            return 0, False, [], []
        return _fake

    def _run(self, max_pages=1, priority_only=False, killed=False):
        with tempfile.TemporaryDirectory() as td:
            with unittest.mock.patch.object(cloner, "_run_uncage_process",
                                            side_effect=self._recorder(killed=killed)), \
                 unittest.mock.patch.object(cloner, "_ensure_uncage_browsers", lambda *a, **k: (True, "")):
                return run_uncage_exporter(
                    self.FIXTURE_URL, Path(td), None,
                    max_pages=max_pages, max_depth=0, priority_only=priority_only,
                )

    def test_timeout_and_no_purge_always_set(self):
        self._run()
        cmd = self.calls[0]
        self.assertIn("--timeout", cmd)
        self.assertEqual(cmd[cmd.index("--timeout") + 1], str(UNCAGE_PAGE_TIMEOUT_SINGLE_MS))
        self.assertIn("--no-purge", cmd)

    def test_priority_only_only_for_multi_page(self):
        self._run(max_pages=1, priority_only=True)
        self.assertNotIn("--priority-only", self.calls[0])
        self.calls.clear()
        self._run(max_pages=5, priority_only=True)
        self.assertIn("--priority-only", self.calls[0])
        self.assertEqual(self.calls[0][self.calls[0].index("--timeout") + 1],
                         str(UNCAGE_PAGE_TIMEOUT_CRAWL_MS))

    def test_safe_flags_never_set(self):
        self._run(max_pages=5, priority_only=True)
        cmd = self.calls[0]
        for forbidden in ("--ignore-robots", "--safe-mode", "--no-headless", "--keep-analytics"):
            self.assertNotIn(forbidden, cmd)

    def test_skip_deps_only_on_degraded_retry(self):
        self._run(killed=True)
        self.assertEqual(len(self.calls), 2)
        self.assertNotIn("--skip-deps", self.calls[0])
        self.assertIn("--skip-deps", self.calls[1])

    def test_happy_path_never_retries(self):
        self._run()
        self.assertEqual(len(self.calls), 1)


class TestSilentStallDeadline(unittest.TestCase):
    """Phase 1d: the wall-clock budget must fire while waiting, not only when a line arrives."""

    def test_silent_child_is_killed(self):
        class _Stdout:
            def readline(self):
                time.sleep(60)          # alive but silent
                return ""

            def close(self):
                pass

        class _Proc:
            def __init__(self):
                self.stdout = _Stdout()
                self.returncode = None

            def poll(self):
                return None

            def kill(self):
                self.returncode = -9

            def wait(self, timeout=None):
                return self.returncode

        with unittest.mock.patch.object(cloner.subprocess, "Popen", lambda *a, **k: _Proc()):
            start = time.time()
            rc, killed, errs, tail = _run_uncage_process(["node", "uncage.js"], Path.cwd(), None, 2)
            elapsed = time.time() - start
        self.assertTrue(killed, "silent stall was not killed")
        self.assertLess(elapsed, 8, f"deadline took {elapsed:.1f}s")


class TestConfirmationGate(unittest.TestCase):
    """Phase 4: intake → commit → submit, and nothing is submitted before a confirmation."""

    class _FakeTM:
        def __init__(self):
            self.submitted = []

        def submit(self, tool_name=None, fn=None, params=None, **kw):
            self.submitted.append((tool_name, params))
            return "task-xyz"

    def setUp(self):
        self.tm = self._FakeTM()
        self._orig = cloner.get_task_manager

    def tearDown(self):
        cloner.get_task_manager = self._orig

    def _call(self, params):
        cloner.get_task_manager = lambda: self.tm
        return clone_website_action(params)

    def test_state1_asks_all_three_and_submits_nothing(self):
        out = self._call({"url": "https://example.com"})
        self.assertIn("CLONE NOT STARTED", out)
        self.assertIn("scope", out)
        self.assertIn("output", out)
        self.assertIn("folder", out)
        self.assertEqual(self.tm.submitted, [])

    def test_state2_asks_only_for_the_missing_value(self):
        out = self._call({
            "url": "https://example.com",
            "mode": "single_page",
            "output_format": "static",
        })
        self.assertIn("folder", out)
        self.assertNotIn("- scope:", out)
        self.assertNotIn("- output:", out)
        self.assertEqual(self.tm.submitted, [])

    def test_state3_all_present_unconfirmed_reads_back_and_submits_nothing(self):
        out = self._call({
            "url": "https://example.com",
            "mode": "single_page",
            "output_format": "static",
            "target_dir": "Desktop/xyz_clone",
        })
        self.assertIn("CLONE NOT STARTED", out)
        self.assertIn("https://example.com", out)
        self.assertIn("xyz_clone", out)
        self.assertNotIn("Task ID", out)
        self.assertEqual(self.tm.submitted, [])

    def test_readback_names_the_rebuild_and_says_the_capture_is_kept(self):
        out = self._call({
            "url": "https://example.com",
            "mode": "single_page",
            "output_format": "react",
            "target_dir": "Desktop/xyz_clone",
        })
        self.assertIn("React + Vite project", out)
        self.assertIn("always kept and previewed", out)
        self.assertEqual(self.tm.submitted, [])

    def test_readback_passes_a_stack_named_in_the_user_own_words_through(self):
        """Any format ZEZO does not have a phrase for is read back verbatim, so the user hears
        the stack they asked for instead of a default."""
        out = self._call({
            "url": "https://example.com",
            "mode": "single_page",
            "output_format": "svelte",
            "target_dir": "Desktop/xyz_clone",
        })
        self.assertIn("svelte", out)
        self.assertEqual(self.tm.submitted, [])

    def test_confirmed_submits(self):
        out = self._call({
            "url": "https://example.com",
            "mode": "single_page",
            "output_format": "static",
            "target_dir": "Desktop/xyz_clone",
            "confirmed": True,
        })
        self.assertIn("task-xyz", out)
        self.assertEqual(len(self.tm.submitted), 1)
        tool_name, params = self.tm.submitted[0]
        self.assertEqual(tool_name, "website_cloner")
        self.assertEqual(params["target_dir"], "Desktop/xyz_clone")


class TestReverseEngineer(unittest.TestCase):
    """ZEZO rebuilds the capture with its own engine; success is verified on disk, never taken
    from the engine's prose, and uncage's own output is never rewritten."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="zezo_re_test_"))
        self.clone_dir = self.tmp / "site_clone"
        (self.clone_dir / "assets").mkdir(parents=True)
        self.original_index = "<html><body>hero</body></html>"
        (self.clone_dir / "index.html").write_text(self.original_index, encoding="utf-8")
        (self.clone_dir / "assets" / "style.css").write_text("body{}", encoding="utf-8")
        self.ctx = _StubCtx()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, engine, output_format="raw_html"):
        with unittest.mock.patch("actions.antigravity_agent.antigravity_action", engine):
            return _run_reverse_engineer("https://example.com", self.clone_dir, self.ctx, output_format)

    # ── the prompt ────────────────────────────────────────────────────────
    def test_prompt_names_the_capture_and_keeps_the_no_prose_guardrails(self):
        prompt = reverse_engineer_prompt("https://example.com", "raw_html")
        self.assertIn("https://example.com", prompt)
        self.assertIn("reverse engineer", prompt.lower())
        self.assertIn(RE_ARTIFACT_SINGLE, prompt)
        # These guardrails are what keep the engine writing files instead of an essay.
        self.assertIn("do not write an analysis report", prompt.lower())
        self.assertIn("do not create a design system", prompt.lower())
        self.assertIn("counts as failure", prompt.lower())

    def test_every_curated_format_has_a_clause_and_a_verification_spec(self):
        for fmt in RE_OUTPUT_CLAUSES:
            self.assertTrue(_re_output_clause(fmt).strip(), f"{fmt} has an empty clause")
            self.assertIn(fmt, RE_ARTIFACT_SPECS, f"{fmt} has no verification spec")

    def test_unknown_format_is_passed_through_as_a_named_stack(self):
        clause = _re_output_clause("svelte")
        self.assertIn("svelte", clause)
        self.assertIn(RE_ARTIFACT_APP_DIR, clause)

    def test_default_format_is_a_single_html_rebuild(self):
        self.assertEqual(DEFAULT_OUTPUT_FORMAT, "raw_html")
        self.assertNotIn(DEFAULT_OUTPUT_FORMAT, CAPTURE_ONLY_FORMATS)

    # ── how the engine is driven ──────────────────────────────────────────
    def test_engine_runs_in_place_on_the_capture_folder_in_verbatim_mode(self):
        seen = {}

        def _engine(params, **kw):
            seen.update(params)
            (self.clone_dir / RE_ARTIFACT_SINGLE).write_text("<html>rebuilt</html>", encoding="utf-8")
            return '{"status": "success"}'

        ok, detail, _ = self._run(_engine)
        self.assertTrue(ok, detail)
        # cwd is the capture folder itself, exactly like running the agent by hand on an export.
        self.assertEqual(seen["project_path"], str(self.clone_dir))
        self.assertTrue(seen["run_in_place"])
        self.assertIs(seen["task_ctx"], self.ctx)
        # verbatim: the engine must not append its own stack directives to this prompt.
        self.assertEqual(seen["prompt_mode"], "verbatim")
        self.assertTrue(seen["skip_design"])
        self.assertTrue(seen["skip_preview"])
        self.assertIn("reverse engineer", seen["task"].lower())

    def test_uncage_output_is_never_rewritten(self):
        def _engine(params, **kw):
            (self.clone_dir / RE_ARTIFACT_SINGLE).write_text("<html>rebuilt</html>", encoding="utf-8")
            return '{"status": "success"}'

        self._run(_engine)
        self.assertEqual(
            (self.clone_dir / "index.html").read_text(encoding="utf-8"), self.original_index
        )
        self.assertTrue((self.clone_dir / "assets" / "style.css").exists())

    # ── single-file verification ──────────────────────────────────────────
    def test_single_html_success_reports_the_new_file(self):
        def _engine(params, **kw):
            (self.clone_dir / RE_ARTIFACT_SINGLE).write_text("<html>rebuilt</html>", encoding="utf-8")
            return '{"status": "success"}'

        ok, detail, artifact = self._run(_engine)
        self.assertTrue(ok, detail)
        self.assertEqual(artifact.name, RE_ARTIFACT_SINGLE)
        self.assertIn(RE_ARTIFACT_SINGLE, detail)

    def test_prose_instead_of_a_file_fails(self):
        ok, detail, artifact = self._run(lambda params, **kw: '{"status": "success"}')
        self.assertFalse(ok)
        self.assertIsNone(artifact)
        self.assertIn("no new HTML file", detail)

    def test_new_uncage_snapshot_is_never_a_valid_artifact(self):
        def _engine(params, **kw):
            (self.clone_dir / "captured-raw-2.html").write_text("<html>raw</html>", encoding="utf-8")
            return '{"status": "success"}'

        ok, detail, _ = self._run(_engine)
        self.assertFalse(ok, "a raw uncage snapshot must never pass as the rebuilt artifact")

    def test_engine_reported_failure_keeps_the_reason(self):
        def _engine(params, **kw):
            (self.clone_dir / RE_ARTIFACT_SINGLE).write_text("<html>rebuilt</html>", encoding="utf-8")
            return '{"status": "failed", "error": "quota exceeded"}'

        ok, detail, _ = self._run(_engine)
        self.assertFalse(ok, "engine reported failure but the artifact was accepted")
        self.assertIn("quota exceeded", detail)

    # ── project verification ──────────────────────────────────────────────
    def test_project_format_needs_its_profile_shape(self):
        def _engine(params, **kw):
            app = self.clone_dir / RE_ARTIFACT_APP_DIR
            (app / "src").mkdir(parents=True)
            (app / "package.json").write_text("{}", encoding="utf-8")
            (app / "src" / "App.tsx").write_text("export default 1", encoding="utf-8")
            return '{"status": "success"}'

        ok, detail, artifact = self._run(_engine, "react")
        self.assertTrue(ok, detail)
        self.assertEqual(artifact, self.clone_dir / RE_ARTIFACT_APP_DIR)
        self.assertIn("1 source file", detail)

    def test_project_without_source_files_fails(self):
        def _engine(params, **kw):
            app = self.clone_dir / RE_ARTIFACT_APP_DIR
            (app / "src").mkdir(parents=True)
            (app / "package.json").write_text("{}", encoding="utf-8")
            return '{"status": "success"}'

        ok, detail, _ = self._run(_engine, "react")
        self.assertFalse(ok)
        self.assertIn("no source files", detail)

    def test_project_missing_its_manifest_fails(self):
        ok, detail, _ = self._run(lambda params, **kw: '{"status": "success"}', "php")
        self.assertFalse(ok)
        self.assertIn(RE_ARTIFACT_APP_DIR, detail)

    def test_custom_stack_succeeds_when_real_files_appear(self):
        def _engine(params, **kw):
            app = self.clone_dir / RE_ARTIFACT_APP_DIR
            app.mkdir(parents=True)
            (app / "main.go").write_text("package main", encoding="utf-8")
            return '{"status": "success"}'

        ok, detail, artifact = self._run(_engine, "go")
        self.assertTrue(ok, detail)
        self.assertEqual(artifact, self.clone_dir / RE_ARTIFACT_APP_DIR)

    def test_custom_stack_with_no_files_fails(self):
        ok, detail, artifact = self._run(lambda params, **kw: '{"status": "success"}', "svelte")
        self.assertFalse(ok)
        self.assertIsNone(artifact)
        self.assertIn("no files for the requested stack", detail)

    def test_prompt_fits_the_windows_command_line_budget(self):
        """The prompt travels as one argv element, and verbatim mode deliberately skips the
        engine's 6000-char truncation - so this is what guards it instead."""
        for fmt in ("raw_html", "nextjs", "svelte"):
            prompt = reverse_engineer_prompt("https://example.com", fmt)
            self.assertLess(len(prompt), 16000, f"{fmt} prompt is too long for the CLI")

    def test_worker_flags_are_forwarded_to_the_engine(self):
        """antigravity_action builds a fresh worker dict, so these flags must be copied explicitly."""
        import actions.antigravity_agent as aa
        seen = {}

        with unittest.mock.patch.object(aa, "_run_worker",
                                        lambda payload, ctx=None: seen.update(payload) or {"status": "success"}):
            aa.antigravity_action({
                "task": "Reverse engineer the captured project.",
                "project_path": str(self.clone_dir),
                "run_in_place": True,
                "task_ctx": self.ctx,
                "skip_design": True,
                "skip_preview": True,
                "prompt_mode": "verbatim",
            })
        self.assertTrue(seen.get("skip_design"), "skip_design never reached _run_worker")
        self.assertTrue(seen.get("skip_preview"), "skip_preview never reached _run_worker")
        self.assertEqual(seen.get("prompt_mode"), "verbatim", "prompt_mode never reached _run_worker")


class TestFailureEscalation(unittest.TestCase):
    """Phase 5 step 6: the user can hand a failed rebuild folder to a fleet agent."""

    def test_dispatch_forwards_the_folder(self):
        from core.fleet_manager import fleet_manager
        seen = {}

        def _recorder(agent_id=None, prompt=None, path=None, model_override=None, **kw):
            seen.update({"agent_id": agent_id, "prompt": prompt, "path": path})
            return {"success": True, "task_id": "t1", "agent_name": "Verve", "tool": "antigravity_run"}

        with unittest.mock.patch.object(fleet_manager, "dispatch_task", _recorder):
            out = fleet_control({
                "action": "dispatch",
                "agent_id": "VERVE",
                "task": "Finish the React rebuild of the cloned site in this folder.",
                "path": r"C:\Users\Hamza\Desktop\linear_app_cloned_app",
            })
        self.assertIn("Dispatched", out)
        self.assertEqual(seen["path"], r"C:\Users\Hamza\Desktop\linear_app_cloned_app")

    def test_dispatch_schema_documents_path(self):
        from actions.fleet_control import TOOL as FLEET_TOOL
        self.assertIn("path", FLEET_TOOL["parameters"]["properties"])



class TestDeliverableOpeningAndCloneHygiene(unittest.TestCase):
    """Tests for deliverable browser launch routing and antigravity_clone.html avoidance on rebuilds."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="zezo_open_test_"))
        self.clone_dir = self.tmp / "test_clone"
        self.clone_dir.mkdir(parents=True)
        (self.clone_dir / "index.html").write_text("<html><body>Test Index</body></html>", encoding="utf-8")
        self.ctx = _StubCtx()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_open_in_browser_file_url_calls_webbrowser_directly(self):
        """file:// URLs must bypass browser_control and open directly via webbrowser."""
        with unittest.mock.patch("webbrowser.open", return_value=True) as mock_webbrowser,              unittest.mock.patch("actions.browser_control.browser_control") as mock_bc:
            cloner._open_in_browser("file:///C:/path/to/rebuilt.html")
            mock_webbrowser.assert_called_once_with("file:///C:/path/to/rebuilt.html")
            mock_bc.assert_not_called()

    def test_open_in_browser_http_url_uses_browser_control(self):
        """http:// URLs call browser_control and do not trigger webbrowser if successful."""
        with unittest.mock.patch("webbrowser.open") as mock_webbrowser,              unittest.mock.patch("actions.browser_control.browser_control", return_value="Opened in browser") as mock_bc:
            cloner._open_in_browser("http://127.0.0.1:9400/rebuilt.html")
            mock_bc.assert_called_once_with({"action": "go_to", "url": "http://127.0.0.1:9400/rebuilt.html"})
            mock_webbrowser.assert_not_called()

    def test_open_in_browser_validation_error_falls_back_to_webbrowser(self):
        """If browser_control returns a validation error string, fall back to webbrowser."""
        with unittest.mock.patch("webbrowser.open", return_value=True) as mock_webbrowser,              unittest.mock.patch("actions.browser_control.browser_control", return_value="Validation error: Invalid URL scheme"):
            cloner._open_in_browser("http://127.0.0.1:9400/test.html")
            mock_webbrowser.assert_called_once_with("http://127.0.0.1:9400/test.html")

    def test_rebuild_format_does_not_generate_antigravity_clone_html(self):
        """When output_format is a rebuild, antigravity_clone.html is NOT written."""
        rebuilt_file = self.clone_dir / "rebuilt.html"
        rebuilt_file.write_text("<!DOCTYPE html><html><body>Rebuilt</body></html>", encoding="utf-8")

        with unittest.mock.patch.object(cloner, "run_uncage_exporter", return_value=(True, "ok")),              unittest.mock.patch.object(cloner, "verify_local_assets", return_value=(True, "all present")),              unittest.mock.patch.object(cloner, "detect_tech_stack", return_value="standard_html"),              unittest.mock.patch.object(cloner, "_run_reverse_engineer", return_value=(True, "Rebuilt clean page", rebuilt_file)),              unittest.mock.patch.object(cloner, "_open_deliverable", return_value="file:///rebuilt.html"),              unittest.mock.patch.object(cloner, "register_rebuild"):
            
            res = cloner._clone_worker({
                "url": "https://example.com",
                "mode": "single_page",
                "output_format": "raw_html",
                "target_dir": str(self.clone_dir),
            }, ctx=self.ctx)

            self.assertEqual(res["status"], "success")
            self.assertFalse((self.clone_dir / "antigravity_clone.html").exists(),
                             "antigravity_clone.html must not be written on rebuild tasks")
            self.assertTrue(rebuilt_file.exists())

    def test_capture_only_format_generates_antigravity_clone_html(self):
        """When output_format is in CAPTURE_ONLY_FORMATS, antigravity_clone.html IS generated."""
        with unittest.mock.patch.object(cloner, "run_uncage_exporter", return_value=(True, "ok")),              unittest.mock.patch.object(cloner, "verify_local_assets", return_value=(True, "all present")),              unittest.mock.patch.object(cloner, "detect_tech_stack", return_value="standard_html"),              unittest.mock.patch.object(cloner, "_faithful_cleanup", return_value="<html>Clean</html>"),              unittest.mock.patch.object(cloner, "_open_deliverable", return_value="http://127.0.0.1:9400/antigravity_clone.html"):

            res = cloner._clone_worker({
                "url": "https://example.com",
                "mode": "single_page",
                "output_format": "capture_only",
                "target_dir": str(self.clone_dir),
            }, ctx=self.ctx)

            self.assertEqual(res["status"], "success")
            self.assertTrue((self.clone_dir / "antigravity_clone.html").exists(),
                            "antigravity_clone.html must be generated for capture_only format")


if __name__ == "__main__":
    unittest.main()
