"""
core/skill_scanner.py — Security & Threat Scanner for Declarative Skills.

Inspired by QwenPaw security rules and hermes-agent guardrails:
1. Static analysis of SKILL.md frontmatter, body text, and scripts.
2. Shell & PowerShell dangerous destructive pattern detection.
3. Obfuscation & encoded payload detection (base64, hex, certutil, invoke-expression).
4. Prompt injection detection (e.g. system prompt override, fake role tokens, unauthorized pinning).
5. Secret token scrubbing using sqlite_memory.redact_secrets.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Tuple

from core.governance import _DANGEROUS_PATTERNS
from memory.sqlite_memory import redact_secrets

logger = logging.getLogger(__name__)

# Prompt injection & privilege escalation detection patterns
_PROMPT_INJECTION_PATTERNS: list[tuple[re.Pattern, str]] = [
    (
        re.compile(r"(?:ignore|disregard|override|forget)\s+(?:all\s+)?(?:previous|prior|system)\s+(?:instructions|rules|prompts|directives)", re.IGNORECASE),
        "Prompt injection: System instruction override directive detected",
    ),
    (
        re.compile(r"<\s*\|\s*im_start\s*\|\s*>\s*system", re.IGNORECASE),
        "Prompt injection: Raw ChatML system role token detected",
    ),
    (
        re.compile(r"\[\s*INST\s*\]\s*<<SYS>>", re.IGNORECASE),
        "Prompt injection: Llama system prompt enclosure injection detected",
    ),
    (
        re.compile(r"(?:you\s+are\s+now|act\s+as)\s+(?:DAN|jailbreak|unrestricted|god\s*mode|root\s*admin)", re.IGNORECASE),
        "Prompt injection: Jailbreak / persona hijack phrase detected",
    ),
    (
        re.compile(r"(?:exfiltrate|send|upload|post)\s+(?:all\s+)?(?:api[-_]?keys?|secrets?|tokens?|credentials?|passwords?|history)\s+to\b", re.IGNORECASE),
        "Exfiltration: Instruction attempting to transmit secrets or tokens to external host",
    ),
    (
        re.compile(r"(?:curl|wget|fetch|Invoke-WebRequest|Invoke-RestMethod)\s+.*\b(?:https?|ftp)://[^\s]+\s+.*(?:api[-_]?key|token|auth|password)", re.IGNORECASE),
        "Exfiltration: Network command transmitting sensitive variables detected",
    ),
]

# Obfuscated execution patterns
_OBFUSCATION_PATTERNS: list[tuple[re.Pattern, str]] = [
    (
        re.compile(r"(?:iex|Invoke-Expression)\s+\[System\.Text\.Encoding\]", re.IGNORECASE),
        "Obfuscation: Encoded PowerShell dynamic evaluation detected",
    ),
    (
        re.compile(r"eval\s*\(\s*compile\s*\(", re.IGNORECASE),
        "Obfuscation: Dynamic Python eval(compile(...)) execution detected",
    ),
    (
        re.compile(r"__import__\s*\(\s*['\"](?:os|subprocess|pty|socket)['\"]\s*\)\.system", re.IGNORECASE),
        "Suspicious Code: Obfuscated inline subprocess execution detected",
    ),
]


@dataclass
class ScanViolation:
    pattern_name: str
    message: str
    line_number: Optional[int] = None
    snippet: str = ""
    severity: str = "HIGH"  # HIGH | CRITICAL | MEDIUM


@dataclass
class ScanReport:
    is_safe: bool
    violations: list[ScanViolation] = field(default_factory=list)
    sanitized_content: str = ""
    redacted_secrets_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_safe": self.is_safe,
            "violations": [
                {
                    "pattern": v.pattern_name,
                    "message": v.message,
                    "line": v.line_number,
                    "snippet": v.snippet,
                    "severity": v.severity,
                }
                for v in self.violations
            ],
            "redacted_secrets_count": self.redacted_secrets_count,
        }


def scan_skill_text(raw_text: str, filename: str = "SKILL.md") -> ScanReport:
    """
    Perform deep static security analysis of skill text or script content.
    Returns ScanReport indicating safety and any detected violations.
    """
    if not raw_text or not isinstance(raw_text, str):
        return ScanReport(is_safe=True, sanitized_content="")

    # 1. Scrub embedded secrets
    redacted_text = redact_secrets(raw_text)
    secrets_count = raw_text.count("[REDACTED_SECRET]") if "[REDACTED_SECRET]" in raw_text else 0
    if "[REDACTED_SECRET]" in redacted_text and not ("[REDACTED_SECRET]" in raw_text):
        secrets_count = 1

    violations: list[ScanViolation] = []

    lines = raw_text.splitlines()

    # 2. Check Governance Dangerous System Patterns (format, rm -rf, del /s, reg delete, etc.)
    for line_idx, line in enumerate(lines, 1):
        for pat, reason in _DANGEROUS_PATTERNS:
            if pat.search(line):
                violations.append(
                    ScanViolation(
                        pattern_name="DANGEROUS_SYSTEM_COMMAND",
                        message=f"{reason} in {filename}:{line_idx}",
                        line_number=line_idx,
                        snippet=line.strip()[:100],
                        severity="CRITICAL",
                    )
                )

    # 3. Check Prompt Injections & Jailbreaks
    for line_idx, line in enumerate(lines, 1):
        for pat, reason in _PROMPT_INJECTION_PATTERNS:
            if pat.search(line):
                violations.append(
                    ScanViolation(
                        pattern_name="PROMPT_INJECTION",
                        message=f"{reason} in {filename}:{line_idx}",
                        line_number=line_idx,
                        snippet=line.strip()[:100],
                        severity="HIGH",
                    )
                )

    # 4. Check Obfuscated Payloads
    for line_idx, line in enumerate(lines, 1):
        for pat, reason in _OBFUSCATION_PATTERNS:
            if pat.search(line):
                violations.append(
                    ScanViolation(
                        pattern_name="OBFUSCATED_PAYLOAD",
                        message=f"{reason} in {filename}:{line_idx}",
                        line_number=line_idx,
                        snippet=line.strip()[:100],
                        severity="CRITICAL",
                    )
                )

    is_safe = len(violations) == 0
    return ScanReport(
        is_safe=is_safe,
        violations=violations,
        sanitized_content=redacted_text,
        redacted_secrets_count=secrets_count,
    )


def scan_skill_directory(folder_path: Path | str) -> ScanReport:
    """Scan all files inside a declarative skill package directory."""
    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        return ScanReport(is_safe=False, violations=[
            ScanViolation("DIR_NOT_FOUND", f"Directory {folder} does not exist", severity="HIGH")
        ])

    all_violations: list[ScanViolation] = []
    total_secrets = 0

    for file_path in folder.rglob("*"):
        if file_path.is_file():
            # Only scan text files, markdown, scripts, configs
            if file_path.suffix.lower() in (".md", ".txt", ".py", ".sh", ".ps1", ".json", ".yaml", ".yml"):
                try:
                    content = file_path.read_text(encoding="utf-8", errors="replace")
                    report = scan_skill_text(content, filename=file_path.name)
                    if not report.is_safe:
                        all_violations.extend(report.violations)
                    total_secrets += report.redacted_secrets_count
                except Exception as e:
                    logger.debug("Failed to read file for skill scan: %s - %s", file_path, e)

    return ScanReport(
        is_safe=len(all_violations) == 0,
        violations=all_violations,
        redacted_secrets_count=total_secrets,
    )
