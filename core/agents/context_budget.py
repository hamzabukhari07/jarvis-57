"""
core/agents/context_budget.py - Context Token Budget & Truncation Manager.

Enforces provider-aware token counting and conservative safety margins across
Gemini, Groq, Ollama, and generic providers.

Key Responsibilities:
  1. Count tokens accurately (Native Gemini, Tiktoken for Groq/Ollama, Char-fallback).
  2. Apply a strict 20% safety margin for proxy estimations.
  3. Truncate oversized tool outputs before LLM injection / SQLite persistence.
  4. Manage rolling summary triggers and history trimming to prevent context overflow.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Try importing tiktoken with graceful fallback
try:
    import tiktoken
    _TIKTOKEN_AVAILABLE = True
except ImportError:
    _TIKTOKEN_AVAILABLE = False
    tiktoken = None  # type: ignore

# ── Model Context Limits & Nominal Budgets ────────────────────────────────────

@dataclass(frozen=True)
class ModelBudgetSpec:
    total_window: int
    nominal_history_budget: int
    tool_output_ceiling: int
    rolling_summary_turn_trigger: int
    safety_margin: float  # e.g. 0.0 for Native, 0.20 for Proxy, 0.25 for Heuristic


# Pre-configured specifications based on approved Phase 1 Revision 5 blueprint
BUDGET_SPECS: Dict[str, ModelBudgetSpec] = {
    "gemini": ModelBudgetSpec(
        total_window=1_048_576,
        nominal_history_budget=12_000,
        tool_output_ceiling=4_000,
        rolling_summary_turn_trigger=15,
        safety_margin=0.0,  # Native exact counting
    ),
    "groq": ModelBudgetSpec(
        total_window=128_000,
        nominal_history_budget=8_000,
        tool_output_ceiling=2_400,
        rolling_summary_turn_trigger=12,
        safety_margin=0.20,  # 20% safety buffer for proxy
    ),
    "ollama": ModelBudgetSpec(
        total_window=8_192,
        nominal_history_budget=2_500,
        tool_output_ceiling=800,
        rolling_summary_turn_trigger=8,
        safety_margin=0.20,  # 20% safety buffer for proxy
    ),
    "default": ModelBudgetSpec(
        total_window=8_192,
        nominal_history_budget=4_000,
        tool_output_ceiling=1_000,
        rolling_summary_turn_trigger=10,
        safety_margin=0.25,  # Heuristic fallback
    ),
}


class ContextBudget:
    """
    Manages token budgeting, counting methods, safety margins, and history truncation.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        provider: str = "default",
        gemini_client: Optional[Any] = None,
    ):
        self.model_name = (model_name or "").strip().lower()
        self.provider = (provider or "default").strip().lower()
        self.gemini_client = gemini_client

        # Normalize provider key
        if "gemini" in self.provider:
            self.provider_key = "gemini"
        elif "groq" in self.provider:
            self.provider_key = "groq"
        elif "ollama" in self.provider:
            self.provider_key = "ollama"
        else:
            self.provider_key = "default"

        self.spec = BUDGET_SPECS.get(self.provider_key, BUDGET_SPECS["default"])

        # Cache encoding instance if tiktoken is available
        self._tiktoken_enc = None
        if _TIKTOKEN_AVAILABLE and tiktoken is not None:
            try:
                # Use cl100k_base as standard proxy for modern LLMs
                self._tiktoken_enc = tiktoken.get_encoding("cl100k_base")
            except Exception as e:
                logger.warning(f"Failed to load tiktoken encoding: {e}")

    def get_effective_budget(self) -> int:
        """
        Returns the effective token history budget after deducting the safety margin.
        Formula: Nominal Budget * (1.0 - Safety Margin)
        """
        return int(self.spec.nominal_history_budget * (1.0 - self.spec.safety_margin))

    def get_tool_output_ceiling(self) -> int:
        """Returns the maximum token ceiling for an individual tool response."""
        return self.spec.tool_output_ceiling

    def count_tokens(self, text: str) -> int:
        """
        Count tokens using provider-appropriate methods:
          1. Gemini REST client if available and provider is gemini.
          2. Tiktoken proxy (cl100k_base) for Groq/Ollama/OpenAI.
          3. Heuristic division (len(text) // 4) as conservative fallback.
        """
        if not text:
            return 0

        # Method 1: Native Gemini counting
        if self.provider_key == "gemini" and self.gemini_client is not None:
            try:
                count_resp = self.gemini_client.models.count_tokens(
                    model=self.model_name or "gemini-2.5-flash",
                    contents=text,
                )
                if hasattr(count_resp, "total_tokens"):
                    return int(count_resp.total_tokens)
            except Exception as e:
                logger.debug(f"Gemini native count_tokens failed, falling back: {e}")

        # Method 2: Tiktoken proxy
        if self._tiktoken_enc is not None:
            try:
                return len(self._tiktoken_enc.encode(text, disallowed_special=()))
            except Exception as e:
                logger.debug(f"Tiktoken encoding failed, using fallback: {e}")

        # Method 3: Heuristic division (1 token ≈ 4 characters)
        return max(1, len(text) // 4)

    def count_messages_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """
        Calculate the total token cost for a list of conversation messages.
        Includes a standard 4-token structural framing per message.
        """
        total = 0
        for msg in messages:
            content = str(msg.get("content") or "")
            tool_res = str(msg.get("tool_result") or "")
            role = str(msg.get("role") or "")
            total += 4  # Formatting framing tokens
            total += self.count_tokens(role)
            total += self.count_tokens(content)
            if tool_res:
                total += self.count_tokens(tool_res)
        return total

    def truncate_tool_output(self, output: str) -> str:
        """
        Truncates oversized tool outputs exceeding the model's tool ceiling.
        Appends an explicit truncation disclaimer.
        """
        if not output:
            return ""

        ceiling = self.get_tool_output_ceiling()
        current_tokens = self.count_tokens(output)

        if current_tokens <= ceiling:
            return output

        # Calculate character budget based on token ratio
        ratio = len(output) / max(1, current_tokens)
        char_cutoff = int(ceiling * ratio * 0.95)  # 5% safety margin
        truncated_text = output[:char_cutoff].rstrip()

        return (
            f"{truncated_text}\n\n"
            f"[Output truncated at ~{ceiling} tokens. Request specific sections for details.]"
        )

    def should_summarize(self, turn_count: int) -> bool:
        """Check if total conversation turns trigger rolling summary generation."""
        return turn_count > self.spec.rolling_summary_turn_trigger

    def trim_history(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        rolling_summary: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Drops the oldest non-system messages until the entire context fits
        within the effective token budget.
        Always preserves the last 2 messages (current turn context).
        """
        if not messages:
            return []

        effective_budget = self.get_effective_budget()

        # Fixed overhead calculation
        fixed_tokens = 0
        if system_prompt:
            fixed_tokens += self.count_tokens(system_prompt) + 4
        if rolling_summary:
            fixed_tokens += self.count_tokens(rolling_summary) + 4

        available_history_budget = max(200, effective_budget - fixed_tokens)

        # Iteratively drop oldest messages until within budget
        trimmed = list(messages)
        while len(trimmed) > 2 and self.count_messages_tokens(trimmed) > available_history_budget:
            trimmed.pop(0)

        return trimmed

