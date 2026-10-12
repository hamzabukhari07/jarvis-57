from pathlib import Path

file_path = Path("core/ui_server.py")
text = file_path.read_text(encoding="utf-8")

# 1. Register routes in _run_thread
old_routes = """        app.router.add_get("/api/attachments", self._attachments_list_handler)
        app.router.add_get("/zezo-avatar.png", self._avatar_handler)"""

new_routes = """        app.router.add_get("/api/attachments", self._attachments_list_handler)
        app.router.add_get("/api/memory/stats", self._memory_stats_handler)
        app.router.add_post("/api/memory/clear", self._memory_clear_handler)
        app.router.add_post("/api/memory/optimize", self._memory_optimize_handler)
        app.router.add_post("/api/workspace/set", self._workspace_set_handler)
        app.router.add_get("/zezo-avatar.png", self._avatar_handler)"""

text = text.replace(old_routes, new_routes)

# 2. Key saving fix in _save_config_handler
old_key_block = """            keys_to_save = {}
            for k in ("gemini_api_key", "groq_api_key", "elevenlabs_api_key", "tavily_api_key",
                      "gemini_key", "groq_key", "elevenlabs_key", "tavily_key"):
                if k in data and data[k] is not None and str(data[k]).strip() and not str(data[k]).startswith("••••"):
                    normalized_k = k if k.endswith("_api_key") else f"{k.replace('_key', '')}_api_key"
                    keys_to_save[normalized_k] = str(data[k]).strip()"""

new_key_block = """            keys_to_save = {}
            for k in ("gemini_api_key", "groq_api_key", "elevenlabs_api_key", "tavily_api_key",
                      "gemini_key", "groq_key", "elevenlabs_key", "tavily_key"):
                val = str(data.get(k) or "").strip()
                if val and "••••" not in val and "..." not in val:
                    normalized_k = k if k.endswith("_api_key") else f"{k.replace('_key', '')}_api_key"
                    keys_to_save[normalized_k] = val"""

text = text.replace(old_key_block, new_key_block)

# 3. Add handler implementations before _avatar_handler
handlers_code = """    async def _memory_stats_handler(self, request: web.Request) -> web.Response:
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

    async def _memory_clear_handler(self, request: web.Request) -> web.Response:
        try:
            from memory.sqlite_memory import get_db_path
            db_path = get_db_path()
            if db_path.exists():
                import sqlite3
                with sqlite3.connect(str(db_path)) as conn:
                    conn.execute("DELETE FROM history_turns")
                    try:
                        conn.execute("DELETE FROM history_turns_fts")
                    except Exception:
                        pass
                    conn.commit()
            return web.json_response({"status": "success", "message": "Conversation history cleared"})
        except Exception as e:
            logger.exception("Error in /api/memory/clear: %s", e)
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

    async def _avatar_handler(self, request: web.Request) -> web.Response:"""

text = text.replace("    async def _avatar_handler(self, request: web.Request) -> web.Response:", handlers_code)

file_path.write_text(text, encoding="utf-8")
print("ui_server.py successfully updated with real memory & workspace endpoints!")

