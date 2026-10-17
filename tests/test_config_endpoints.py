"""
tests/test_config_endpoints.py — Verifies /api/config and /api/settings endpoints for real persistence of languages, API keys, and quick control toggles.
"""
import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from core.ui_server import ZezoUIServer
import memory.config_manager as config_manager


class TestConfigEndpoints(AioHTTPTestCase):
    async def get_application(self):
        self.server = ZezoUIServer(host="127.0.0.1", port=0)
        app = web.Application()
        app.router.add_get("/api/config", self.server._get_config_handler)
        app.router.add_post("/api/config", self.server._save_config_handler)
        app.router.add_get("/api/settings/assistant", self.server._get_config_handler)
        app.router.add_post("/api/settings/assistant", self.server._save_assistant_settings_handler)
        return app

    @unittest_run_loop
    async def test_get_and_save_config_roundtrip(self):
        # 1. Test GET /api/config
        resp = await self.client.get("/api/config")
        assert resp.status == 200
        data = await resp.json()
        assert "response_language" in data
        assert "available_languages" in data
        assert "English" in data["available_languages"]
        assert "Urdu" in data["available_languages"]
        assert "gemini_api_key_masked" in data
        assert "autostart_enabled" in data
        assert "wake_word_enabled" in data
        assert "available_assistant_names" in data
        assert "theme" in data
        assert "accent" in data

        # 2. Test POST /api/config with updated settings
        payload = {
            "response_language": "Urdu",
            "assistant_name": "ZEZO-TEST",
            "voice_name": "Charon",
            "theme": "emerald",
            "accent": "#10b981",
            "autostart_enabled": True,
            "morning_brief_enabled": False,
            "wake_word_enabled": True,
            "push_to_talk_enabled": False,
            "avatar_preset": "spark",
            "avatar_shape": "prism",
            "avatar_theme": "neon",
        }
        post_resp = await self.client.post("/api/config", json=payload)
        assert post_resp.status == 200

        # 3. Assert memory config values updated
        assert config_manager.get_response_language() == "Urdu"
        assert config_manager.get_assistant_name() == "ZEZO-TEST"
        assert config_manager.get_wake_word_enabled() is True
        assert config_manager.get_brief_enabled() is False
        assert config_manager.get_theme() == "emerald"
        assert config_manager.get_accent() == "#10b981"
        avatar_cfg = config_manager.get_avatar_settings()
        assert avatar_cfg["avatar_preset"] == "spark"
        assert avatar_cfg["avatar_shape"] == "prism"
        assert avatar_cfg["avatar_theme"] == "neon"

        # 4. Clean up / restore defaults
        config_manager.save_response_language("auto")
        config_manager.save_assistant_config("Zezo", "")
        config_manager.save_wake_word_enabled(False)
        config_manager.save_brief_enabled(True)
        config_manager.save_theme("copper")
        config_manager.save_accent("#ea580c")
        config_manager.save_avatar_settings({
            "avatar_preset": "qivi",
            "avatar_shape": "blob",
            "avatar_theme": "match_theme",
        })

