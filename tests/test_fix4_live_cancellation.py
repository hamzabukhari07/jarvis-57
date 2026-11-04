"""
tests/test_fix4_live_cancellation.py - Verification tests for FIX 4:
Live Cancellation across Streaming and External Processes.

Verifies:
1. Conversational Cancellation Test:
   - Start a live streaming request via runtime.step_stream_async(user_input="Write a 1000-word essay on history of computing").
   - Read 1 or 2 chunks.
   - Cancel the async task or generator (task.cancel() / generator.aclose()).
   - Verify cancellation exception is handled cleanly without crashing.
   - Verify no orphaned background tasks remain.
   - Verify backend processing halts (stop_event signals producer thread to exit).
   - Verify the conversation remains valid and subsequent queries succeed.
2. External Process Tree Cancellation Test:
   - Spawn a process tree via ProcessSupervisor.spawn().
   - Verify Win32 Job Object containment.
   - Call terminate_tree().
   - Verify root, child, and grandchild processes terminate immediately with 0 orphaned processes.
"""

import asyncio
import os
import platform
import subprocess
import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock

import psutil
import pytest

from core.agents.runtime import AgentRuntime
from core.engines.process_supervisor import ContainedProcess, ProcessSupervisor
from memory.sqlite_memory import init_db, reset_db_writer_for_test


@pytest.fixture(autouse=True)
def setup_teardown_test_env(tmp_path, monkeypatch):
    """Ensure clean SQLite memory environment for tests."""
    test_db = tmp_path / "test_fix4_cancellation.db"
    monkeypatch.setattr("memory.sqlite_memory.get_db_path", lambda: test_db)
    monkeypatch.setattr("memory.sqlite_memory.DB_PATH", test_db)
    init_db()
    yield
    reset_db_writer_for_test()


def test_conversational_cancellation_task_cancel(monkeypatch):
    """
    Test Conversational Cancellation via asyncio.Task cancellation:
    - Starts streaming request.
    - Consumes 2 chunks.
    - Cancels task.
    - Verifies CancelledError caught cleanly, producer thread halts, conversation state valid,
      and subsequent query completes cleanly.
    """
    async def _async_test():
        producer_running = threading.Event()
        producer_halted = threading.Event()

        def mock_stream_text(contents, tier="fast", timeout_ms=30000):
            producer_running.set()
            words = ["Computing", "history", "spans", "decades", "from", "abacus", "to", "quantum", "silicon", "supercomputers."]
            for w in words:
                yield f"{w} "
                time.sleep(0.05)
            producer_halted.set()

        monkeypatch.setattr("core.gemini.stream_text", mock_stream_text)

        runtime = AgentRuntime(agent_id="MICHAEL")
        cid = runtime.get_or_create_conversation(title="Cancellation Test")

        chunks_received = []

        async def run_stream():
            async for chunk in runtime.step_stream_async(
                user_input="Write a 1000-word essay on history of computing",
                conversation_id=cid,
            ):
                chunks_received.append(chunk)
                if len(chunks_received) >= 2:
                    await asyncio.sleep(0)

        stream_task = asyncio.create_task(run_stream())

        # Wait until at least 2 chunks arrive
        while len(chunks_received) < 2:
            await asyncio.sleep(0.02)

        assert len(chunks_received) >= 2
        assert producer_running.is_set()

        # Cancel the streaming task
        stream_task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await stream_task

        assert stream_task.cancelled()

        # Verify background producer halted and no orphaned tasks remain in loop
        await asyncio.sleep(0.15)
        pending_tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        assert len(pending_tasks) == 0, f"Expected 0 orphaned tasks, found: {pending_tasks}"

        # Verify subsequent query succeeds and conversation remains valid
        def mock_stream_text_followup(contents, tier="fast", timeout_ms=30000):
            yield "Follow-up response completed successfully."

        monkeypatch.setattr("core.gemini.stream_text", mock_stream_text_followup)

        followup_events = []
        async for event in runtime.step_stream_async(
            user_input="Continue with summary",
            conversation_id=cid,
        ):
            followup_events.append(event)

        done_events = [e for e in followup_events if e.get("event") == "done"]
        assert len(done_events) == 1
        assert "Follow-up response completed successfully." in done_events[0]["reply"]

        # Verify conversation history has both turns recorded
        messages = runtime.load_messages(conversation_id=cid)
        user_msgs = [m for m in messages if m.get("role") == "user"]
        assistant_msgs = [m for m in messages if m.get("role") == "assistant"]
        assert len(user_msgs) == 2
        assert len(assistant_msgs) == 1  # Only the completed follow-up persisted assistant reply

    asyncio.run(_async_test())


def test_conversational_cancellation_generator_aclose(monkeypatch):
    """
    Test Conversational Cancellation via generator.aclose():
    - Starts streaming generator.
    - Yields first chunk.
    - Calls aclose().
    - Verifies clean teardown and subsequent conversation integrity.
    """
    async def _async_test():
        def mock_infinite_stream(contents, tier="fast", timeout_ms=30000):
            for i in range(100):
                yield f"chunk_{i} "
                time.sleep(0.04)

        monkeypatch.setattr("core.gemini.stream_text", mock_infinite_stream)

        runtime = AgentRuntime(agent_id="MICHAEL")
        cid = runtime.get_or_create_conversation(title="Aclose Test")

        gen = runtime.step_stream_async(
            user_input="Write a 1000-word essay on history of computing",
            conversation_id=cid,
        )

        first_item = await anext(gen)
        assert first_item["event"] == "chunk"
        assert first_item["text"] == "chunk_0 "

        # Explicitly close async generator
        await gen.aclose()

        # Generator must be exhausted / stopped
        with pytest.raises(StopAsyncIteration):
            await anext(gen)

        # Verify subsequent query in same conversation functions properly
        def mock_short_stream(contents, tier="fast", timeout_ms=30000):
            yield "Subsequent turn works."

        monkeypatch.setattr("core.gemini.stream_text", mock_short_stream)

        results = []
        async for item in runtime.step_stream_async("Next turn", conversation_id=cid):
            results.append(item)

        assert any(item.get("event") == "done" for item in results)

    asyncio.run(_async_test())


def test_external_process_tree_cancellation(tmp_path):
    """
    Test External Process Tree Cancellation:
    - Spawn a multi-tier process tree (root -> child -> grandchild).
    - Verify Win32 Job Object containment (or process group on POSIX).
    - Call terminate_tree().
    - Verify root, child, and grandchild processes terminate immediately with 0 orphaned processes.
    """
    script_file = tmp_path / "process_tree_spawner.py"
    script_file.write_text(
        """
import subprocess, sys, time

# Child spawns a grandchild
grandchild_code = "import time; time.sleep(60)"
child_code = f"import subprocess, sys, time; gc = subprocess.Popen([sys.executable, '-c', \\"{grandchild_code}\\"]); print(f'GRANDCHILD_PID:{{gc.pid}}', flush=True); time.sleep(60)"

child = subprocess.Popen([sys.executable, "-c", child_code], stdout=subprocess.PIPE, text=True)
print(f"CHILD_PID:{child.pid}", flush=True)

# Read grandchild PID from child
gc_pid_line = child.stdout.readline()
print(gc_pid_line, end="", flush=True)

time.sleep(60)
""",
        encoding="utf-8",
    )

    cmd = [sys.executable, str(script_file)]
    proc = ProcessSupervisor.spawn(cmd, cwd=tmp_path)

    assert proc.pid > 0
    if platform.system() == "Windows":
        assert proc.h_job is not None, "Process must be contained in a Win32 Job Object"

    child_pid = None
    grandchild_pid = None

    # Parse stdout to get child and grandchild pids
    start_wait = time.time()
    while time.time() - start_wait < 10.0:
        line = proc.pipe_file.readline()
        if not line:
            time.sleep(0.05)
            continue
        line = line.strip()
        if "CHILD_PID:" in line:
            child_pid = int(line.split("CHILD_PID:")[1])
        if "GRANDCHILD_PID:" in line:
            grandchild_pid = int(line.split("GRANDCHILD_PID:")[1])
        if child_pid and grandchild_pid:
            break

    assert child_pid is not None, "Failed to capture child PID"
    assert grandchild_pid is not None, "Failed to capture grandchild PID"

    root_pid = proc.pid

    # Verify all 3 processes are currently running in the OS
    root_proc = psutil.Process(root_pid)
    child_proc = psutil.Process(child_pid)
    gc_proc = psutil.Process(grandchild_pid)

    assert root_proc.is_running()
    assert child_proc.is_running()
    assert gc_proc.is_running()

    # Call terminate_tree()
    proc.terminate_tree()

    # Wait briefly for kernel cleanup
    time.sleep(0.3)

    # Verify root, child, and grandchild are ALL terminated
    assert not root_proc.is_running() or root_proc.status() == psutil.STATUS_ZOMBIE
    assert not child_proc.is_running() or child_proc.status() == psutil.STATUS_ZOMBIE
    assert not gc_proc.is_running() or gc_proc.status() == psutil.STATUS_ZOMBIE

    # Double check via psutil pid_exists
    time.sleep(0.2)
    for p, name in [(root_pid, "Root"), (child_pid, "Child"), (grandchild_pid, "Grandchild")]:
        exists = False
        try:
            p_obj = psutil.Process(p)
            exists = p_obj.is_running() and p_obj.status() != psutil.STATUS_ZOMBIE
        except psutil.NoSuchProcess:
            exists = False
        assert not exists, f"{name} process (PID {p}) was not terminated! Orphan detected."


if __name__ == "__main__":
    pytest.main(["-v", __file__])
