"""
core/fleet package — ZEZO Autonomous Fleet Management Subsystem.

Provides modular components for managing the multi-agent fleet:
- FleetAgent: Dataclass defining agent profile and runtime state.
- FleetRegistry: Storage, CRUD, desk allocation, and JSON config persistence.
- FleetDispatcher: Risk-tier sandboxing, skill injection, task dispatch, and telemetry.
- FleetOrchestrator: Multi-agent task decomposition, peer delegation, and teardown/merge gates.
"""

from core.fleet.registry import (
    FleetAgent,
    FleetRegistry,
    OFFICE_DESK_COORDINATES,
    VALID_RISK_TIERS,
    CORE_AGENT_IDS,
    VALID_TOOLS,
    _infer_agent_defaults,
)
from core.fleet.dispatcher import FleetDispatcher
from core.fleet.orchestrator import FleetOrchestrator

__all__ = [
    "FleetAgent",
    "FleetRegistry",
    "FleetDispatcher",
    "FleetOrchestrator",
    "OFFICE_DESK_COORDINATES",
    "VALID_RISK_TIERS",
    "CORE_AGENT_IDS",
    "VALID_TOOLS",
    "_infer_agent_defaults",
]
