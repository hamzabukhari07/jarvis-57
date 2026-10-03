"""
tests/test_temporal_prompt_suite.py — Temporal Prompt Gating & Local Time Directives Unit Tests.

Lead Architect: Hamza Bukhari
Project: ZEZO (Autonomous Desktop AI Operating System v2)
"""

import pytest
from pathlib import Path
from datetime import datetime


class TestTemporalPromptSuite:
    def test_prompt_file_contains_temporal_gating(self):
        prompt_path = Path("core/prompt.txt")
        assert prompt_path.exists(), "core/prompt.txt must exist"
        text = prompt_path.read_text(encoding="utf-8")

        assert "[TEMPORAL CONTEXT & LOCAL TIME" in text
        assert "[SYSTEM LOCAL DATE & TIME]" in text
        assert "NEVER call web_search" in text
        assert "today's date" in text
        assert "under 0.2s" in text

    def test_prompt_tokens_integrity(self):
        prompt_path = Path("core/prompt.txt")
        text = prompt_path.read_text(encoding="utf-8")

        for token in ("{assistant_name}", "{platform}", "{capabilities}", "{limits}"):
            assert token in text, f"Required prompt token {token} missing from prompt.txt"

    def test_local_time_formatting_contract(self):
        now = datetime.now()
        time_str = now.strftime("%A, %B %d, %Y — %I:%M:%S %p (%H:%M 24h)")
        assert str(now.year) in time_str
        assert now.strftime("%B") in time_str
        assert now.strftime("%A") in time_str
