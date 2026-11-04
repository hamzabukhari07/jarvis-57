"""
tests/test_engine_adapter_core.py — Unit tests for EngineAdapter Core, Event Allowlist,
and SafePromptManager (Step 2).
"""

import os
from pathlib import Path
import pytest

from core.engines.adapter import (
    ALLOWED_EVENT_TYPES,
    DISALLOWED_PAYLOAD_KEYS,
    EngineEvent,
    MilestoneDetector,
    SafePromptManager,
    build_sanitized_environment,
    redact_sensitive_tokens,
    sanitize_event_payload,
)


def test_redact_sensitive_tokens():
    """Verify that Gemini, Groq, and OpenAI keys are masked."""
    text = "Error with key AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6 and gsk_1234567890abcdef1234567890abcdef1234567890abcdef"
    redacted = redact_sensitive_tokens(text)
    assert "AIzaSy" not in redacted
    assert "gsk_" not in redacted
    assert "[REDACTED_API_KEY]" in redacted


def test_sanitize_event_payload_thought_suppression():
    """
    Verify that reasoning keys and embedded <think> blocks are completely eliminated
    from nested telemetry payloads.
    """
    dirty_payload = {
        "status": "processing",
        "thought": "This is internal reasoning that must not leak",
        "nested": {
            "thinking": "Deep cognitive model reflection",
            "message": "Public step update <think>secret thoughts</think> done.",
            "tool_call": {
                "name": "edit_file",
                "args": {"path": "main.py"},
                "chain_of_thought": "Should I edit line 5?",
            },
        },
    }

    clean = sanitize_event_payload(dirty_payload)

    # Assert disallowed keys are stripped
    assert "thought" not in clean
    assert "thinking" not in clean["nested"]
    assert "chain_of_thought" not in clean["nested"]["tool_call"]

    # Assert allowed keys and public content remain
    assert clean["status"] == "processing"
    assert clean["nested"]["message"] == "Public step update  done."
    assert clean["nested"]["tool_call"]["name"] == "edit_file"


def test_safe_prompt_manager_small_prompt(tmp_path):
    """Verify small prompt stays inline and creates no temp files."""
    mgr = SafePromptManager(tmp_path, "task_100")
    eff, pfile = mgr.write_prompt_if_needed("Small task prompt", threshold=800)
    assert eff == "Small task prompt"
    assert pfile is None
    mgr.cleanup()
    assert not (tmp_path / ".zezo_tmp").exists()


def test_safe_prompt_manager_large_prompt_lifecycle(tmp_path):
    """
    Verify large prompt (> 800 chars) writes to .zezo_tmp/prompt_<task_id>.md
    and cleanup deletes the file and empty directory.
    """
    large_prompt = "A" * 1500
    mgr = SafePromptManager(tmp_path, "task_200")
    eff, pfile = mgr.write_prompt_if_needed(large_prompt, threshold=800)

    assert pfile is not None
    assert pfile.exists()
    assert pfile.name == "prompt_task_200.md"
    assert "Execute all directives" in eff
    assert pfile.read_text(encoding="utf-8") == large_prompt

    # Cleanup must remove file and directory
    mgr.cleanup()
    assert not pfile.exists()
    assert not (tmp_path / ".zezo_tmp").exists()


def test_milestone_detector(tmp_path):
    """Verify milestone detector reports new files on disk without synthetic percentages."""
    initial = {"existing.txt"}
    (tmp_path / "existing.txt").write_text("old", encoding="utf-8")

    detector = MilestoneDetector(tmp_path, initial)
    assert len(detector.check_milestones()) == 0

    # Create deliverable DESIGN.md
    (tmp_path / "DESIGN.md").write_text("# Design Spec", encoding="utf-8")
    new_ms = detector.check_milestones()
    assert len(new_ms) == 1
    assert "Design Specification Generated" in new_ms[0]

    # Repeated check should not re-trigger same milestone
    assert len(detector.check_milestones()) == 0


def test_build_sanitized_environment(monkeypatch):
    """Verify environment sanitization injects safe baseline and config keys."""
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyTestKey1234567890123456789012345")
    env = build_sanitized_environment({"EXTRA_CUSTOM_FLAG": "ENABLED"})

    assert "SYSTEMROOT" in env or "PATH" in env
    assert env.get("PYTHONIOENCODING") == "utf-8"
    assert env.get("EXTRA_CUSTOM_FLAG") == "ENABLED"
    assert env.get("GEMINI_API_KEY") == "AIzaSyTestKey1234567890123456789012345"

