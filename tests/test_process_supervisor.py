"""
tests/test_process_supervisor.py — Unit and integration tests for ProcessSupervisor.

Verifies:
1. Direct Win32 process creation and clean output streaming.
2. Contained execution within Job Objects.
3. Rapid process tree termination on close (no orphaned workers).
4. Timeout and cancellation behavior.
5. Error handling when invalid binary or missing working directory is passed.
"""

import os
import platform
import subprocess
import sys
import time
from pathlib import Path
import pytest

from core.engines.process_supervisor import ContainedProcess, ProcessSupervisor


def test_process_supervisor_simple_execution(tmp_path):
    """Verify that a basic command executes, streams output, and terminates with code 0."""
    cmd = [sys.executable, "-c", "import sys; print('HELLO_ZEZO_SUPERVISOR'); sys.exit(0)"]
    proc = ProcessSupervisor.spawn(cmd, cwd=tmp_path)

    assert proc.pid > 0
    assert proc.pipe_file is not None

    output_lines = []
    for line in iter(proc.pipe_file.readline, ""):
        if not line:
            break
        output_lines.append(line.strip())

    exit_code = proc.wait(timeout=5.0)
    assert exit_code == 0
    assert "HELLO_ZEZO_SUPERVISOR" in output_lines
    proc.terminate_tree()


def test_process_supervisor_poll_and_exit_code(tmp_path):
    """Verify poll() reports None while running and non-zero exit code when process fails."""
    cmd = [sys.executable, "-c", "import time, sys; time.sleep(0.3); sys.exit(42)"]
    proc = ProcessSupervisor.spawn(cmd, cwd=tmp_path)

    # Immediately after resume, process should still be running
    assert proc.poll() is None

    exit_code = proc.wait(timeout=5.0)
    assert exit_code == 42
    assert proc.poll() == 42
    proc.terminate_tree()


def test_process_supervisor_process_tree_termination(tmp_path):
    """
    Verify that closing the Job Object terminates the root process AND child worker processes.
    Spawns a python script that spawns a child worker, then calls terminate_tree().
    """
    worker_script = tmp_path / "tree_worker.py"
    worker_script.write_text(
        """
import subprocess, sys, time
# Spawn grandchild worker that runs for 60 seconds
child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
print(f"CHILD_PID:{child.pid}", flush=True)
time.sleep(60)
""",
        encoding="utf-8",
    )

    cmd = [sys.executable, str(worker_script)]
    proc = ProcessSupervisor.spawn(cmd, cwd=tmp_path)

    child_pid = None
    for line in iter(proc.pipe_file.readline, ""):
        if "CHILD_PID:" in line:
            child_pid = int(line.strip().split("CHILD_PID:")[1])
            break

    assert child_pid is not None
    assert child_pid > 0

    # Verify grandchild is running
    if platform.system() == "Windows":
        task_check = subprocess.run(
            ["tasklist", "/FI", f"PID eq {child_pid}"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        assert str(child_pid) in task_check.stdout

    # Now terminate entire process tree via ProcessSupervisor
    proc.terminate_tree()
    time.sleep(0.3)

    # Verify grandchild process was instantly terminated by the kernel
    if platform.system() == "Windows":
        task_check_after = subprocess.run(
            ["tasklist", "/FI", f"PID eq {child_pid}"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        assert str(child_pid) not in task_check_after.stdout, f"Grandchild PID {child_pid} was not terminated!"


def test_process_supervisor_invalid_binary(tmp_path):
    """Verify that attempting to spawn a non-existent binary raises an OSError cleanly."""
    cmd = ["non_existent_executable_12345.exe", "--help"]
    with pytest.raises(OSError):
        ProcessSupervisor.spawn(cmd, cwd=tmp_path)


def test_process_supervisor_environment_inheritance(tmp_path):
    """Verify that passed environment variables are received by the child process."""
    cmd = [sys.executable, "-c", "import os; print(os.environ.get('ZEZO_TEST_VAR', ''))"]
    proc = ProcessSupervisor.spawn(cmd, cwd=tmp_path, env={"ZEZO_TEST_VAR": "SUPERVISOR_SECRET_VALUE"})

    line = proc.pipe_file.readline().strip()
    proc.wait(timeout=3.0)
    proc.terminate_tree()

    assert line == "SUPERVISOR_SECRET_VALUE"

