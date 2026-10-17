"""
Local UI WebSocket & Static HTTP Server for ZEZO.
Bridges the Python agent engine (main.py, task_manager, log_bus) with the
modern HTML5 / ES Modules desktop web frontend.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import threading
import platform
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

from aiohttp import web, WSMsgType

logger = logging.getLogger("zezo.ui_server")

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"


def _norm_token(s: str) -> str:
    """Normalized match key: lowercased, spaces/underscores/hyphens removed."""
    return re.sub(r"[\s_\-]+", "", (s or "").lower())


def _scan_folder(root: Path, cap: int = 5000) -> tuple[list[str], int, bool]:
    """Bounded recursive scan so a huge dropped folder never blocks the request.

    Returns (relative_paths, total_size_bytes_of_scanned_files, truncated).
    """
    rel_paths: list[str] = []
    total = 0
    truncated = False
    try:
        for dirpath, _dirs, files in os.walk(root):
            for fn in files:
                if len(rel_paths) >= cap:
                    truncated = True
                    return rel_paths, total, truncated
                fp = Path(dirpath) / fn
                try:
                    total += fp.stat().st_size
                except Exception:
                    pass
                try:
                    rel_paths.append(str(fp.relative_to(root)))
                except Exception:
                    rel_paths.append(fn)
    except Exception:
        pass
    return rel_paths, total, truncated


class ZezoUIServer:
    """Thread-safe local WebSocket & Static file server for the desktop Web UI."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self.host = host
        self.port = port
        self.frontend_dir = FRONTEND_DIR
        self._clients: set[web.WebSocketResponse] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None
        self._stopped = threading.Event()

        # Lazy attachment registry: dropped/uploaded files are registered by
        # path only and NOT read until the user explicitly asks (file_processor
        # resolves them from here). Keeps the drop path instant and silent.
        self._attached: list[dict[str, Any]] = []
        self._attached_lock = threading.Lock()

        # Callbacks from main.py / engine
        self.on_text_command: Callable[[str], None] | None = None
        self.on_interrupt: Callable[[], None] | None = None
        self.on_mute_toggle: Callable[[bool], None] | None = None
        self.on_speaker_mute_toggle: Callable[[bool], None] | None = None
        self.on_sleep_toggle: Callable[[bool], None] | None = None
        self.on_remote_clicked: Callable[[], tuple[str, str] | None] | None = None
        self.on_file_uploaded: Callable[[dict[str, Any]], None] | None = None
        self.on_assistant_settings_changed: Callable[[str, str, str], None] | None = None
        self.on_pipeline_settings_changed: Callable[[], None] | None = None
        self.on_audio_devices_changed: Callable[[str, str], None] | None = None
        self.get_initial_state: Callable[[], dict[str, Any]] | None = None

    def start(self) -> None:
        """Start the server in a background daemon thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stopped.clear()
        self._thread = threading.Thread(target=self._run_thread, daemon=True, name="ZezoUIServer")
        self._thread.start()

    def _run_thread(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._start_server())
        try:
            self._loop.run_forever()
        finally:
            self._loop.run_until_complete(self._cleanup())
            self._loop.close()

    async def _start_server(self) -> None:
        app = web.Application()
        app.router.add_get("/", self._index_handler)
        app.router.add_get("/index.html", self._index_handler)
        app.router.add_get("/office", self._office_view_handler)
        app.router.add_get("/ws", self._ws_handler)
        app.router.add_get("/api/health", self._health_handler)
        app.router.add_get("/api/tools", self._tools_inspection_handler)
        app.router.add_get("/api/tasks", self._tasks_list_handler)
        app.router.add_get("/api/fleet/state", self._fleet_state_handler)
        app.router.add_get("/api/fleet/agent", self._fleet_agent_profile_handler)
        app.router.add_post("/api/fleet/save_agent", self._fleet_save_agent_handler)
        app.router.add_post("/api/fleet/save_soul", self._fleet_save_soul_handler)
        app.router.add_post("/api/fleet/dispatch_task", self._fleet_dispatch_task_handler)
        app.router.add_post("/api/fleet/chat", self._fleet_chat_handler)
        app.router.add_post("/api/fleet/delete_agent", self._fleet_delete_agent_handler)
        app.router.add_post("/api/fleet/open_folder", self._fleet_open_folder_handler)
        app.router.add_post("/api/fleet/pick_folder", self._fleet_pick_folder_handler)
        app.router.add_post("/api/upload", self._upload_handler)
        app.router.add_get("/api/config", self._get_config_handler)
        app.router.add_post("/api/config", self._save_config_handler)
        app.router.add_get("/api/settings/assistant", self._get_config_handler)
        app.router.add_post("/api/settings/assistant", self._save_assistant_settings_handler)
        app.router.add_get("/api/settings/agents", self._get_config_handler)
        app.router.add_post("/api/settings/agents", self._save_agents_settings_handler)
        app.router.add_get("/api/settings/pipeline", self._get_config_handler)
        app.router.add_post("/api/settings/pipeline", self._save_pipeline_settings_handler)
        app.router.add_get("/api/settings/keys", self._get_config_handler)
        app.router.add_post("/api/settings/keys", self._save_keys_settings_handler)
        app.router.add_get("/api/preview_voice", self._preview_voice_handler)
        app.router.add_get("/api/models", self._models_list_handler)
        app.router.add_get("/api/audio_devices", self._audio_devices_handler)
        app.router.add_get("/api/skills", self._skills_list_handler)
        app.router.add_post("/api/skills/mode", self._skills_mode_handler)
        app.router.add_post("/api/skills/install", self._skills_install_handler)
        app.router.add_post("/api/skills/save", self._skills_save_handler)
        app.router.add_post("/api/skills/delete", self._skills_delete_handler)
        app.router.add_get("/api/attachments", self._attachments_list_handler)
        app.router.add_get("/api/memory/stats", self._memory_stats_handler)
        app.router.add_get("/api/memory/graph", self._memory_graph_handler)
        app.router.add_get("/api/memory/notes", self._memory_notes_list_handler)
        app.router.add_get("/api/memory/note", self._memory_note_detail_handler)
        app.router.add_post("/api/memory/note", self._memory_save_note_handler)
        app.router.add_post("/api/memory/add", self._memory_create_note_handler)
        app.router.add_post("/api/memory/delete", self._memory_delete_note_handler)
        app.router.add_post("/api/memory/clear", self._memory_clear_handler)
        app.router.add_post("/api/memory/wipe_all", self._memory_wipe_all_handler)
        app.router.add_post("/api/memory/optimize", self._memory_optimize_handler)
        app.router.add_post("/api/workspace/set", self._workspace_set_handler)
        app.router.add_get("/api/remote", self._remote_gateway_handler)
        app.router.add_post("/api/remote/new_key", self._remote_new_key_handler)
        app.router.add_get("/api/backend_logs", self._get_backend_logs_handler)
        app.router.add_post("/api/backend_logs/clear", self._clear_backend_logs_handler)
        app.router.add_get("/api/system/status", self._system_status_handler)
        app.router.add_get("/zezo-avatar.png", self._avatar_handler)
        app.router.add_get("/favicon.ico", self._favicon_handler)

        # Serve compiled React SPA (frontend/dist) static assets
        frontend_dist = self.frontend_dir / "dist"
        if (frontend_dist / "assets").exists():
            app.router.add_static("/assets", path=str(frontend_dist / "assets"), show_index=False)

        # Serve frontend public static assets (avatar, icons, audio)
        frontend_public = self.frontend_dir / "public"
        if frontend_public.exists():
            app.router.add_static("/public", path=str(frontend_public), show_index=False)

        self._runner = web.AppRunner(app)
        await self._runner.setup()

        # Attempt to bind to requested port, with fallback retry
        for attempt in range(5):
            try:
                self._site = web.TCPSite(self._runner, self.host, self.port)
                await self._site.start()
                logger.info("Zezo UI Server running at http://%s:%d", self.host, self.port)
                self._log_bus_task = asyncio.create_task(self._poll_log_bus_loop())
                break
            except OSError:
                if attempt == 4:
                    raise
                self.port += 1

    async def _poll_log_bus_loop(self) -> None:
        cursor = 0
        while not self._stopped.is_set():
            try:
                await asyncio.sleep(0.25)
                if not self._clients:
                    continue
                try:
                    from core import log_bus
                    new_lines, cursor = log_bus.since(cursor, min_level="DEBUG")
                    if new_lines:
                        self.broadcast("backend_logs", {
                            "lines": new_lines,
                            "stats": log_bus.stats(),
                            "sources": log_bus.sources()
                        })
                except Exception as e:
                    logger.debug("log_bus polling error: %s", e)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug("Error in log bus polling task: %s", e)

    async def _health_handler(self, request: web.Request) -> web.Response:
        return web.json_response({"status": "ok", "app": "ZEZO", "port": self.port})

    async def _tools_inspection_handler(self, request: web.Request) -> web.Response:
        """Inspect allowed and filtered tools with reasons, optionally scoped by agent_id or mode."""
        agent_id = request.query.get("agent_id") or request.query.get("agent")
        mode = request.query.get("mode")
        try:
            from core.action_loader import get_action_registry
            reg = get_action_registry()
            res = reg.filter_tools(agent_id=agent_id, mode=mode)
            return web.json_response({"status": "success", "data": res})
        except Exception as e:
            logger.exception("Error in /api/tools handler: %s", e)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _tasks_list_handler(self, request: web.Request) -> web.Response:
        """Fetch all background tasks categorized for Kanban boards and monitoring."""
        try:
            from core.task_manager import get_task_manager
            tm = get_task_manager()
            tasks = tm.all_tasks()
            return web.json_response({"status": "success", "tasks": tasks})
        except Exception as e:
            logger.exception("Error in /api/tasks handler: %s", e)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    # ── Lazy attachment registry ──────────────────────────────────────────
    def register_attachment(self, info: dict[str, Any]) -> None:
        """Register a dropped/uploaded file by path only. Content is read later,
        on demand, when the user asks (file_processor pulls from here)."""
        with self._attached_lock:
            self._attached = [a for a in self._attached if a.get("path") != info.get("path")]
            self._attached.insert(0, info)
            del self._attached[50:]  # keep the 50 most recent

    def list_attachments(self) -> list[dict[str, Any]]:
        with self._attached_lock:
            return list(self._attached)

    def latest_attachment(self) -> dict[str, Any] | None:
        with self._attached_lock:
            return dict(self._attached[0]) if self._attached else None

    def find_attachment(self, name: str) -> dict[str, Any] | None:
        """Match an attachment by name (normalized, then substring) for multi-file drops."""
        target = _norm_token(name)
        if not target:
            return None
        with self._attached_lock:
            items = list(self._attached)
        for a in items:
            if _norm_token(a.get("name", "")) == target:
                return dict(a)
        for a in items:
            key = _norm_token(a.get("name", ""))
            if target in key or key in target:
                return dict(a)
        return None

    def remove_attachment(self, path: str) -> None:
        with self._attached_lock:
            self._attached = [a for a in self._attached if a.get("path") != path]

    def clear_attachments(self) -> None:
        with self._attached_lock:
            self._attached = []

    async def _upload_handler(self, request: web.Request) -> web.Response:
        try:
            reader = await request.multipart()
            uploads_dir = BASE_DIR / "uploads"
            uploads_dir.mkdir(parents=True, exist_ok=True)

            saved_files = []
            has_folder = False
            root_folder_name = ""

            while True:
                part = await reader.next()
                if part is None:
                    break
                if part.filename:
                    # Sanitize relative path to prevent path traversal
                    raw_rel = part.filename.replace("\\", "/").strip("/")
                    parts = [p for p in raw_rel.split("/") if p and p not in ("..", ".")]
                    if not parts:
                        continue

                    if len(parts) > 1:
                        has_folder = True
                        if not root_folder_name:
                            root_folder_name = parts[0]
                        dest_file = uploads_dir.joinpath(*parts)
                    else:
                        dest_file = uploads_dir / parts[0]

                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(dest_file, "wb") as f:
                        while True:
                            chunk = await part.read_chunk()
                            if not chunk:
                                break
                            f.write(chunk)
                    saved_files.append(dest_file)

            if not saved_files:
                return web.json_response({"status": "error", "message": "No files received"}, status=400)

            # Folder drop: register as the active workspace (cheap metadata, so
            # coding commands keep their target) but DO NOT read its contents.
            # A bounded scan keeps a huge folder from blocking the request.
            if has_folder and root_folder_name:
                root_folder_dir = uploads_dir / root_folder_name
                from core.repo_context import remember_repo
                remember_repo(str(root_folder_dir))
                try:
                    from memory.memory_manager import remember
                    remember("active_project", str(root_folder_dir), category="projects")
                except Exception:
                    pass

                rel_paths, total_size, truncated = _scan_folder(root_folder_dir, cap=5000)

                folder_info = {
                    "name": root_folder_name,
                    "path": str(root_folder_dir),
                    "size": total_size,
                    "file_type": "folder",
                    "is_folder": True,
                    "files_count": len(rel_paths),
                    "text": "",
                    "engine": "attached",
                    "is_truncated": truncated,
                }

                self.register_attachment(folder_info)
                self.broadcast("file_ingested", folder_info)
                self.broadcast("log", {
                    "text": f"[Payload] Attached workspace folder '{root_folder_name}' ({len(rel_paths)} files). Read on request."
                })

                if self.on_file_uploaded:
                    try:
                        self.on_file_uploaded(folder_info)
                    except Exception as e:
                        logger.warning("on_file_uploaded callback error: %s", e)

                return web.json_response({
                    "status": "success",
                    "folder": folder_info,
                    "files": [folder_info],
                })

            # Lazy: register each file by path only. Content is read later, on
            # demand, via file_processor — nothing is extracted on the drop path.
            results = []
            for sf in saved_files:
                file_info = {
                    "name": sf.name,
                    "path": str(sf),
                    "size": sf.stat().st_size,
                    "file_type": sf.suffix.lower().lstrip(".") or "file",
                    "engine": "attached",
                    "text": "",
                    "is_truncated": False,
                    "is_folder": False,
                }
                results.append(file_info)

                self.register_attachment(file_info)
                self.broadcast("file_ingested", file_info)
                self.broadcast("log", {
                    "text": f"[Payload] Attached '{sf.name}' ({sf.stat().st_size:,} bytes). Read on request."
                })

                if self.on_file_uploaded:
                    try:
                        self.on_file_uploaded(file_info)
                    except Exception as e:
                        logger.warning("on_file_uploaded callback error: %s", e)

            return web.json_response({
                "status": "success",
                "files": results
            })
        except Exception as e:
            logger.exception("Upload handler error: %s", e)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _save_keys_settings_handler(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
            from memory.config_manager import (
                save_api_keys_transactional, is_configured, get_masked_gemini_key,
                get_masked_groq_key, get_masked_elevenlabs_key, get_masked_tavily_key,
                get_groq_api_key, get_elevenlabs_api_key, get_tavily_api_key,
            )

            gemini_key = data.get("gemini_api_key")
            groq_key = data.get("groq_api_key")
            elevenlabs_key = data.get("elevenlabs_api_key")
            tavily_key = data.get("tavily_api_key")

            ok, err = save_api_keys_transactional(
                gemini_api_key=gemini_key,
                groq_api_key=groq_key,
                elevenlabs_api_key=elevenlabs_key,
                tavily_api_key=tavily_key,
                validate=True,
            )
            if not ok:
                return web.json_response({"status": "error", "message": err}, status=400)

            res_payload = {
                "has_gemini_key": is_configured(),
                "gemini_api_key_masked": get_masked_gemini_key(),
                "has_groq_key": bool(get_groq_api_key()),
                "groq_api_key_masked": get_masked_groq_key(),
                "has_elevenlabs_key": bool(get_elevenlabs_api_key()),
                "elevenlabs_api_key_masked": get_masked_elevenlabs_key(),
                "has_tavily_key": bool(get_tavily_api_key()),
                "tavily_api_key_masked": get_masked_tavily_key(),
            }
            self.broadcast("api_keys_updated", res_payload)
            return web.json_response({"status": "success", "data": res_payload})
        except Exception as e:
            logger.exception("Save API keys error: %s", e)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _save_assistant_settings_handler(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
            voice = str(data.get("voice_name", "Charon")).strip() or "Charon"
            lang = str(data.get("response_language", "auto")).strip() or "auto"
            fallback_voice = data.get("fallback_voice")

            from memory.config_manager import (
                save_assistant_config, save_voice, save_response_language, get_assistant_name,
                save_api_keys_transactional, is_configured, get_masked_gemini_key, get_masked_groq_key,
                get_masked_elevenlabs_key, get_masked_tavily_key, save_fallback_voice, get_fallback_voice,
                save_voice_fallback_mode, get_voice_fallback_mode, get_groq_api_key, get_elevenlabs_api_key, get_tavily_api_key,
            )
            name = str(data.get("assistant_name") or "").strip() or get_assistant_name()

            gemini_key = data.get("gemini_api_key")
            groq_key = data.get("groq_api_key")
            elevenlabs_key = data.get("elevenlabs_api_key")
            tavily_key = data.get("tavily_api_key")
            if gemini_key is not None or groq_key is not None or elevenlabs_key is not None or tavily_key is not None:
                ok, err = save_api_keys_transactional(
                    gemini_api_key=gemini_key,
                    groq_api_key=groq_key,
                    elevenlabs_api_key=elevenlabs_key,
                    tavily_api_key=tavily_key,
                    validate=True,
                )
                if not ok:
                    return web.json_response({"status": "error", "message": err}, status=400)

            save_assistant_config(name, "")
            save_voice(voice)
            save_response_language(lang)
            if fallback_voice is not None:
                save_fallback_voice(str(fallback_voice))

            voice_fallback = data.get("voice_fallback")
            if voice_fallback is not None:
                if isinstance(voice_fallback, bool):
                    save_voice_fallback_mode("auto" if voice_fallback else "off")
                else:
                    save_voice_fallback_mode(str(voice_fallback))

            if self.on_assistant_settings_changed:
                try:
                    self.on_assistant_settings_changed(name, voice, lang)
                except Exception as e:
                    logger.warning("on_assistant_settings_changed error: %s", e)

            res_payload = {
                "assistant_name": name,
                "voice_name": voice,
                "response_language": lang,
                "fallback_voice": get_fallback_voice(),
                "voice_fallback": get_voice_fallback_mode(),
                "voice_fallback_enabled": get_voice_fallback_mode() == "auto",
                "has_gemini_key": is_configured(),
                "gemini_api_key_masked": get_masked_gemini_key(),
                "has_groq_key": bool(get_groq_api_key()),
                "groq_api_key_masked": get_masked_groq_key(),
                "has_elevenlabs_key": bool(get_elevenlabs_api_key()),
                "elevenlabs_api_key_masked": get_masked_elevenlabs_key(),
            }
            self.broadcast("assistant_settings_updated", res_payload)

            return web.json_response({
                "status": "success",
                "data": res_payload
            })
        except Exception as e:
            logger.exception("Save assistant settings error: %s", e)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _save_agents_settings_handler(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
            from memory.config_manager import (
                save_preferred_creation_agent, get_preferred_creation_agent,
                save_preferred_edit_agent, get_preferred_edit_agent,
                CREATION_AGENTS, EDIT_AGENTS,
            )

            creation_agent = data.get("preferred_creation_agent")
            if creation_agent is not None:
                save_preferred_creation_agent(str(creation_agent))

            edit_agent = data.get("preferred_edit_agent")
            if edit_agent is not None:
                save_preferred_edit_agent(str(edit_agent))

            res_payload = {
                "preferred_creation_agent": get_preferred_creation_agent(),
                "preferred_edit_agent": get_preferred_edit_agent(),
                "creation_agents": list(CREATION_AGENTS),
                "edit_agents": list(EDIT_AGENTS),
            }
            self.broadcast("agent_settings_updated", res_payload)

            return web.json_response({
                "status": "success",
                "data": res_payload
            })
        except Exception as e:
            logger.exception("Save agent settings error: %s", e)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _save_pipeline_settings_handler(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
            mode = str(data.get("pipeline_mode", "live")).strip().lower() or "live"

            from memory.config_manager import (
                save_pipeline_mode, save_stt_engine, save_llm_engine,
                save_tts_engine, save_tts_voice, save_voice_fallback_mode,
                get_pipeline_mode, get_stt_engine, get_llm_engine, get_tts_engine, get_tts_voice,
                get_voice_fallback_mode, get_groq_api_key, get_masked_groq_key, save_api_keys_transactional,
                is_configured, get_masked_gemini_key, get_elevenlabs_api_key, get_masked_elevenlabs_key,
            )

            groq_key = data.get("groq_api_key")
            if groq_key is not None and str(groq_key).strip() and "••••" not in str(groq_key):
                ok, err = save_api_keys_transactional(
                    groq_api_key=str(groq_key).strip(),
                    validate=True,
                )
                if not ok:
                    return web.json_response({"status": "error", "message": err}, status=400)

            save_pipeline_mode(mode)

            voice_fallback = data.get("voice_fallback")
            if voice_fallback is not None:
                if isinstance(voice_fallback, bool):
                    save_voice_fallback_mode("auto" if voice_fallback else "off")
                else:
                    save_voice_fallback_mode(str(voice_fallback))

            # Always persist engine selections — they are only used in cascade
            # mode, but saving them regardless means switching to cascade later
            # works without re-entering the settings, and avoids the reset-to-Live
            # bug when the mode was briefly ambiguous.
            stt = str(data.get("stt_engine", get_stt_engine())).strip().lower() or get_stt_engine()
            llm = str(data.get("llm_engine", get_llm_engine())).strip().lower() or get_llm_engine()
            tts = str(data.get("tts_engine", get_tts_engine())).strip().lower() or get_tts_engine()
            voice = str(data.get("tts_voice", "")).strip()

            save_stt_engine(stt)
            save_llm_engine(llm)
            save_tts_engine(tts)
            if voice:
                save_tts_voice(voice)

            res_payload = {
                "pipeline_mode": get_pipeline_mode(),
                "stt_engine": get_stt_engine(),
                "llm_engine": get_llm_engine(),
                "tts_engine": get_tts_engine(),
                "tts_voice": get_tts_voice(),
                "voice_fallback": get_voice_fallback_mode(),
                "voice_fallback_enabled": get_voice_fallback_mode() == "auto",
                "has_gemini_key": is_configured(),
                "gemini_api_key_masked": get_masked_gemini_key(),
                "has_groq_key": bool(get_groq_api_key()),
                "groq_api_key_masked": get_masked_groq_key(),
                "has_elevenlabs_key": bool(get_elevenlabs_api_key()),
                "elevenlabs_api_key_masked": get_masked_elevenlabs_key(),
            }

            if self.on_pipeline_settings_changed:
                try:
                    self.on_pipeline_settings_changed()
                except Exception as e:
                    logger.warning("on_pipeline_settings_changed error: %s", e)

            self.broadcast("pipeline_settings_updated", res_payload)

            return web.json_response({
                "status": "success",
                "data": res_payload
            })
        except Exception as e:
            logger.exception("Save pipeline settings error: %s", e)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _get_config_handler(self, request: web.Request) -> web.Response:
        try:
            from memory.config_manager import (
                get_assistant_name, get_voice, get_response_language,
                get_autostart_enabled, get_brief_enabled,
                get_wake_word_enabled, get_push_to_talk_enabled,
                get_masked_gemini_key, get_masked_groq_key, get_masked_elevenlabs_key, get_masked_tavily_key,
                is_configured, get_opencode_model, get_kilo_model, get_antigravity_model,
                get_fallback_voice, FALLBACK_VOICES, get_voice_fallback_mode,
                get_preferred_creation_agent, get_preferred_edit_agent,
                CREATION_AGENTS, EDIT_AGENTS,
                get_pipeline_mode, get_stt_engine, get_llm_engine, get_tts_engine, get_tts_voice,
                PIPELINE_MODES, STT_ENGINES, LLM_ENGINES, TTS_ENGINES,
                get_groq_api_key, get_elevenlabs_api_key, get_tavily_api_key,
                AVAILABLE_LANGUAGES, AVAILABLE_VOICES,
                get_thinking_enabled, get_proactive_audio_enabled,
                get_theme, get_accent,
                get_avatar_settings, save_avatar_settings,
            )
            try:
                from core.wake_word import list_wake_presets
                _assistant_names = [p["name"] for p in list_wake_presets()]
            except Exception:
                _assistant_names = []
            data = {
                "status": "success",
                "assistant_name": get_assistant_name(),
                "available_assistant_names": _assistant_names,
                "wake_phrase": f"Hey {get_assistant_name()}",
                "voice_name": get_voice(),
                "response_language": get_response_language(),
                "theme": get_theme(),
                "accent": get_accent(),
                **get_avatar_settings(),
                "fallback_voice": get_fallback_voice(),
                "fallback_voices": list(FALLBACK_VOICES),
                "voice_fallback": get_voice_fallback_mode(),
                "voice_fallback_enabled": get_voice_fallback_mode() == "auto",
                "autostart_enabled": get_autostart_enabled(),
                "morning_brief_enabled": get_brief_enabled(),
                "wake_word_enabled": get_wake_word_enabled(),
                "push_to_talk_enabled": get_push_to_talk_enabled(),
                "thinking_enabled": get_thinking_enabled(),
                "proactive_audio_enabled": get_proactive_audio_enabled(),
                "has_gemini_key": is_configured(),
                "gemini_api_key_masked": get_masked_gemini_key(),
                "has_groq_key": bool(get_groq_api_key()),
                "groq_api_key_masked": get_masked_groq_key(),
                "has_elevenlabs_key": bool(get_elevenlabs_api_key()),
                "elevenlabs_api_key_masked": get_masked_elevenlabs_key(),
                "has_tavily_key": bool(get_tavily_api_key()),
                "tavily_api_key_masked": get_masked_tavily_key(),
                "opencode_model": get_opencode_model(),
                "kilo_model": get_kilo_model(),
                "antigravity_model": get_antigravity_model(),
                "preferred_creation_agent": get_preferred_creation_agent(),
                "preferred_edit_agent": get_preferred_edit_agent(),
                "pipeline_mode": get_pipeline_mode(),
                "stt_engine": get_stt_engine(),
                "llm_engine": get_llm_engine(),
                "tts_engine": get_tts_engine(),
                "tts_voice": get_tts_voice(),
                "available_languages": list(AVAILABLE_LANGUAGES),
                "available_voices": list(AVAILABLE_VOICES),
                **self._collect_audio_state(),
            }
            return web.json_response(data)
        except Exception as e:
            logger.exception("Get config error: %s", e)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _save_config_handler(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
            from memory.config_manager import (
                save_assistant_config, save_voice, save_response_language,
                get_assistant_name,
                save_autostart_enabled, save_brief_enabled,
                save_wake_word_enabled, get_wake_word_enabled,
                save_push_to_talk_enabled,
                save_api_keys_transactional,
                save_pipeline_mode, save_stt_engine, save_llm_engine,
                save_tts_engine, save_tts_voice, save_voice_fallback_mode,
                save_fallback_voice,
                save_preferred_creation_agent, save_preferred_edit_agent,
                save_opencode_model, save_kilo_model, save_antigravity_model,
                save_thinking_enabled, save_proactive_audio_enabled,
                save_theme, save_accent,
                save_avatar_settings,
            )

            # 1. Controls
            if "autostart_enabled" in data or "autostart" in data:
                save_autostart_enabled(bool(data.get("autostart_enabled", data.get("autostart"))))
            if "morning_brief_enabled" in data or "morning_brief" in data:
                save_brief_enabled(bool(data.get("morning_brief_enabled", data.get("morning_brief"))))
            if "wake_word_enabled" in data or "wake_word" in data:
                val = bool(data.get("wake_word_enabled", data.get("wake_word")))
                changed = (val != get_wake_word_enabled())
                save_wake_word_enabled(val)
                # Only act on a REAL change — autosave re-sends the same value and
                # must not cause spurious sleep/wake + session reconnects.
                if changed and hasattr(self, "on_wake_toggle") and self.on_wake_toggle:
                    try:
                        self.on_wake_toggle(val)
                    except Exception:
                        pass
            if "push_to_talk_enabled" in data or "push_to_talk" in data:
                val = bool(data.get("push_to_talk_enabled", data.get("push_to_talk")))
                save_push_to_talk_enabled(val)
                if hasattr(self, "on_ptt_toggle") and self.on_ptt_toggle:
                    try:
                        self.on_ptt_toggle(val)
                    except Exception:
                        pass
            if "thinking_enabled" in data:
                save_thinking_enabled(bool(data["thinking_enabled"]))
            if "proactive_audio_enabled" in data:
                save_proactive_audio_enabled(bool(data["proactive_audio_enabled"]))
            if "theme" in data and data["theme"]:
                save_theme(str(data["theme"]))
            if "accent" in data and data["accent"]:
                save_accent(str(data["accent"]))

            # Avatar customization persistence
            save_avatar_settings(data)

            # 2. Assistant & Language (identity is user-selectable — see Persona tab)
            _posted_name = str(data.get("assistant_name") or "").strip()
            save_assistant_config(_posted_name or get_assistant_name(), "")
            voice_name = data.get("voice_name")
            if voice_name is not None:
                save_voice(str(voice_name).strip())
            resp_lang = data.get("response_language")
            if resp_lang is not None:
                save_response_language(str(resp_lang).strip())

            # 3. Keys
            keys_to_save = {}
            for k in ("gemini_api_key", "groq_api_key", "elevenlabs_api_key", "tavily_api_key",
                      "gemini_key", "groq_key", "elevenlabs_key", "tavily_key"):
                val = str(data.get(k) or "").strip()
                if val and "••••" not in val and "..." not in val:
                    normalized_k = k if k.endswith("_api_key") else f"{k.replace('_key', '')}_api_key"
                    keys_to_save[normalized_k] = val

            if keys_to_save:
                ok, err = save_api_keys_transactional(
                    gemini_api_key=keys_to_save.get("gemini_api_key"),
                    groq_api_key=keys_to_save.get("groq_api_key"),
                    elevenlabs_api_key=keys_to_save.get("elevenlabs_api_key"),
                    tavily_api_key=keys_to_save.get("tavily_api_key"),
                    validate=True,
                )
                if not ok:
                    return web.json_response({"status": "error", "message": err}, status=400)

            # 4. Pipeline & Engines
            if "pipeline_mode" in data:
                save_pipeline_mode(str(data["pipeline_mode"]))
            if "stt_engine" in data:
                save_stt_engine(str(data["stt_engine"]))
            if "llm_engine" in data:
                save_llm_engine(str(data["llm_engine"]))
            if "tts_engine" in data:
                save_tts_engine(str(data["tts_engine"]))
            if "tts_voice" in data:
                save_tts_voice(str(data["tts_voice"]))
            if "voice_fallback" in data:
                save_voice_fallback_mode(str(data["voice_fallback"]))
            if "fallback_voice" in data:
                save_fallback_voice(str(data["fallback_voice"]))

            # 5. Autonomous Coding Agents & Models
            if "preferred_creation_agent" in data:
                save_preferred_creation_agent(str(data["preferred_creation_agent"]))
            if "preferred_edit_agent" in data:
                save_preferred_edit_agent(str(data["preferred_edit_agent"]))
            if "opencode_model" in data:
                save_opencode_model(str(data["opencode_model"]))
            if "kilo_model" in data:
                save_kilo_model(str(data["kilo_model"]))
            if "antigravity_model" in data:
                save_antigravity_model(str(data["antigravity_model"]))

            # Notify UI callbacks if relevant
            if voice_name or resp_lang or _posted_name:
                if self.on_assistant_settings_changed:
                    try:
                        self.on_assistant_settings_changed(get_assistant_name(), voice_name or "Charon", resp_lang or "auto")
                    except Exception:
                        pass

            if any(k in data for k in ("pipeline_mode", "stt_engine", "llm_engine", "tts_engine")):
                if self.on_pipeline_settings_changed:
                    try:
                        self.on_pipeline_settings_changed()
                    except Exception:
                        pass

            return await self._get_config_handler(request)
        except Exception as e:
            logger.exception("Save config error: %s", e)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _preview_voice_handler(self, request: web.Request) -> web.Response:
        voice = request.query.get("voice", "Puck").strip().lower()
        # Check dist assets first, then public assets
        mp3_path = self.frontend_dir / "dist" / "assets" / "voices" / f"{voice}.mp3"
        if not mp3_path.exists():
            mp3_path = self.frontend_dir / "public" / "assets" / "voices" / f"{voice}.mp3"
        if mp3_path.exists():
            return web.FileResponse(mp3_path)
        return web.Response(status=404, text="Voice preview not found")

    async def _index_handler(self, request: web.Request) -> web.Response:
        frontend_dist_idx = self.frontend_dir / "dist" / "index.html"
        if frontend_dist_idx.exists():
            return web.FileResponse(frontend_dist_idx)
        return web.Response(
            text="<h1>ZEZO React Workstation Initializing...</h1><p>Please compile the frontend using: <code>cd frontend && npm run build</code></p>",
            content_type="text/html",
            status=503
        )

    async def _attachments_list_handler(self, request: web.Request) -> web.Response:
        """Fetch all currently registered file and folder attachments."""
        try:
            return web.json_response({
                "status": "success",
                "attachments": self.list_attachments()
            })
        except Exception as e:
            logger.exception("Error in /api/attachments handler: %s", e)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _system_status_handler(self, request: web.Request) -> web.Response:
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent
            return web.json_response({
                "status": "success",
                "cpu": cpu,
                "mem": mem,
                "gpu": 0,
                "net": 0,
            })
        except Exception:
            return web.json_response({"status": "success", "cpu": 0, "mem": 0, "gpu": 0, "net": 0})

    async def _office_view_handler(self, request: web.Request) -> web.Response:
        frontend_dist_idx = self.frontend_dir / "dist" / "index.html"
        if frontend_dist_idx.exists():
            return web.FileResponse(frontend_dist_idx)
        return web.Response(text="<h1>Scranton Office Deck</h1><p>Open via ZEZO React Desktop Workstation.</p>", content_type="text/html")

    async def _fleet_state_handler(self, request: web.Request) -> web.Response:
        try:
            from core.fleet_manager import fleet_manager
            return web.json_response({
                "status": "success",
                "fleet": fleet_manager.get_fleet_deck_state()
            })
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _fleet_agent_profile_handler(self, request: web.Request) -> web.Response:
        agent_id = request.query.get("id", "").strip()
        try:
            from core.fleet_manager import fleet_manager
            res = fleet_manager.get_agent_full_profile(agent_id)
            return web.json_response(res)
        except Exception as e:
            return web.json_response({"success": False, "error": str(e)}, status=500)

    async def _fleet_save_agent_handler(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
            from core.fleet_manager import fleet_manager
            res = fleet_manager.save_agent_profile(data)
            self.broadcast("fleet_updated", {"fleet": fleet_manager.get_fleet_deck_state()})
            return web.json_response(res)
        except Exception as e:
            return web.json_response({"success": False, "error": str(e)}, status=500)

    async def _fleet_save_soul_handler(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
            agent_id = str(data.get("agent_id") or data.get("id") or "").strip()
            soul = str(data.get("soul_prompt") or data.get("soul_md") or data.get("prompt_prefix") or "").strip()
            from core.fleet_manager import fleet_manager
            res = fleet_manager.save_agent_soul(agent_id, soul)
            self.broadcast("fleet_updated", {"fleet": fleet_manager.get_fleet_deck_state()})
            return web.json_response(res)
        except Exception as e:
            return web.json_response({"success": False, "error": str(e)}, status=500)

    async def _fleet_dispatch_task_handler(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
            agent_id = str(data.get("agent_id") or data.get("id") or "").strip()
            prompt = str(data.get("prompt") or data.get("task") or "").strip()
            path = data.get("path")
            from core.fleet_manager import fleet_manager
            res = fleet_manager.dispatch_task(agent_id, prompt, path)
            self.broadcast("fleet_updated", {"fleet": fleet_manager.get_fleet_deck_state()})
            return web.json_response(res)
        except Exception as e:
            return web.json_response({"success": False, "error": str(e)}, status=500)

    async def _fleet_chat_handler(self, request: web.Request) -> web.Response:
        """Interactive real-time conversational chat response from a fleet agent."""
        try:
            data = await request.json()
            agent_id = str(data.get("agent_id") or data.get("id") or "").strip()
            prompt = str(data.get("prompt") or data.get("message") or "").strip()
            engine_override = (data.get("engine") or "").strip() or None
            model_override = (data.get("model") or "").strip() or None

            from core.fleet_manager import fleet_manager
            agent = fleet_manager.get_agent(agent_id) or fleet_manager.resolve_agent_by_mention_or_capability(agent_id)
            if not agent:
                if agent_id.lower() in ("zezo", "os", "assistant", ""):
                    name = "Zezo"
                    role = "Autonomous Desktop AI Operating System"
                    soul_prompt = "You are Zezo, an autonomous AI desktop operating system built by Hamza Bukhari."
                    specialty = "Desktop control, multi-agent coordination, voice directives, coding pipelines"
                    active_engine = (engine_override or "antigravity_run").strip()
                    active_model = (model_override or "gemini-3.8-flash-low").strip()
                else:
                    return web.json_response({"success": False, "error": f"Agent '{agent_id}' not found."}, status=404)
            else:
                name = agent.displayName if hasattr(agent, "displayName") and agent.displayName else agent.name
                role = agent.role or "Autonomous Specialist"
                soul_prompt = agent.prompt_prefix or f"You are {name}, {role}."
                specialty = getattr(agent, "specialty", "") or ""
                active_engine = (engine_override or agent.default_tool or "antigravity_run").strip()
                active_model = (model_override or agent.model_id or "").strip()

            sys_prompt = (
                f"{soul_prompt}\n"
                f"Your role is {role}. Specialty: {specialty}.\n"
                f"You are conversing directly with Hamza (the User & Architect). "
                f"Give concise, intelligent, authentic, and helpful responses matching your persona. "
                f"If asked to write code or plan architecture, provide clean actionable markdown with snippets."
            )

            response_text = ""

            # Instant Intelligent Conversational Engine
            # Chat is conversational — we route directly to high-speed LLM endpoints matching the selected engine/model,
            # avoiding heavy multi-file CLI cold-start overhead (12-35s) on Windows.
            if "antigravity" in active_engine.lower() or "gemini" in active_model.lower():
                try:
                    from core import gemini
                    # Call Gemini directly with the agent's persona
                    full_convo = f"{sys_prompt}\n\nHamza: {prompt}\n\n{name}:"
                    response_text = gemini.text(
                        full_convo,
                        tier=gemini.FAST,
                        timeout_ms=5000,
                        allow_groq=True,
                        default=""
                    )
                except Exception as e:
                    logger.debug("[FleetChat] Direct Gemini chat failed: %s", e)

            elif "opencode" in active_engine.lower() or "kilo" in active_engine.lower():
                # For OpenCode and Kilo agents, use llm_router with instant streaming/generation
                try:
                    from core import llm_router
                    response_text = llm_router.generate_text(
                        prompt=prompt,
                        system=sys_prompt,
                        tier=llm_router.FAST,
                        timeout_ms=5000,
                    )
                except Exception as e:
                    logger.debug("[FleetChat] OpenCode/Kilo router failed: %s", e)
            elif "groq" in active_engine.lower():
                try:
                    from core.llm_client import call_groq_text
                    response_text = call_groq_text(
                        prompt=prompt,
                        system=sys_prompt,
                        model=active_model if (active_model and "groq" not in active_model) else "llama-3.3-70b-versatile",
                        timeout=15,
                    )
                except Exception as e:
                    logger.debug("[FleetChat] Groq call_groq_text failed: %s", e)

            # Fallback to ultra-fast Gemini/Groq ladder
            if not response_text:
                try:
                    from core import gemini
                    response_text = gemini.text(
                        f"{sys_prompt}\n\nHamza: {prompt}\n\n{name}:",
                        tier=gemini.FAST,
                        timeout_ms=5000,
                        allow_groq=True,
                        default=""
                    )
                except Exception as e:
                    logger.debug("[FleetChat] Fallback Gemini fast call failed: %s", e)

            if not response_text:
                try:
                    from core import llm_router
                    response_text = llm_router.generate_text(
                        prompt=prompt,
                        system=sys_prompt,
                        timeout_ms=4000,
                    )
                except Exception as e:
                    logger.debug("[FleetChat] llm_router fallback failed: %s", e)

            if not response_text:
                response_text = f"Hello Hamza! I am {name}. I received your message: '{prompt}'. Ready to assist on {role}."

            return web.json_response({
                "success": True,
                "agent_id": agent.name,
                "reply": response_text.strip(),
                "engine": active_engine,
                "model": active_model,
            })
        except Exception as e:
            logger.exception("Error in _fleet_chat_handler: %s", e)
            return web.json_response({"success": False, "error": str(e)}, status=500)

    async def _fleet_delete_agent_handler(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
            agent_id = str(data.get("agent_id") or data.get("id") or "").strip()
            from core.fleet_manager import fleet_manager
            res = fleet_manager.delete_agent(agent_id)
            self.broadcast("fleet_updated", {"fleet": fleet_manager.get_fleet_deck_state()})
            return web.json_response(res)
        except Exception as e:
            return web.json_response({"success": False, "error": str(e)}, status=500)

    async def _fleet_open_folder_handler(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
            raw_path = str(data.get("path") or "").strip()
            if not raw_path or raw_path.lower() in ("direct workspace", "main"):
                target_path = BASE_DIR
            else:
                p = Path(raw_path)
                if not p.is_absolute():
                    p = BASE_DIR / p
                target_path = p

            if not target_path.exists():
                target_path.mkdir(parents=True, exist_ok=True)

            # Open folder in native OS file explorer (Windows / macOS / Linux)
            import platform
            system = platform.system()
            if system == "Windows":
                os.startfile(str(target_path))
            elif system == "Darwin":
                subprocess.Popen(["open", str(target_path)])
            else:
                subprocess.Popen(["xdg-open", str(target_path)])

            return web.json_response({"success": True, "path": str(target_path)})
        except Exception as e:
            logger.warning("[UI Server] Failed to open folder in explorer: %s", e)
            return web.json_response({"success": False, "error": str(e)}, status=500)

    async def _fleet_pick_folder_handler(self, request: web.Request) -> web.Response:
        """Open native OS folder selection dialog and return the chosen path."""
        try:
            data = await request.json() if request.can_read_body else {}
        except Exception:
            data = {}
        initial_dir = str(data.get("initial_dir") or "").strip()
        if not initial_dir or not Path(initial_dir).exists():
            initial_dir = str(Path.home() / "Desktop" if (Path.home() / "Desktop").exists() else Path.home())

        def _open_native_dialog() -> str:
            selected_path = ""
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                root.attributes("-topmost", True)
                chosen = filedialog.askdirectory(
                    initialdir=initial_dir,
                    title="Select Workspace Folder for Fleet Agent"
                )
                root.destroy()
                if chosen:
                    selected_path = str(Path(chosen).resolve()).replace("\\", "/")
            except Exception as ex:
                logger.debug("[UI Server] Tkinter dialog fallback: %s", ex)

            # PowerShell fallback if tkinter failed or returned empty
            if not selected_path:
                try:
                    import platform
                    if platform.system() == "Windows":
                        ps_script = (
                            "[System.Reflection.Assembly]::LoadWithPartialName('System.windows.forms') | Out-Null; "
                            "$f = New-Object System.Windows.Forms.FolderBrowserDialog; "
                            f"$f.SelectedPath = '{initial_dir.replace('/', chr(92))}'; "
                            "$f.Description = 'Select Workspace Folder for Fleet Agent'; "
                            "if ($f.ShowDialog((New-Object System.Windows.Forms.NativeWindow)) -eq [System.Windows.Forms.DialogResult]::OK) { "
                            "Write-Output $f.SelectedPath }"
                        )
                        res = subprocess.run(
                            ["powershell", "-NoProfile", "-Command", ps_script],
                            capture_output=True,
                            text=True,
                            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
                            timeout=60,
                        )
                        out = res.stdout.strip()
                        if out and Path(out).exists():
                            selected_path = str(Path(out).resolve()).replace("\\", "/")
                except Exception as ex:
                    logger.debug("[UI Server] PowerShell folder dialog fallback error: %s", ex)

            return selected_path

        loop = asyncio.get_running_loop()
        try:
            chosen = await loop.run_in_executor(None, _open_native_dialog)
            if chosen:
                return web.json_response({"success": True, "path": chosen})
            return web.json_response({"success": False, "cancelled": True})
        except Exception as e:
            logger.warning("[UI Server] Error in pick folder dialog: %s", e)
            return web.json_response({"success": False, "error": str(e)}, status=500)

    async def _skills_list_handler(self, request: web.Request) -> web.Response:
        """Return list of discovered declarative skills, optionally filtered by domain."""
        domain = request.query.get("domain")
        try:
            from core.skill_loader import get_skill_registry
            reg = get_skill_registry()
            skills = reg.list_skills(domain=domain)
            domains = reg.list_domains()
            return web.json_response({"status": "success", "skills": skills, "domains": domains})
        except Exception as e:
            logger.exception("Error in /api/skills handler: %s", e)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _models_list_handler(self, request: web.Request) -> web.Response:
        """Return dynamic, categorized model lists from core.models."""
        try:
            from core import models
            engine = request.query.get("engine")

            opencode_models = [
                "opencode/big-pickle",
                "opencode/nemotron-3-ultra-free",
                "opencode/nemotron-3.5-lightning-free",
                "opencode/mimo-v2.6-flash-free",
                "opencode/ling-3.1-flash-free",
                "opencode/longcat-2.5-preview-free",
                "opencode/space-bunny-free",
                "opencode/fledge-alpha-free",
                "opencode/muse-spark-1.3-contributor-free",
                "openrouter/openrouter/free",
                "openrouter/google/gemma-4-31b-it:free",
                "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free",
            ]
            kilo_models = [
                "kilo/kilo-auto/free",
                "kilo/stepfun/step-3.7-flash:free",
                "kilo/deepseek/deepseek-chat:free",
                "kilo/qwen/qwen-2.5-coder-32b-instruct:free",
                "kilo/minimax/minimax-01:free",
                "kilo/nvidia/nemotron-3-ultra-550b-a55b:free",
                "kilo/poolside/laguna-s-2.1:free",
            ]
            antigravity_models = list(models.ANTIGRAVITY_CLI_MODELS)
            groq_models = [
                "groq/llama-3.3-70b-versatile",
                "groq/deepseek-r1-distill-llama-70b",
                "groq/qwen-2.5-coder-32b",
            ]
            gemini_models = list(dict.fromkeys(models.GEMINI_FAST_MODELS + models.GEMINI_SMART_MODELS))

            categorized = {
                "opencode_run": opencode_models,
                "kilo_run": kilo_models,
                "antigravity_run": antigravity_models,
                "groq": groq_models,
                "gemini": gemini_models,
                "none": gemini_models + groq_models,
            }

            all_models = list(dict.fromkeys(
                antigravity_models + opencode_models + kilo_models + groq_models + gemini_models
            ))

            if engine and engine in categorized:
                return web.json_response({
                    "status": "success",
                    "engine": engine,
                    "models": categorized[engine],
                    "all_models": all_models,
                })

            return web.json_response({
                "status": "success",
                "default_engine_models": categorized,
                "all_models": all_models,
            })
        except Exception as e:
            logger.exception("Error in /api/models handler: %s", e)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _audio_devices_handler(self, request: web.Request) -> web.Response:
        """Return real host audio input/output devices and current configuration."""
        try:
            return web.json_response(self._collect_audio_state())
        except Exception as e:
            logger.exception("Error in /api/audio_devices handler: %s", e)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _skills_mode_handler(self, request: web.Request) -> web.Response:
        """Update toggle mode (pinned, disabled, auto_activate) for a skill."""
        try:
            data = await request.json()
            name = str(data.get("name") or "").strip()
            pinned = bool(data.get("pinned", False))
            disabled = bool(data.get("disabled", False))
            auto_activate = bool(data.get("auto_activate", True))

            from core.skill_loader import get_skill_registry
            reg = get_skill_registry()
            ok = reg.set_skill_mode(name, pinned=pinned, disabled=disabled, auto_activate=auto_activate)
            if not ok:
                return web.json_response({"status": "error", "message": f"Skill '{name}' not found"}, status=404)
            return web.json_response({"status": "success", "name": name, "pinned": pinned, "disabled": disabled, "auto_activate": auto_activate})
        except Exception as e:
            logger.exception("Error in /api/skills/mode handler: %s", e)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _skills_install_handler(self, request: web.Request) -> web.Response:
        """Install a new skill from local file path or zip archive."""
        try:
            data = await request.json()
            source = str(data.get("source") or data.get("path") or "").strip()
            domain = str(data.get("domain") or "").strip()
            if not source:
                return web.json_response({"status": "error", "message": "Source path or zip required"}, status=400)

            from core.skill_loader import get_skill_registry
            reg = get_skill_registry()
            ok, msg = reg.install_skill(source, target_domain=domain)
            if not ok:
                return web.json_response({"status": "error", "message": msg}, status=400)
            return web.json_response({"status": "success", "message": msg, "skills": reg.list_skills()})
        except Exception as e:
            logger.exception("Error in /api/skills/install handler: %s", e)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _skills_save_handler(self, request: web.Request) -> web.Response:
        """Synthesize or update a declarative skill package."""
        try:
            data = await request.json()
            name = str(data.get("name") or "").strip()
            desc = str(data.get("description") or "").strip()
            instructions = str(data.get("instructions") or "").strip()
            domain = str(data.get("domain") or "").strip()
            author = str(data.get("author") or "user").strip()
            triggers = data.get("triggers") if isinstance(data.get("triggers"), list) else None
            tags = data.get("tags") if isinstance(data.get("tags"), list) else None

            from core.skill_loader import get_skill_registry
            reg = get_skill_registry()
            ok, msg = reg.save_learned_skill(
                name=name,
                description=desc,
                instructions=instructions,
                domain=domain,
                author=author,
                triggers=triggers,
                tags=tags,
            )
            if not ok:
                return web.json_response({"status": "error", "message": msg}, status=400)
            return web.json_response({"status": "success", "message": msg, "skills": reg.list_skills()})
        except Exception as e:
            logger.exception("Error in /api/skills/save handler: %s", e)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _skills_delete_handler(self, request: web.Request) -> web.Response:
        """Delete a skill package from disk."""
        try:
            data = await request.json()
            name = str(data.get("name") or "").strip()
            from core.skill_loader import get_skill_registry
            reg = get_skill_registry()
            ok, msg = reg.delete_skill(name)
            if not ok:
                return web.json_response({"status": "error", "message": msg}, status=404)
            return web.json_response({"status": "success", "message": msg, "skills": reg.list_skills()})
        except Exception as e:
            logger.exception("Error in /api/skills/delete handler: %s", e)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _memory_stats_handler(self, request: web.Request) -> web.Response:
        try:
            from memory.sqlite_memory import get_db_path
            from core.repo_context import get_last_repo
            db_path = get_db_path()
            size_bytes = db_path.stat().st_size if db_path.exists() else 0
            turns_count = 0
            facts_count = 0
            if db_path.exists():
                import sqlite3
                with sqlite3.connect(str(db_path)) as conn:
                    try:
                        c = conn.cursor()
                        c.execute("SELECT COUNT(*) FROM history_turns")
                        turns_count = c.fetchone()[0]
                    except Exception:
                        pass
                    try:
                        c.execute("SELECT COUNT(*) FROM facts")
                        facts_count = c.fetchone()[0]
                    except Exception:
                        pass
            active_ws = get_last_repo() or str(BASE_DIR)
            return web.json_response({
                "status": "success",
                "db_path": str(db_path),
                "db_size_kb": round(size_bytes / 1024, 1),
                "turns_count": turns_count,
                "facts_count": facts_count,
                "active_workspace": active_ws,
                "fts5_enabled": True,
            })
        except Exception as e:
            logger.exception("Error in /api/memory/stats: %s", e)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _memory_graph_handler(self, request: web.Request) -> web.Response:
        """Fetch compiled knowledge graph topology (nodes + links) from Markdown vault."""
        try:
            from memory.vault_engine import vault_engine
            graph_data = vault_engine.get_graph()
            return web.json_response(graph_data)
        except Exception as e:
            logger.exception("Error in /api/memory/graph: %s", e)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _memory_notes_list_handler(self, request: web.Request) -> web.Response:
        """Fetch list of all markdown memory notes in the vault."""
        try:
            from memory.vault_engine import vault_engine
            notes = vault_engine.get_all_notes()
            return web.json_response({"status": "success", "notes": notes})
        except Exception as e:
            logger.exception("Error in /api/memory/notes: %s", e)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _memory_note_detail_handler(self, request: web.Request) -> web.Response:
        """Fetch full markdown content and outbound links for a specific note."""
        try:
            file_param = request.query.get("file") or request.query.get("id") or ""
            if not file_param:
                return web.json_response({"status": "error", "message": "Missing file or id parameter"}, status=400)
            from memory.vault_engine import vault_engine
            note = vault_engine.get_note_content(file_param)
            if not note:
                return web.json_response({"status": "error", "message": "Note not found"}, status=404)
            return web.json_response({"status": "success", "note": note})
        except Exception as e:
            logger.exception("Error in /api/memory/note: %s", e)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _memory_save_note_handler(self, request: web.Request) -> web.Response:
        """Save or edit content of an existing markdown note."""
        try:
            data = await request.json()
            file_name = str(data.get("file") or "").strip()
            content = str(data.get("content") or "")
            if not file_name:
                return web.json_response({"status": "error", "message": "File name required"}, status=400)
            from memory.vault_engine import vault_engine
            res = vault_engine.save_note(file_name, content)
            self.broadcast("memory_updated", {"action": "saved", "file": file_name})
            return web.json_response(res)
        except Exception as e:
            logger.exception("Error in /api/memory/note save: %s", e)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _memory_create_note_handler(self, request: web.Request) -> web.Response:
        """Create a new memory note in the vault."""
        try:
            data = await request.json()
            title = str(data.get("title") or "").strip()
            category = str(data.get("category") or "knowledge").strip()
            content = str(data.get("content") or "").strip()
            tags = data.get("tags") if isinstance(data.get("tags"), list) else None
            if not title:
                return web.json_response({"status": "error", "message": "Title required"}, status=400)
            from memory.vault_engine import vault_engine
            res = vault_engine.create_note(title, category, content, tags)
            self.broadcast("memory_updated", {"action": "created", "title": title})
            return web.json_response(res)
        except Exception as e:
            logger.exception("Error in /api/memory/add: %s", e)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _memory_delete_note_handler(self, request: web.Request) -> web.Response:
        """Delete a memory note from the vault."""
        try:
            data = await request.json()
            file_name = str(data.get("file") or "").strip()
            if not file_name:
                return web.json_response({"status": "error", "message": "File name required"}, status=400)
            from memory.vault_engine import vault_engine
            res = vault_engine.delete_note(file_name)
            self.broadcast("memory_updated", {"action": "deleted", "file": file_name})
            return web.json_response(res)
        except Exception as e:
            logger.exception("Error in /api/memory/delete: %s", e)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _memory_clear_handler(self, request: web.Request) -> web.Response:
        try:
            from memory.sqlite_memory import get_db_path
            db_path = get_db_path()
            if db_path.exists():
                import sqlite3
                with sqlite3.connect(str(db_path)) as conn:
                    conn.execute("DELETE FROM turns")
                    try:
                        conn.execute("DELETE FROM turns_fts")
                    except Exception:
                        pass
                    conn.commit()
            return web.json_response({"status": "success", "message": "Conversation history cleared"})
        except Exception as e:
            logger.exception("Error in /api/memory/clear: %s", e)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _memory_wipe_all_handler(self, request: web.Request) -> web.Response:
        """Atomically purge all 4 memory layers: SQLite turns/facts, Vault Markdown notes, and long_term.json."""
        try:
            from memory.sqlite_memory import wipe_all_sqlite_memory
            from memory.vault_engine import vault_engine
            from memory.memory_manager import wipe_all_long_term_json

            preserve_profile = False
            try:
                if request.can_read_body:
                    body = await request.json()
                    preserve_profile = bool(body.get("preserve_profile", False))
            except Exception:
                preserve_profile = False

            sqlite_counts = wipe_all_sqlite_memory()
            vault_res = vault_engine.wipe_all_vault_memory(preserve_profile=preserve_profile)
            wipe_all_long_term_json()

            self.broadcast("memory_updated", {"action": "wiped", "details": sqlite_counts})

            return web.json_response({
                "status": "success",
                "message": "All memory layers successfully wiped and reset to clean state",
                "sqlite_deleted": sqlite_counts,
                "vault_deleted_conv_files": vault_res.get("deleted_conv_files", 0),
            })
        except Exception as e:
            logger.exception("Error in /api/memory/wipe_all: %s", e)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _memory_optimize_handler(self, request: web.Request) -> web.Response:
        try:
            from memory.sqlite_memory import get_db_path
            db_path = get_db_path()
            if db_path.exists():
                import sqlite3
                with sqlite3.connect(str(db_path)) as conn:
                    conn.execute("PRAGMA optimize")
                    conn.execute("VACUUM")
            return web.json_response({"status": "success", "message": "Memory database optimized and vacuumed"})
        except Exception as e:
            logger.exception("Error in /api/memory/optimize: %s", e)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _workspace_set_handler(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
            ws_path = str(data.get("path") or "").strip()
            from core.repo_context import remember_repo, forget_repo
            if ws_path and ws_path.lower() != "reset":
                remember_repo(ws_path)
            else:
                forget_repo()
            from core.repo_context import get_last_repo
            active_ws = get_last_repo() or str(BASE_DIR)
            return web.json_response({"status": "success", "active_workspace": active_ws})
        except Exception as e:
            logger.exception("Error in /api/workspace/set: %s", e)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _get_backend_logs_handler(self, request: web.Request) -> web.Response:
        try:
            from core import log_bus
            min_lvl = request.query.get("min_level", "DEBUG")
            snapshot = log_bus.snapshot(min_level=min_lvl)
            return web.json_response({
                "status": "success",
                "lines": snapshot[-1200:] if len(snapshot) > 1200 else snapshot,
                "stats": log_bus.stats(),
                "sources": log_bus.sources(),
            })
        except Exception as e:
            logger.exception("Error in /api/backend_logs handler: %s", e)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _clear_backend_logs_handler(self, request: web.Request) -> web.Response:
        try:
            from core import log_bus
            log_bus.clear()
            self.broadcast("backend_logs_cleared", {})
            return web.json_response({"status": "success", "message": "Backend logs cleared"})
        except Exception as e:
            logger.exception("Error in /api/backend_logs/clear: %s", e)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _avatar_handler(self, request: web.Request) -> web.Response:
        for p in (
            self.frontend_dir / "dist" / "zezo-avatar.png",
            self.frontend_dir / "public" / "zezo-avatar.png",
            BASE_DIR / "frontend" / "public" / "zezo-avatar.png",
            BASE_DIR / "web" / "dist" / "zezo-avatar.png",
            BASE_DIR / "web" / "public" / "zezo-avatar.png",
        ):
            if p.exists():
                return web.FileResponse(p)
        return web.Response(status=404)

    def _resolve_remote_details(self) -> tuple[str, str]:
        url, key = "", ""
        if self.on_remote_clicked:
            try:
                res = self.on_remote_clicked()
                if res:
                    url, key = str(res[0]), str(res[1])
            except Exception as e:
                logger.warning("on_remote_clicked error: %s", e)
        if not url:
            lan_ip = "127.0.0.1"
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                lan_ip = s.getsockname()[0]
                s.close()
            except Exception:
                pass
            url = f"http://{lan_ip}:8000"
        if not key:
            key = "8F3A-9K"
        return url, key

    async def _remote_gateway_handler(self, request: web.Request) -> web.Response:
        url, key = self._resolve_remote_details()
        return web.json_response({
            "status": "success",
            "url": url,
            "key": key,
            "login_url": f"{url}/auto-login?key={key}",
        })

    async def _remote_new_key_handler(self, request: web.Request) -> web.Response:
        url, key = self._resolve_remote_details()
        return web.json_response({
            "status": "success",
            "url": url,
            "key": key,
            "login_url": f"{url}/auto-login?key={key}",
        })

    async def _favicon_handler(self, request: web.Request) -> web.Response:
        for p in [self.frontend_dir / "dist" / "favicon.ico", self.frontend_dir / "public" / "favicon.ico"]:
            if p.exists():
                return web.FileResponse(p)
        return web.Response(status=204)

    async def _ws_handler(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(heartbeat=15.0)
        await ws.prepare(request)
        self._clients.add(ws)
        logger.debug("New web client connected (%d active)", len(self._clients))

        # Send initial full state immediately upon connect
        try:
            initial_data = self._build_initial_state()
            await ws.send_str(json.dumps({"type": "init", "data": initial_data}))
        except Exception as e:
            logger.warning("Failed to send initial state to client: %s", e)

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        payload = json.loads(msg.data)
                        await self._handle_client_message(ws, payload)
                    except json.JSONDecodeError:
                        logger.warning("Invalid JSON from client: %s", msg.data)
                elif msg.type == WSMsgType.ERROR:
                    logger.debug("WebSocket connection closed with error %s", ws.exception())
        finally:
            self._clients.discard(ws)
            logger.debug("Client disconnected (%d active)", len(self._clients))

        return ws

    async def _handle_client_message(self, ws: web.WebSocketResponse, payload: dict) -> None:
        msg_type = payload.get("type", "")

        if msg_type in ("user_message", "text_command"):
            text = str(payload.get("text") or payload.get("command") or "").strip()
            if text and self.on_text_command:
                threading.Thread(target=self.on_text_command, args=(text,), daemon=True).start()

        elif msg_type == "interrupt":
            if self.on_interrupt:
                self.on_interrupt()

        elif msg_type == "mute_toggle":
            muted = bool(payload.get("muted", False))
            if self.on_mute_toggle:
                self.on_mute_toggle(muted)

        elif msg_type in ("speaker_mute_toggle", "deafen_toggle"):
            muted = bool(payload.get("muted") if "muted" in payload else payload.get("deafened", False))
            if self.on_speaker_mute_toggle:
                try:
                    self.on_speaker_mute_toggle(muted)
                except Exception as e:
                    logger.warning("Failed on_speaker_mute_toggle: %s", e)
            self.broadcast("speaker_status", {"muted": muted})

        elif msg_type == "confirm_response":
            accepted = bool(payload.get("accepted", False))
            try:
                from core import confirm
                confirm.resolve(accepted)
            except Exception as e:
                logger.warning("Failed resolving confirmation: %s", e)

        elif msg_type == "sleep_toggle":
            sleeping = bool(payload.get("sleeping", False))
            if self.on_sleep_toggle:
                try:
                    self.on_sleep_toggle(sleeping)
                except Exception as e:
                    logger.warning("Failed on_sleep_toggle: %s", e)
            self.broadcast("state_change", {"state": "sleeping" if sleeping else "listening"})

        elif msg_type == "get_backend_logs":
            try:
                from core import log_bus
                snapshot = log_bus.snapshot(min_level="DEBUG")
                await ws.send_str(json.dumps({
                    "type": "backend_logs_snapshot",
                    "data": {
                        "lines": snapshot[-1200:] if len(snapshot) > 1200 else snapshot,
                        "stats": log_bus.stats(),
                        "sources": log_bus.sources()
                    }
                }))
            except Exception as e:
                logger.warning("Failed to get backend logs snapshot: %s", e)

        elif msg_type == "clear_backend_logs":
            try:
                from core import log_bus
                log_bus.clear()
                self.broadcast("backend_logs_cleared", {})
            except Exception as e:
                logger.warning("Failed to clear log bus: %s", e)

        elif msg_type == "export_backend_logs":
            try:
                from core import log_bus
                full_text = log_bus.export_text()
                await ws.send_str(json.dumps({
                    "type": "backend_logs_export_data",
                    "data": {"text": full_text}
                }))
            except Exception as e:
                logger.warning("Failed to export log bus: %s", e)

        elif msg_type == "get_remote_key":
            url, key = self._resolve_remote_details()
            await ws.send_str(json.dumps({
                "type": "remote_key_data",
                "data": {"url": url, "key": key, "login_url": f"{url}/auto-login?key={key}"}
            }))

        elif msg_type == "task_cancel":
            task_id = str(payload.get("task_id", "")).strip()
            if task_id:
                try:
                    from core.task_manager import get_task_manager
                    get_task_manager().cancel(task_id)
                except Exception as e:
                    logger.warning("Failed to cancel task %s: %e", task_id, e)

        elif msg_type == "payload_remove":
            item_path = str(payload.get("path", "")).strip()
            is_folder = bool(payload.get("is_folder", False))
            if item_path:
                self.remove_attachment(item_path)
            if is_folder and item_path:
                try:
                    from core.repo_context import forget_repo
                    forget_repo(item_path)
                except Exception as e:
                    logger.debug("payload_remove repo cleanup error: %s", e)
            self.broadcast("log", {
                "text": f"[Payload] Removed '{payload.get('name', 'item')}' from active payloads."
            })

        elif msg_type == "payload_clear":
            self.clear_attachments()
            try:
                from core.repo_context import forget_repo
                forget_repo()
            except Exception as e:
                logger.debug("payload_clear repo cleanup error: %s", e)
            self.broadcast("log", {
                "text": "[Payload] Cleared all ingested payloads."
            })

        elif msg_type == "create_shortcut":
            if hasattr(self, "on_create_shortcut") and self.on_create_shortcut:
                try:
                    self.on_create_shortcut()
                except Exception as e:
                    logger.warning("Failed to create desktop shortcut: %s", e)

        elif msg_type == "wake_toggle":
            enable = bool(payload.get("enable", False))
            if hasattr(self, "on_wake_toggle") and self.on_wake_toggle:
                try:
                    res = self.on_wake_toggle(enable)
                    self.broadcast("wake_status", {"enabled": enable, "status": res})
                except Exception as e:
                    logger.warning("Failed to toggle wake word: %s", e)

        elif msg_type == "ptt_toggle":
            enable = bool(payload.get("enable", False))
            if hasattr(self, "on_ptt_toggle") and self.on_ptt_toggle:
                try:
                    scope = self.on_ptt_toggle(enable)
                    self.broadcast("ptt_status", {"enabled": enable, "scope": scope})
                except Exception as e:
                    logger.warning("Failed to toggle PTT: %s", e)

        elif msg_type == "save_pipeline_settings":
            mode = str(payload.get("pipeline_mode", "live")).strip().lower() or "live"
            try:
                from memory.config_manager import (
                    save_pipeline_mode, save_stt_engine, save_llm_engine,
                    save_tts_engine, save_tts_voice, save_voice_fallback_mode,
                    get_pipeline_mode, get_stt_engine, get_llm_engine, get_tts_engine, get_tts_voice,
                    get_voice_fallback_mode, get_groq_api_key, get_masked_groq_key, save_api_keys,
                )
                save_pipeline_mode(mode)

                voice_fallback = payload.get("voice_fallback")
                if voice_fallback is not None:
                    if isinstance(voice_fallback, bool):
                        save_voice_fallback_mode("auto" if voice_fallback else "off")
                    else:
                        save_voice_fallback_mode(str(voice_fallback))

                groq_key = payload.get("groq_api_key")
                if groq_key is not None and str(groq_key).strip():
                    save_api_keys(groq_api_key=str(groq_key).strip())

                # Always save engine selections, regardless of mode.
                stt = str(payload.get("stt_engine", get_stt_engine())).strip().lower() or get_stt_engine()
                llm = str(payload.get("llm_engine", get_llm_engine())).strip().lower() or get_llm_engine()
                tts = str(payload.get("tts_engine", get_tts_engine())).strip().lower() or get_tts_engine()
                voice = str(payload.get("tts_voice", "")).strip()
                save_stt_engine(stt)
                save_llm_engine(llm)
                save_tts_engine(tts)
                if voice:
                    save_tts_voice(voice)

                if self.on_pipeline_settings_changed:
                    try:
                        self.on_pipeline_settings_changed()
                    except Exception as e:
                        logger.warning("on_pipeline_settings_changed error: %s", e)

                self.broadcast("pipeline_settings_updated", {
                    "pipeline_mode": get_pipeline_mode(),
                    "stt_engine": get_stt_engine(),
                    "llm_engine": get_llm_engine(),
                    "tts_engine": get_tts_engine(),
                    "tts_voice": get_tts_voice(),
                    "voice_fallback": get_voice_fallback_mode(),
                    "voice_fallback_enabled": get_voice_fallback_mode() == "auto",
                    "has_groq_key": bool(get_groq_api_key()),
                    "groq_api_key_masked": get_masked_groq_key(),
                })
            except Exception as e:
                logger.warning("Failed to save pipeline settings from WS: %s", e)

        elif msg_type == "set_accent":
            color = str(payload.get("color", "")).strip().lower()
            if color:
                try:
                    from memory.config_manager import save_accent
                    save_accent(color)
                    self.broadcast("accent_changed", {"color": color})
                except Exception as e:
                    logger.warning("Failed to persist accent: %s", e)

        elif msg_type == "set_clipboard":
            text = str(payload.get("text", ""))
            try:
                from PyQt6.QtWidgets import QApplication
                app = QApplication.instance()
                if app:
                    cb = app.clipboard()
                    if cb:
                        cb.setText(text)
                else:
                    if platform.system() == "Windows":
                        subprocess.run(["clip"], input=text.encode("utf-8"), check=False)
            except Exception as e:
                logger.warning("Failed to set system clipboard: %s", e)

        elif msg_type == "autostart_toggle":
            enable = bool(payload.get("enable", False))
            try:
                from memory.config_manager import save_autostart_enabled
                res = save_autostart_enabled(enable)
                self.broadcast("autostart_status", {"enabled": enable, "success": res})
            except Exception as e:
                logger.warning("Failed to toggle autostart: %s", e)

        elif msg_type == "brief_toggle":
            enable = bool(payload.get("enable", False))
            try:
                from memory.config_manager import save_brief_enabled
                save_brief_enabled(enable)
                self.broadcast("brief_status", {"enabled": enable})
            except Exception as e:
                logger.warning("Failed to toggle morning brief: %s", e)

        elif msg_type == "save_assistant_settings":
            name = str(payload.get("assistant_name") or "").strip()
            voice = str(payload.get("voice_name", "Charon")).strip() or "Charon"
            lang = str(payload.get("response_language", "auto")).strip() or "auto"
            fallback_voice = payload.get("fallback_voice")
            try:
                from memory.config_manager import (
                    save_assistant_config, save_voice, save_response_language,
                    get_user_name, save_fallback_voice, get_fallback_voice, get_assistant_name,
                )
                name = name or get_assistant_name()
                user = get_user_name()
                save_assistant_config(name, user)
                save_voice(voice)
                save_response_language(lang)
                if fallback_voice is not None:
                    save_fallback_voice(str(fallback_voice))

                if self.on_assistant_settings_changed:
                    self.on_assistant_settings_changed(name, voice, lang)

                self.broadcast("assistant_settings_updated", {
                    "assistant_name": name,
                    "voice_name": voice,
                    "response_language": lang,
                    "fallback_voice": get_fallback_voice(),
                })
            except Exception as e:
                logger.warning("Failed to save assistant settings from WS: %s", e)

        elif msg_type == "save_api_keys":
            gemini_key = payload.get("gemini_api_key")
            groq_key = payload.get("groq_api_key")
            try:
                from memory.config_manager import (
                    save_api_keys, is_configured, get_masked_gemini_key, get_masked_groq_key
                )
                save_api_keys(gemini_api_key=gemini_key, groq_api_key=groq_key)
                self.broadcast("api_keys_updated", {
                    "status": "success",
                    "has_gemini_key": is_configured(),
                    "gemini_api_key_masked": get_masked_gemini_key(),
                    "groq_api_key_masked": get_masked_groq_key(),
                })
            except Exception as e:
                logger.warning("Failed to save API keys from WS: %s", e)

        elif msg_type == "get_fleet_state":
            try:
                from core.fleet_manager import fleet_manager
                await ws.send_str(json.dumps({
                    "type": "fleet_state",
                    "data": {"fleet": fleet_manager.get_fleet_deck_state()}
                }))
            except Exception as e:
                logger.warning("Failed to send fleet state: %s", e)

        elif msg_type == "get_agent_profile":
            agent_id = str(payload.get("agent_id") or payload.get("id") or "").strip()
            try:
                from core.fleet_manager import fleet_manager
                profile = fleet_manager.get_agent_full_profile(agent_id)
                await ws.send_str(json.dumps({
                    "type": "agent_profile_data",
                    "data": profile
                }))
            except Exception as e:
                logger.warning("Failed to get agent profile: %s", e)

        elif msg_type == "save_agent_soul":
            agent_id = str(payload.get("agent_id") or payload.get("id") or "").strip()
            soul = str(payload.get("soul_prompt") or payload.get("soul_md") or "").strip()
            try:
                from core.fleet_manager import fleet_manager
                res = fleet_manager.save_agent_soul(agent_id, soul)
                self.broadcast("fleet_updated", {"fleet": fleet_manager.get_fleet_deck_state()})
            except Exception as e:
                logger.warning("Failed to save agent soul: %s", e)

        elif msg_type == "dispatch_fleet_task":
            agent_id = str(payload.get("agent_id") or payload.get("id") or "").strip()
            prompt = str(payload.get("prompt") or payload.get("task") or "").strip()
            path = payload.get("path")
            try:
                from core.fleet_manager import fleet_manager
                res = fleet_manager.dispatch_task(agent_id, prompt, path)
                self.broadcast("fleet_updated", {"fleet": fleet_manager.get_fleet_deck_state()})
            except Exception as e:
                logger.warning("Failed to dispatch fleet task: %s", e)

        elif msg_type == "get_audio_devices":
            try:
                await ws.send_str(json.dumps({
                    "type": "audio_devices_updated",
                    "data": self._collect_audio_state(),
                }))
            except Exception as e:
                logger.warning("Failed to send audio devices: %s", e)

        elif msg_type == "save_audio_devices":
            in_name  = str(payload.get("input_device", "")  or "").strip()
            out_name = str(payload.get("output_device", "") or "").strip()
            try:
                from memory.config_manager import save_input_device, save_output_device
                save_input_device(in_name)
                save_output_device(out_name)
                if self.on_audio_devices_changed:
                    self.on_audio_devices_changed(in_name, out_name)
                self.broadcast("audio_devices_updated", self._collect_audio_state())
            except Exception as e:
                logger.warning("Failed to save audio devices from WS: %s", e)

    def _collect_audio_state(self) -> dict[str, Any]:
        """Truthful audio endpoint state for the AUDIO I/O panel.

        The panel used to be static HTML, so it showed whatever device name was
        written into the markup — even when the saved device could not be opened
        and the app had silently fallen back to the OS default. This reports the
        saved names, the devices the app can actually open at its sample rates,
        and whether the saved device is among them. `*_available: false` is the
        honest signal that a fallback is in effect.
        """
        state: dict[str, Any] = {
            "input_device": "", "output_device": "",
            "input_devices": [], "output_devices": [],
            "default_input_device": "", "default_output_device": "",
            "input_available": True, "output_available": True,
        }
        try:
            from memory.config_manager import get_input_device, get_output_device
            cur_in  = (get_input_device()  or "").strip()
            cur_out = (get_output_device() or "").strip()
            try:
                from core import audio_devices
                inputs  = audio_devices.list_devices("input")
                outputs = audio_devices.list_devices("output")
            except Exception as e:
                logger.warning("audio device listing failed: %s", e)
                inputs, outputs = [], []
            # The device the OS currently calls "default" — what ZEZO uses when
            # nothing is pinned. Shown so the panel can say which mic/speaker is
            # really active under "System default".
            try:
                import sounddevice as sd
                default_in  = (sd.query_devices(kind="input")  or {}).get("name", "")
                default_out = (sd.query_devices(kind="output") or {}).get("name", "")
            except Exception:
                default_in = default_out = ""
            state.update({
                "input_device":    cur_in,
                "output_device":   cur_out,
                "current_input":   cur_in,
                "current_output":  cur_out,
                "input_devices":   inputs,
                "output_devices":  outputs,
                "inputs":          [{"name": d, "is_default": d == default_in} for d in inputs],
                "outputs":         [{"name": d, "is_default": d == default_out} for d in outputs],
                "default_input_device":  default_in,
                "default_output_device": default_out,
                # Empty string means "system default", which is always valid.
                "input_available":  (not cur_in)  or (cur_in  in inputs),
                "output_available": (not cur_out) or (cur_out in outputs),
            })
        except Exception as e:
            logger.warning("Failed to collect audio state: %s", e)
        return state

    def _build_initial_state(self) -> dict:
        if self.get_initial_state:
            try:
                state = self.get_initial_state()
                state.update(self._collect_audio_state())
                return state
            except Exception as e:
                logger.warning("Error getting initial state: %s", e)

        # Fallback default initial state
        tasks = []
        try:
            from core.task_manager import get_task_manager
            tasks = get_task_manager().list_tasks()
        except Exception:
            pass

        from memory.config_manager import (
            get_assistant_name, get_voice, get_response_language,
            get_autostart_enabled, get_brief_enabled,
            get_wake_word_enabled, get_push_to_talk_enabled,
            get_masked_gemini_key, get_masked_groq_key, get_masked_elevenlabs_key, get_masked_tavily_key, is_configured,
            get_opencode_model, get_kilo_model, get_antigravity_model,
            get_fallback_voice, FALLBACK_VOICES, get_voice_fallback_mode,
            get_preferred_creation_agent, get_preferred_edit_agent,
            CREATION_AGENTS, EDIT_AGENTS,
            get_pipeline_mode, get_stt_engine, get_llm_engine, get_tts_engine, get_tts_voice,
            PIPELINE_MODES, STT_ENGINES, LLM_ENGINES, TTS_ENGINES,
            get_groq_api_key, get_elevenlabs_api_key, get_tavily_api_key,
        )
        try:
            from core.wake_word import list_wake_presets
            _assistant_names = [p["name"] for p in list_wake_presets()]
        except Exception:
            _assistant_names = []
        return {
            "state": "OFFLINE",
            "muted": False,
            "sleeping": False,
            "assistant_name": get_assistant_name(),
            "available_assistant_names": _assistant_names,
            "wake_phrase": f"Hey {get_assistant_name()}",
            "voice_name": get_voice(),
            "response_language": get_response_language(),
            "fallback_voice": get_fallback_voice(),
            "fallback_voices": list(FALLBACK_VOICES),
            "voice_fallback": get_voice_fallback_mode(),
            "voice_fallback_enabled": get_voice_fallback_mode() == "auto",
            "autostart_enabled": get_autostart_enabled(),
            "morning_brief_enabled": get_brief_enabled(),
            "wake_word_enabled": get_wake_word_enabled(),
            "push_to_talk_enabled": get_push_to_talk_enabled(),
            "preferred_creation_agent": get_preferred_creation_agent(),
            "preferred_edit_agent": get_preferred_edit_agent(),
            "creation_agents": list(CREATION_AGENTS),
            "edit_agents": list(EDIT_AGENTS),
            "has_gemini_key": is_configured(),
            "gemini_api_key_masked": get_masked_gemini_key(),
            "groq_api_key_masked": get_masked_groq_key(),
            "elevenlabs_api_key_masked": get_masked_elevenlabs_key(),
            "tavily_api_key_masked": get_masked_tavily_key(),
            "opencode_model": get_opencode_model(),
            "kilo_model": get_kilo_model(),
            "antigravity_model": get_antigravity_model(),
            "pipeline_mode": get_pipeline_mode(),
            "stt_engine": get_stt_engine(),
            "llm_engine": get_llm_engine(),
            "tts_engine": get_tts_engine(),
            "tts_voice": get_tts_voice(),
            "pipeline_modes": list(PIPELINE_MODES),
            "stt_engines": list(STT_ENGINES),
            "llm_engines": list(LLM_ENGINES),
            "tts_engines": list(TTS_ENGINES),
            "has_groq_key": bool(get_groq_api_key()),
            "has_elevenlabs_key": bool(get_elevenlabs_api_key()),
            "has_tavily_key": bool(get_tavily_api_key()),
            "tasks": tasks,
            "timestamp": time.time(),
            **self._collect_audio_state(),
        }

    def broadcast(self, event_type: str, data: dict[str, Any]) -> None:
        """Thread-safe broadcast of a JSON event to all connected web clients."""
        if not self._clients or not self._loop or self._loop.is_closed():
            return
        payload = json.dumps({"type": event_type, "data": data})
        asyncio.run_coroutine_threadsafe(self._broadcast_async(payload), self._loop)

    async def _broadcast_async(self, message: str) -> None:
        if not self._clients:
            return
        # Broadcast concurrently across all active client sockets
        await asyncio.gather(
            *(client.send_str(message) for client in list(self._clients)),
            return_exceptions=True
        )

    def stop(self) -> None:
        """Stop the UI server."""
        self._stopped.set()
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    async def _cleanup(self) -> None:
        for ws in list(self._clients):
            await ws.close()
        self._clients.clear()
        if self._site:
            await self._site.stop()
        if self._runner:
            await self._runner.cleanup()


# Global singleton instance
_ui_server: ZezoUIServer | None = None


def get_ui_server() -> ZezoUIServer:
    """Get or create the global UI server singleton."""
    global _ui_server
    if _ui_server is None:
        _ui_server = ZezoUIServer()
    return _ui_server
