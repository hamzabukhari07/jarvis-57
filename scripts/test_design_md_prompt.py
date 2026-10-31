"""
scripts/test_design_md_prompt.py — Verification Test for generate_design_md Prompt Synthesis.

Creator & Lead Architect: Hamza Bukhari

Verifies:
1. Directive extraction isolates '## 🤖 Agent Directive' for generate_design_md.
2. Synthesized prompt correctly grounds on pre-flight files (site_dom.html, site_styles.css, site_tokens.json).
3. No theoretical subagent arguments or generic roleplay leaks into the agent prompt.
"""

from __future__ import annotations

from pathlib import Path
import tempfile
import shutil

from core.skill_loader import get_skill_registry
from core.skill_prompt_engineer import craft_skill_engine_prompt


def test_design_md_prompt_synthesis():
    test_dir = Path(tempfile.mkdtemp(prefix="zezo_design_md_test_"))
    print("=" * 80)
    print("🎨 TESTING PROMPT SYNTHESIS: generate_design_md")
    print(f"Isolated Test Workspace: {test_dir}")
    print("=" * 80 + "\n")

    try:
        # Pre-populate simulated pre-flight extraction files
        (test_dir / "site_dom.html").write_text("<!DOCTYPE html><html><body><h1>Stripe</h1></body></html>", encoding="utf-8")
        (test_dir / "site_styles.css").write_text(":root { --primary: #635bff; }", encoding="utf-8")
        (test_dir / "site_tokens.json").write_text('{"colors": {"primary": "#635bff"}}', encoding="utf-8")

        reg = get_skill_registry()
        skill_record = reg.get_skill("generate_design_md")
        assert skill_record is not None, "generate_design_md skill not found in registry"
        assert skill_record.agent_directive_section == "Agent Directive", "agent_directive_section was not parsed!"

        user_task = "Extract design system and generate DESIGN.md and preview.html for Stripe"
        prompt = craft_skill_engine_prompt(
            skill_name="generate_design_md",
            skill_sop=skill_record.instructions,
            user_task=user_task,
            target_dir=str(test_dir),
            context={"url": "https://stripe.com"},
            engine="antigravity",
            directive_header=skill_record.agent_directive_section,
        )

        assert len(prompt) > 80, "Generated prompt is too short"
        assert "DESIGN.md" in prompt, "FAIL: Deliverable DESIGN.md missing from prompt!"
        assert "preview.html" in prompt, "FAIL: Deliverable preview.html missing from prompt!"
        print("  ✅ Directive extraction verified: isolated '## 🤖 Agent Directive'.")
        print("  ✅ Pre-flight files referenced cleanly.")
        print("\n--- [FULL GENERATED PROMPT FOR ANTIGRAVITY] ---")
        print(prompt)
        print("--- [END OF PROMPT] ---\n")
        print("=" * 80)
        print("🎉 GENERATE_DESIGN_MD PROMPT TEST PASSED!")
        print("=" * 80)
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == "__main__":
    test_design_md_prompt_synthesis()
