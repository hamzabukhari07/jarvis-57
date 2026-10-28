"""
tests/test_design_resolver_blueprint.py — Unit & Integration tests for
Automated Blueprint & Master Template Generation Engine in core/design_resolver.py
"""

from pathlib import Path
import pytest
import time

from core.design_resolver import generate_blueprint_and_template
from core.master_template_builder import inject_semantic_slots


def test_inject_semantic_slots_presence():
    sample_html = """<!DOCTYPE html>
    <html>
      <head><title>Test Page</title></head>
      <body>
        <header class="hero-header"><h1>Hero Section</h1></header>
        <section id="portfolio" class="projects"><div>Project 1</div></section>
        <section id="about" class="skills-section"><div>About & Skills</div></section>
        <footer id="footer" class="contact"><div>Contact info</div></footer>
      </body>
    </html>"""

    slotted = inject_semantic_slots(sample_html)
    for slot in ["HERO", "PROJECTS", "SKILLS", "CONTACT"]:
        assert f"<!-- SLOT:{slot}_START -->" in slotted
        assert f"<!-- SLOT:{slot}_END -->" in slotted


def test_generate_blueprint_and_template_execution(tmp_path):
    sample_ref = Path("skills/website_build/references/1_landing_pages/Crazy UI landing page.html")
    if not sample_ref.exists():
        sample_ref = Path("skills/website_build/references/1_landing_pages/blinq.html")
    if not sample_ref.exists():
        pytest.skip("Reference template not found")

    out_dir = tmp_path / "saas_build"
    t0 = time.perf_counter()
    design_md, mt = generate_blueprint_and_template(sample_ref, out_dir)
    dt = time.perf_counter() - t0

    assert design_md.exists()
    assert mt.exists()
    assert design_md.name == "DESIGN.md"
    assert mt.name == "master-template.html"
    assert not (out_dir / "blueprint.html").exists(), "blueprint.html must NOT be generated"

    md_size = design_md.stat().st_size
    mt_size = mt.stat().st_size
    assert md_size < 30000, f"DESIGN.md exceeded 30 KB: {md_size} bytes"
    assert mt_size < 40960, f"Master template exceeded 40 KB: {mt_size} bytes"
    assert dt < 1.0, f"First generation took too long: {dt:.3f}s (must be < 1.0s)"

    # Verify DESIGN.md has <design-context> DSL
    md_content = design_md.read_text(encoding="utf-8")
    assert "<design-context>" in md_content
    assert "</design-context>" in md_content
    assert "colors:" in md_content
    assert "typography:" in md_content
    assert "rounded:" in md_content

    # Verify master-template.html slots
    mt_content = mt.read_text(encoding="utf-8")
    for slot in ["HERO", "PROJECTS", "SKILLS", "CONTACT"]:
        assert f"<!-- SLOT:{slot}_START -->" in mt_content
        assert f"<!-- SLOT:{slot}_END -->" in mt_content

    # Second run: Verify cache hit is instant (< 0.1s)
    out_dir_2 = tmp_path / "saas_build_2"
    t1 = time.perf_counter()
    design_md_2, mt_2 = generate_blueprint_and_template(sample_ref, out_dir_2)
    dt_cache = time.perf_counter() - t1

    assert design_md_2.exists()
    assert mt_2.exists()
    assert dt_cache < 0.1, f"Cached retrieval took too long: {dt_cache:.3f}s (must be < 0.1s)"

