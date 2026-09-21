"""
tests/test_file_reader_suite.py — Unit tests for ZEZO Universal Multi-Format File Reader Engine
"""

import os
import tempfile
from pathlib import Path
import pytest

from core.file_reader import (
    read_file,
    _is_scanned_pdf,
    _get_pdf_page_count,
    _read_text_direct,
    DEFAULT_MAX_CHARS
)


class TestFileReaderSuite:

    def test_direct_read_plain_text(self, tmp_path):
        test_file = tmp_path / "sample.py"
        test_file.write_text("def hello_zezo():\n    return 'autonomous'\n", encoding="utf-8")
        
        res = read_file(test_file)
        assert res.file_type == "code"
        assert res.engine == "direct_read"
        assert "hello_zezo" in res.text
        assert not res.is_truncated

    def test_direct_read_encoding_fallback(self, tmp_path):
        test_file = tmp_path / "latin.txt"
        # Write latin-1 specific bytes
        test_file.write_bytes("Café Münster".encode("latin-1"))
        
        res = read_file(test_file)
        assert "Café Münster" in res.text
        assert res.file_type == "text"

    def test_legacy_office_rejection(self, tmp_path):
        test_file = tmp_path / "old_document.doc"
        test_file.write_text("dummy", encoding="utf-8")
        
        res = read_file(test_file)
        assert res.engine == "legacy_rejection"
        assert ".docx" in res.text

    def test_scanned_pdf_heuristic(self):
        # Empty text -> scanned
        assert _is_scanned_pdf("", 5) is True
        # Less than 50 chars total -> scanned
        assert _is_scanned_pdf("Small header only", 3) is True
        # High char density -> native text
        dense_text = "This is a full page containing lots of readable text and information. " * 20
        assert _is_scanned_pdf(dense_text, 1) is False

    def test_truncation_guard(self, tmp_path):
        test_file = tmp_path / "large_file.txt"
        # 100KB content
        test_file.write_text("A" * 100000, encoding="utf-8")
        
        res = read_file(test_file, max_chars=1000)
        assert res.is_truncated is True
        assert res.original_len == 100000
        assert "[TRUNCATED: Showing first 1,000 of 100,000 characters." in res.text

    def test_archive_inspection(self, tmp_path):
        import zipfile
        zip_path = tmp_path / "bundle.zip"
        with zipfile.ZipFile(zip_path, "w") as z:
            z.writestr("zezo_engine.py", "print('hello')")
            z.writestr("config.json", '{"key": "value"}')
            
        res = read_file(zip_path)
        assert res.file_type == "archive"
        assert "zezo_engine.py" in res.text
        assert "config.json" in res.text

    def test_background_file_processor_summary_payload(self, tmp_path):
        from actions.file_processor import file_processor
        from core.task_manager import get_task_manager
        import time

        test_doc = tmp_path / "resume.txt"
        test_doc.write_text("Hamza Bukhari - Full Stack Developer & AI Engineer with React and FastAPI.", encoding="utf-8")

        tm = get_task_manager()
        msg = file_processor({"file_path": str(test_doc), "action": "summarize"})
        assert "background task queue" in msg

        # Wait for background task to complete
        start = time.time()
        done_tasks = []
        while time.time() - start < 10.0:
            done_tasks = tm.get_categorized_tasks().get("done", [])
            if done_tasks:
                break
            time.sleep(0.5)

        assert len(done_tasks) > 0
        latest = done_tasks[0]
        res = latest.get("result", {})
        assert isinstance(res, dict)
        assert "summary" in res
        assert len(res["summary"]) > 0

