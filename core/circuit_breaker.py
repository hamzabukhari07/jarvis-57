from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class RiskTier(str, Enum):
    L0_READ_ONLY = "L0_READ_ONLY"
    L1_LOW_RISK = "L1_LOW_RISK"
    L2_DESTRUCTIVE = "L2_DESTRUCTIVE"


class BreakerState(str, Enum):
    CLOSED = "CLOSED"
    HALF_OPEN = "HALF_OPEN"
    OPEN = "OPEN"


def _map_risk_tier(tool_name: str) -> RiskTier:
    from core.governance import ToolRisk, get_tool_risk
    tr = get_tool_risk(tool_name)
    if tr == ToolRisk.READ_ONLY:
        return RiskTier.L0_READ_ONLY
    elif tr in (ToolRisk.CODE_EXECUTION, ToolRisk.PRIVILEGED_OS):
        return RiskTier.L2_DESTRUCTIVE
    return RiskTier.L1_LOW_RISK


def get_tool_tier(tool_name: str) -> RiskTier:
    return _map_risk_tier(tool_name)


@dataclass
class ToolMetrics:
    tool_name: str
    tier: RiskTier
    state: BreakerState = BreakerState.CLOSED
    failure_count: int = 0
    consecutive_successes: int = 0
    last_failure_time: float = 0.0
    tripped_reason: str = ""
    human_override_required: bool = False
    error_timestamps: List[float] = field(default_factory=list)


class RiskAwareCircuitBreaker:
    """Per-tool risk-aware circuit breaker protecting system against cascade failures."""

    def __init__(self, velocity_window_sec: float = 15.0, velocity_threshold: int = 3):
        self._lock = threading.Lock()
        self.velocity_window_sec = velocity_window_sec
        self.velocity_threshold = velocity_threshold
        self._tools: Dict[str, ToolMetrics] = {}

    def _get_or_create_metrics(self, tool_name: str) -> ToolMetrics:
        tname = (tool_name or "unknown").strip().lower()
        if tname not in self._tools:
            tier = get_tool_tier(tname)
            self._tools[tname] = ToolMetrics(tool_name=tname, tier=tier)
        return self._tools[tname]

    def get_tool_tier(self, tool_name: str) -> RiskTier:
        return _map_risk_tier(tool_name)

    def can_execute(self, tool_name: str) -> Tuple[bool, Optional[str]]:
        with self._lock:
            metrics = self._get_or_create_metrics(tool_name)
            now = time.time()
            tier = metrics.tier

            if metrics.state == BreakerState.CLOSED:
                return True, None

            if metrics.state == BreakerState.OPEN:
                if tier == RiskTier.L0_READ_ONLY:
                    if (now - metrics.last_failure_time) >= 10.0:
                        metrics.state = BreakerState.HALF_OPEN
                        return True, None
                    return False, f"CircuitBreaker: Tool '{tool_name}' paused ({metrics.tripped_reason}). Retry in 10s."

                if tier == RiskTier.L1_LOW_RISK:
                    if (now - metrics.last_failure_time) >= 60.0:
                        metrics.state = BreakerState.HALF_OPEN
                        return True, None
                    return False, f"CircuitBreaker: Tool '{tool_name}' throttled ({metrics.tripped_reason}). Cooldown active."

                if tier == RiskTier.L2_DESTRUCTIVE:
                    if metrics.human_override_required:
                        return False, f"CircuitBreaker: Tool '{tool_name}' blocked ({metrics.tripped_reason}). Human confirmation required to re-arm."
                    if (now - metrics.last_failure_time) >= 120.0:
                        metrics.state = BreakerState.HALF_OPEN
                        return True, None
                    return False, f"CircuitBreaker: Tool '{tool_name}' tripped ({metrics.tripped_reason})."

            if metrics.state == BreakerState.HALF_OPEN:
                return True, None

        return True, None

    def record_success(self, tool_name: str) -> None:
        with self._lock:
            metrics = self._get_or_create_metrics(tool_name)
            metrics.consecutive_successes += 1
            tier = metrics.tier

            if metrics.state == BreakerState.HALF_OPEN:
                if tier == RiskTier.L0_READ_ONLY and metrics.consecutive_successes >= 1:
                    metrics.state = BreakerState.CLOSED
                    metrics.failure_count = 0
                elif tier == RiskTier.L1_LOW_RISK and metrics.consecutive_successes >= 3:
                    metrics.state = BreakerState.CLOSED
                    metrics.failure_count = 0
                elif tier == RiskTier.L2_DESTRUCTIVE and metrics.consecutive_successes >= 2:
                    metrics.state = BreakerState.CLOSED
                    metrics.failure_count = 0
                    metrics.human_override_required = False

    def record_failure(self, tool_name: str, error_message: str) -> str:
        now = time.time()
        with self._lock:
            metrics = self._get_or_create_metrics(tool_name)
            tier = metrics.tier
            metrics.failure_count += 1
            metrics.consecutive_successes = 0
            metrics.last_failure_time = now
            metrics.tripped_reason = f"Tool '{tool_name}' failed: {error_message[:80]}"

            metrics.error_timestamps.append(now)
            cutoff = now - self.velocity_window_sec
            metrics.error_timestamps = [t for t in metrics.error_timestamps if t > cutoff]

            velocity_tripped = len(metrics.error_timestamps) >= self.velocity_threshold

            if tier == RiskTier.L0_READ_ONLY:
                if velocity_tripped or metrics.failure_count >= 3:
                    metrics.state = BreakerState.OPEN
            elif tier == RiskTier.L1_LOW_RISK:
                if velocity_tripped or metrics.failure_count >= 2:
                    metrics.state = BreakerState.OPEN
            elif tier == RiskTier.L2_DESTRUCTIVE:
                metrics.state = BreakerState.OPEN
                metrics.human_override_required = True

            return f"CircuitBreaker [{tool_name}]: state={metrics.state.value} (failures={metrics.failure_count})"

    def human_rearm(self, tool_name: Optional[str] = None) -> str:
        with self._lock:
            target_tools = [self._get_or_create_metrics(tool_name)] if tool_name else list(self._tools.values())
            for m in target_tools:
                m.state = BreakerState.CLOSED
                m.failure_count = 0
                m.consecutive_successes = 0
                m.human_override_required = False
                m.error_timestamps.clear()
            names = [m.tool_name for m in target_tools] or ["all tools"]
            return f"CircuitBreaker manually re-armed for {', '.join(names)}."

    def get_status_summary(self) -> Dict[str, dict]:
        with self._lock:
            return {
                tool: {
                    "tier": m.tier.value,
                    "state": m.state.value,
                    "failures": m.failure_count,
                    "consecutive_successes": m.consecutive_successes,
                    "human_override_required": m.human_override_required,
                    "tripped_reason": m.tripped_reason,
                }
                for tool, m in self._tools.items()
            }


circuit_breaker = RiskAwareCircuitBreaker()
