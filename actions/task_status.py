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
    if status == "queued":
        bits.append(d.get("message", "Waiting in queue"))
    elif status == "running":
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
    action = (parameters.get("action") or "status").strip().lower()
    task_id = (parameters.get("task_id") or "").strip()

    if action in ("cancel", "stop", "kill"):
        if task_id:
            st = tm.status(task_id)
            tool_name = st.get("tool", "task") if st else "task"
            ok = tm.cancel(task_id)
            if ok:
                return f"Task {task_id} ({tool_name}) has been cancelled successfully."
            return f"Could not cancel task '{task_id}' (it may have already finished or does not exist)."
        
        # Cancel any active running or queued coding task
        active = tm.list_active()
        if active:
            # Prefer currently running coding tasks
            target = next((t for t in active if t.get("status") == "running"), active[0])
            tid = target["id"]
            tool_name = target.get("tool", "task")
            ok = tm.cancel(tid)
            if ok:
                return f"Task {tid} ({tool_name}) has been cancelled."
            return f"Failed to cancel active task {tid}."
        return "No active background tasks are currently running to cancel."

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
        "Check the status, live progress, or cancel background tasks (antigravity_run, opencode_run, kilo_run). "
        "Call this whenever the user asks 'kahan tak pohncha', 'how is it going', 'status batao', "
        "'kya ban gaya', or asks to cancel/stop a task ('cancel task', 'kilo band karo', 'stop opencode', 'task roko'). "
        "To cancel a running task, set action='cancel'. If task_id is omitted, it operates on the active task."
    ),
    "behavior": "BLOCKING",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Operation to perform: 'status' (default) to check progress, or 'cancel' to stop and terminate the running task.",
            },
            "task_id": {
                "type": "STRING",
                "description": "Optional 8-char task ID. Leave empty to check or cancel the active/most recent task.",
            },
        },
        "required": [],
    },
    "handler": task_status,
}
