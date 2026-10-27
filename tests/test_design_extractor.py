"""
tests/test_design_extractor.py — Unit & Integration tests for core/design_extractor.py
"""

from pathlib import Path
import pytest

from core.design_extractor import (
    DEFAULT_SVG_PLACEHOLDER,
    strip_base64_images,
    extract_keyframes,
    generate_blueprint_html,
    extract_design_system_from_html,
)


def test_strip_base64_images():
    raw_html = '<div style="background: url(\'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=\');"><img src="data:image/jpeg;base64,/9j/4AAQSkZJRg=="></div>'
    stripped = strip_base64_images(raw_html)
    assert DEFAULT_SVG_PLACEHOLDER in stripped
    assert "iVBORw0KGgo" not in stripped
    assert "/9j/4AAQSkZJRg==" not in stripped


def test_extract_keyframes():
    css = """
    @keyframes floatEffect {
      0% { transform: translateY(0); }
      50% { transform: translateY(-10px); }
      100% { transform: translateY(0); }
    }
    @-webkit-keyframes spinGlow {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }
    """
    kf = extract_keyframes(css)
    assert "floatEffect" in kf
    assert "spinGlow" in kf
    assert "translateY(-10px)" in kf["floatEffect"]


def test_generate_blueprint_html_size_and_tokens(tmp_path):
    sample_html = """<!DOCTYPE html>
    <html>
      <head>
        <style>
          :root {
            --bg: #0b0f19;
            --surface: #111827;
            --accent: #3b82f6;
            --text-primary: #f9fafb;
            --text-secondary: #9ca3af;
            --border: #1f2937;
            --font-display: "Clash Display", sans-serif;
          }
          @keyframes glowPulse {
            0%, 100% { opacity: 0.8; }
            50% { opacity: 1; }
          }
        </style>
      </head>
      <body>
        <h1>Enterprise Cloud Platform</h1>
      </body>
    </html>
    """
    bp = generate_blueprint_html(sample_html, title="Enterprise Cloud")
    assert "<!DOCTYPE html>" in bp
    assert "Enterprise Cloud" in bp
    assert ":root {" in bp
    assert "--bg: #0b0f19;" in bp
    assert "--accent: #3b82f6;" in bp
    assert "@keyframes glowPulse" in bp
    assert len(bp.encode("utf-8")) < 25000

    out_file = tmp_path / "blueprint.html"
    bp2 = generate_blueprint_html(sample_html, title="Saved Blueprint", output_path=out_file)
    assert out_file.exists()
    assert out_file.read_text(encoding="utf-8") == bp2


def test_extract_design_system_backward_compatibility():
    ref_files = list(Path("skills/website_build/references").rglob("*.html"))
    if not ref_files:
        pytest.skip("No reference templates found on disk")
    sample_ref = ref_files[0]
    md = extract_design_system_from_html(sample_ref)
    assert "---" in md
    assert "colors:" in md
    assert "typography:" in md
    assert "rounded:" in md
