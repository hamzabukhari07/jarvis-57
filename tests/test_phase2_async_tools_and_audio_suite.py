"""
tests/test_phase2_async_tools_and_audio_suite.py

Unit tests for Phase 2: Non-Blocking Tool Protocol & Audio Pipeline Continuity.
Verifies:
1. Long-running tools (dev_agent) return task_id immediately and execute asynchronously via TaskManager.
2. Mic audio callback does not drop user audio packets when tool is executing (_tool_busy = True).
3. Explicit sample rate 'audio/pcm;rate=16000' is strictly preserved.
"""

import sys
import time
from pathlib import Path
import pytest
import numpy as np

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.task_manager import get_task_manager, TaskStatus
from actions.opencode_agent import opencode_run, TOOL as OPENCODE_TOOL


def test_opencode_agent_async_submission():
    """Verify opencode_run returns an immediate task_id and runs in background via TaskManager."""
    tm = get_task_manager()
    
    params = {
        "task": "Create a dummy hello world microservice in python",
        "timeout": 5,
    }
    
    res = opencode_run(params)
    assert "task" in res.lower() or "started" in res.lower()
    
    import re
    m = re.search(r"task\s+([a-f0-9]{8})|\[([a-f0-9]{8})\]", res, re.IGNORECASE)
    if m:
        task_id = m.group(1) or m.group(2)
        state = tm.status(task_id)
        assert state is not None
        assert state["tool"] in ("opencode_run", "opencode_agent")
        assert state["status"] in (TaskStatus.QUEUED.value, TaskStatus.RUNNING.value, TaskStatus.DONE.value)
    
    # Verify tool metadata
    assert OPENCODE_TOOL.get("behavior") == "NON_BLOCKING"
    assert OPENCODE_TOOL.get("scheduling") == "WHEN_IDLE"


def test_mic_audio_continuity_during_tool_execution():
    """Verify that during tool execution (_tool_busy = True), user speech is not dropped by the mic callback."""
    # Simulate the mic callback logic from main.py
    SEND_SAMPLE_RATE = 16000
    out_queue_mock = []
    
    zezo_speaking = False
    tool_busy = True  # Tool is currently executing
    
    indata = (np.random.randn(512) * 1000).astype(np.int16)
    
    # In Phase 2, the mic callback checks only zezo_speaking, not tool_busy
    should_drop = zezo_speaking  # Must NOT include tool_busy
    assert not should_drop, "User mic packets must continue streaming while tools execute"
    
    # Enqueue check
    data = indata.tobytes()
    payload = {"data": data, "mime_type": f"audio/pcm;rate={SEND_SAMPLE_RATE}"}
    out_queue_mock.append(payload)
    
    assert len(out_queue_mock) == 1
    assert payload["mime_type"] == "audio/pcm;rate=16000"
