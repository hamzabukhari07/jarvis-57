"""
Phase 3 Verification Test Suite: Groq Background LLM Router Migration
Tests:
1. actions/youtube_video.py text summarization via core.llm_router
2. actions/flight_finder.py JSON parsing via core.llm_router
3. actions/file_processor.py text summarization via core.llm_router
4. actions/dev_agent.py project file planning via core.llm_router
5. Provider fallback ladder validation (Groq -> Gemini -> Ollama)
"""

import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import core.llm_router as llm_router
import actions.youtube_video as youtube_video
import actions.flight_finder as flight_finder
import actions.file_processor as file_processor
import actions.dev_agent as dev_agent


class TestPhase3GroqMigrationSuite(unittest.TestCase):

    @patch("core.llm_client.call_groq_text")
    @patch("memory.config_manager.get_groq_api_key", return_value="gsk_dummy_test_key")
    def test_youtube_summarization_routes_to_groq(self, mock_key, mock_groq):
        mock_groq.return_value = "Sir, this is a concise test summary generated via Groq LPU."
        
        summary = youtube_video._summarize_with_gemini("This is a long video transcript...", "https://youtube.com/watch?v=123")
        self.assertIn("Groq LPU", summary)
        mock_groq.assert_called_once()

    @patch("core.llm_client.call_groq_text")
    @patch("memory.config_manager.get_groq_api_key", return_value="gsk_dummy_test_key")
    def test_flight_finder_parsing_routes_to_groq(self, mock_key, mock_groq):
        mock_groq.return_value = '[{"airline": "Emirates", "departure": "10:00", "arrival": "14:00", "duration": "4h", "stops": 0, "price": "$450", "currency": "USD"}]'
        
        flights = flight_finder._parse_flights_with_gemini("Sample Google Flights web text", "DXB", "LHR", "2026-11-01")
        self.assertEqual(len(flights), 1)
        self.assertEqual(flights[0]["airline"], "Emirates")
        self.assertEqual(flights[0]["price"], "$450")
        mock_groq.assert_called_once()

    @patch("core.llm_client.call_groq_text")
    @patch("memory.config_manager.get_groq_api_key", return_value="gsk_dummy_test_key")
    def test_file_processor_text_doc_routes_to_groq(self, mock_key, mock_groq):
        mock_groq.return_value = "Document Analysis: Key points extracted successfully via Groq."
        
        client = file_processor._gemini_client()
        resp = client.generate_content("Analyze this document content text.")
        self.assertIn("Groq", resp.text)
        mock_groq.assert_called_once()

    @patch("core.llm_client.call_groq_text")
    @patch("memory.config_manager.get_groq_api_key", return_value="gsk_dummy_test_key")
    def test_dev_agent_plan_routes_to_groq(self, mock_key, mock_groq):
        mock_groq.return_value = '{"project_name": "test_app", "entry_point": "main.py", "files": [{"path": "main.py", "description": "Entry", "imports": []}], "run_command": "python main.py", "dependencies": []}'
        
        plan = dev_agent._plan_project("Create a test project", "python")
        self.assertEqual(plan["project_name"], "test_app")
        self.assertEqual(plan["entry_point"], "main.py")
        mock_groq.assert_called_once()

    @patch("core.llm_client.call_groq_text", side_effect=Exception("Groq rate limit exceeded"))
    @patch("core.gemini.text", return_value="Gemini fallback response text")
    @patch("memory.config_manager.get_groq_api_key", return_value="gsk_dummy_test_key")
    def test_llm_router_graceful_fallback_to_gemini(self, mock_key, mock_gemini, mock_groq):
        output = llm_router.generate_text("Test query with failing Groq")
        self.assertEqual(output, "Gemini fallback response text")
        mock_gemini.assert_called_once()


if __name__ == "__main__":
    unittest.main()
