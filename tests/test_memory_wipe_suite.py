"""
tests/test_memory_wipe_suite.py — Unit test suite for 4-layer memory total wipe engine.
"""

import json
import os
import tempfile
import sqlite3
from pathlib import Path
import pytest

from memory.vault_engine import VaultEngine
import memory.sqlite_memory as sm
import memory.memory_manager as mm


def test_vault_engine_wipe_memory():
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir)
        engine = VaultEngine(vault_dir=vault_path)

        # Clear any initial auto-synced convs
        for p in vault_path.glob("conv_*.md"):
            p.unlink()

        # Create multiple test conversation notes
        (vault_path / "conv_20261011_001.md").write_text("# Session 1\n[[Hamza Bukhari]]", encoding="utf-8")
        (vault_path / "conv_20261011_002.md").write_text("# Session 2\n[[ZEZO OS]]", encoding="utf-8")
        
        all_notes = list(vault_path.glob("*.md"))
        assert len(all_notes) >= 5, "Vault should contain seeded notes plus test session notes"

        # Wipe memory
        res = engine.wipe_all_vault_memory(preserve_profile=True)
        assert res["status"] == "success"
        assert res["deleted_conv_files"] == 2

        # Check remaining notes
        remaining = list(vault_path.glob("*.md"))
        assert not any(p.name.startswith("conv_") for p in remaining), "All conv_*.md files must be deleted"
        assert (vault_path / "user_profile.md").exists(), "Profile note must be preserved"
        assert (vault_path / "projects.md").exists(), "Projects note must be preserved"


def test_sqlite_wipe_all_memory(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = Path(tmpdir) / "test_brain.db"
        monkeypatch.setattr(sm, "get_db_path", lambda: test_db)
        sm.init_db()

        # Insert test records
        conn = sm._get_connection()
        try:
            with conn:
                conn.execute(
                    "INSERT INTO turns (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                    ("sess_1", "user", "Hello Zezo", "2026-10-11 12:00:00"),
                )
                conn.execute(
                    "INSERT INTO facts (category, key, value, updated_at) VALUES (?, ?, ?, ?)",
                    ("preferences", "test_key", "test_val", "2026-10-11 12:00:00"),
                )
        finally:
            conn.close()

        # Verify insertion
        conn = sm._get_connection()
        try:
            assert conn.execute("SELECT COUNT(*) FROM turns").fetchone()[0] == 1
            assert conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0] == 1
        finally:
            conn.close()

        # Execute wipe
        counts = sm.wipe_all_sqlite_memory()
        assert counts.get("turns") == 1
        assert counts.get("facts") == 1

        # Verify tables are completely empty
        conn = sm._get_connection()
        try:
            assert conn.execute("SELECT COUNT(*) FROM turns").fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM user_explicit_rules").fetchone()[0] == 0
        finally:
            conn.close()


def test_long_term_json_wipe(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        test_json = Path(tmpdir) / "long_term.json"
        monkeypatch.setattr(mm, "MEMORY_PATH", test_json)

        # Seed with data
        test_json.write_text(json.dumps({"identity": {"name": "Hamza"}, "sessions": [{"id": 1}]}), encoding="utf-8")
        assert test_json.stat().st_size > 0

        # Wipe
        mm.wipe_all_long_term_json()

        # Verify clean structure
        data = json.loads(test_json.read_text(encoding="utf-8"))
        assert data["identity"] == {}
        assert "sessions" not in data or data.get("sessions") == []
