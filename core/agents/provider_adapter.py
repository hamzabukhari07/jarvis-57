"""
core/agents/provider_adapter.py - Unified LLM Provider Adapter.

Provides a unified interface across Gemini, Groq, and Ollama/Local LLMs.
Normalizes requests, responses, tool calls, error states, and token usage metadata.

Key Invariants:
  1. Context budgets are checked and enforced before executing LLM requests.
  2. Clearly distinguishes native token counts from approximate estimations.
  3. Provides both synchronous and async invocation paths.
  4. Preserves backward-compatibility with existing core/llm_client and core/gemini.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from core.agents.context_budget import ContextBudget

logger = logging.getLogger(__name__)


class ProviderType(str, Enum):
    GEMINI = "gemini"
    GROQ = "groq"
    OLLAMA = "ollama"
    OPENAI = "openai"


@dataclass
class ProviderUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    is_estimated: bool = True  # True if calculated via proxy/heuristic


@dataclass
class NormalizedResponse:
    content: str
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    usage: ProviderUsage = field(default_factory=ProviderUsage)
    raw_response: Any = None
    model_name: str = ""
    provider: str = ""
    latency_ms: float = 0.0


class ProviderError(Exception):
    """Base exception for provider communication errors."""
    def __init__(self, message: str, provider: str, status_code: Optional[int] = None):
        super().__init__(f"[{provider.upper()}] {message}")
        self.message = message
        self.provider = provider
        self.status_code = status_code


class ProviderAdapter:
    """
    Unified adapter normalizing LLM interactions across Gemini, Groq, and Ollama.
    """

    def __init__(
        self,
        provider: Union[str, ProviderType] = ProviderType.GEMINI,
        model_name: Optional[str] = None,
        context_budget: Optional[ContextBudget] = None,
    ):
        raw_p = str(provider.value if isinstance(provider, ProviderType) else provider).lower()
        if "gemini" in raw_p:
            self.provider_type = ProviderType.GEMINI
        elif "groq" in raw_p:
            self.provider_type = ProviderType.GROQ
        elif "ollama" in raw_p:
            self.provider_type = ProviderType.OLLAMA
        else:
            self.provider_type = ProviderType.OPENAI

        self.model_name = model_name or self._default_model_for_provider(self.provider_type)
        self.context_budget = context_budget or ContextBudget(
            model_name=self.model_name,
            provider=self.provider_type.value,
        )

    @staticmethod
    def _default_model_for_provider(provider: ProviderType) -> str:
        if provider == ProviderType.GEMINI:
            return "gemini-2.5-flash"
        elif provider == ProviderType.GROQ:
            return "llama-3.3-70b-versatile"
        elif provider == ProviderType.OLLAMA:
            return "llama3.2"
        return "gpt-4o-mini"

    def execute(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        rolling_summary: Optional[str] = None,
    ) -> NormalizedResponse:
        """
        Executes a normalized LLM request with context budget enforcement.
        """
        import time
        start_t = time.perf_counter()

        # 1. Budget Verification & Context Trimming
        trimmed_messages = self.context_budget.trim_history(
            messages=messages,
            system_prompt=system_prompt,
            rolling_summary=rolling_summary,
        )

        # 2. Provider Dispatch
        if self.provider_type == ProviderType.GEMINI:
            resp = self._execute_gemini(
                messages=trimmed_messages,
                system_prompt=system_prompt,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens,
                rolling_summary=rolling_summary,
            )
        elif self.provider_type == ProviderType.GROQ:
            resp = self._execute_groq(
                messages=trimmed_messages,
                system_prompt=system_prompt,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens,
                rolling_summary=rolling_summary,
            )
        elif self.provider_type in (ProviderType.OLLAMA, ProviderType.OPENAI):
            resp = self._execute_ollama_or_openai(
                messages=trimmed_messages,
                system_prompt=system_prompt,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens,
                rolling_summary=rolling_summary,
            )
        else:
            raise ProviderError(f"Unsupported provider: {self.provider_type}", provider="unknown")

        resp.latency_ms = round((time.perf_counter() - start_t) * 1000, 2)
        resp.provider = self.provider_type.value
        resp.model_name = self.model_name
        return resp

    async def execute_async(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        rolling_summary: Optional[str] = None,
    ) -> NormalizedResponse:
        """Asynchronously executes the request off the main event loop."""
        return await asyncio.to_thread(
            self.execute,
            messages=messages,
            system_prompt=system_prompt,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            rolling_summary=rolling_summary,
        )

    # ── Internal Provider Handlers ────────────────────────────────────────────

    def _execute_gemini(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str],
        tools: Optional[List[Dict[str, Any]]],
        temperature: float,
        max_tokens: int,
        rolling_summary: Optional[str],
    ) -> NormalizedResponse:
        try:
            from core import gemini
            # Build combined query text
            full_prompt_parts = []
            if rolling_summary:
                full_prompt_parts.append(f"CONVERSATION SUMMARY UP TO RECENT TURNS:\n{rolling_summary}\n")

            if messages and len(messages) > 1:
                full_prompt_parts.append("[CONVERSATION HISTORY - Prior turns in this active dialogue:]")
                for m in messages[:-1]:
                    role = "User" if m.get("role") == "user" else "Assistant"
                    cnt = m.get("content", "")
                    full_prompt_parts.append(f"{role}: {cnt}")
                full_prompt_parts.append("[CURRENT TURN]")
                last_m = messages[-1]
                role = "User" if last_m.get("role") == "user" else "Assistant"
                full_prompt_parts.append(f"{role}: {last_m.get('content', '')}")
            else:
                for m in messages:
                    role = "User" if m.get("role") == "user" else "Assistant"
                    cnt = m.get("content", "")
                    full_prompt_parts.append(f"{role}: {cnt}")

            query_text = "\n".join(full_prompt_parts)
            if system_prompt:
                query_text = f"System: {system_prompt}\n\n{query_text}"

            # Use core/gemini text generation ladder
            raw_text = gemini.text(
                contents=query_text,
                tier="fast",
                timeout_ms=30000,
            )

            # Calculate token usage (Gemini Native or Budget fallback)
            prompt_toks = self.context_budget.count_tokens(query_text)
            comp_toks = self.context_budget.count_tokens(raw_text)

            return NormalizedResponse(
                content=raw_text,
                tool_calls=[],
                usage=ProviderUsage(
                    prompt_tokens=prompt_toks,
                    completion_tokens=comp_toks,
                    total_tokens=prompt_toks + comp_toks,
                    is_estimated=False,  # Native calculation
                ),
                raw_response=raw_text,
            )
        except Exception as e:
            logger.error(f"Gemini execution error: {e}")
            raise ProviderError(str(e), provider="gemini")

    def _execute_groq(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str],
        tools: Optional[List[Dict[str, Any]]],
        temperature: float,
        max_tokens: int,
        rolling_summary: Optional[str],
    ) -> NormalizedResponse:
        try:
            from core.llm_client import call_groq_text, call_groq_tools
            sys_combined = system_prompt or ""
            if rolling_summary:
                sys_combined = f"{sys_combined}\n\nCONVERSATION SUMMARY:\n{rolling_summary}".strip()

            # If tools are provided, route to call_groq_tools
            if tools:
                prompt_content = messages[-1].get("content", "") if messages else ""
                tool_result = call_groq_tools(
                    prompt=prompt_content,
                    tools=tools,
                    system=sys_combined,
                    model=self.model_name,
                    timeout=30,
                )
                tool_calls = []
                if isinstance(tool_result, dict) and "tool" in tool_result:
                    tool_calls.append({
                        "name": tool_result["tool"],
                        "parameters": tool_result.get("args", {}),
                    })
                content_out = tool_result.get("text", "") if isinstance(tool_result, dict) else str(tool_result or "")

                # Estimate usage
                p_toks = self.context_budget.count_messages_tokens(messages)
                c_toks = self.context_budget.count_tokens(content_out)
                return NormalizedResponse(
                    content=content_out,
                    tool_calls=tool_calls,
                    usage=ProviderUsage(
                        prompt_tokens=p_toks,
                        completion_tokens=c_toks,
                        total_tokens=p_toks + c_toks,
                        is_estimated=True,  # Groq tiktoken proxy estimation
                    ),
                    raw_response=tool_result,
                )
            else:
                # Text-only call
                prompt_content = "\n".join(f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages)
                raw_text = call_groq_text(
                    prompt=prompt_content,
                    system=sys_combined,
                    model=self.model_name,
                    timeout=30,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                p_toks = self.context_budget.count_tokens(prompt_content)
                c_toks = self.context_budget.count_tokens(raw_text)
                return NormalizedResponse(
                    content=raw_text,
                    tool_calls=[],
                    usage=ProviderUsage(
                        prompt_tokens=p_toks,
                        completion_tokens=c_toks,
                        total_tokens=p_toks + c_toks,
                        is_estimated=True,  # Groq tiktoken proxy estimation
                    ),
                    raw_response=raw_text,
                )
        except Exception as e:
            logger.error(f"Groq execution error: {e}")
            raise ProviderError(str(e), provider="groq")

    def _execute_ollama_or_openai(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str],
        tools: Optional[List[Dict[str, Any]]],
        temperature: float,
        max_tokens: int,
        rolling_summary: Optional[str],
    ) -> NormalizedResponse:
        try:
            from core.llm_client import call_llm
            prompt_content = messages[-1].get("content", "") if messages else ""
            sys_combined = system_prompt or ""
            if rolling_summary:
                sys_combined = f"{sys_combined}\n\nCONVERSATION SUMMARY:\n{rolling_summary}".strip()

            raw_text = call_llm(
                prompt=prompt_content,
                system=sys_combined,
                model=self.model_name,
                timeout=30,
            )

            p_toks = self.context_budget.count_tokens(prompt_content)
            c_toks = self.context_budget.count_tokens(raw_text)

            return NormalizedResponse(
                content=raw_text,
                tool_calls=[],
                usage=ProviderUsage(
                    prompt_tokens=p_toks,
                    completion_tokens=c_toks,
                    total_tokens=p_toks + c_toks,
                    is_estimated=True,
                ),
                raw_response=raw_text,
            )
        except Exception as e:
            logger.error(f"Local LLM execution error: {e}")
            raise ProviderError(str(e), provider=self.provider_type.value)

