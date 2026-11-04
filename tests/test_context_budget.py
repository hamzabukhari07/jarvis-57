"""
tests/test_context_budget.py - Tests for core/agents/context_budget.py.

Verifies:
  1. Gemini native token counting vs proxy estimation.
  2. 20% safety margin calculation on effective history budgets.
  3. Deterministic self-consistency for repeated inputs.
  4. Tool output truncation exceeding model ceilings.
  5. Rolling summary triggers based on turn count.
  6. History trimming respecting effective token budget limits.
"""

import pytest
from core.agents.context_budget import ContextBudget, BUDGET_SPECS


def test_gemini_native_token_counting():
    """Verify Gemini budget configuration and mock client native counting."""
    class MockGeminiClient:
        class models:
            @staticmethod
            def count_tokens(model, contents):
                class Resp:
                    total_tokens = 42
                return Resp()

    budget = ContextBudget(model_name="gemini-2.5-flash", provider="gemini", gemini_client=MockGeminiClient())
    count = budget.count_tokens("Hello world system prompt")
    assert count == 42
    # 0% safety margin for native Gemini -> effective budget equals nominal budget (12,000)
    assert budget.get_effective_budget() == 12_000


def test_groq_proxy_token_counting_with_safety_buffer():
    """Verify Groq applies a 20% safety margin to nominal budget."""
    budget = ContextBudget(model_name="llama-3.3-70b-versatile", provider="groq")
    # Nominal is 8,000 -> 8000 * (1 - 0.20) = 6,400
    assert budget.get_effective_budget() == 6_400
    assert budget.get_tool_output_ceiling() == 2_400


def test_ollama_proxy_token_counting_with_safety_buffer():
    """Verify Ollama applies a 20% safety margin to nominal budget."""
    budget = ContextBudget(model_name="llama3.2", provider="ollama")
    # Nominal is 2,500 -> 2500 * (1 - 0.20) = 2,000
    assert budget.get_effective_budget() == 2_000
    assert budget.get_tool_output_ceiling() == 800


def test_token_counting_self_consistency():
    """Verify token counting is deterministic for identical inputs."""
    budget = ContextBudget(model_name="llama-3.3-70b-versatile", provider="groq")
    sample_text = "Detailed code block with symbols: def test(): return [x for x in range(10)]"
    c1 = budget.count_tokens(sample_text)
    c2 = budget.count_tokens(sample_text)
    assert c1 == c2
    assert c1 > 0


def test_tool_output_truncation_under_ceiling():
    """Verify tool output exceeding ceiling is truncated with clear notification."""
    budget = ContextBudget(model_name="llama-3.3-70b-versatile", provider="groq")
    ceiling = budget.get_tool_output_ceiling()

    # Generate oversized payload
    oversized = "line of detailed output data\n" * 5000
    assert budget.count_tokens(oversized) > ceiling

    truncated = budget.truncate_tool_output(oversized)
    assert len(truncated) < len(oversized)
    assert f"[Output truncated at ~{ceiling} tokens. Request specific sections for details.]" in truncated


def test_rolling_summary_turn_trigger():
    """Verify turn count triggers rolling summary according to spec."""
    budget = ContextBudget(provider="groq")
    trigger = budget.spec.rolling_summary_turn_trigger  # 12
    assert budget.should_summarize(10) is False
    assert budget.should_summarize(12) is False
    assert budget.should_summarize(13) is True


def test_history_trimming_preserves_recent_turns():
    """Verify history trimming drops oldest turns while preserving recent turn context."""
    budget = ContextBudget(provider="ollama")  # effective budget = 2000 tokens

    # Build 20 messages with considerable content
    messages = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"Turn {i}: " + ("data " * 150)}
        for i in range(20)
    ]
    trimmed = budget.trim_history(messages)
    assert len(trimmed) < len(messages)
    assert len(trimmed) >= 2
    # The last 2 messages must be preserved
    assert trimmed[-1]["content"] == messages[-1]["content"]
    assert trimmed[-2]["content"] == messages[-2]["content"]

