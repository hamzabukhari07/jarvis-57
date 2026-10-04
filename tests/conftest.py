import os
import tempfile
from pathlib import Path

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
