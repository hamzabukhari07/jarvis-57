"""
tests/test_antigravity_optimizations.py — Runtime verification for Antigravity speed and sanitization fixes.

Creator & Lead Architect: Hamza Bukhari
"""
from pathlib import Path
import tempfile
import shutil

from core.url_prefetch import _clean_html_dom
from core.antigravity_runner import _tree_snapshot
from core.undo import capture_repo_snapshot


def test_dom_sanitizer_preserves_svg_geometry_and_strips_scripts():
    sample_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
    <script>window.__NEXT_DATA__ = {"huge": "hydration data"};</script>
    <noscript><iframe src="https://www.googletagmanager.com"></iframe></noscript>
</head>
<body>
    <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==" />
    <svg viewBox="0 0 24 24" class="w-6 h-6 text-blue-500" width="24" height="24">
        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" fill="currentColor" />
    </svg>
    <div class="hero">Hello World</div>
</body>
</html>
"""
    cleaned = _clean_html_dom(sample_html)
    assert "<script" not in cleaned
    assert "<noscript" not in cleaned
    assert "data:image/placeholder" in cleaned
    assert 'viewBox="0 0 24 24"' in cleaned
    assert 'class="w-6 h-6 text-blue-500"' in cleaned
    assert "<!-- SVG paths omitted for brevity -->" in cleaned
    assert "Hello World" in cleaned


def test_skip_lists_ignore_heavy_assets():
    test_dir = Path(tempfile.mkdtemp(prefix="zezo_opt_test_"))
    try:
        code_file = test_dir / "index.html"
        code_file.write_text("<h1>Test</h1>", encoding="utf-8")
        asset_dir = test_dir / "assets"
        asset_dir.mkdir()
        asset_file = asset_dir / "logo.png"
        asset_file.write_bytes(b"PNG_DATA" * 50)

        snap = _tree_snapshot(test_dir)
        assert "index.html" in snap
        assert not any("assets" in k for k in snap.keys())

        undo_snap = capture_repo_snapshot(test_dir)
        assert "index.html" in undo_snap
        assert not any("assets" in k for k in undo_snap.keys())
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == "__main__":
    test_dom_sanitizer_preserves_svg_geometry_and_strips_scripts()
    test_skip_lists_ignore_heavy_assets()
    print("All optimization runtime tests passed!")
