"""
test_memory_recovery_and_isolation_suite.py — Verifies long_term.json protection and recovery.
"""
import os
import json
import tempfile
from pathlib import Path
from memory.memory_manager import load_memory, save_memory, MEMORY_PATH


def test_real_memory_is_restored_and_valid():
    real_path = Path(__file__).resolve().parent.parent / "memory" / "long_term.json"
    assert real_path.exists(), "memory/long_term.json must exist"
    assert real_path.stat().st_size > 5000, f"memory/long_term.json size ({real_path.stat().st_size}) must be > 5000 bytes"
    
    data = json.loads(real_path.read_text(encoding="utf-8"))
    assert "identity" in data
    assert data["identity"].get("name", {}).get("value") == "Hamza"


def test_auto_recovery_from_backup_on_zero_bytes(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_json = Path(tmp_dir) / "test_mem.json"
        tmp_bak = Path(tmp_dir) / "test_mem.json.bak"
        
        # Valid backup
        valid_data = {"identity": {"name": {"value": "Hamza"}}, "preferences": {}}
        tmp_bak.write_text(json.dumps(valid_data), encoding="utf-8")
        
        # Corrupted 0-byte file
        tmp_json.write_text("", encoding="utf-8")
        assert tmp_json.stat().st_size == 0
        
        monkeypatch.setattr("memory.memory_manager.MEMORY_PATH", tmp_json)
        
        loaded = load_memory()
        assert loaded.get("identity", {}).get("name", {}).get("value") == "Hamza"
        assert tmp_json.stat().st_size > 0, "0-byte file must be auto-recovered from backup replica"


def test_save_memory_atomic_and_never_leaves_zero_bytes(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_json = Path(tmp_dir) / "test_mem.json"
        monkeypatch.setattr("memory.memory_manager.MEMORY_PATH", tmp_json)
        
        save_memory({"identity": {"name": {"value": "Hamza Bukhari"}}})
        assert tmp_json.exists()
        assert tmp_json.stat().st_size > 0
        
        # Backup replica also created
        bak = tmp_json.with_suffix(".json.bak")
        assert bak.exists()
        assert bak.stat().st_size > 0
