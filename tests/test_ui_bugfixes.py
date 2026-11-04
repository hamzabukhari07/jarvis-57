import os
from pathlib import Path
import pytest
from core.engines.antigravity import AntigravityEngineAdapter, EngineLaunchConfig

def test_antigravity_cli_prompt_under_800_chars():
    engine = AntigravityEngineAdapter()
    short_prompt = "Hello Antigravity, please print Hello World."
    config = EngineLaunchConfig(
        engine_id="antigravity_run",
        prompt=short_prompt,
        workspace_path=Path.cwd(),
    )
    cmd = engine.build_cli_command(config)
    assert "-p" in cmd
    idx = cmd.index("-p")
    assert cmd[idx + 1] == short_prompt

def test_antigravity_cli_prompt_over_800_chars_inlined_safely(tmp_path):
    engine = AntigravityEngineAdapter()
    long_instruction = "Task instruction: analyze the dental SaaS marketing strategy.\n"
    filler = "Detailed requirement step: evaluate conversion funnels and churn metrics.\n" * 20
    large_prompt = long_instruction + filler
    assert len(large_prompt) > 800

    prompt_file = tmp_path / "prompt_test.md"
    prompt_file.write_text(large_prompt, encoding="utf-8")

    config = EngineLaunchConfig(
        engine_id="antigravity_run",
        prompt=f"Task instructions are in: {prompt_file.name}",
        workspace_path=Path.cwd(),
    )
    cmd = engine.build_cli_command(config, prompt_file=prompt_file)
    assert "-p" in cmd
    idx = cmd.index("-p")
    passed_prompt = cmd[idx + 1]

    # Verify Antigravity receives the actual prompt content, not just a file path
    assert "Task instruction: analyze the dental SaaS marketing strategy." in passed_prompt
    assert "Detailed requirement step: evaluate conversion funnels and churn metrics." in passed_prompt
    assert not passed_prompt.startswith("Task instructions are in:")

def test_antigravity_cli_prompt_exceeding_max_cli_bound(tmp_path):
    engine = AntigravityEngineAdapter()
    huge_prompt = "A" * 30000
    prompt_file = tmp_path / "prompt_huge.md"
    prompt_file.write_text(huge_prompt, encoding="utf-8")

    config = EngineLaunchConfig(
        engine_id="antigravity_run",
        prompt=f"Task instructions are in: {prompt_file.name}",
        workspace_path=Path.cwd(),
    )
    cmd = engine.build_cli_command(config, prompt_file=prompt_file)
    assert "-p" in cmd
    idx = cmd.index("-p")
    passed_prompt = cmd[idx + 1]
    # For extreme sizes > 24,000 characters, falls back to explicit file read-and-execute instruction
    assert "Read and execute all directives and requirements in" in passed_prompt
    assert prompt_file.as_posix() in passed_prompt
