"""
core/governance.py — Multi-Tier Security & Governance Policy Matrix.

Inspired by QwenPaw (Tier 2-3 Governance) and Hermes (Tool Guardrails).
Classifies every action into:
  - ALLOW: Frictionless, silent execution for safe read-only operations.
  - ASK: Interactive user confirmation gate for sensitive/irreversible actions.
  - DENY: Hard block with immediate security alert for dangerous/destructive commands.
"""

from __future__ import annotations

import enum
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional


class PolicyDecision(str, enum.Enum):
    ALLOW = "ALLOW"
    ASK   = "ASK"
    DENY  = "DENY"


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
    "shutdown_jarvis": "Shutting down the assistant",
    "modify_system_setting": "Modifying critical system configuration",
    "kill_process": "Terminating a system process",
}


def _check_path_safety(target_path: str) -> Optional[str]:
    """Check if a path tries to escape or tamper with critical Windows system directories."""
    if not target_path or not isinstance(target_path, str):
        return None
    try:
        norm = os.path.normpath(str(target_path)).lower()
        # Check system directory blacklist
        for sys_path in _FORBIDDEN_SYSTEM_PATHS:
            if norm == sys_path or norm.startswith(sys_path + "\\") or norm.startswith(sys_path + "/"):
                return f"Path '{target_path}' resides inside protected system directory '{sys_path}'"
        
        # Check forbidden critical files (e.g. hosts file)
        base_name = os.path.basename(norm).lower()
        if base_name in _FORBIDDEN_FILES:
            return f"Modification of critical system file '{base_name}' is forbidden"
    except Exception:
        pass
    return None


def evaluate(tool_name: str, args: dict[str, Any] | None = None) -> tuple[PolicyDecision, str]:
    """
    Evaluate a proposed tool call and parameters.
    Returns:
      (PolicyDecision.ALLOW, "Reason")
      (PolicyDecision.ASK, "Confirmation prompt / details")
      (PolicyDecision.DENY, "Violation explanation")
    """
    name = (tool_name or "").strip()
    params = args or {}

    # 1. Scan arguments stringified for dangerous patterns
    arg_str = " ".join(f"{k}={v}" for k, v in params.items() if v is not None)
    for pattern, reason in _DANGEROUS_PATTERNS:
        if pattern.search(arg_str):
            return PolicyDecision.DENY, reason

    # 2. Check path safety if tool operates on files or paths
    path_keys = ["file_path", "filepath", "path", "destination", "target", "dir", "folder"]
    for pk in path_keys:
        val = params.get(pk)
        if isinstance(val, str):
            violation = _check_path_safety(val)
            if violation:
                return PolicyDecision.DENY, violation

    # 3. Check shell commands passed into dev_agent / computer_control / code_helper
    cmd = params.get("command") or params.get("cmd") or params.get("code")
    if isinstance(cmd, str):
        for pattern, reason in _DANGEROUS_PATTERNS:
            if pattern.search(cmd):
                return PolicyDecision.DENY, reason

    # 4. Check if action is categorized under ASK (Sensitive)
    if name in _SENSITIVE_ACTIONS:
        return PolicyDecision.ASK, _SENSITIVE_ACTIONS[name]

    # 5. Otherwise, ALLOW
    return PolicyDecision.ALLOW, "Operation verified safe by governance policy"
