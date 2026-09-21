"""
Local UI WebSocket & Static HTTP Server for ZEZO.
Bridges the Python agent engine (main.py, task_manager, log_bus) with the
modern HTML5 / ES Modules desktop web frontend.
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Callable

from aiohttp import web, WSMsgType

logger = logging.getLogger("zezo.ui_server")

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"


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

        # Callbacks from main.py / engine
        self.on_text_command: Callable[[str], None] | None = None
        self.on_interrupt: Callable[[], None] | None = None
        self.on_mute_toggle: Callable[[bool], None] | None = None
        self.on_remote_clicked: Callable[[], tuple[str, str] | None] | None = None
        self.on_file_uploaded: Callable[[dict[str, Any]], None] | None = None
        self.on_assistant_settings_changed: Callable[[str, str, str], None] | None = None
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
        app.router.add_get("/ws", self._ws_handler)
        app.router.add_get("/api/health", self._health_handler)
        app.router.add_post("/api/upload", self._upload_handler)
        app.router.add_post("/api/settings/assistant", self._save_assistant_settings_handler)
        app.router.add_get("/api/preview_voice", self._preview_voice_handler)

        # Serve frontend static assets
        if self.frontend_dir.exists():
            app.router.add_static("/", path=str(self.frontend_dir), show_index=False)

        self._runner = web.AppRunner(app)
        await self._runner.setup()

        # Attempt to bind to requested port, with fallback retry
        for attempt in range(5):
            try:
                self._site = web.TCPSite(self._runner, self.host, self.port)
                await self._site.start()
                logger.info("Zezo UI Server running at http://%s:%d", self.host, self.port)
                break
            except OSError:
                if attempt == 4:
                    raise
                self.port += 1

    async def _health_handler(self, request: web.Request) -> web.Response:
        return web.json_response({"status": "ok", "app": "ZEZO", "port": self.port})

    async def _upload_handler(self, request: web.Request) -> web.Response:
        try:
            reader = await request.multipart()
            uploads_dir = BASE_DIR / "uploads"
            uploads_dir.mkdir(parents=True, exist_ok=True)

            saved_files = []
            while True:
                part = await reader.next()
                if part is None:
                    break
                if part.filename:
                    filename = Path(part.filename).name
                    dest_file = uploads_dir / filename
                    with open(dest_file, "wb") as f:
                        while True:
                            chunk = await part.read_chunk()
                            if not chunk:
                                break
                            f.write(chunk)
                    saved_files.append(dest_file)

            if not saved_files:
                return web.json_response({"status": "error", "message": "No files received"}, status=400)

            # Ingest files using core.file_reader
            from core.file_reader import read_file
            results = []
            for sf in saved_files:
                res = read_file(sf)
                file_info = {
                    "name": sf.name,
                    "path": str(sf),
                    "size": sf.stat().st_size,
                    "file_type": res.file_type,
                    "engine": res.engine,
                    "text": res.text,
                    "is_truncated": res.is_truncated,
                }
                results.append(file_info)

                # Broadcast to web UI
                self.broadcast("file_ingested", file_info)
                self.broadcast("log", {
                    "text": f"[Payload] Ingested '{sf.name}' ({sf.stat().st_size:,} bytes) via {res.engine}."
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

    async def _save_assistant_settings_handler(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
            name = str(data.get("assistant_name", "ZEZO")).strip() or "ZEZO"
            voice = str(data.get("voice_name", "Charon")).strip() or "Charon"
            lang = str(data.get("response_language", "auto")).strip() or "auto"

            from memory.config_manager import save_assistant_config, save_voice, save_response_language
            save_assistant_config(name, "")
            save_voice(voice)
            save_response_language(lang)

            if self.on_assistant_settings_changed:
                try:
                    self.on_assistant_settings_changed(name, voice, lang)
                except Exception as e:
                    logger.warning("on_assistant_settings_changed error: %s", e)

            self.broadcast("assistant_settings_updated", {
                "assistant_name": name,
                "voice_name": voice,
                "response_language": lang,
            })

            return web.json_response({
                "status": "success",
                "data": {"assistant_name": name, "voice_name": voice, "response_language": lang}
            })
        except Exception as e:
            logger.exception("Save assistant settings error: %s", e)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _preview_voice_handler(self, request: web.Request) -> web.Response:
        voice = request.query.get("voice", "Puck").strip().lower()
        mp3_path = self.frontend_dir / "assets" / "voices" / f"{voice}.mp3"
        if mp3_path.exists():
            return web.FileResponse(mp3_path)
        return web.Response(status=404, text="Voice preview not found")

    async def _index_handler(self, request: web.Request) -> web.Response:
        idx = self.frontend_dir / "index.html"
        if idx.exists():
            return web.FileResponse(idx)
        return web.Response(text="<h1>ZEZO UI Engine Online</h1><p>Frontend assets initializing...</p>", content_type="text/html")

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

        if msg_type == "user_message":
            text = str(payload.get("text", "")).strip()
            if text and self.on_text_command:
                threading.Thread(target=self.on_text_command, args=(text,), daemon=True).start()

        elif msg_type == "interrupt":
            if self.on_interrupt:
                self.on_interrupt()

        elif msg_type == "mute_toggle":
            muted = bool(payload.get("muted", False))
            if self.on_mute_toggle:
                self.on_mute_toggle(muted)

        elif msg_type == "get_remote_key":
            url, key = "http://localhost:8765", "8F3A-9K2L"
            if self.on_remote_clicked:
                try:
                    res = self.on_remote_clicked()
                    if res:
                        url, key = res[0], res[1]
                except Exception:
                    pass
            await ws.send_str(json.dumps({
                "type": "remote_key_data",
                "data": {"url": url, "key": key}
            }))

        elif msg_type == "task_cancel":
            task_id = str(payload.get("task_id", "")).strip()
            if task_id:
                try:
                    from core.task_manager import get_task_manager
                    get_task_manager().cancel(task_id)
                except Exception as e:
                    logger.warning("Failed to cancel task %s: %e", task_id, e)

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

        elif msg_type == "set_accent":
            color = str(payload.get("color", "")).strip().lower()
            if color:
                try:
                    cfg_file = BASE_DIR / "config" / "api_keys.json"
                    if cfg_file.exists():
                        data = json.loads(cfg_file.read_text(encoding="utf-8"))
                    else:
                        data = {}
                    data["ui_color"] = color
                    cfg_file.write_text(json.dumps(data, indent=4), encoding="utf-8")
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

        elif msg_type == "save_assistant_settings":
            name = str(payload.get("assistant_name", "ZEZO")).strip() or "ZEZO"
            voice = str(payload.get("voice_name", "Charon")).strip() or "Charon"
            lang = str(payload.get("response_language", "auto")).strip() or "auto"
            try:
                from memory.config_manager import save_assistant_config, save_voice, save_response_language
                save_assistant_config(name, "")
                save_voice(voice)
                save_response_language(lang)

                if self.on_assistant_settings_changed:
                    self.on_assistant_settings_changed(name, voice, lang)

                self.broadcast("assistant_settings_updated", {
                    "assistant_name": name,
                    "voice_name": voice,
                    "response_language": lang,
                })
            except Exception as e:
                logger.warning("Failed to save assistant settings from WS: %s", e)

    def _build_initial_state(self) -> dict:
        if self.get_initial_state:
            try:
                return self.get_initial_state()
            except Exception as e:
                logger.warning("Error getting initial state: %s", e)

        # Fallback default initial state
        tasks = []
        try:
            from core.task_manager import get_task_manager
            tasks = get_task_manager().list_tasks()
        except Exception:
            pass

        from memory.config_manager import get_assistant_name, get_voice, get_response_language
        return {
            "state": "IDLE",
            "muted": False,
            "assistant_name": get_assistant_name(),
            "voice_name": get_voice(),
            "response_language": get_response_language(),
            "tasks": tasks,
            "timestamp": time.time(),
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
