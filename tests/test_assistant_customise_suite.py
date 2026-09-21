import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest
from memory.config_manager import (
    get_assistant_name, save_assistant_config,
    get_voice, save_voice,
    get_response_language, save_response_language,
    AVAILABLE_VOICES, AVAILABLE_LANGUAGES,
)
from core.ui_server import ZezoUIServer


class TestAssistantCustomiseSuite(unittest.TestCase):
    def test_1_config_persistence(self):
        # Save and verify
        orig_name = get_assistant_name()
        from memory.config_manager import get_user_name
        orig_user = get_user_name()
        orig_voice = get_voice()
        orig_lang = get_response_language()

        try:
            save_assistant_config("ZEZO-TEST", orig_user)
            self.assertEqual(get_assistant_name(), "ZEZO-TEST")

            save_voice("Fenrir")
            self.assertEqual(get_voice(), "Fenrir")

            save_response_language("English")
            self.assertEqual(get_response_language(), "English")

            save_response_language("Urdu")
            self.assertEqual(get_response_language(), "Urdu")
        finally:
            save_assistant_config(orig_name, orig_user)
            save_voice(orig_voice)
            save_response_language(orig_lang)

    def test_2_voice_assets_exist(self):
        voices_dir = Path(__file__).resolve().parent.parent / "frontend" / "assets" / "voices"
        for v in ["puck", "charon", "kore", "fenrir", "aoede"]:
            mp3_file = voices_dir / f"{v}.mp3"
            self.assertTrue(mp3_file.exists(), f"Voice preview file {mp3_file} missing")
            self.assertGreater(mp3_file.stat().st_size, 1000, f"Voice preview file {mp3_file} empty")

    def test_3_prompt_language_directive(self):
        from main import _render_prompt
        template = "Protocol: [LANGUAGE]\n{language_directive}\n[END]"

        # English
        lang_dir = (
            "STRICT FIXED RESPONSE LANGUAGE DIRECTIVE:\n"
            "- You MUST ALWAYS speak and reply to the user in English, regardless of what language the user speaks in."
        )
        rendered = _render_prompt(template, {"language_directive": lang_dir})
        self.assertIn("STRICT FIXED RESPONSE LANGUAGE DIRECTIVE", rendered)
        self.assertIn("English", rendered)

    def test_4_initial_state_contains_voice_and_lang(self):
        server = ZezoUIServer()
        state = server._build_initial_state()
        self.assertIn("voice_name", state)
        self.assertIn("response_language", state)
        self.assertIn("assistant_name", state)


if __name__ == "__main__":
    unittest.main()
