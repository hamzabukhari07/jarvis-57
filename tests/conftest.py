import os
import sys
import tempfile
from pathlib import Path

import pytest

# Create dedicated test temp isolation directory BEFORE ANY PROJECT IMPORTS
_TEST_TEMP_DIR = tempfile.mkdtemp(prefix="zezo_test_isolation_")
_TEST_DB_PATH = os.path.join(_TEST_TEMP_DIR, "test_zezo_brain.db")

# Force all memory writes to isolated temp DB and JSON file
os.environ["ZEZO_DB_PATH"] = _TEST_DB_PATH
_TEST_MEMORY_PATH = os.path.join(_TEST_TEMP_DIR, "test_long_term.json")
Path(_TEST_MEMORY_PATH).write_text("{}", encoding="utf-8")
os.environ["ZEZO_MEMORY_PATH"] = _TEST_MEMORY_PATH
os.environ["ZEZO_TEST_MODE"] = "1"
os.environ["ZEZO_WORKSPACE"] = _TEST_TEMP_DIR

# Force repo_context's store into the isolated temp dir BEFORE core.repo_context is imported.
# memory/repo_context.json is a PRODUCTION file and memory/*.json is gitignored, so a test that
# calls remember_repo() used to pollute the real store invisibly and permanently (Issue 10).
_TEST_REPO_CONTEXT_PATH = os.path.join(_TEST_TEMP_DIR, "test_repo_context.json")
Path(_TEST_REPO_CONTEXT_PATH).write_text("{}", encoding="utf-8")
os.environ["ZEZO_REPO_CONTEXT_STORE"] = _TEST_REPO_CONTEXT_PATH


@pytest.fixture(autouse=True)
def _isolate_repo_context_store(tmp_path, monkeypatch):
    """Point core.repo_context at a per-test temp store, never the real memory file."""
    store = tmp_path / "repo_context.json"
    store.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("ZEZO_REPO_CONTEXT_STORE", str(store))
    repo_context = sys.modules.get("core.repo_context")
    if repo_context is not None:
        # The module-level _STORE_PATH was already resolved at import time; re-point it per test.
        monkeypatch.setattr(repo_context, "_STORE_PATH", store, raising=False)
    return store
