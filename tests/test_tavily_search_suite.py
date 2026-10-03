"""
tests/test_tavily_search_suite.py
Comprehensive unit and integration tests for Tavily AI search, Groq synthesis,
and multi-tier search fallback ladder in ZEZO OS.
"""
import json
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

from actions import web_search
from memory import config_manager


class TestTavilySearchSuite(unittest.TestCase):

    def test_validate_tavily_key_format_check(self):
        """Short or empty Tavily keys fail immediate pre-flight validation."""
        ok, err = config_manager.validate_tavily_key("")
        self.assertFalse(ok)
        self.assertIn("Invalid", err)

        ok, err = config_manager.validate_tavily_key("short")
        self.assertFalse(ok)

    def test_masked_tavily_key(self):
        """Tavily key is masked securely."""
        with patch("memory.config_manager.load_api_keys", return_value={"tavily_api_key": "tvly-abcdef1234567890"}):
            masked = config_manager.get_masked_tavily_key()
            self.assertTrue(masked.startswith("tvly-"))
            self.assertIn("••••••••••••", masked)
            self.assertTrue(masked.endswith("7890"))

    def test_save_api_keys_transactional_tavily_key(self):
        """Transactional save updates tavily_api_key."""
        mock_data = {}
        with patch("memory.config_manager.load_api_keys", return_value=mock_data), \
             patch("memory.config_manager._atomic_write_config") as mock_write, \
             patch("memory.config_manager.validate_tavily_key", return_value=(True, "Tavily API key is valid")):
            ok, msg = config_manager.save_api_keys_transactional(tavily_api_key="tvly-mockvalidkey12345678", validate=True)
            self.assertTrue(ok)
            self.assertEqual(mock_data.get("tavily_api_key"), "tvly-mockvalidkey12345678")
            mock_write.assert_called_once()

    @patch("urllib.request.urlopen")
    def test_tavily_search_direct_success(self, mock_urlopen):
        """Tavily search returns formatted list on HTTP 200."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps({
            "answer": "Zezo is an autonomous OS.",
            "results": [
                {
                    "title": "Zezo Project",
                    "content": "Zezo is created by Hamza Bukhari.",
                    "url": "https://example.com/zezo",
                    "score": 0.98,
                }
            ]
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        with patch("memory.config_manager.get_tavily_api_key", return_value="tvly-mockkey12345"):
            res = web_search._tavily_search("what is zezo", search_depth="basic", max_results=3)
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0]["title"], "Zezo Project")
            self.assertEqual(res[0]["answer"], "Zezo is an autonomous OS.")

            formatted = web_search._format_tavily("what is zezo", res)
            self.assertIn("Summary: Zezo is an autonomous OS.", formatted)
            self.assertIn("Zezo Project", formatted)

    @patch("actions.web_search._tavily_search")
    @patch("actions.web_search._gemini_search")
    @patch("actions.web_search._ddg_search")
    def test_multi_tier_fallback_ladder(self, mock_ddg, mock_gemini, mock_tavily):
        """Hierarchy: Tavily (Tier 1) -> Gemini (Tier 2) -> DuckDuckGo (Tier 3)."""
        # Scenario 1: Tavily Succeeds
        mock_tavily.return_value = [{"title": "Tavily Title", "snippet": "Tavily Content", "url": "https://tavily.com"}]
        out = web_search._search("query 1")
        self.assertIn("Tavily Title", out)
        mock_gemini.assert_not_called()
        mock_ddg.assert_not_called()

        # Scenario 2: Tavily Empty, Gemini Succeeds
        mock_tavily.return_value = []
        mock_gemini.return_value = "Gemini Grounded Answer"
        out = web_search._search("query 2")
        self.assertEqual(out, "Gemini Grounded Answer")
        mock_ddg.assert_not_called()

        # Scenario 3: Tavily Empty, Gemini Fails -> DDG Fallback
        mock_tavily.return_value = []
        mock_gemini.side_effect = RuntimeError("Quota exhausted")
        mock_ddg.return_value = [{"title": "DDG Title", "snippet": "DDG Content", "url": "https://ddg.com"}]
        out = web_search._search("query 3")
        self.assertIn("DDG Title", out)

    @patch("actions.web_search._tavily_search")
    @patch("core.llm_client.call_groq_text")
    def test_research_groq_synthesis(self, mock_groq_call, mock_tavily):
        """Research mode uses Groq LPU to synthesize raw excerpts."""
        mock_tavily.return_value = [{"title": "Tavily Source", "snippet": "Key technical details", "url": "https://source.com"}]
        mock_groq_call.return_value = "Synthesized Groq Briefing on quantum computing."

        with patch("memory.config_manager.get_groq_api_key", return_value="gsk_mockgroq123"):
            out = web_search._research("quantum computing")
            self.assertEqual(out, "Synthesized Groq Briefing on quantum computing.")
            mock_groq_call.assert_called_once()


if __name__ == "__main__":
    unittest.main()
