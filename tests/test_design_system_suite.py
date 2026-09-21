"""
tests/test_design_system_suite.py — 6 Comprehensive Verification Tests for Hamza Taste 3.0 & Antigravity.

Runs automated verification across:
  1. Explicit Reference Match (Saas)
  2. Multi-word & Fuzzy Reference Match (Dub, Aura Frame)
  3. Session Memory & Persistent Memory Awareness
  4. Semantic Category Routing (Dashboard, AI Agent, Media, OS)
  5. Autonomous Agent Choice on Generic Prompts
  6. Real Gemini Prompt Formatting & Voice Feedback Integration
"""

import os
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from core.design_resolver import (
    is_ui_task,
    resolve_design,
    format_design_prompt,
    ResolvedDesign,
)
from actions.antigravity_agent import antigravity_action


class TestDesignSystemSuite(unittest.TestCase):

    def test_1_explicit_reference_match(self):
        """Test 1: Explicit Reference Match (e.g. saas)."""
        res = resolve_design("Build a modern SaaS landing page with dark theme")
        self.assertTrue(res.is_active())
        self.assertIn("Saas", res.source_name)
        self.assertIn("colors:", res.design_spec)
        self.assertIn("components:", res.design_spec)
        self.assertIn("ANTI-SLOP", res.anti_slop_rules)
        print(f"  [PASS] Test 1: Explicit Match -> {res.source_name} ({res.source_type})")

    def test_2_multiword_fuzzy_reference_match(self):
        """Test 2: Multi-word & Fuzzy Reference Match (e.g. dub landing page, aura frame)."""
        res_dub = resolve_design("Create an interface inspired by dub landing page")
        self.assertTrue(res_dub.is_active())
        self.assertIn("dub", res_dub.source_name.lower())

        res_aura = resolve_design("Build aura frame component")
        self.assertTrue(res_aura.is_active())
        self.assertIn("aura", res_aura.source_name.lower())
        print(f"  [PASS] Test 2: Fuzzy Match -> Dub: {res_dub.source_name}, Aura: {res_aura.source_name}")

    def test_3_session_memory_awareness(self):
        """Test 3: Session Memory & Persistent Memory Awareness."""
        fake_session = {"active_design_path": "skills/hamza_taste/references/design md/Aura-Frame-DESIGN.md"}
        res = resolve_design("Build the hero section", session_memory=fake_session)
        self.assertTrue(res.is_active())
        self.assertIn("Aura", res.source_name)

        fake_session_name = {"active_design": "saas"}
        res_name = resolve_design("Build the pricing cards", session_memory=fake_session_name)
        self.assertTrue(res_name.is_active())
        self.assertIn("Saas", res_name.source_name)
        print(f"  [PASS] Test 3: Session Memory -> Path: {res.source_name}, Name: {res_name.source_name}")

    def test_4_semantic_category_routing(self):
        """Test 4: Semantic Category Routing across 13 HTML Reference Templates."""
        # Dashboard -> Standalone Ecosystem
        res_dash = resolve_design("Build an admin analytics ecosystem platform")
        self.assertTrue(res_dash.is_active())
        self.assertIn("Ecosystem", res_dash.source_name)

        # AI Agent -> autonomus
        res_ai = resolve_design("Build an autonomous bot assistant UI")
        self.assertTrue(res_ai.is_active())
        self.assertIn("Autonomus", res_ai.source_name)

        # Media / Art -> image gen
        res_media = resolve_design("Build a photo gallery generator app")
        self.assertTrue(res_media.is_active())
        self.assertIn("Image", res_media.source_name)

        # Hardware / Tech -> nexus
        res_nexus = resolve_design("Build a futuristic matrix hardware app")
        self.assertTrue(res_nexus.is_active())
        self.assertIn("Nexus", res_nexus.source_name)
        print(f"  [PASS] Test 4: Semantic Routes -> Dash: {res_dash.source_name}, AI: {res_ai.source_name}, Media: {res_media.source_name}, Tech: {res_nexus.source_name}")

    def test_5_autonomous_agent_choice(self):
        """Test 5: Autonomous Agent Choice on Generic Prompts."""
        res_gen = resolve_design("Build a website")
        self.assertTrue(res_gen.is_active())
        self.assertIn("reference_autonomous", res_gen.source_type)
        self.assertTrue(any(c in res_gen.source_name.lower() for c in ("saas", "dub", "aura", "crazy", "nami", "autonomus", "image")))
        print(f"  [PASS] Test 5: Autonomous Agent Choice -> {res_gen.source_name} ({res_gen.source_type})")

    def test_6_prompt_formatting_and_voice_feedback(self):
        """Test 6: Real Gemini Prompt Formatting & Voice Feedback Integration."""
        res = resolve_design("Build a SaaS landing page")
        prompt_block = format_design_prompt(res)
        
        self.assertTrue("MASTER RAW HTML REFERENCE TEMPLATE" in prompt_block or "MASTER DESIGN SYSTEM SPECIFICATION" in prompt_block)
        self.assertIn("MANDATORY AESTHETIC DIRECTIVE", prompt_block)
        self.assertIn("Purple/Indigo Gradients", prompt_block)
        self.assertIn("Unstyled Native Controls", prompt_block)
        
        from core.task_manager import get_task_manager
        tm = get_task_manager()
        with tm._lock:
            tm._tasks.clear()
            tm._coding_queue.clear()

        voice_resp = antigravity_action(
            {"task": "Build a SaaS landing page", "project_path": "Desktop/website"}
        )
        self.assertIn("ZEZO Coder task start ho gaya hai", voice_resp)
        self.assertIn("Saas", voice_resp)
        print(f"  [PASS] Test 6: Prompt & Voice -> Output: {voice_resp[:90]}...")

    def test_10_raw_html_injection_in_prompt(self):
        """Test 10: Verify that raw HTML content from reference templates is loaded and injected."""
        res = resolve_design("Build a modern SaaS landing page")
        self.assertTrue(res.is_active())
        self.assertTrue(len(res.raw_html) > 100)
        self.assertIn("<html", res.raw_html.lower())
        prompt_block = format_design_prompt(res)
        self.assertIn("MASTER RAW HTML REFERENCE TEMPLATE", prompt_block)
        self.assertIn("```html", prompt_block)
        print(f"  [PASS] Test 10: Raw HTML Injection -> Loaded {len(res.raw_html)} chars of pure HTML into prompt.")



    def test_7_existing_repo_preservation(self):
        """Test 7: Verify that existing repository design is extracted and preserved."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            index_file = tmp_path / "index.html"
            index_file.write_text("""<!DOCTYPE html>
<html>
<head>
  <style>
    :root {
      --bg: #1e1b4b;
      --text: #ffffff;
      --accent: #ec4899;
    }
    body { background-color: var(--bg); color: var(--text); font-family: Inter; }
  </style>
</head>
<body>
  <header class="hero"><h1>Custom Hero Title</h1></header>
</body>
</html>""", encoding="utf-8")
            
            res = resolve_design("Add 5 sections to the landing page", repo_path=tmp_path)
            self.assertTrue(res.is_active())
            self.assertEqual(res.source_type, "project_existing")
            self.assertIn("Project", res.source_name)
            self.assertIn("#1e1b4b", res.design_spec)
            print(f"  [PASS] Test 7: Existing Repo Preservation -> {res.source_name} ({res.source_type})")

    def test_8_redesign_intent_overrides_existing_repo(self):
        """Test 8: Verify that explicit redesign/theme change requests override project_existing."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            index_file = tmp_path / "index.html"
            index_file.write_text("<html><body><h1>Old Real Estate Page</h1></body></html>", encoding="utf-8")

            # 1. User asks to change design using Saas-DESIGN
            res_saas = resolve_design(
                "Change the design of the real estate landing page. Using Saas-DESIGN.md reference, update color theme and styling.",
                repo_path=tmp_path,
            )
            self.assertTrue(res_saas.is_active())
            self.assertIn("saas", res_saas.source_name.lower())
            self.assertNotEqual(res_saas.source_type, "project_existing")

            # 2. User asks to regenerate with Dub design
            res_dub = resolve_design(
                "Regenerate the landing page with dub design theme",
                repo_path=tmp_path,
            )
            self.assertTrue(res_dub.is_active())
            self.assertIn("dub", res_dub.source_name.lower())
            self.assertNotEqual(res_dub.source_type, "project_existing")
            print(f"  [PASS] Test 8: Redesign Intent Overrides Existing -> Saas: {res_saas.source_name}, Dub: {res_dub.source_name}")

    def test_9_diverse_domain_and_generic_scenarios(self):
        """Test 9: Test real estate, creative agency, and generic landing page routing."""
        # Real Estate -> Dub landing page (warm, conversion-oriented)
        res_re = resolve_design("Build a modern real estate landing page with property listings")
        self.assertTrue(res_re.is_active())
        self.assertIn("dub", res_re.source_name.lower())

        # Creative Agency -> Crazy UI landing page
        res_agency = resolve_design("Build a creative design agency showcase portfolio")
        self.assertTrue(res_agency.is_active())
        self.assertIn("crazy", res_agency.source_name.lower())

        # Completely generic landing page (variety autonomous choice)
        res_generic = resolve_design("Build a nice landing page for my company")
        self.assertTrue(res_generic.is_active())
        self.assertEqual(res_generic.source_type, "reference_autonomous")
        print(f"  [PASS] Test 9: Diverse Domains -> RealEstate: {res_re.source_name}, Agency: {res_agency.source_name}, Generic: {res_generic.source_name}")


    def test_11_extract_design_system_url(self):
        """Test 11: Verify URL extraction support in extract_design_system action."""
        import tempfile
        from unittest.mock import patch, MagicMock
        from actions.design_extractor import extract_design_action

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "Qwenpaw-DESIGN.md"
            mock_html = """<!DOCTYPE html>
<html>
<head>
  <style>
    :root {
      --primary: #6366f1;
      --bg: #0f172a;
      --text: #f8fafc;
    }
    body { background-color: var(--bg); color: var(--text); font-family: Inter; }
  </style>
</head>
<body>
  <header><h1>QwenPaw Agent Framework</h1></header>
</body>
</html>"""
            mock_response = MagicMock()
            mock_response.read.return_value = mock_html.encode("utf-8")
            mock_response.__enter__.return_value = mock_response

            with patch("urllib.request.urlopen", return_value=mock_response):
                resp = extract_design_action({
                    "file_path": "https://qwenpaw.agentscope.io/",
                    "output_path": str(out_file),
                })
                self.assertIn("successfully extracted", resp)
                self.assertTrue(out_file.exists())
                content = out_file.read_text(encoding="utf-8")
                self.assertIn("colors:", content)
                self.assertIn("#0f172a", content)
                print(f"  [PASS] Test 11: Live URL Extraction -> Saved to {out_file.name}")


if __name__ == "__main__":
    print("\n[RUNNING] Hamza Taste 3.0 & Antigravity 11-Test Suite...\n" + "=" * 60)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDesignSystemSuite)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        sys.exit(1)
    print("\n[SUCCESS] All 11 Design System & Antigravity Verification Tests Passed!\n")

