import unittest
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from memory.config_manager import save_response_language, get_response_language
from core.action_loader import discover_actions
from core.ui_server import get_ui_server

class TestLanguageAndMuteFix(unittest.TestCase):
    def test_response_language_config(self):
        save_response_language("English")
        self.assertEqual(get_response_language(), "English")
        
        save_response_language("Urdu")
        self.assertEqual(get_response_language(), "Urdu")
        
        save_response_language("English")
        self.assertEqual(get_response_language(), "English")

    def test_ui_server_initial_state(self):
        srv = get_ui_server()
        state = srv._build_initial_state()
        self.assertIn("response_language", state)
        self.assertIn("muted", state)
        self.assertIn("sleeping", state)
        self.assertEqual(state["response_language"], "English")

    def test_prompt_language_directive(self):
        # When English is configured:
        save_response_language("English")
        resp_lang = get_response_language()
        if resp_lang.lower() == "auto":
            lang_dir = "- Spoken Language: Match the user's language naturally. If they speak Urdu, reply in natural Urdu. If English, reply in natural English."
        else:
            lang_dir = (
                f"- Spoken Language Strict Enforcement: You MUST ALWAYS speak and reply exclusively in {resp_lang}. "
                f"Even if the user speaks to you in Urdu, Hindi, Spanish, or any other language, you MUST understand their intent but deliver your spoken response exclusively in {resp_lang}. "
                f"NEVER switch languages unless the user explicitly commands you to change your language (e.g. \"speak in Urdu\" or \"switch to Hindi\")."
            )
        self.assertIn("exclusively in English", lang_dir)
        self.assertIn("NEVER switch languages", lang_dir)

    def test_action_loader_discovery(self):
        registry = discover_actions(repo_root / "actions")
        self.assertGreaterEqual(len(registry._actions), 20)

if __name__ == "__main__":
    unittest.main()
