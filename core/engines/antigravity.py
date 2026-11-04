"""
core/engines/antigravity.py — Google Antigravity CLI (agy) Engine Adapter.

Implements Antigravity CLI integration via Headless CLI Streaming (Mode A).
- Streams live telemetry using --output-format stream-json.
- Adheres strictly to the invariant: NEVER use --dangerously-skip-permissions.
  Uses safe headless print mode (-p/--print) or --mode accept-edits.
- Treats external engine output as untrusted input.
- Enforces strict thought suppression via the Event Allowlist.
- Runs contained inside Win32 Job Objects via ProcessSupervisor.

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
    EngineProtocol,
    sanitize_event_payload,
)

logger = logging.getLogger("zezo.engines.antigravity")


def _resolve_model(model: Optional[str]) -> str:
    """Resolve configured model or normalize short aliases.

    Validates against ANTIGRAVITY_CLI_MODELS. If invalid or unrecognized, logs a warning
    and returns empty string so the caller omits --model and agy uses its default.
    """
    from memory.config_manager import get_antigravity_model, DEFAULT_ANTIGRAVITY_MODEL
    from core.models import ANTIGRAVITY_MODEL_ALIASES, ANTIGRAVITY_CLI_MODELS
    selected = (model or "").strip() or get_antigravity_model() or DEFAULT_ANTIGRAVITY_MODEL
    if not selected:
        return ""
    canonical = ANTIGRAVITY_MODEL_ALIASES.get(selected.lower(), selected)
    if canonical in ANTIGRAVITY_CLI_MODELS:
        return canonical
    logger.warning(
        "antigravity: model '%s' (resolved from '%s') is not in ANTIGRAVITY_CLI_MODELS; "
        "omitting --model so agy uses its default.",
        canonical,
        selected,
    )
    return ""


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
    """Map of relative path -> mtime_ns for every file under `repo`."""
    out: dict[str, int] = {}
    skip = (
        ".git", "node_modules", ".venv", "venv", "__pycache__",
        "assets", "public", "images", "fonts", ".next", "dist", "build"
    )
    try:
        for p in repo.rglob("*"):
            if p.is_file() and not any(part in skip for part in p.parts):
                out[p.relative_to(repo).as_posix()] = p.stat().st_mtime_ns
    except Exception:
        pass
    return out


def _launch_smart_preview(repo: Path) -> None:
    """Smart preview opener when deliverables are generated."""
    idx = repo / "index.html"
    if idx.exists():
        import webbrowser
        try:
            from actions.website_cloner import start_local_preview_server
            preview_url, _ = start_local_preview_server(repo)
            webbrowser.open(preview_url)
            logger.info("Preview server opened via HTTP on %s", preview_url)
        except Exception:
            webbrowser.open(idx.resolve().as_uri())


def run_antigravity_task(payload: dict, ctx: Optional[Any] = None) -> dict:
    """
    Standardized worker executing Antigravity CLI via AntigravityEngineAdapter.
    Preserves repo snapshots, undo tracking, and deliverable summaries for TaskManager.
    """
    from core.repo_context import resolve
    from core.undo import capture_repo_snapshot, register_repo_undo

    prompt = (payload.get("prompt") or payload.get("task") or "").strip()
    repo_val = payload.get("project_path") or payload.get("repo") or payload.get("repo_path")
    if not repo_val:
        resolved_p, _ = resolve()
        repo = resolved_p or (Path.home() / "Desktop" / "website").resolve()
    else:
        repo = Path(repo_val).resolve()

    repo.mkdir(parents=True, exist_ok=True)
    _ensure_gitignore(repo)
    snapshot = capture_repo_snapshot(repo)
    before_tree = _tree_snapshot(repo)

    model_override = payload.get("model") or payload.get("model_id")
    resolved_model = _resolve_model(model_override)
    skip_preview = bool(payload.get("skip_preview", False))

    adapter = AntigravityEngineAdapter()
    config = EngineLaunchConfig(
        engine_id="antigravity",
        prompt=prompt,
        workspace_path=repo,
        model=resolved_model,
        task_id=getattr(ctx, "task_id", None),
        timeout_sec=int(payload.get("timeout_sec", 600)),
        protocol=EngineProtocol.CLI_STREAM,
    )

    res = adapter.execute(config, ctx=ctx)

    after_tree = _tree_snapshot(repo)
    created_list = [rel for rel, mt in after_tree.items() if before_tree.get(rel) != mt]
    entry_point = "index.html" if (repo / "index.html").exists() else "main.py"

    try:
        changed_count = register_repo_undo(repo, snapshot, "Antigravity Agent")
        if changed_count > 0 and created_list:
            first_file = Path(created_list[0]).name
            from memory.memory_manager import remember
            remember("active_file", first_file, category="projects")
    except Exception as e:
        logger.debug("Antigravity undo registration failed: %s", e)

    if not skip_preview and (repo / "index.html").exists():
        _launch_smart_preview(repo)

    is_success = res.get("status") == "done"
    summary = (
        f"Antigravity CLI successfully finished in '{repo.name}'."
        if is_success
        else f"Antigravity CLI exited with status: {res.get('error', 'failed')}."
    )

    deliverables = [f for f in ("DESIGN.md", "preview.html", "preview-dark.html", "index.html") if (repo / f).exists()]
    files_created_summary = ", ".join(deliverables or created_list[:4])
    hud_summary = (
        f"### ✅ Antigravity Build Complete\n\n"
        f"- **Workspace:** `{repo.name}`\n"
        f"- **Status:** {'Success' if is_success else 'Finished with warnings'}\n"
        f"- **Deliverables:** `{files_created_summary}`\n"
        f"- **Entrypoint:** `{entry_point}`\n"
    ) if files_created_summary else summary

    result_payload = {
        "status": "success" if is_success else "failed",
        "return_code": res.get("exit_code", 0 if is_success else 1),
        "repo": str(repo),
        "project_name": repo.name,
        "files": created_list,
        "entry_point": entry_point,
        "hud_summary": hud_summary,
        "summary": summary,
        "output": "\n".join(res.get("stdout_summary", [])),
        "prompt_full": prompt,
    }

    return result_payload


class AntigravityEngineAdapter(EngineAdapter):
    """Concrete adapter for Google Antigravity CLI (agy)."""

    def resolve_binary(self) -> Optional[Path]:
        """Discovers the absolute path to the agy binary."""
        # 1. Project-local tools directory
        local_candidates = [
            Path("tools") / "antigravity" / ("agy.exe" if platform.system() == "Windows" else "agy"),
            Path.cwd() / "tools" / "antigravity" / ("agy.exe" if platform.system() == "Windows" else "agy"),
        ]
        for lc in local_candidates:
            if lc.exists() and lc.is_file():
                return lc.resolve()

        # 2. Known user local AppData paths
        candidates = [
            Path.home() / "AppData" / "Local" / "agy" / "bin" / ("agy.exe" if platform.system() == "Windows" else "agy"),
            Path.home() / ".antigravity" / "bin" / ("agy.exe" if platform.system() == "Windows" else "agy"),
            Path.home() / ".agy" / "bin" / ("agy.exe" if platform.system() == "Windows" else "agy"),
        ]
        for c in candidates:
            if c.exists() and c.is_file():
                return c.resolve()

        # 3. System PATH
        for name in ("agy", "agy.exe", "antigravity", "antigravity.exe"):
            b = shutil.which(name)
            if b:
                return Path(b).resolve()

        return None

    def build_cli_command(self, config: EngineLaunchConfig, prompt_file: Optional[Path] = None) -> List[str]:
        """
        Builds the secure, argument-delimited agy command vector.
        Strictly omits --dangerously-skip-permissions.
        """
        bin_path = self.resolve_binary()
        if not bin_path:
            raise FileNotFoundError("Antigravity CLI binary (agy) not found.")

        # Determine effective prompt string
        # Antigravity CLI print mode (-p) supports inlining prompt text up to safe command line bounds (~24KB).
        # When prompt_file is provided by SafePromptManager for large prompts, read its full contents
        # so Antigravity receives the complete instruction rather than an unread file reference.
        # If the file exceeds safe limits (24,000 chars), pass an explicit instruction referencing the file.
        if prompt_file and prompt_file.exists():
            try:
                file_content = prompt_file.read_text(encoding="utf-8").strip()
                if file_content and len(file_content) <= 24000:
                    effective_prompt = file_content
                else:
                    effective_prompt = (
                        f"Read and execute all directives and requirements in {prompt_file.as_posix()} "
                        f"to complete the requested task."
                    )
            except Exception as e:
                logger.warning("[Antigravity] Failed to read prompt_file %s: %s", prompt_file, e)
                effective_prompt = config.prompt
        else:
            effective_prompt = config.prompt

        cmd = [
            str(bin_path),
            "-p",
            effective_prompt,
            "--add-dir",
            str(config.workspace_path.resolve()),
            "--output-format",
            "stream-json",
            "--mode",
            "accept-edits",  # Non-interactive automated edit mode without dangerous permission bypass
        ]

        if config.model:
            cmd.extend(["--model", config.model])

        return cmd

    def parse_stream_event(self, raw_line: str) -> Optional[EngineEvent]:
        """
        Parses stream-json NDJSON lines from agy, sanitizing thoughts and untrusted input.
        """
        if not raw_line or not raw_line.startswith("{"):
            return None

        try:
            raw_ev = json.loads(raw_line)
            if not isinstance(raw_ev, dict):
                return None

            # Untrusted input defense: sanitize recursively
            ev = sanitize_event_payload(raw_ev)

            # Extract event data
            step_update = ev.get("step_update") or ev.get("step") or ev.get("update")
            tool_name = ev.get("tool") or ev.get("tool_name") or ev.get("tool_status") or ev.get("tool_use")
            status_val = ev.get("status") or ev.get("state")
            text_val = ev.get("text") or ev.get("content") or ev.get("message") or ev.get("output")

            event_type = "status"
            msg = ""

            if tool_name:
                event_type = "tool_use"
                desc = ev.get("description") or ev.get("input") or ""
                desc_str = f"({desc[:60]}...)" if desc else ""
                msg = f"Tool: {tool_name} {desc_str}".strip()
            elif step_update:
                event_type = "step_start"
                msg = str(step_update)
            elif status_val:
                event_type = "status"
                msg = f"Status: {status_val}"
            elif text_val:
                event_type = "output"
                last_seg = str(text_val).strip().splitlines()[-1] if str(text_val).strip() else ""
                msg = last_seg[:100]

            if not msg:
                return None

            return EngineEvent(
                event_type=event_type,
                message=msg,
                step_label=msg[:60],
                payload=ev,
            )
        except Exception as e:
            logger.debug("[AntigravityEngineAdapter] Error parsing stream line: %s", e)
            return None

