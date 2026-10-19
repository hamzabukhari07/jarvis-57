"""
tests/test_workspace_picker.py — Tests workspace picker endpoint and folder junk filtering.
"""
import tempfile
from pathlib import Path
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from unittest.mock import patch
from core.ui_server import ZezoUIServer, _scan_folder


class TestWorkspacePicker(AioHTTPTestCase):
    async def get_application(self):
        self.zezo_server = ZezoUIServer(host="127.0.0.1", port=0)
        app = web.Application()
        app.router.add_post("/api/workspace/pick", self.zezo_server._workspace_pick_handler)
        return app

    def test_scan_folder_ignores_junk(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            proj = Path(tmp_dir) / "test_project"
            proj.mkdir()
            (proj / "main.py").write_text("print('hello')")
            (proj / "README.md").write_text("# Test")

            # Create ignored dirs
            nm = proj / "node_modules" / "bad_pkg"
            nm.mkdir(parents=True)
            (nm / "index.js").write_text("module.exports = {}")

            git = proj / ".git" / "objects"
            git.mkdir(parents=True)
            (git / "pack.idx").write_text("binary")

            rel_paths, total_size, truncated = _scan_folder(proj, cap=100)

            # Assert ignored dirs are skipped
            assert not any("node_modules" in p for p in rel_paths)
            assert not any(".git" in p for p in rel_paths)
            assert any("main.py" in p for p in rel_paths)
            assert any("README.md" in p for p in rel_paths)
            assert len(rel_paths) == 2

    @unittest_run_loop
    async def test_pick_workspace_folder_success(self):
        import asyncio
        test_dir = Path(__file__).parent.resolve()
        fut = asyncio.Future()
        fut.set_result(str(test_dir))
        with patch("asyncio.BaseEventLoop.run_in_executor", return_value=fut):
            resp = await self.client.post("/api/workspace/pick")
            assert resp.status == 200
            data = await resp.json()
            assert data["status"] == "success"
            assert "folder" in data
            assert data["folder"]["name"] == test_dir.name
            assert data["folder"]["is_folder"] is True
            assert data["folder"]["files_count"] >= 1
