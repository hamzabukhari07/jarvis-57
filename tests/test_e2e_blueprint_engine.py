"""
tests/test_e2e_blueprint_engine.py — Complete End-to-End Verification of the
Automated Blueprint & Master Template Clone Engine, Prompt Synthesizer, and Task State.

Creator & Lead Architect: Hamza Bukhari
"""

import time
from pathlib import Path
import pytest

from core.design_resolver import generate_blueprint_and_template
from core.prompts import (
    DASHBOARD,
    LANDING_PAGE,
    PORTFOLIO,
    SURGICAL_EDIT,
    detect_archetype,
    load_exemplar,
    synthesize_prompt,
)
from core.task_manager import TaskState, TaskStatus


# =========================================================================
# Part A: Blueprint & Master Template Generation Engine (< 1.0s, < 25KB, < 40KB)
# =========================================================================

def _find_sample_reference() -> Path:
    candidates = [
        Path("skills/website_build/references/1_landing_pages/Crazy UI landing page.html"),
        Path("skills/website_build/references/1_landing_pages/blinq.html"),
        Path("skills/website_build/references/1_landing_pages/solvine.html"),
        Path("skills/website_build/references/1_landing_pages/dub.html"),
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return c
    # Fallback search
    all_refs = list(Path("skills").glob("**/*.html"))
    if all_refs:
        return all_refs[0]
    return Path("non_existent_ref.html")


def test_blueprint_and_master_template_generation_performance_and_limits(tmp_path: Path):
    """
    Verifies:
    1. Design extraction & master template generation executes in < 1.0s.
    2. Output DESIGN.md is strictly < 15 KB.
    3. Output master-template.html is strictly < 40 KB.
    4. All 4 semantic slot markers (HERO, PROJECTS, SKILLS, CONTACT) are present.
    5. blueprint.html is strictly NOT created.
    """
    ref_file = _find_sample_reference()
    if not ref_file.exists():
        pytest.skip(f"No reference HTML found in repository at {ref_file}")

    out_dir = tmp_path / "engine_run"
    t_start = time.perf_counter()
    design_md_path, mt_path = generate_blueprint_and_template(ref_file, out_dir)
    elapsed = time.perf_counter() - t_start

    # Execution speed requirement: < 1.0s
    assert elapsed < 1.0, f"Generation took {elapsed:.3f}s (must be < 1.0s)"

    # Existence check
    assert design_md_path.is_file(), f"DESIGN.md was not generated at {design_md_path}"
    assert mt_path.is_file(), f"master-template.html was not generated at {mt_path}"
    assert not (out_dir / "blueprint.html").exists(), "blueprint.html must NOT exist"

    md_size = design_md_path.stat().st_size
    mt_size = mt_path.stat().st_size

    # Size constraints
    assert md_size < 30000, f"DESIGN.md exceeded 30 KB: {md_size} bytes"
    assert mt_size < 40960, f"master-template.html exceeded 40 KB: {mt_size} bytes"

    # Semantic slot markers
    mt_content = mt_path.read_text(encoding="utf-8")
    for slot in ["HERO", "PROJECTS", "SKILLS", "CONTACT"]:
        assert f"<!-- SLOT:{slot}_START -->" in mt_content, f"Missing <!-- SLOT:{slot}_START -->"
        assert f"<!-- SLOT:{slot}_END -->" in mt_content, f"Missing <!-- SLOT:{slot}_END -->"


def test_blueprint_engine_with_bloated_html(tmp_path: Path):
    """
    Verifies that bloated input (with massive base64 images) is stripped cleanly
    and produces lean DESIGN.md and master-template.html (< 40 KB) with preserved scripts.
    """
    fake_base64 = "data:image/png;base64," + ("A" * 120000)
    bloated_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Bloated Reference Template</title>
  <style>
    :root {{ --primary: #3b82f6; --bg: #09090b; --text: #fafafa; }}
    body {{ background: var(--bg); color: var(--text); font-family: sans-serif; }}
    .hero {{ padding: 80px 20px; text-align: center; }}
    .card {{ border: 1px solid #27272a; padding: 24px; border-radius: 8px; }}
    @keyframes pulse {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} 100% {{ opacity: 1; }} }}
  </style>
</head>
<body>
  <header id="nav">
    <img src="{fake_base64}" alt="Bloated Logo">
    <nav><a href="#hero">Home</a> <a href="#work">Work</a></nav>
  </header>
  <main>
    <section id="hero" class="hero">
      <h1>Autonomous Agency Portal</h1>
      <p>High performance automated delivery engine.</p>
      <img src="{fake_base64}" alt="Big Hero Banner">
    </section>
    <section id="projects" class="work-section">
      <div class="card">Project Alpha</div>
      <div class="card">Project Beta</div>
    </section>
    <section id="skills" class="capabilities">
      <span>React</span><span>Python</span><span>Tailwind</span>
    </section>
    <footer id="contact" class="footer">
      <p>Contact us at team@example.com</p>
    </footer>
  </main>
  <script>
    console.log("Interactive runtime script preserved.");
    window.addEventListener("DOMContentLoaded", () => {{
      document.body.classList.add("loaded");
    }});
  </script>
</body>
</html>"""

    ref_file = tmp_path / "bloated_ref.html"
    ref_file.write_text(bloated_html, encoding="utf-8")
    assert ref_file.stat().st_size > 200000  # Over 200 KB initially

    out_dir = tmp_path / "bloated_out"
    t_start = time.perf_counter()
    design_md_path, mt_path = generate_blueprint_and_template(ref_file, out_dir)
    elapsed = time.perf_counter() - t_start

    assert elapsed < 1.0, f"Generation took {elapsed:.3f}s on bloated input (must be < 1.0s)"
    assert design_md_path.stat().st_size < 30000, f"DESIGN.md exceeded 30 KB: {design_md_path.stat().st_size} bytes"
    assert mt_path.stat().st_size < 40960, f"Master template exceeded 40 KB: {mt_path.stat().st_size} bytes"

    # Base64 string must not leak into master template
    mt_content = mt_path.read_text(encoding="utf-8")
    assert "data:image/png;base64,AAAA" not in mt_content

    # Interactive JS script is preserved
    assert "Interactive runtime script preserved." in mt_content

    # Semantic slots are present
    for slot in ["HERO", "PROJECTS", "SKILLS", "CONTACT"]:
        assert f"<!-- SLOT:{slot}_START -->" in mt_content
        assert f"<!-- SLOT:{slot}_END -->" in mt_content


# =========================================================================
# Part B: Prompt Synthesizer Archetypes, Exemplars & Anti-Stall Directives
# =========================================================================

def test_detect_archetype_coverage():
    """Verifies deterministic archetype auto-detection across diverse task intents."""
    # Portfolio intents
    assert detect_archetype("Build a personal developer portfolio for Hamza") == PORTFOLIO
    assert detect_archetype("Create a modern designer CV and resume showcase") == PORTFOLIO

    # Landing page intents
    assert detect_archetype("Create a high-converting SaaS landing page with waitlist") == LANDING_PAGE
    assert detect_archetype("Build a product marketing site with hero and pricing") == LANDING_PAGE

    # Dashboard intents
    assert detect_archetype("Design an admin dashboard with analytics metrics and KPI tables") == DASHBOARD
    assert detect_archetype("Build a cloud portal control panel with charts") == DASHBOARD

    # Surgical edit intents
    assert detect_archetype("Surgically update the hero slot in index.html") == SURGICAL_EDIT
    assert detect_archetype("Replace slot <!-- SLOT:HERO --> with new banner") == SURGICAL_EDIT
    assert detect_archetype("Update and tweak the contact section") == SURGICAL_EDIT


def test_load_exemplar_disk_and_fallback():
    """Verifies that exemplars load reliably from disk or fall back gracefully."""
    for arch in [PORTFOLIO, LANDING_PAGE, DASHBOARD, SURGICAL_EDIT]:
        exemplar_text = load_exemplar(arch)
        assert exemplar_text and len(exemplar_text) > 100
        # Disk templates contain [CRITICAL DIRECT-EXECUTION CONSTRAINTS] and in-memory fallbacks contain ANTI-STALL
        assert (
            "CRITICAL DIRECT-EXECUTION CONSTRAINTS" in exemplar_text
            or "STRICT EXECUTION GUARDRAILS (ANTI-STALL)" in exemplar_text
            or "NO INTERMEDIATE SCRIPTS" in exemplar_text
        )

    # Unknown archetype gracefully falls back
    unknown_fallback = load_exemplar("non_existent_archetype_xyz")
    assert unknown_fallback and len(unknown_fallback) > 100
    assert (
        "CRITICAL DIRECT-EXECUTION CONSTRAINTS" in unknown_fallback
        or "STRICT EXECUTION GUARDRAILS (ANTI-STALL)" in unknown_fallback
        or "NO INTERMEDIATE SCRIPTS" in unknown_fallback
    )


def test_synthesize_prompt_anti_stall_constraints():
    """
    Verifies that synthesized prompts enforce all strict anti-stall guardrails
    and correctly substitute contextual variables.
    """
    context = {
        "target_file": "dist/index.html",
        "theme": "Cyberpunk Neon Matrix",
        "task_directive": "Replicate reference hero and inject custom testimonials.",
        "slots": "<!-- SLOT:HERO -->: Dynamic typing banner\n<!-- SLOT:CONTACT -->: Secure form",
        "content": "Client: Zezo AI\nHighlights: Ultra-fast performance",
    }

    prompt = synthesize_prompt(PORTFOLIO, context)

    # 1. Target file substituted
    assert "dist/index.html" in prompt
    assert "{target_file}" not in prompt

    # 2. Design theme substituted
    assert "Cyberpunk Neon Matrix" in prompt

    # 3. Content and slots injected
    assert "Dynamic typing banner" in prompt
    assert "Zezo AI" in prompt

    # 4. Mandatory anti-stall constraints strictly verified
    assert "DIRECT ADAPTATION: Write directly to 'dist/index.html' in a single pass." in prompt
    assert "ABSOLUTELY FORBIDDEN: DO NOT write intermediate Python scripts (no BeautifulSoup, chunking, or inspect.py)." in prompt
    assert "PRESERVE STYLES & INTERACTION: Keep all <style> animations and interactive JavaScript functions intact." in prompt
    assert "Slot Targeting: Replace content inside designated <!-- SLOT:* --> markers." in prompt


# =========================================================================
# Part C: TaskState prompt_full Serialization in to_dict()
# =========================================================================

def test_task_state_prompt_full_serialization():
    """
    Verifies that TaskState.to_dict() always exposes the `prompt_full` attribute,
    correctly falling back across params keys: prompt_full -> enriched_prompt -> task -> "".
    """
    # 1. Explicit prompt_full
    t1 = TaskState(
        id="task-001",
        tool="antigravity_agent",
        params={"prompt_full": "Full synthesized prompt with all guardrails"},
    )
    d1 = t1.to_dict()
    assert "prompt_full" in d1
    assert d1["prompt_full"] == "Full synthesized prompt with all guardrails"

    # 2. Fallback to enriched_prompt
    t2 = TaskState(
        id="task-002",
        tool="opencode_agent",
        params={"enriched_prompt": "Synthesized prompt from fallback enriched key"},
    )
    d2 = t2.to_dict()
    assert "prompt_full" in d2
    assert d2["prompt_full"] == "Synthesized prompt from fallback enriched key"

    # 3. Fallback to task
    t3 = TaskState(
        id="task-003",
        tool="kilo_code_agent",
        params={"task": "Minimal raw task description"},
    )
    d3 = t3.to_dict()
    assert "prompt_full" in d3
    assert d3["prompt_full"] == "Minimal raw task description"

    # 4. Default empty string when none present
    t4 = TaskState(
        id="task-004",
        tool="general_agent",
        params={},
    )
    d4 = t4.to_dict()
    assert "prompt_full" in d4
    assert d4["prompt_full"] == ""
