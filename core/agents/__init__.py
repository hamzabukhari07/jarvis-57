"""
core/agents package — ZEZO Autonomous Agent Management Subsystem.

Provides modular components for agent management and task coordination:
- AgentProfile: Dataclass defining agent profile and runtime state.
- AgentRegistry: Storage, CRUD, desk allocation, and JSON config persistence.
- AgentDispatcher: Risk-tier sandboxing, skill injection, task dispatch, and telemetry.
- AgentOrchestrator: Multi-agent task decomposition, peer delegation, and teardown/merge gates.
"""

from core.agents.registry import (
    AgentProfile,
    AgentRegistry,
    OFFICE_DESK_COORDINATES,
    VALID_RISK_TIERS,
    CORE_AGENT_IDS,
    VALID_TOOLS,
    _infer_agent_defaults,
)
from core.agents.dispatcher import AgentDispatcher
from core.agents.orchestrator import AgentOrchestrator

__all__ = [
    "AgentProfile",
    "AgentRegistry",
    "AgentDispatcher",
    "AgentOrchestrator",
    "OFFICE_DESK_COORDINATES",
    "VALID_RISK_TIERS",
    "CORE_AGENT_IDS",
    "VALID_TOOLS",
    "_infer_agent_defaults",
]
