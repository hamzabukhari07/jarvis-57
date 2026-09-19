"""
actions/kilo_agent.py — Kilo Code integration (async).

Delegates multi-file edits and refactors to Kilo Code CLI using free models.
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
from memory.config_manager import get_kilo_model

if platform.system() == "Windows":
    _WIN_HIDE = {"creationflags": subprocess.CREATE_NO_WINDOW}
else:
    _WIN_HIDE = {}


def _find_kilo_bin() -> Optional[str]:
    for name in ("kilo", "kilo.exe", "kilocode", "kilocode.exe"):
        b = shutil.which(name)
        if b:
            return b
    home_bin = Path.home() / ".kilo" / "bin" / (
        "kilo.exe" if platform.system() == "Windows" else "kilo"
    )
    return str(home_bin) if home_bin.exists() else None


def _resolve_model(model: Optional[str]) -> str:
    selected = (model or "").strip() or get_kilo_model()
    if not selected.startswith("kilo/"):
        return f"kilo/{selected}"
    return selected


def _run_worker(params: dict, ctx: TaskContext) -> dict:
    repo = params["repo"]
    task = params["task"]
    model = params["model"]
    kilo_bin = params["bin"]

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    cmd = [kilo_bin, "run", task, "--model", model, "--auto"]
    ctx.report(2, f"launching Kilo in {Path(repo).name}")

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
            ctx.report(min(90, 5 + line_count), text)
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


def kilo_agent(parameters: dict, player=None, speak=None) -> str:
    task = (parameters.get("task") or parameters.get("prompt") or "").strip()
    if not task:
        return "Please tell me the coding task you want Kilo Code to run."

    explicit_path = (
        parameters.get("project_path") or parameters.get("path") or ""
    )
    repo, source = resolve(explicit=explicit_path)

    if repo is None:
        return (
            "I need to know which project to work in. "
            "Which folder should Kilo Code edit? "
            "Give me the path, for example 'E:/projects/myapp'."
        )

    kilo_bin = _find_kilo_bin()
    if not kilo_bin:
        return (
            "Kilo Code CLI is not installed. "
            "Run: npm install -g @kilocode/cli   or install "
            "Kilo Code from https://kilo.ai"
        )

    model = _resolve_model(parameters.get("model"))

    tm = get_task_manager()
    task_id = tm.submit(
        "kilo_agent",
        _run_worker,
        {
            "repo": str(repo),
            "task": task,
            "model": model,
            "bin": kilo_bin,
        },
    )

    if player and hasattr(player, "show_content"):
        player.show_content(
            f"KILO — {model}",
            f"Task: {task}\nRepo: {repo}\nID: {task_id}\nSource: {source}",
        )

    return (
        f"Kilo Code is running task {task_id} in {repo.name} "
        f"using {model}. Ask me for its status any time."
    )


TOOL = {
    "name": "kilo_run",
    "description": (
        "Run Kilo Code CLI for multi-file edits WITHIN one project: "
        "refactors, targeted changes across 2-3 files. "
        "DO NOT use for a single function (use code_helper). "
        "DO NOT use for a full autonomous feature (use opencode_run). "
        "Returns a task_id immediately. Ask the user for the project "
        "path if you do not have one."
    ),
    "behavior": "NON_BLOCKING",
    "scheduling": "WHEN_IDLE",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "task": {"type": "STRING", "description": "Clear coding task."},
            "model": {"type": "STRING", "description": "Optional Kilo model override."},
            "project_path": {
                "type": "STRING",
                "description": "Project folder path.",
            },
        },
        "required": ["task"],
    },
    "handler": kilo_agent,
}
