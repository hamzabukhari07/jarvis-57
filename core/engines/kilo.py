"""
core/engines/kilo.py — Kilo Code CLI Engine Adapter.

Implements Kilo Code CLI integration via Headless CLI Streaming (Mode A).
- Streams live telemetry using --format json.
- Adheres strictly to security requirements:
  - Never uses --dangerously-skip-permissions.
  - Treats external engine output as untrusted input.
  - Enforces strict thought suppression via the Event Allowlist.
  - Runs contained inside Win32 Job Objects via ProcessSupervisor.
- Note: Kilo Code CLI does not support stdio ACP (uses local HTTP/WS).
  Mode A is the designated stable execution path for Kilo.

Author: Hamza Bukhari
"""

from __future__ import annotations

import json
import logging
import platform
import shutil
from pathlib import Path
from typing import List, Optional

from core.engines.adapter import (
    EngineAdapter,
    EngineEvent,
    EngineLaunchConfig,
    sanitize_event_payload,
)

logger = logging.getLogger("zezo.engines.kilo")


def _ensure_gitignore(repo_path: Path) -> None:
    """Ensure minimal .gitignore exists in repo so scanners don't index huge dependencies."""
    try:
        if not repo_path.exists():
            return
        gi = repo_path / ".gitignore"
        ignore_entries = [
            "node_modules/",
            ".venv/",
            "venv/",
            "__pycache__/",
            ".next/",
            "dist/",
            "build/",
            "*.log",
        ]
        if not gi.exists():
            gi.write_text("\n".join(ignore_entries) + "\n", encoding="utf-8")
        else:
            existing = gi.read_text(encoding="utf-8", errors="ignore")
            missing = [entry for entry in ignore_entries if entry.strip("/") not in existing]
            if missing:
                with open(gi, "a", encoding="utf-8") as f:
                    f.write("\n# Auto-added ignore rules\n" + "\n".join(missing) + "\n")
    except Exception:
        pass


def _tree_snapshot(repo: Path) -> dict[str, int]:
    """Map of relative path -> mtime_ns for files under repo."""
    out: dict[str, int] = {}
    skip = (".git", "node_modules", ".venv", "__pycache__")
    try:
        for p in repo.rglob("*"):
            if any(part in skip for part in p.parts):
                continue
            if p.is_file():
                try:
                    out[str(p.relative_to(repo))] = p.stat().st_mtime_ns
                except OSError:
                    pass
    except Exception:
        pass
    return out


def run_kilo_task(payload: dict, ctx: Any) -> dict:
    """Standardized worker executing Kilo Code via KiloEngineAdapter."""
    from core.repo_context import resolve
    from core.undo import capture_repo_snapshot, register_repo_undo
    from memory.config_manager import get_kilo_model
    import re

    prompt = payload.get("prompt") or payload.get("task") or ""
    if not prompt:
        if hasattr(ctx, "on_fail"):
            ctx.on_fail("No prompt provided for Kilo Code execution.")
        return {"status": "error", "message": "No prompt provided"}

    repo_val = payload.get("repo") or payload.get("cwd") or payload.get("project_path")
    if not repo_val:
        resolved_p, _ = resolve()
        repo = resolved_p or (Path.home() / "Desktop" / "website").resolve()
    else:
        repo = Path(repo_val).resolve()

    repo.mkdir(parents=True, exist_ok=True)
    _ensure_gitignore(repo)

    # Pre-fetch fallback hook
    url_match = re.search(r"https?://[^\s\"'>]+", prompt)
    if url_match and not (repo / "site_dom.html").exists():
        target_url = url_match.group(0).rstrip(".,;)")
        try:
            from core.url_prefetch import prefetch_url_assets
            prefetch_url_assets(target_url, repo, ctx)
        except Exception as e_pref:
            logger.warning("prefetch_url_assets failed for %s: %s", target_url, e_pref)

    snapshot = capture_repo_snapshot(repo)
    before_tree = _tree_snapshot(repo)

    model = payload.get("model") or payload.get("model_id") or get_kilo_model() or "kilo/default"
    owns_task = bool(payload.get("owns_task", True))

    adapter = KiloEngineAdapter()
    config = EngineLaunchConfig(
        engine_id="kilo",
        prompt=prompt,
        workspace_path=repo,
        model=model,
        task_id=getattr(ctx, "task_id", None),
        timeout_sec=int(payload.get("timeout_sec", 600)),
        protocol=EngineProtocol.CLI_STREAM,
        auto_approve_edits=True,
    )

    res = adapter.execute(config, ctx=ctx)

    if hasattr(ctx, "cancelled") and ctx.cancelled():
        return {"status": "cancelled", "repo": str(repo)}

    after_tree = _tree_snapshot(repo)
    created_list = [rel for rel, mt in after_tree.items() if before_tree.get(rel) != mt]
    entry_point = "index.html" if (repo / "index.html").exists() else "main.py"

    try:
        undo_entry = register_repo_undo(str(repo), snapshot, "Kilo Code")
        if undo_entry and undo_entry.get("changes"):
            first_file = Path(undo_entry["changes"][0]["path"]).name
            from memory.memory_manager import remember
            remember("active_file", first_file, category="projects")
    except Exception as e:
        logger.debug("Kilo undo registration failed: %s", e)

    is_success = res.get("status") == "done"
    summary = (
        f"Kilo Code successfully finished in '{repo.name}'."
        if is_success
        else f"Kilo Code exited with status: {res.get('error', 'failed')}."
    )

    result_payload = {
        "status": "success" if is_success else "failed",
        "return_code": res.get("exit_code", 0 if is_success else 1),
        "repo": str(repo),
        "project_name": repo.name,
        "files": created_list,
        "entry_point": entry_point,
        "summary": summary,
        "model": model,
        "tail": res.get("stdout_summary", [])[-15:],
    }

    if owns_task:
        if is_success and hasattr(ctx, "on_complete"):
            ctx.on_complete(result_payload)
        elif not is_success and hasattr(ctx, "on_fail"):
            ctx.on_fail(summary)

    return result_payload


class KiloEngineAdapter(EngineAdapter):
    """Concrete adapter for Kilo Code CLI (kilo / kilo.cmd)."""

    def resolve_binary(self) -> Optional[Path]:
        """Discovers the absolute path to the kilo binary."""
        # 1. Project-local tools directory
        local_candidates = [
            Path("tools") / "kilo" / ("kilo.exe" if platform.system() == "Windows" else "kilo"),
            Path.cwd() / "tools" / "kilo" / ("kilo.exe" if platform.system() == "Windows" else "kilo"),
            Path("tools") / "kilo" / "kilo.cmd",
        ]
        for lc in local_candidates:
            if lc.exists() and lc.is_file():
                return lc.resolve()

        # 2. System PATH
        for name in ("kilo", "kilo.exe", "kilo.cmd", "kilocode", "kilocode.cmd"):
            b = shutil.which(name)
            if b:
                return Path(b).resolve()

        # 3. Known user and npm global paths
        candidates = [
            Path.home() / ".kilo" / "bin" / ("kilo.exe" if platform.system() == "Windows" else "kilo"),
            Path.home() / "AppData" / "Roaming" / "npm" / "kilo.cmd",
            Path.home() / "AppData" / "Local" / "kilo" / "bin" / "kilo.exe",
        ]
        for c in candidates:
            if c.exists() and c.is_file():
                return c.resolve()

        return None

    def build_cli_command(self, config: EngineLaunchConfig, prompt_file: Optional[Path] = None) -> List[str]:
        """
        Builds the secure, argument-delimited kilo command vector.
        Strictly avoids dangerous permission bypasses.
        """
        bin_path = self.resolve_binary()
        if not bin_path:
            raise FileNotFoundError("Kilo Code CLI binary not found.")

        cmd: List[str] = [str(bin_path), "run"]

        if prompt_file and prompt_file.exists():
            cmd.extend([
                f"Execute the task outlined in {prompt_file.as_posix()}",
                "--file",
                str(prompt_file.resolve()),
            ])
        else:
            cmd.append(config.prompt)

        cmd.extend([
            "--dir",
            str(config.workspace_path.resolve()),
            "--format",
            "json",
        ])

        if config.model:
            cmd.extend(["--model", config.model])

        if config.auto_approve_edits:
            cmd.append("--auto")

        return cmd

    def parse_stream_event(self, raw_line: str) -> Optional[EngineEvent]:
        """
        Parses JSON stream events from Kilo Code, sanitizing thoughts and untrusted input.
        """
        if not raw_line or not raw_line.startswith("{"):
            return None

        try:
            raw_ev = json.loads(raw_line)
            if not isinstance(raw_ev, dict):
                return None

            ev = sanitize_event_payload(raw_ev)

            ev_type = ev.get("type") or ev.get("event") or "status"
            msg = ""
            event_type = "status"

            if ev_type in ("tool_use", "tool_call"):
                event_type = "tool_use"
                tool_name = ev.get("tool") or ev.get("name") or (ev.get("data", {}).get("tool") if isinstance(ev.get("data"), dict) else "tool")
                msg = f"Tool: {tool_name}"
            elif ev_type in ("step_start", "step"):
                event_type = "step_start"
                step_title = ev.get("title") or ev.get("message") or (ev.get("data", {}).get("title") if isinstance(ev.get("data"), dict) else "Step")
                msg = str(step_title)
            elif ev_type in ("error", "fatal"):
                event_type = "error"
                msg = ev.get("message") or ev.get("error") or "Kilo encountered an error."
            elif ev_type in ("message", "content", "text"):
                event_type = "output"
                content = ev.get("content") or ev.get("text") or (ev.get("data", {}).get("content") if isinstance(ev.get("data"), dict) else "")
                if content:
                    last_line = str(content).strip().splitlines()[-1]
                    msg = last_line[:100]
            else:
                m = ev.get("message") or ev.get("status") or ev.get("title")
                if m:
                    msg = str(m)[:100]

            if not msg:
                return None

            return EngineEvent(
                event_type=event_type,
                message=msg,
                step_label=msg[:60],
                payload=ev,
            )
        except Exception as e:
            logger.debug("[KiloEngineAdapter] Error parsing stream line: %s", e)
            return None

