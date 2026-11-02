from core import clipboard_watcher


def test_current_clipboard_payload(monkeypatch):
    class MockClipboard:
        @staticmethod
        def paste():
            return "https://example.com"

    monkeypatch.setattr(clipboard_watcher, "_PYPERCLIP", True)
    monkeypatch.setattr(clipboard_watcher, "pyperclip", MockClipboard())

    payload = clipboard_watcher.ClipboardWatcher().get_current_payload()

    assert payload["text"] == "https://example.com"
    assert payload["type"] == "url"
    assert payload["preview"] == "https://example.com"
    assert payload["timestamp"] > 0
