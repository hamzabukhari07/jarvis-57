"""
core/governance.py — Multi-Tier Security & Governance Policy Matrix.

Classifies actions into a formal 5-tier ToolRisk taxonomy:
  - READ_ONLY: Safe read-only inspection (Allowed frictionless).
  - LOCAL_MUTATION: Local state changes (Allowed if confidence >= 0.70).
  - EXTERNAL_MUTATION: Outbound messaging / publishing (Requires confirmation).
  - CODE_EXECUTION: Autonomous agent execution (Gated with ApprovalScope).
  - PRIVILEGED_OS: Irreversible system actions / shutdown (Requires explicit user approval).
"""

from __future__ import annotations

import enum
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


class PolicyDecision(str, enum.Enum):
    ALLOW = "ALLOW"
    ASK   = "ASK"
    DENY  = "DENY"


class ToolRisk(str, enum.Enum):
    READ_ONLY         = "read_only"
    LOCAL_MUTATION    = "local_mutation"
    EXTERNAL_MUTATION = "external_mutation"
    CODE_EXECUTION    = "code_execution"
    PRIVILEGED_OS     = "privileged_os"


class ApprovalState(str, enum.Enum):
    PENDING  = "pending"
    APPROVED = "approved"
    DENIED   = "denied"
    EXPIRED  = "expired"


@dataclass(frozen=True)
class ApprovalScope:
    job_id: str
    tool_name: str
    risk: ToolRisk
    expires_at: float


@dataclass(frozen=True)
class ApprovalGrant:
    scope: ApprovalScope
    state: ApprovalState = ApprovalState.APPROVED
    approved_by: Optional[str] = None

    def can_execute(self, job_id: str, tool_name: str, now: float | None = None) -> bool:
        current_time = time.time() if now is None else now
        return (
            self.state is ApprovalState.APPROVED
            and self.scope.job_id == job_id
            and self.scope.tool_name == tool_name
            and current_time < self.scope.expires_at
        )


# ── Action to Risk Classification Mapping ─────────────────────────────────────
# Default / Fallback Risk Taxonomy for Core & Inline Actions
_DEFAULT_TOOL_RISKS: dict[str, ToolRisk] = {
    "screen_process":         ToolRisk.READ_ONLY,
    "web_search":             ToolRisk.READ_ONLY,
    "web_read_page":          ToolRisk.READ_ONLY,
    "system_status":          ToolRisk.READ_ONLY,
    "task_status":            ToolRisk.READ_ONLY,
    "weather_report":         ToolRisk.READ_ONLY,
    "flight_finder":          ToolRisk.READ_ONLY,
    "game_updater":           ToolRisk.READ_ONLY,
    "extract_design_system":  ToolRisk.READ_ONLY,
    "file_processor":         ToolRisk.READ_ONLY,
    "read_skill":             ToolRisk.READ_ONLY,
    "list_skills":            ToolRisk.READ_ONLY,
    "recall_memory":          ToolRisk.READ_ONLY,

    "computer_control":       ToolRisk.LOCAL_MUTATION,
    "open_app":               ToolRisk.LOCAL_MUTATION,
    "desktop_control":        ToolRisk.LOCAL_MUTATION,
    "file_controller":        ToolRisk.LOCAL_MUTATION,
    "computer_settings":      ToolRisk.LOCAL_MUTATION,
    "youtube_video":          ToolRisk.LOCAL_MUTATION,
    "reminder":               ToolRisk.LOCAL_MUTATION,
    "manage_monitor":         ToolRisk.LOCAL_MUTATION,
    "browser_control":        ToolRisk.LOCAL_MUTATION,
    "save_learned_skill":     ToolRisk.LOCAL_MUTATION,
    "save_memory":            ToolRisk.LOCAL_MUTATION,
    "undo":                   ToolRisk.LOCAL_MUTATION,
    "close_camera":           ToolRisk.LOCAL_MUTATION,

    "send_message":           ToolRisk.EXTERNAL_MUTATION,
    "agent_reach":            ToolRisk.EXTERNAL_MUTATION,

    "opencode_run":           ToolRisk.CODE_EXECUTION,
    "kilo_run":               ToolRisk.CODE_EXECUTION,
    "antigravity_run":        ToolRisk.CODE_EXECUTION,
    "code_helper":            ToolRisk.CODE_EXECUTION,
    "dev_agent":              ToolRisk.CODE_EXECUTION,
    "clone_website":          ToolRisk.CODE_EXECUTION,
    "fleet_control":          ToolRisk.LOCAL_MUTATION,

    "shutdown_zezo":          ToolRisk.PRIVILEGED_OS,
}

TOOL_RISK_MAP = _DEFAULT_TOOL_RISKS


def get_tool_risk(tool_name: str, parameters: dict | None = None) -> Optional[ToolRisk]:
    """Return the assigned risk tier for any action name, accounting for fine-grained sub-actions and action definitions. Returns None for unknown tools (fail closed)."""
    if tool_name == "send_message":
        act = str((parameters or {}).get("action", "")).lower().strip()
        if act in ("search", "search_contact", "find_chat", "find_contact", "read", "list", "get_status"):
            return ToolRisk.READ_ONLY
        return ToolRisk.EXTERNAL_MUTATION

    # Check dynamically discovered action risk if loaded in sys.modules
    mod_name = f"actions.{tool_name}"
    if mod_name in sys.modules:
        mod = sys.modules[mod_name]
        tool_decl = getattr(mod, "TOOL", None)
        if isinstance(tool_decl, dict) and "risk" in tool_decl:
            r = str(tool_decl["risk"]).lower().strip()
            for tr in ToolRisk:
                if tr.value == r:
                    return tr

    return _DEFAULT_TOOL_RISKS.get(tool_name, None)


# ── Critical System Paths (Forbidden to modify / delete) ──────────────────────
_FORBIDDEN_SYSTEM_PATHS = [
    r"c:\windows",
    r"c:\windows\system32",
    r"c:\windows\syswow64",
    r"c:\programdata\microsoft",
    r"c:\recovery",
    r"c:\boot",
    r"c:\bootmgr",
    r"c:\pagefile.sys",
    r"c:\hiberfil.sys",
]

_FORBIDDEN_FILES = [
    "hosts",
    "sam",
    "system",
    "security",
    "software",
    "ntuser.dat",
]

# ── Dangerous Shell Command Patterns (Hard DENY) ──────────────────────────────
_DANGEROUS_PATTERNS = [
    # Drive formatting & disk destruction
    (re.compile(r"\bformat\s+[a-z]:", re.IGNORECASE), "Disk formatting attempt detected"),
    (re.compile(r"\bdiskpart\b", re.IGNORECASE), "Raw disk partitioning tool execution blocked"),
    
    # Destructive mass deletion
    (re.compile(r"\brmdir\s+/[sS]\s+/[qQ]\s+[a-zA-Z]:\\", re.IGNORECASE), "Recursive root directory deletion blocked"),
    (re.compile(r"\bdel\s+/[fF]\s+/[sS]\s+/[qQ]\s+[a-zA-Z]:\\", re.IGNORECASE), "Recursive root file deletion blocked"),
    (re.compile(r"\brm\s+-rf\s+/[^\s]*", re.IGNORECASE), "Destructive Linux root deletion command blocked"),
    (re.compile(r"\bRemove-Item\s+.*-Recurse\s+.*-Force\s+[a-zA-Z]:\\", re.IGNORECASE), "Destructive PowerShell root deletion blocked"),
    
    # Shadow copy & backup tampering (Ransomware behavior)
    (re.compile(r"\bvssadmin\s+delete\s+shadows", re.IGNORECASE), "Volume shadow copy deletion blocked (Ransomware guard)"),
    (re.compile(r"\bwmic\s+shadowcopy\s+delete", re.IGNORECASE), "WMIC shadow copy deletion blocked"),
    (re.compile(r"\bbcdedit\s+/set\s+.*recoveryenabled\s+no", re.IGNORECASE), "Boot recovery disabling attempt blocked"),

    # Registry tampering
    (re.compile(r"\breg\s+delete\s+hk(lm|cu|cr|u)\b", re.IGNORECASE), "Destructive system registry deletion blocked"),
    (re.compile(r"\bRemove-ItemProperty\s+.*-Path\s+hklm:", re.IGNORECASE), "HKLM registry key deletion blocked"),

    # Suspicious Obfuscation
    (re.compile(r"powershell(\.exe)?\s+.*-[eE](nc(odedcommand)?)?\s+[A-Za-z0-9+/=]{16,}", re.IGNORECASE), "Encoded/obfuscated PowerShell execution blocked"),
    (re.compile(r"\bcertutil(\.exe)?\s+-decode\b", re.IGNORECASE), "Certutil binary decoding blocked"),
]

# ── Sensitive Actions requiring Confirmation (ASK) ───────────────────────────
_SENSITIVE_ACTIONS = {
    "shutdown_zezo": "Shutting down the assistant",
}


def _check_path_safety(target_path: str) -> Optional[str]:
    """Check if a path tries to escape or tamper with critical Windows system directories."""
    if not target_path or not isinstance(target_path, str):
        return None
    try:
        norm = os.path.normpath(str(target_path)).lower()
        for sys_path in _FORBIDDEN_SYSTEM_PATHS:
            if norm == sys_path or norm.startswith(sys_path + "\\") or norm.startswith(sys_path + "/"):
                return f"Path '{target_path}' resides inside protected system directory '{sys_path}'"
        
        base_name = os.path.basename(norm).lower()
        if base_name in _FORBIDDEN_FILES:
            return f"Modification of critical system file '{base_name}' is forbidden"
    except Exception:
        pass
    return None


def evaluate(
    tool_name: str,
    args: dict[str, Any] | None = None,
    confidence: float = 1.0,
) -> tuple[PolicyDecision, str]:
    """
    Evaluate a proposed tool call against 5-tier risk taxonomy and safety patterns.
    Returns:
      (PolicyDecision.ALLOW, "Reason")
      (PolicyDecision.ASK, "Confirmation prompt / details")
      (PolicyDecision.DENY, "Violation explanation")
    """
    name = (tool_name or "").strip()
    params = args or {}
    risk = get_tool_risk(name, params)

    # 0. Fail closed on unknown/unregistered tools (DENY)
    if risk is None:
        return PolicyDecision.DENY, f"Action '{name}' is unknown and unregistered in governance taxonomy (fail-closed)."

    # 1. Scan arguments for hard dangerous patterns (DENY)
    arg_str = " ".join(f"{k}={v}" for k, v in params.items() if v is not None)
    for pattern, reason in _DANGEROUS_PATTERNS:
        if pattern.search(arg_str):
            return PolicyDecision.DENY, reason

    # 2. Check path safety if tool operates on files or paths (DENY)
    path_keys = ["file_path", "filepath", "path", "destination", "target", "dir", "folder"]
    for pk in path_keys:
        val = params.get(pk)
        if isinstance(val, str):
            violation = _check_path_safety(val)
            if violation:
                return PolicyDecision.DENY, violation

    # 3. Check shell commands passed into dev_agent / computer_control / code_helper (DENY)
    cmd = params.get("command") or params.get("cmd") or params.get("code")
    if isinstance(cmd, str):
        for pattern, reason in _DANGEROUS_PATTERNS:
            if pattern.search(cmd):
                return PolicyDecision.DENY, reason

    # 4. Check PRIVILEGED_OS or explicit sensitive actions (ASK)
    if risk is ToolRisk.PRIVILEGED_OS or name in _SENSITIVE_ACTIONS:
        desc = _SENSITIVE_ACTIONS.get(name, f"Executing privileged action: {name}")
        return PolicyDecision.ASK, desc

    # 5. Check confidence thresholds
    if risk is ToolRisk.LOCAL_MUTATION and confidence < 0.70:
        return PolicyDecision.ASK, f"Low perception confidence ({confidence:.2f}) for local mutation '{name}'"

    # 6. Otherwise, ALLOW
    return PolicyDecision.ALLOW, f"Operation verified safe by governance policy ({risk.value})"
