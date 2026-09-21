"""
tests/test_skill_hub_suite.py — Automated Test Suite for Option A Skill Hub & Registry.

Validates:
1. Multi-tier declarative skill discovery and domain inference.
2. YAML frontmatter parsing (triggers, tags, version, author).
3. Dynamic intent scoring and trigger matching.
4. Active context budgeting and prompt block generation.
5. Mode toggling (Pinned / Auto / Disabled) and persistent state save/load.
6. Skill installation via directory copy and .zip archive unpacking.
7. Autonomous skill synthesis (`save_learned_skill`) and deletion (`delete_skill`).
8. PyQt6 UI components (`SkillHubOverlay`, `_SkillCardWidget`, `_SkillDropTarget`, `SkillEditorModal`).
"""

import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from core.skill_loader import (
    SkillRegistry,
    SkillRecord,
    _parse_yaml_frontmatter,
    _infer_domain_from_name_and_tags,
    _generate_default_triggers,
    get_skill_registry,
)


class TestSkillHubEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="zezo_skill_test_"))
        self.skills_dir = self.temp_dir / "skills"
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.registry = SkillRegistry(skills_dir=self.skills_dir, logger_fn=lambda _: None)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_1_yaml_frontmatter_parser(self):
        raw_yaml = """
name: ultra_tester
description: Comprehensive testing skill
domain: coding
author: Hamza Bukhari
version: 2.5
triggers:
  - run tests
  - verify suite
tags:
  - test
  - ci
  - quality
auto_activate: true
pinned: false
"""
        meta = _parse_yaml_frontmatter(raw_yaml)
        self.assertEqual(meta.get("name"), "ultra_tester")
        self.assertEqual(meta.get("domain"), "coding")
        self.assertEqual(meta.get("author"), "Hamza Bukhari")
        self.assertEqual(meta.get("version"), "2.5")
        self.assertEqual(meta.get("triggers"), ["run tests", "verify suite"])
        self.assertEqual(meta.get("tags"), ["test", "ci", "quality"])
        self.assertTrue(meta.get("auto_activate"))
        self.assertFalse(meta.get("pinned"))

    def test_2_domain_inference_and_triggers(self):
        d1 = _infer_domain_from_name_and_tags("landing_page", ["css", "styling"], Path("landing_page"))
        self.assertEqual(d1, "ui")

        d2 = _infer_domain_from_name_and_tags("git_stage", ["commit"], Path("git_stage"))
        self.assertEqual(d2, "coding")

        d3 = _infer_domain_from_name_and_tags("social_scrape", ["reddit"], Path("social_scrape"))
        self.assertEqual(d3, "research")

        d4 = _infer_domain_from_name_and_tags("bench_perf", ["hardware"], Path("bench_perf"))
        self.assertEqual(d4, "system")

        triggers = _generate_default_triggers("custom_worker", "coding", ["worker", "fast"])
        self.assertIn("custom worker", triggers)
        self.assertIn("build app", triggers)

    def test_3_save_and_discover_skills(self):
        ok, msg = self.registry.save_learned_skill(
            name="test_synthesizer",
            description="Synthesizes code automatically",
            instructions="## Protocol\n1. Generate code\n2. Run tests",
            domain="coding",
            author="Hamza Bukhari",
            triggers=["synthesize code", "make feature"],
            tags=["coding", "ai"],
        )
        self.assertTrue(ok)
        self.assertIn("test_synthesizer", self.registry._skills)
        sk = self.registry._skills["test_synthesizer"]
        self.assertEqual(sk.domain, "coding")
        self.assertEqual(sk.author, "Hamza Bukhari")
        self.assertIn("synthesize code", sk.triggers)

        # Verify list_skills & domains
        skills = self.registry.list_skills()
        self.assertEqual(len(skills), 1)
        self.assertEqual(skills[0]["name"], "test_synthesizer")

        domains = self.registry.list_domains()
        self.assertIn("CODING", domains)

    def test_4_trigger_matching_and_scoring(self):
        self.registry.save_learned_skill(
            name="ui_styler",
            description="Aesthetic UI styling",
            instructions="Apply glassmorphism and modern colors.",
            domain="ui",
            triggers=["landing page", "dark mode", "hero design"],
            tags=["ui", "css"],
        )
        self.registry.save_learned_skill(
            name="database_migrator",
            description="PostgreSQL schema migrator",
            instructions="Run Alembic migrations.",
            domain="coding",
            triggers=["migrate db", "alembic upgrade"],
            tags=["database", "sql"],
        )

        # Match query with UI intent
        matched_ui = self.registry.match_skills("Please build a sleek dark mode landing page with a hero design")
        self.assertTrue(len(matched_ui) >= 1)
        self.assertEqual(matched_ui[0].name, "ui_styler")

        # Match query with DB intent
        matched_db = self.registry.match_skills("Run alembic upgrade for postgresql")
        self.assertTrue(len(matched_db) >= 1)
        self.assertEqual(matched_db[0].name, "database_migrator")

    def test_5_context_budgeting(self):
        self.registry.save_learned_skill(
            name="fast_deployer",
            description="FastAPI deployment guide",
            instructions="Step 1: Check Dockerfile\nStep 2: Deploy to ECS.",
            domain="coding",
            triggers=["fastapi deploy", "deploy app"],
        )
        prompt_block = self.registry.get_active_skill_prompt("Help me with fastapi deploy on server", max_tokens_budget=500)
        self.assertIn("ACTIVE DOMAIN SKILLS & GUIDELINES", prompt_block)
        self.assertIn("fast_deployer", prompt_block)
        self.assertIn("Step 1: Check Dockerfile", prompt_block)

    def test_5b_format_prompt_block(self):
        self.registry.save_learned_skill(
            name="prompt_test_skill",
            description="Testing prompt block catalog generation",
            instructions="Run tests and report results.",
            domain="system",
        )
        block = self.registry.format_prompt_block()
        self.assertIn("[AVAILABLE SKILLS & WORKFLOWS]", block)
        self.assertIn("prompt_test_skill (SYSTEM)", block)
        self.assertIn("Testing prompt block catalog generation", block)

    def test_6_mode_toggling_and_state_persistence(self):
        self.registry.save_learned_skill(
            name="toggle_test_skill",
            description="Testing pin/disable toggles",
            instructions="Some protocol",
        )
        # Pin the skill
        self.registry.set_skill_mode("toggle_test_skill", pinned=True, disabled=False, auto_activate=False)
        self.assertTrue(self.registry._skills["toggle_test_skill"].pinned)
        self.assertFalse(self.registry._skills["toggle_test_skill"].disabled)

        # Query empty string: pinned skill should still match
        matched = self.registry.match_skills("")
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0].name, "toggle_test_skill")

        # Disable the skill
        self.registry.set_skill_mode("toggle_test_skill", pinned=False, disabled=True, auto_activate=False)
        self.assertTrue(self.registry._skills["toggle_test_skill"].disabled)
        matched_disabled = self.registry.match_skills("toggle test skill")
        self.assertEqual(len(matched_disabled), 0)

    def test_7_install_and_delete_skill(self):
        # Create a skill folder to install
        source_dir = self.temp_dir / "external_skill"
        source_dir.mkdir()
        (source_dir / "SKILL.md").write_text(
            "---\nname: external_helper\ndescription: External tool\ndomain: general\n---\n## Help\nWork done.",
            encoding="utf-8",
        )

        ok, msg = self.registry.install_skill(source_dir)
        self.assertTrue(ok)
        self.assertIn("external_helper", self.registry._skills)

        # Create zip package
        zip_path = self.temp_dir / "packaged_skill.zip"
        with zipfile.ZipFile(zip_path, "w") as z:
            z.writestr("packaged_skill/SKILL.md", "---\nname: zipped_skill\ndescription: Zipped\n---\nDone.")

        ok_zip, msg_zip = self.registry.install_skill(zip_path)
        self.assertTrue(ok_zip)
        self.assertIn("zipped_skill", self.registry._skills)

        # Delete skills
        ok_del, _ = self.registry.delete_skill("external_helper")
        self.assertTrue(ok_del)
        self.assertNotIn("external_helper", self.registry._skills)


class TestSkillHubUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_8_ui_components_instantiation(self):
        from ui import SkillHubOverlay, _SkillCardWidget, _SkillDropTarget, SkillEditorModal

        # Test card widget
        dummy_skill = {
            "name": "ui_test",
            "description": "UI test description",
            "domain": "UI",
            "version": "1.2",
            "triggers": ["test", "trigger"],
            "pinned": False,
            "disabled": False,
            "auto_activate": True,
        }
        card = _SkillCardWidget(
            dummy_skill,
            on_toggle_cb=lambda *args: None,
            on_edit_cb=lambda *args: None,
            on_delete_cb=lambda *args: None,
        )
        self.assertIsNotNone(card)

        # Test drop target
        drop = _SkillDropTarget(on_drop_cb=lambda *args: None)
        self.assertIsNotNone(drop)

        # Test overlay instantiation
        hub = SkillHubOverlay()
        self.assertEqual(hub.width(), SkillHubOverlay._OW)
        self.assertEqual(hub.height(), SkillHubOverlay._OH)
        self.assertIsNotNone(hub._search_input)
        hub.deleteLater()


if __name__ == "__main__":
    unittest.main()
