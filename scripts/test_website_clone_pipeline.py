"""
scripts/test_website_clone_pipeline.py — End-to-End Pipeline Verification Test for website_clone.

Creator & Lead Architect: Hamza Bukhari

Verifies:
1. Pre-flight asset capture executes properly and verifies files on disk.
2. Master directive section from skills/website_clone/SKILL.md is isolated cleanly without CLI leak.
3. AntiGravity action receives project_path=target_dir pointing to the folder with files present.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch


def test_website_clone_pipeline_e2e():
    test_dir = Path(tempfile.mkdtemp(prefix="zezo_clone_pipeline_test_"))
    print("=" * 80)
    print("🚀 TESTING END-TO-END PIPELINE: website_clone")
    print(f"Isolated Test Directory: {test_dir}")
    print("=" * 80 + "\n")

    try:
        # ── Step 1: Pre-Flight Ingestion Execution ───────────────────────────
        print("[Step 1] Testing actions/uncage_capture_handler.py execution...")
        from actions.uncage_capture_handler import execute as execute_uncage

        with patch("actions.website_cloner.run_uncage_exporter") as mock_exporter:
            def fake_export(url: str, output_dir: Path, **kwargs):
                out = Path(output_dir)
                out.mkdir(parents=True, exist_ok=True)
                (out / "index.html").write_text("<!DOCTYPE html><html><body><h1>Linear Clone Test</h1></body></html>", encoding="utf-8")
                (out / "asset-map.json").write_text('{"assets": []}', encoding="utf-8")
                (out / "assets").mkdir(exist_ok=True)
                (out / "assets" / "style.css").write_text("body { background: #000; color: #fff; }", encoding="utf-8")
                return True, "Capture complete"

            mock_exporter.side_effect = fake_export

            ok = execute_uncage(url="https://linear.app", output_dir=test_dir)
            assert ok is True, "uncage_capture_handler.execute returned False"
            assert (test_dir / "index.html").exists(), "index.html was not written to disk"
            assert (test_dir / "asset-map.json").exists(), "asset-map.json was not written to disk"
            assert (test_dir / "assets" / "style.css").exists(), "assets/style.css was not written to disk"
            print("  ✅ Pre-flight capture succeeded. Files verified physically on disk.")

        # ── Step 2: Grounded Prompt Synthesis & Directive Extraction ─────────
        print("\n[Step 2] Testing master directive extraction & disk-grounded prompt...")
        from core.skill_loader import get_skill_registry
        from core.skill_prompt_engineer import craft_skill_engine_prompt

        reg = get_skill_registry()
        skill_record = reg.get_skill("website_clone")
        assert skill_record is not None, "website_clone skill not found in registry"

        user_task = "Clone https://linear.app and produce a clean single-file raw HTML rebuild"
        prompt = craft_skill_engine_prompt(
            skill_name="website_clone",
            skill_sop=skill_record.instructions,
            user_task=user_task,
            target_dir=str(test_dir),
            context={"url": "https://linear.app"},
            engine="antigravity",
            directive_header=skill_record.agent_directive_section,
        )

        assert len(prompt) > 80, "Generated prompt is too short"
        assert "node tools/uncage" not in prompt, "FAIL: Uncage bash CLI leaked into agent prompt!"
        assert "npm install" not in prompt, "FAIL: npm CLI leaked into agent prompt!"
        assert "HTML" in prompt or "website" in prompt.lower()
        print("  ✅ Prompt synthesis verified: Pure reverse-engineering directive generated (0 CLI leaks).")
        print(f"  Snippet: {prompt[:180]}...")

        # ── Step 3: Run Skill Orchestrator Contract ──────────────────────────
        print("\n[Step 3] Testing actions/run_skill.py orchestrator dispatch...")
        from actions.run_skill import handler as run_skill_handler

        with patch("actions.antigravity_agent.antigravity_action") as mock_agy:
            mock_agy.return_value = "Mock AntiGravity Task Dispatched"
            res = run_skill_handler({
                "skill_name": "website_clone",
                "task": user_task,
                "project_path": str(test_dir),
                "direct": True,
            })

            assert mock_agy.called, "antigravity_action was never invoked by run_skill!"
            call_params = mock_agy.call_args[0][0]
            assert call_params["project_path"] == str(test_dir), f"Wrong project_path: {call_params['project_path']}"
            assert call_params["task"] == user_task, f"Wrong task: {call_params['task']}"
            print("  ✅ AntiGravity dispatch contract verified: exact project_path received with files present.")
            print(f"  Result: {res}")

        print("\n" + "=" * 80)
        print("🎉 ALL END-TO-END WEBSITE CLONE PIPELINE CHECKS PASSED!")
        print("=" * 80)
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == "__main__":
    test_website_clone_pipeline_e2e()
