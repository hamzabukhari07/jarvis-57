"""
core/loop_gates.py — Runtime Execution Guards & Doom Loop Detection Engine.

Inspired by QwenPaw runtime gates (doom_loop.py, step budget) and hermes-agent:
Provides 4 key runtime evaluation gates:
1. iteration_cap: Limits sequential loops / agent turns per task to prevent runaways.
2. doom_loop: Windowed argument & signature similarity detection with steering feedback (INTERRUPT_AND_CONTINUE).
3. tool_budget: Maximum tool invocations per session / turn.
4. watchdog_timeout: Maximum wall-clock execution time per sub-step.
"""

from __future__ import annotations

import collections
import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class GateDecision(str, Enum):
    PROCEED = "PROCEED"
    WARN = "WARN"
    INTERRUPT = "INTERRUPT"
    BLOCK = "BLOCK"


@dataclass
class GateResult:
    decision: GateDecision
    reason: Optional[str] = None
    coaching_feedback: Optional[str] = None

    @property
    def can_proceed(self) -> bool:
        return self.decision in (GateDecision.PROCEED, GateDecision.WARN)


@dataclass
class ToolCallEntry:
    tool_name: str
    params_hash: str
    timestamp: float
    raw_preview: str


class LoopGatesEngine:
    """Thread-safe engine managing loop evaluation gates and similarity tracking."""

    def __init__(
        self,
        max_iterations: int = 25,
        max_tool_budget: int = 50,
        similarity_window: int = 4,
        similarity_threshold: int = 3,
        watchdog_timeout_sec: float = 300.0,
        idle_reset_sec: float = 60.0,
    ):
        self._lock = threading.RLock()
        self.max_iterations = max_iterations
        self.max_tool_budget = max_tool_budget
        self.similarity_window = similarity_window
        self.similarity_threshold = similarity_threshold
        self.watchdog_timeout_sec = watchdog_timeout_sec
        self.idle_reset_sec = idle_reset_sec

        # Context-keyed history buffers
        self._history: Dict[str, collections.deque[ToolCallEntry]] = collections.defaultdict(
            lambda: collections.deque(maxlen=20)
        )
        self._iteration_counts: Dict[str, int] = collections.defaultdict(int)
        self._tool_counts: Dict[str, int] = collections.defaultdict(int)
        self._session_start_times: Dict[str, float] = {}
        self._session_last_active_times: Dict[str, float] = {}

    def _compute_param_hash(self, tool_name: str, params: dict) -> str:
        """Create normalized structural hash of tool parameters."""
        try:
            # Sort keys for deterministic serialization
            norm_str = json.dumps(params or {}, sort_keys=True, default=str)
        except Exception:
            norm_str = str(params or {})
        return hashlib.sha256(f"{tool_name}:{norm_str}".encode("utf-8")).hexdigest()[:16]

    def evaluate(
        self,
        tool_name: str,
        params: dict,
        session_id: str = "global",
        now: Optional[float] = None,
    ) -> GateResult:
        """
        Evaluate tool execution against all 4 runtime gates.
        Returns GateResult indicating whether tool is allowed, steered, or blocked.
        """
        current_time = time.time() if now is None else now

        with self._lock:
            # Auto-reset session if idle time between tool invocations exceeds idle_reset_sec
            last_active = self._session_last_active_times.get(session_id)
            if last_active is not None and (current_time - last_active) > self.idle_reset_sec:
                self.reset_session(session_id)

            if session_id not in self._session_start_times:
                self._session_start_times[session_id] = current_time

            self._session_last_active_times[session_id] = current_time

            # 1. Watchdog Timeout Gate
            elapsed = current_time - self._session_start_times[session_id]
            if elapsed > self.watchdog_timeout_sec:
                return GateResult(
                    decision=GateDecision.BLOCK,
                    reason=f"Watchdog timeout exceeded ({round(elapsed, 1)}s > {self.watchdog_timeout_sec}s). Execution halted.",
                    coaching_feedback="Task exceeded max allowable execution duration. Wrap up results and summarize.",
                )

            # 2. Tool Budget Gate
            self._tool_counts[session_id] += 1
            if self._tool_counts[session_id] > self.max_tool_budget:
                return GateResult(
                    decision=GateDecision.BLOCK,
                    reason=f"Tool invocation budget exceeded ({self._tool_counts[session_id]} > {self.max_tool_budget}).",
                    coaching_feedback="Tool budget exhausted. Provide final answer with gathered facts.",
                )

            # 3. Iteration Cap Gate
            self._iteration_counts[session_id] += 1
            if self._iteration_counts[session_id] > self.max_iterations:
                return GateResult(
                    decision=GateDecision.BLOCK,
                    reason=f"Turn iteration limit reached ({self._iteration_counts[session_id]} > {self.max_iterations}).",
                    coaching_feedback="Iteration limit reached. Halt loop and formulate response.",
                )

            # 4. Doom-Loop / Similarity Detection Gate
            param_hash = self._compute_param_hash(tool_name, params)
            history = self._history[session_id]

            # Count recent identical tool invocations in window
            recent_matches = [e for e in history if e.tool_name == tool_name and e.params_hash == param_hash]
            
            # Record current entry
            preview = f"{tool_name}({list((params or {}).keys())})"
            history.append(ToolCallEntry(
                tool_name=tool_name,
                params_hash=param_hash,
                timestamp=current_time,
                raw_preview=preview,
            ))

            if len(recent_matches) >= self.similarity_threshold:
                # Doom loop triggered: return steering interrupt coaching feedback
                coaching = (
                    f"⚠️ [DOOM-LOOP INTERRUPT]: You called '{tool_name}' with identical arguments {len(recent_matches) + 1} times sequentially without progress. "
                    "Do NOT repeat this identical call. Change strategy: inspect alternative files, try a different action, or report the obstacle."
                )
                return GateResult(
                    decision=GateDecision.INTERRUPT,
                    reason=f"Doom-Loop detected: {len(recent_matches) + 1} identical invocations of '{tool_name}'.",
                    coaching_feedback=coaching,
                )

            return GateResult(decision=GateDecision.PROCEED)

    def reset_session(self, session_id: Optional[str] = "global") -> None:
        """Reset counters for a completed or new conversation turn/session."""
        with self._lock:
            if session_id is None:
                self._history.clear()
                self._iteration_counts.clear()
                self._tool_counts.clear()
                self._session_start_times.clear()
                self._session_last_active_times.clear()
                return

            self._history.pop(session_id, None)
            self._iteration_counts.pop(session_id, None)
            self._tool_counts.pop(session_id, None)
            self._session_start_times.pop(session_id, None)
            self._session_last_active_times.pop(session_id, None)


# Global runtime instance
loop_gates = LoopGatesEngine()
