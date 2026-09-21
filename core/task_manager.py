"""
core/task_manager.py

Background task registry. Thread-safe. No asyncio required.

A coding agent (OpenCode / Kilo) submits a task and returns immediately
with a short task_id. The actual subprocess runs in a daemon thread.
Progress and state are readable via task_status().
"""

from __future__ import annotations

import logging
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

_ANSI_RE = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def strip_ansi(text: str) -> str:
    """Strip terminal ANSI color/cursor escape sequences."""
    return _ANSI_RE.sub('', text) if text else ""


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
    pid: Optional[int] = None
    params: dict = field(default_factory=dict)
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    notified: bool = False
    cancel_event: threading.Event = field(default_factory=threading.Event)
    _high_cpu_sec: int = field(default=0, repr=False)

    def to_dict(self) -> dict:
        prog = 100 if self.status == TaskStatus.DONE else self.progress
        return {
            "id": self.id,
            "tool": self.tool,
            "status": self.status.value,
            "progress": prog,
            "message": strip_ansi(self.message),
            "result": self.result,
            "error": self.error,
            "pid": self.pid,
            "params": self.params,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "elapsed_sec": round(
                (self.finished_at or time.time()) - self.started_at, 1
            ),
        }


CODING_TOOLS = {"opencode_agent", "kilo_agent", "dev_agent", "antigravity_agent"}
MAX_CONCURRENT_CODING_TASKS = 1


class TaskManager:
    MAX_WALLCLOCK_SEC: int = 1200  # 20 minutes max execution time

    def __init__(self, max_tasks: int = 100, ttl_sec: int = 3600):
        self._tasks: dict[str, TaskState] = {}
        self._last_task_id: Optional[str] = None
        self._lock = threading.RLock()
        self._max = max_tasks
        self._ttl = ttl_sec
        self._watchdog_started = False
        self._coding_queue: list[tuple[str, Callable, dict, TaskContext, TaskState]] = []

    # ── public ───────────────────────────────────────────────

    def submit(
        self,
        tool_name: str,
        fn: Callable[[dict, "TaskContext"], dict],
        params: dict,
    ) -> str:
        task_id = uuid.uuid4().hex[:8]
        state = TaskState(id=task_id, tool=tool_name, params=dict(params or {}))
        ctx = TaskContext(task_id, self)

        with self._lock:
            # Rapid duplicate submission debounce (prevents double-invocations from live voice stream)
            if tool_name in CODING_TOOLS:
                repo_target = (params or {}).get("repo") or (params or {}).get("project_path")
                now = time.time()
                for existing in self._tasks.values():
                    if (
                        existing.tool == tool_name
                        and existing.status in (TaskStatus.RUNNING, TaskStatus.QUEUED)
                        and not existing.finished_at
                        and (now - existing.started_at) < 8.0
                    ):
                        ex_repo = existing.params.get("repo") or existing.params.get("project_path")
                        if ex_repo and repo_target and str(ex_repo).lower() == str(repo_target).lower():
                            logger.info(
                                "Debounced duplicate %s call (returning active task %s in '%s')",
                                tool_name, existing.id, repo_target
                            )
                            return existing.id

            self._prune()
            self._tasks[task_id] = state
            self._last_task_id = task_id
            self._ensure_watchdog()

            if tool_name in CODING_TOOLS:
                active_coding = [
                    s for s in self._tasks.values()
                    if s.tool in CODING_TOOLS and s.status == TaskStatus.RUNNING and not s.finished_at
                ]
                if len(active_coding) >= MAX_CONCURRENT_CODING_TASKS:
                    state.status = TaskStatus.QUEUED
                    self._coding_queue.append((task_id, fn, params, ctx, state))
                    pos = len(self._coding_queue)
                    state.message = f"queued (position #{pos})"
                    logger.info("task %s [%s] queued at position %d", task_id, tool_name, pos)
                    return task_id

            self._start_task_thread(task_id, fn, params, ctx, state)
            return task_id

    def _start_task_thread(
        self,
        task_id: str,
        fn: Callable[[dict, "TaskContext"], dict],
        params: dict,
        ctx: TaskContext,
        state: TaskState,
    ) -> None:
        with self._lock:
            state.status = TaskStatus.RUNNING
            state.started_at = time.time()
            state.message = "running"

        def _run():
            try:
                result = fn(params, ctx)
                with self._lock:
                    if state.cancel_event.is_set():
                        state.status = TaskStatus.CANCELLED
                    elif state.status != TaskStatus.FAILED:
                        state.status = TaskStatus.DONE
                        if result is not None:
                            state.result = result
                        state.progress = 100
                        state.message = state.message or "completed"
            except Exception as e:
                logger.exception("task %s failed", task_id)
                with self._lock:
                    state.status = TaskStatus.FAILED
                    state.error = f"{type(e).__name__}: {e}"
                    state.message = f"failed: {e}"
            finally:
                with self._lock:
                    state.finished_at = time.time()
                    if state.pid:
                        self._terminate_pid(state.pid)
                    self._dequeue_next_coding_task()

        threading.Thread(
            target=_run, name=f"jarvis-task-{task_id}", daemon=True
        ).start()
        logger.info("task %s [%s] started", task_id, state.tool)


    def _dequeue_next_coding_task(self) -> None:
        """Called when a coding task completes; starts next queued task."""
        if not self._coding_queue:
            return
        active_coding = [
            s for s in self._tasks.values()
            if s.tool in CODING_TOOLS and s.status == TaskStatus.RUNNING and not s.finished_at
        ]
        if len(active_coding) < MAX_CONCURRENT_CODING_TASKS and self._coding_queue:
            next_task_id, next_fn, next_params, next_ctx, next_state = self._coding_queue.pop(0)
            for idx, item in enumerate(self._coding_queue, 1):
                item[4].message = f"queued (position #{idx})"
            self._start_task_thread(next_task_id, next_fn, next_params, next_ctx, next_state)

    def status(self, task_id: str) -> Optional[dict]:
        with self._lock:
            s = self._tasks.get(task_id)
            if not s:
                return None
            d = s.to_dict()
            # Consistency safeguard: if finished_at is set, status cannot be RUNNING or QUEUED
            if s.finished_at and d["status"] in (TaskStatus.RUNNING.value, TaskStatus.QUEUED.value):
                d["status"] = TaskStatus.DONE.value if not s.error else TaskStatus.FAILED.value
            if d["status"] in (TaskStatus.DONE.value, "done", "completed"):
                d["progress"] = 100
            return d

    def get_latest_task(self) -> Optional[dict]:
        with self._lock:
            if self._last_task_id and self._last_task_id in self._tasks:
                return self.status(self._last_task_id)
            if self._tasks:
                latest = max(self._tasks.values(), key=lambda s: s.started_at)
                return self.status(latest.id)
            return None

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            s = self._tasks.get(task_id)
            if not s or s.status in (
                TaskStatus.DONE, TaskStatus.FAILED, TaskStatus.CANCELLED
            ):
                return False
            self._coding_queue = [item for item in self._coding_queue if item[0] != task_id]
            s.cancel_event.set()
            s.status = TaskStatus.CANCELLED
            s.finished_at = time.time()
            self._terminate_pid(s.pid)
            self._dequeue_next_coding_task()
            return True

    def list_active(self) -> list[dict]:
        with self._lock:
            return [
                self.status(s.id) for s in self._tasks.values()
                if s.status in (TaskStatus.QUEUED, TaskStatus.RUNNING) and not s.finished_at
            ]

    def get_unnotified_finished_tasks(self) -> list[TaskState]:
        with self._lock:
            return [
                s for s in self._tasks.values()
                if s.status in (TaskStatus.DONE, TaskStatus.FAILED, TaskStatus.CANCELLED)
                and not s.notified
            ]

    def all_tasks(self) -> list[dict]:
        with self._lock:
            return [s.to_dict() for s in self._tasks.values()]

    def list_tasks(self) -> list[dict]:
        """Unified task list query."""
        return self.all_tasks()

    def get_categorized_tasks(self) -> dict[str, list[dict]]:
        """Returns tasks categorized into running, queued, and done lists.
        Thread-safe.
        """
        with self._lock:
            running = []
            queued = []
            done = []
            for s in self._tasks.values():
                d = self.status(s.id)
                if not d:
                    continue
                if d["status"] == TaskStatus.RUNNING.value and not s.finished_at:
                    running.append(d)
                elif d["status"] == TaskStatus.QUEUED.value and not s.finished_at:
                    queued.append(d)
                else:
                    done.append(d)
            running.sort(key=lambda x: x.get("started_at", 0) or 0, reverse=True)
            done.sort(key=lambda x: x.get("finished_at", 0) or x.get("started_at", 0) or 0, reverse=True)
            return {
                "running": running,
                "queued": queued,
                "done": done,
            }

    def get_active_tasks_cpu_percent(self) -> float:
        """Sums the CPU % of all running task subprocesses."""
        total_cpu = 0.0
        try:
            import psutil
            with self._lock:
                active_pids = [
                    s.pid for s in self._tasks.values()
                    if s.status in (TaskStatus.QUEUED, TaskStatus.RUNNING) and s.pid
                ]
            for pid in active_pids:
                try:
                    p = psutil.Process(pid)
                    if p.is_running():
                        total_cpu += p.cpu_percent(interval=None)
                        for child in p.children(recursive=True):
                            if child.is_running():
                                total_cpu += child.cpu_percent(interval=None)
                except Exception:
                    continue
        except Exception:
            pass
        return total_cpu

    # ── internal ─────────────────────────────────────────────

    def _set_pid(self, task_id: str, pid: int) -> None:
        with self._lock:
            s = self._tasks.get(task_id)
            if s:
                s.pid = pid

    def _report(self, task_id: str, progress: int, message: str = "") -> None:
        with self._lock:
            s = self._tasks.get(task_id)
            if not s:
                return
            if progress is not None and progress >= 0:
                s.progress = max(0, min(100, progress))
            if message:
                s.message = strip_ansi(message)[-280:]

    def _on_complete(self, task_id: str, result: Optional[dict] = None) -> None:
        with self._lock:
            s = self._tasks.get(task_id)
            if not s or s.status in (TaskStatus.CANCELLED, TaskStatus.FAILED):
                return
            s.status = TaskStatus.DONE
            s.progress = 100
            s.message = "completed"
            if result is not None:
                s.result = result

    def _on_fail(self, task_id: str, error: str) -> None:
        with self._lock:
            s = self._tasks.get(task_id)
            if not s or s.status == TaskStatus.CANCELLED:
                return
            s.status = TaskStatus.FAILED
            s.error = str(error)
            s.message = f"failed: {error}"


    def _ensure_watchdog(self) -> None:
        if not self._watchdog_started:
            self._watchdog_started = True
            threading.Thread(
                target=self._watchdog_loop, name="jarvis-task-watchdog", daemon=True
            ).start()

    def _watchdog_loop(self) -> None:
        """Every 5 seconds, monitors task wall-clock timeouts and high CPU usage."""
        import psutil
        while True:
            time.sleep(5)
            try:
                now = time.time()
                with self._lock:
                    running_tasks = [
                        s for s in self._tasks.values()
                        if s.status in (TaskStatus.QUEUED, TaskStatus.RUNNING)
                    ]

                for state in running_tasks:
                    elapsed = now - state.started_at

                    # 1. Hard 20-minute wall-clock timeout check
                    if elapsed > self.MAX_WALLCLOCK_SEC:
                        logger.warning(
                            "Task %s (%s) exceeded 20-minute timeout (%.1fs). Terminating.",
                            state.id, state.tool, elapsed
                        )
                        state.cancel_event.set()
                        state.status = TaskStatus.FAILED
                        state.error = f"Task exceeded 20-minute wall-clock timeout ({round(elapsed)}s)"
                        state.finished_at = now
                        self._terminate_pid(state.pid)
                        continue

                    # 2. CPU watchdog check (multi-core aware)
                    if state.pid:
                        try:
                            proc = psutil.Process(state.pid)
                            if proc.is_running():
                                core_count = psutil.cpu_count(logical=True) or 4
                                threshold = max(180.0, core_count * 25.0)
                                proc_cpu = proc.cpu_percent(interval=None)
                                for child in proc.children(recursive=True):
                                    if child.is_running():
                                        proc_cpu += child.cpu_percent(interval=None)
                                if proc_cpu > threshold:
                                    state._high_cpu_sec += 5
                                    if state._high_cpu_sec >= 60:
                                        logger.warning(
                                            "[Task %s] %s process tree is using sustained high CPU (%.1f%% > %.1f%% threshold) for 60s+ (PID %d)",
                                            state.id, state.tool, proc_cpu, threshold, state.pid
                                        )
                                        state._high_cpu_sec = 0  # Warn once every 60s
                                else:
                                    state._high_cpu_sec = 0
                            else:
                                state._high_cpu_sec = 0
                        except Exception:
                            state._high_cpu_sec = 0
            except Exception as e:
                logger.debug("Task watchdog error: %s", e)

    def _terminate_pid(self, pid: Optional[int]) -> None:
        """Gracefully terminates (SIGTERM) then kills (SIGKILL) a process tree."""
        if not pid:
            return
        try:
            import psutil
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            for child in children:
                try:
                    child.terminate()
                except Exception:
                    pass
            parent.terminate()
            gone, alive = psutil.wait_procs([parent] + children, timeout=10)
            for p in alive:
                try:
                    p.kill()
                except Exception:
                    pass
        except Exception:
            pass

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

    def set_pid(self, pid: int) -> None:
        self._mgr._set_pid(self.task_id, pid)

    def report(self, progress: int, message: str = "") -> None:
        self._mgr._report(self.task_id, progress, message)

    def on_complete(self, result: Optional[dict] = None) -> None:
        self._mgr._on_complete(self.task_id, result)

    def on_fail(self, error: str) -> None:
        self._mgr._on_fail(self.task_id, error)

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
