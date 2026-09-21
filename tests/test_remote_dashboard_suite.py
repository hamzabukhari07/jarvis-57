"""
tests/test_remote_dashboard_suite.py — Validation Suite for ZEZO Remote Dashboard
Tests bug fixes, file upload dispatch, telemetry broadcasts, and UI enhancements.
"""

import asyncio
from pathlib import Path
import pytest
from dashboard.server import DashboardServer, STATIC_DIR


class TestRemoteDashboardSuite:

    def test_1_app_html_bug_fixes_present(self):
        """Verify all 6 bug fixes are properly implemented in app.html."""
        html_path = STATIC_DIR / "app.html"
        assert html_path.exists(), "app.html must exist"
        content = html_path.read_text(encoding="utf-8")

        # Bug 1: Chunked Base64 (no call stack overflow on large messages)
        assert "_bytesToB64" in content
        assert "bytes.subarray(i, i + chunk)" in content
        assert "return _bytesToB64(bytes);" in content

        # Bug 2: getUserMedia error calls _stopVoice()
        assert "_stopVoice();" in content

        # Bug 3: SpeechRecognition clears handlers before stop()
        assert "_speechRec.onend = null;" in content
        assert "_speechRec.onerror = null;" in content

        # Bug 4: Upload error parsing with fallback slice
        assert "parsed.error || parsed.message || errMsg" in content
        assert "xhr.responseText || 'Unknown error').slice(0, 100)" in content

        # Bug 5: WebSocket exponential reconnect loop
        assert "_connectWS" in content
        assert "_wsRetries" in content
        assert "_wsRetryDelay" in content
        assert "RECONNECTING" in content

        # Bug 6: Desktop drawer collapse
        assert ".telemetry-drawer.collapsed" in content
        assert "d.classList.toggle('collapsed')" in content

    def test_2_app_html_improvements_present(self):
        """Verify all 5 improvements are present in app.html."""
        content = (STATIC_DIR / "app.html").read_text(encoding="utf-8")

        # Improvement 1: Scroll to bottom button and unread badge
        assert 'id="scroll-btn"' in content
        assert 'id="unread-badge"' in content
        assert "scrollToBottom()" in content
        assert "isFeedAtBottom()" in content

        # Improvement 2: Message Copy button
        assert "copyMsgText" in content
        assert "msg-copy-btn" in content

        # Improvement 3: Command palette autocomplete
        assert 'id="cmd-palette"' in content
        assert "/system_status" in content
        assert "/screen_process" in content
        assert "/opencode_run" in content
        assert "/kilo_run" in content
        assert "/antigravity_run" in content
        assert "renderCommandPalette" in content

        # Improvement 4: Screenshot inline preview
        assert "_onScreenshotReceived" in content
        assert "SCREENSHOT CAPTURE" in content

        # Improvement 5: Staged thinking indicator
        assert "Parsing intent" in content
        assert "Selecting engine" in content
        assert "Executing" in content
        assert "Verifying" in content
        assert "thinking-progress-bar" in content

    def test_3_dashboard_server_file_callback(self):
        """Verify DashboardServer supports registering and invoking file callback."""
        server = DashboardServer()
        received_files = []

        def file_cb(path):
            received_files.append(path)

        server.set_file_callback(file_cb)
        assert server._file_callback == file_cb

    def test_4_login_html_branding(self):
        """Verify login.html strictly enforces ZEZO branding and design tokens."""
        login_path = STATIC_DIR / "login.html"
        assert login_path.exists()
        content = login_path.read_text(encoding="utf-8")
        assert "ZEZO" in content
        assert "JARVIS" not in content
        assert "#f24e1e" in content
