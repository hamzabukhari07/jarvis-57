"""
tests/test_design_extractor.py — Unit & Integration tests for core/design_extractor.py
"""

from pathlib import Path
import pytest

from core.design_extractor import (
    DEFAULT_SVG_PLACEHOLDER,
    strip_base64_images,
    extract_keyframes,
    extract_design_tokens,
    extract_design_system_from_html,
)
from core.design_md_generator import generate_design_md
from core.master_template_builder import build_master_template


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


def test_generate_design_md_and_master_template(tmp_path):
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
    tokens = extract_design_tokens(sample_html, name="Enterprise Cloud")
    md = generate_design_md(tokens, name="Enterprise Cloud")
    mt = build_master_template(sample_html, tokens)

    assert "<design-context>" in md
    assert "Enterprise Cloud" in md
    assert "colors:" in md
    assert len(md.encode("utf-8")) < 30000

    assert "<!DOCTYPE html>" in mt
    assert "Enterprise Cloud Platform" in mt
    assert len(mt.encode("utf-8")) < 40000

    md_file = tmp_path / "DESIGN.md"
    mt_file = tmp_path / "master-template.html"
    md_file.write_text(md, encoding="utf-8")
    mt_file.write_text(mt, encoding="utf-8")
    assert md_file.exists()
    assert mt_file.exists()
    assert not (tmp_path / "blueprint.html").exists()


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
