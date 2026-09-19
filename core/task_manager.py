"""
core/task_manager.py

Background task registry. Thread-safe. No asyncio required.

A coding agent (OpenCode / Kilo) submits a task and returns immediately
with a short task_id. The actual subprocess runs in a daemon thread.
Progress and state are readable via task_status().
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskState:
    id: str
    tool: str
    status: TaskStatus = TaskStatus.QUEUED
    progress: int = 0
    message: str = ""
    result: Optional[dict] = None
    error: Optional[str] = None
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    cancel_event: threading.Event = field(default_factory=threading.Event)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tool": self.tool,
            "status": self.status.value,
            "progress": self.progress,
            "message": self.message,
            "result": self.result,
            "error": self.error,
            "elapsed_sec": round(
                (self.finished_at or time.time()) - self.started_at, 1
            ),
        }


class TaskManager:
    def __init__(self, max_tasks: int = 100, ttl_sec: int = 3600):
        self._tasks: dict[str, TaskState] = {}
        self._last_task_id: Optional[str] = None
        self._lock = threading.RLock()
        self._max = max_tasks
        self._ttl = ttl_sec

    # ── public ───────────────────────────────────────────────

    def submit(
        self,
        tool_name: str,
        fn: Callable[[dict, "TaskContext"], dict],
        params: dict,
    ) -> str:
        task_id = uuid.uuid4().hex[:8]
        state = TaskState(id=task_id, tool=tool_name)
        with self._lock:
            self._prune()
            self._tasks[task_id] = state
            self._last_task_id = task_id

        ctx = TaskContext(task_id, self)

        def _run():
            state.status = TaskStatus.RUNNING
            try:
                result = fn(params, ctx)
                if state.cancel_event.is_set():
                    state.status = TaskStatus.CANCELLED
                else:
                    state.status = TaskStatus.DONE
                    state.result = result
                    state.progress = 100
                    state.message = "completed"
            except Exception as e:
                logger.exception("task %s failed", task_id)
                state.status = TaskStatus.FAILED
                state.error = f"{type(e).__name__}: {e}"
            finally:
                state.finished_at = time.time()

        threading.Thread(
            target=_run, name=f"jarvis-task-{task_id}", daemon=True
        ).start()
        logger.info("task %s [%s] submitted", task_id, tool_name)
        return task_id

    def status(self, task_id: str) -> Optional[dict]:
        with self._lock:
            s = self._tasks.get(task_id)
            return s.to_dict() if s else None

    def get_latest_task(self) -> Optional[dict]:
        with self._lock:
            if self._last_task_id and self._last_task_id in self._tasks:
                return self._tasks[self._last_task_id].to_dict()
            if self._tasks:
                # Return most recently started task
                latest = max(self._tasks.values(), key=lambda s: s.started_at)
                return latest.to_dict()
            return None

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            s = self._tasks.get(task_id)
            if not s or s.status in (
                TaskStatus.DONE, TaskStatus.FAILED, TaskStatus.CANCELLED
            ):
                return False
            s.cancel_event.set()
            s.status = TaskStatus.CANCELLED
            s.finished_at = time.time()
            return True

    def list_active(self) -> list[dict]:
        with self._lock:
            return [
                s.to_dict() for s in self._tasks.values()
                if s.status in (TaskStatus.QUEUED, TaskStatus.RUNNING)
            ]

    def all_tasks(self) -> list[dict]:
        with self._lock:
            return [s.to_dict() for s in self._tasks.values()]

    # ── internal ─────────────────────────────────────────────

    def _report(self, task_id: str, progress: int, message: str = "") -> None:
        with self._lock:
            s = self._tasks.get(task_id)
            if not s:
                return
            if progress is not None and progress >= 0:
                s.progress = max(0, min(100, progress))
            if message:
                s.message = message[-280:]

    def _prune(self) -> None:
        now = time.time()
        dead = [
            tid for tid, s in self._tasks.items()
            if s.finished_at and (now - s.finished_at) > self._ttl
        ]
        for tid in dead:
            del self._tasks[tid]
        if len(self._tasks) > self._max:
            finished = sorted(
                (s for s in self._tasks.values() if s.finished_at),
                key=lambda s: s.finished_at,
            )
            while len(self._tasks) > self._max and finished:
                old = finished.pop(0)
                self._tasks.pop(old.id, None)


class TaskContext:
    def __init__(self, task_id: str, mgr: TaskManager):
        self.task_id = task_id
        self._mgr = mgr

    def report(self, progress: int, message: str = "") -> None:
        self._mgr._report(self.task_id, progress, message)

    def cancelled(self) -> bool:
        with self._mgr._lock:
            s = self._mgr._tasks.get(self.task_id)
            return bool(s and s.cancel_event.is_set())


# ── singleton ────────────────────────────────────────────────

_default: Optional[TaskManager] = None
_default_lock = threading.Lock()


def get_task_manager() -> TaskManager:
    global _default
    if _default is None:
        with _default_lock:
            if _default is None:
                _default = TaskManager()
    return _default
