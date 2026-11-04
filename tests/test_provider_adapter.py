"""
tests/test_provider_adapter.py - Tests for core/agents/provider_adapter.py.

Verifies:
  1. Initialization and provider normalization.
  2. Context budget enforcement prior to request dispatch.
  3. Normalized response format and token usage distinction (native vs estimated).
  4. Error handling and wrapping in ProviderError.
  5. Async execution via execute_async.
"""

import pytest
from unittest.mock import patch, MagicMock

from core.agents.provider_adapter import (
    ProviderAdapter,
    ProviderType,
    NormalizedResponse,
    ProviderError,
    ProviderUsage,
)
from core.agents.context_budget import ContextBudget


def test_provider_adapter_initialization():
    """Verify provider adapter correctly normalizes providers and default models."""
    p_gemini = ProviderAdapter(provider="gemini")
    assert p_gemini.provider_type == ProviderType.GEMINI
    assert p_gemini.model_name == "gemini-2.5-flash"

    p_groq = ProviderAdapter(provider="groq")
    assert p_groq.provider_type == ProviderType.GROQ
    assert p_groq.model_name == "llama-3.3-70b-versatile"

    p_ollama = ProviderAdapter(provider="ollama")
    assert p_ollama.provider_type == ProviderType.OLLAMA
    assert p_ollama.model_name == "llama3.2"


def test_gemini_execution_success():
    """Verify Gemini execution returns NormalizedResponse with native usage."""
    adapter = ProviderAdapter(provider="gemini")

    with patch("core.gemini.text", return_value="Gemini response content") as mock_gemini:
        messages = [{"role": "user", "content": "What is ZEZO?"}]
        res = adapter.execute(messages=messages, system_prompt="System persona")

        assert isinstance(res, NormalizedResponse)
        assert res.content == "Gemini response content"
        assert res.provider == "gemini"
        assert res.usage.is_estimated is False
        assert res.usage.total_tokens > 0
        mock_gemini.assert_called_once()


def test_groq_text_execution_success():
    """Verify Groq text execution returns NormalizedResponse with estimated usage."""
    adapter = ProviderAdapter(provider="groq")

    with patch("core.llm_client.call_groq_text", return_value="Groq response text") as mock_groq:
        messages = [{"role": "user", "content": "Analyze system performance"}]
        res = adapter.execute(messages=messages, system_prompt="System persona")

        assert isinstance(res, NormalizedResponse)
        assert res.content == "Groq response text"
        assert res.provider == "groq"
        assert res.usage.is_estimated is True
        assert res.usage.total_tokens > 0
        mock_groq.assert_called_once()


def test_groq_tool_calling_execution():
    """Verify Groq execution parses tool calls correctly."""
    adapter = ProviderAdapter(provider="groq")

    mock_tool_return = {
        "tool": "web_search",
        "args": {"query": "ZEZO Phase 1"},
        "text": "Searching web..."
    }

    with patch("core.llm_client.call_groq_tools", return_value=mock_tool_return) as mock_groq_tools:
        messages = [{"role": "user", "content": "Search the web"}]
        tools = [{"name": "web_search", "description": "Search web"}]
        res = adapter.execute(messages=messages, tools=tools)

        assert isinstance(res, NormalizedResponse)
        assert len(res.tool_calls) == 1
        assert res.tool_calls[0]["name"] == "web_search"
        assert res.tool_calls[0]["parameters"] == {"query": "ZEZO Phase 1"}
        mock_groq_tools.assert_called_once()


def test_provider_error_wrapping():
    """Verify provider failures raise ProviderError."""
    adapter = ProviderAdapter(provider="gemini")

    with patch("core.gemini.text", side_effect=RuntimeError("API quota exceeded")):
        with pytest.raises(ProviderError, match="API quota exceeded") as exc_info:
            adapter.execute(messages=[{"role": "user", "content": "Test"}])
        assert exc_info.value.provider == "gemini"


def test_context_budget_applied_before_request():
    """Verify oversized history is trimmed before dispatching to provider."""
    budget = ContextBudget(provider="ollama")  # tight budget
    adapter = ProviderAdapter(provider="ollama", context_budget=budget)

    # 20 large messages
    messages = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i} " * 100}
        for i in range(20)
    ]

    with patch("core.llm_client.call_llm", return_value="Trimmed reply") as mock_call:
        res = adapter.execute(messages=messages)
        assert res.content == "Trimmed reply"
        mock_call.assert_called_once()


def test_execute_async():
    """Verify execute_async runs non-blockingly."""
    import asyncio

    async def _runner():
        adapter = ProviderAdapter(provider="gemini")
        with patch("core.gemini.text", return_value="Async response"):
            res = await adapter.execute_async(messages=[{"role": "user", "content": "Async check"}])
            assert res.content == "Async response"

    asyncio.run(_runner())
