import pytest
from pathlib import Path
from core.skill_prompt_engineer import craft_skill_engine_prompt, _generate_blueprint_fallback

def test_fallback_prompt_generation_zero_hardcoding():
    """Verify fallback prompt contains zero hardcoded DESIGN.md or ghost files."""
    fallback = _generate_blueprint_fallback(
        skill_name="custom_task_runner",
        skill_sop="Follow best practices for building an analytics dashboard.",
        user_task="Build a lightweight analytics chart in Python using matplotlib",
        target_dir="C:/Users/Hamza Bukhari/Desktop/non_existent_test_dir",
        engine="antigravity",
    )
    assert "DESIGN.md" not in fallback
    assert "site_dom.html" not in fallback
    assert "preview-dark.html" not in fallback
    assert "matplotlib" in fallback or "analytics chart" in fallback

def test_live_ai_synthesis_groq_grounding():
    """Verify Groq LPU synthesizes natural prompt without ghost file declarations."""
    test_dir = Path("C:/Users/Hamza Bukhari/Desktop/test_fresh_workspace_123")
    test_dir.mkdir(parents=True, exist_ok=True)
    try:
        synthesized = craft_skill_engine_prompt(
            skill_name="generate_design_md",
            skill_sop="Analyze the styling and produce DESIGN.md and preview.html.",
            user_task="Create a design system specification for context.dev",
            target_dir=str(test_dir),
            context={"url": "https://www.context.dev/"},
            engine="antigravity",
        )
        assert len(synthesized) > 100
        assert "preview-dark.html" not in synthesized
        # When folder is empty, prompt must instruct fetching or creating, not claim files already exist
        assert "Treat the following files as the sole source of truth" not in synthesized
    finally:
        if test_dir.exists():
            try:
                test_dir.rmdir()
            except Exception:
                pass
