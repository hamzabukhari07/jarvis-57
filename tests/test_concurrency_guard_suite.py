"""
tests/test_concurrency_guard_suite.py — Central Orchestrator & Task Concurrency Guard Unit Tests.

Lead Architect: Hamza Bukhari
Project: ZEZO (Autonomous Desktop AI Operating System v2)
"""

import time
import threading
import pytest
from core.task_manager import TaskManager, TaskStatus, TaskContext, MAX_CONCURRENT_CODING_TASKS, CODING_TOOLS


class TestConcurrencyGuardSuite:
    def test_max_concurrency_constant(self):
        assert MAX_CONCURRENT_CODING_TASKS == 2
        assert "opencode_run" in CODING_TOOLS
        assert "kilo_run" in CODING_TOOLS
        assert "antigravity_run" in CODING_TOOLS

    def test_concurrency_queueing_three_tasks(self):
        """Submit 3 coding tasks: 2 should run immediately and the 3rd should be QUEUED."""
        tm = TaskManager()

        task1_started = threading.Event()
        task2_started = threading.Event()
        task3_started = threading.Event()
        release_all = threading.Event()

        def worker1(params, ctx: TaskContext):
            task1_started.set()
            release_all.wait(timeout=5.0)
            return {"status": "success", "id": 1}

        def worker2(params, ctx: TaskContext):
            task2_started.set()
            release_all.wait(timeout=5.0)
            return {"status": "success", "id": 2}

        def worker3(params, ctx: TaskContext):
            task3_started.set()
            release_all.wait(timeout=5.0)
            return {"status": "success", "id": 3}

        # Submit task 1 and task 2
        t1 = tm.submit("opencode_run", worker1, {"task": "Task 1"})
        t2 = tm.submit("kilo_run", worker2, {"task": "Task 2"})

        # Wait for t1 and t2 to begin running
        assert task1_started.wait(timeout=2.0)
        assert task2_started.wait(timeout=2.0)

        # Submit task 3 (should enter QUEUED state)
        t3 = tm.submit("antigravity_run", worker3, {"task": "Task 3"})
        
        st3 = tm.status(t3)
        assert st3["status"] == TaskStatus.QUEUED.value
        assert "queued" in st3["message"]

        # Confirm 2 running and 1 queued in active list
        active = tm.list_active()
        running_ids = [a["id"] for a in active if a["status"] == TaskStatus.RUNNING.value]
        queued_ids = [a["id"] for a in active if a["status"] == TaskStatus.QUEUED.value]

        assert t1 in running_ids
        assert t2 in running_ids
        assert t3 in queued_ids

        # Release running tasks
        release_all.set()

        # Task 3 should now automatically dequeue and start running
        assert task3_started.wait(timeout=2.0)

        # Allow time for completion
        time.sleep(0.5)

        st1 = tm.status(t1)
        st2 = tm.status(t2)
        st3 = tm.status(t3)

        assert st1["status"] == TaskStatus.DONE.value
        assert st2["status"] == TaskStatus.DONE.value
        assert st3["status"] == TaskStatus.DONE.value

    def test_cancel_queued_task(self):
        """Cancelling a queued task should cleanly remove it from the FIFO queue."""
        tm = TaskManager()

        hold_event = threading.Event()

        def slow_worker(params, ctx: TaskContext):
            hold_event.wait(timeout=5.0)
            return {"done": True}

        # Fill the 2 running slots
        t1 = tm.submit("opencode_run", slow_worker, {})
        t2 = tm.submit("kilo_run", slow_worker, {})

        time.sleep(0.1)

        # Queue tasks 3 and 4
        t3 = tm.submit("antigravity_run", slow_worker, {})
        t4 = tm.submit("quick_snippet", slow_worker, {})

        assert tm.status(t3)["message"] == "queued (position #1)"
        assert tm.status(t4)["message"] == "queued (position #2)"

        # Cancel task 3
        assert tm.cancel(t3) is True
        assert tm.status(t3)["status"] == TaskStatus.CANCELLED.value

        # Task 4 should now shift to position #1
        assert tm.status(t4)["message"] == "queued (position #1)"

        hold_event.set()
