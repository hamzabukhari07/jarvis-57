"""
actions/task_status.py — Report on background tasks.
"""

from __future__ import annotations

from core.task_manager import get_task_manager


def _fmt(d: dict) -> str:
    status = d["status"]
    tool = d["tool"]
    elapsed = d["elapsed_sec"]
    bits = [f"Task {d['id']} ({tool}): {status.upper()}"]
    if status == "running":
        bits.append(f"Progress: {d['progress']}%")
        if d.get("message"):
            bits.append(d["message"])
    elif status == "done":
        bits.append(f"Completed in {elapsed}s")
        if d.get("result"):
            res = d["result"]
            if isinstance(res, dict):
                if res.get("status") == "success":
                    bits.append("Status: Success")
                elif res.get("status") == "failed":
                    bits.append(f"Status: Failed (return code {res.get('return_code')})")
                if res.get("tail"):
                    # Last 3 meaningful output lines
                    tail_lines = [line.strip() for line in res["tail"] if line.strip()]
                    if tail_lines:
                        bits.append(f"Latest log: {' | '.join(tail_lines[-3:])}")
    elif status == "failed":
        bits.append(f"Failed after {elapsed}s: {d.get('error', 'unknown error')}")
    elif status == "cancelled":
        bits.append(f"Cancelled after {elapsed}s")
    return " · ".join(bits)


def task_status(parameters: dict, player=None, speak=None) -> str:
    tm = get_task_manager()
    task_id = (parameters.get("task_id") or "").strip()

    if task_id:
        st = tm.status(task_id)
        if st:
            return _fmt(st)
        latest = tm.get_latest_task()
        if latest:
            return f"No task with id '{task_id}'. Most recent task:\n{_fmt(latest)}"
        return f"No background task found with id '{task_id}'."

    active = tm.list_active()
    if active:
        return "Active Tasks:\n" + "\n".join(_fmt(s) for s in active)

    latest = tm.get_latest_task()
    if latest:
        return f"No tasks are currently running. Most recent task:\n{_fmt(latest)}"

    return "No background tasks have been started in this session."


TOOL = {
    "name": "task_status",
    "description": (
        "Check the status, live progress, or completion result of background tasks (opencode_run, kilo_run). "
        "Call this whenever the user asks 'kahan tak pohncha', 'how is it going', 'status batao', "
        "'kya ban gaya', or inquires about a background coding job. "
        "If the user does not specify a task ID, leave task_id empty to get the current or most recent task."
    ),
    "behavior": "BLOCKING",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "task_id": {
                "type": "STRING",
                "description": "Optional 8-char task ID. Leave empty to check the active or most recent task.",
            },
        },
        "required": [],
    },
    "handler": task_status,
}
