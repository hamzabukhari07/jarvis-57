"""
actions/opencode_agent.py — OpenCode Zen integration (async).

Delegates multi-file coding tasks to OpenCode CLI using Zen free models.
Returns immediately with a task_id; runs the CLI in a background thread.
Query progress with the task_status tool.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from core.repo_context import resolve
from core.task_manager import get_task_manager, TaskContext
from memory.config_manager import get_opencode_model

if platform.system() == "Windows":
    _WIN_HIDE = {"creationflags": subprocess.CREATE_NO_WINDOW}
else:
    _WIN_HIDE = {}


def _find_opencode_bin() -> Optional[str]:
    b = shutil.which("opencode") or shutil.which("opencode.exe")
    if b:
        return b
    home_bin = Path.home() / ".opencode" / "bin" / (
        "opencode.exe" if platform.system() == "Windows" else "opencode"
    )
    return str(home_bin) if home_bin.exists() else None


def _resolve_model(model: Optional[str]) -> str:
    selected = (model or "").strip() or get_opencode_model()
    if selected.startswith("zen/"):
        name = selected.replace("zen/", "")
        if "nemotron" in name:
            return "opencode/nemotron-3-ultra-free"
        if "pickle" in name:
            return "opencode/big-pickle"
        if "mimo" in name:
            return "opencode/mimo-v2.5-free"
        return f"opencode/{name}"
    return selected


def _run_worker(params: dict, ctx: TaskContext) -> dict:
    """Runs in the background thread. Streams progress, respects cancel."""
    repo = params["repo"]
    task = params["task"]
    model = params["model"]
    opencode_bin = params["bin"]

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    cmd = [opencode_bin, "run", task, "--model", model, "--auto"]

    ctx.report(2, f"launching OpenCode in {Path(repo).name}")

    proc = subprocess.Popen(
        cmd,
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        bufsize=1,
        **_WIN_HIDE,
    )

    tail: list[str] = []
    line_count = 0
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            if ctx.cancelled():
                proc.terminate()
                return {"status": "cancelled", "lines": line_count}
            text = line.rstrip()
            if not text:
                continue
            line_count += 1
            tail.append(text)
            if len(tail) > 30:
                tail.pop(0)
            # coarse progress: first 90% based on line count heuristic
            pct = min(90, 5 + line_count)
            ctx.report(pct, text)
    finally:
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

    return {
        "status": "success" if proc.returncode == 0 else "failed",
        "return_code": proc.returncode,
        "repo": repo,
        "model": model,
        "tail": tail[-10:],
    }


def opencode_agent(parameters: dict, player=None, speak=None) -> str:
    task = (parameters.get("task") or parameters.get("prompt") or "").strip()
    if not task:
        return "Please tell me the coding task you want OpenCode to run."

    explicit_path = (
        parameters.get("project_path") or parameters.get("path") or ""
    )
    repo, source = resolve(explicit=explicit_path)

    if repo is None:
        return (
            "I need to know which project to work in. "
            "Which folder should OpenCode edit? "
            "Give me the path, for example 'E:/projects/myapp'."
        )

    opencode_bin = _find_opencode_bin()
    if not opencode_bin:
        return (
            "OpenCode CLI is not installed. Run: "
            "npm install -g opencode-ai@latest   then   "
            "opencode auth login --provider zen"
        )

    model = _resolve_model(parameters.get("model"))

    tm = get_task_manager()
    task_id = tm.submit(
        "opencode_agent",
        _run_worker,
        {
            "repo": str(repo),
            "task": task,
            "model": model,
            "bin": opencode_bin,
        },
    )

    if player and hasattr(player, "show_content"):
        player.show_content(
            f"OPENCODE — {model}",
            f"Task: {task}\nRepo: {repo}\nID: {task_id}\nSource: {source}",
        )

    return (
        f"OpenCode is running task {task_id} in {repo.name} "
        f"using {model}. Ask me for its status any time."
    )


TOOL = {
    "name": "opencode_run",
    "description": (
        "Run OpenCode CLI for a MULTI-FILE coding task: full features, "
        "refactors, bug fixes that span several files. "
        "DO NOT use for a single function (use code_helper). "
        "DO NOT use for a single-file edit (use kilo_run). "
        "DO NOT use for repo analysis without changes (use dev_agent). "
        "The tool returns a task_id immediately; never wait for the "
        "result in the same turn. Ask the user for the project path "
        "if you do not have one — do not guess."
    ),
    "behavior": "NON_BLOCKING",
    "scheduling": "WHEN_IDLE",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "task": {
                "type": "STRING",
                "description": "Clear, detailed coding task.",
            },
            "model": {
                "type": "STRING",
                "description": "Optional OpenCode Zen model override.",
            },
            "project_path": {
                "type": "STRING",
                "description": (
                    "Absolute or user-typed path to the project folder. "
                    "If not given, JARVIS remembers the last used repo."
                ),
            },
        },
        "required": ["task"],
    },
    "handler": opencode_agent,
}
