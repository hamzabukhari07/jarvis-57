"""
actions/reverse_engineer.py - Native REA (Reverse Engineer Anything) Action Tool for ZEZO.

Exposes the 'reverse_engineer' action tool for Gemini Live / Assistant UI.
Invokes the official `rea` CLI engine (`rea capture-browser-scenario`) for 0-LLM CDP evidence extraction
returning pristine canonical evidence envelopes.
"""

import asyncio
import logging
import uuid
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from core.task_manager import TaskContext, get_task_manager

logger = logging.getLogger("zezo.actions.reverse_engineer")

TOOL = {
    "name": "reverse_engineer",
    "description": (
        "Reverse engineer, inspect stack, x-ray, or analyze the architecture of any website or web application using the official "
        "REA CLI engine (`rea capture-browser-scenario`). Extracts runtime DOM snapshots, accessibility tree, "
        "network transactions, request/response bodies and headers, storage, and console logs with zero LLM API cost. "
        "MUST be used whenever the user asks to 'reverse engineer', 'inspect stack', 'x-ray', or inspect 'architecture' of any website."
    ),
    "risk": "read_only",
    "enabled": True,
    "behavior": "NON_BLOCKING",
    "scheduling": "WHEN_IDLE",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "url": {
                "type": "STRING",
                "description": "The URL of the website or web app to inspect (e.g. 'https://linear.app' or 'https://stripe.com').",
            },
            "focus": {
                "type": "STRING",
                "enum": ["full", "architecture", "apis_network", "shaders_webgl", "animations"],
                "description": "Optional focus area for inspection. Defaults to 'full'.",
            },
        },
        "required": ["url"],
    },
    "handler": None,  # assigned below
}


def _teardown_task_worker(params: Dict[str, Any], ctx: TaskContext) -> Dict[str, Any]:
    """Background worker executed via TaskManager daemon thread."""
    from core.teardown_engine import run_native_rea_capture

    url = params.get("url", "").strip()
    focus = params.get("focus", "full").strip()

    def progress_callback(pct: int, msg: str) -> None:
        if ctx.cancelled():
            raise asyncio.CancelledError("REA task cancelled by user.")
        ctx.report(pct, msg)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(run_native_rea_capture(url, focus=focus, progress_callback=progress_callback, parent_task_id=ctx.task_id))
        summary_msg = result.get("summary") or f"Clean-room architectural rebuild and local dev server setup for {result['domain']} completed successfully at {result.get('rebuild_dir', 'workspace')}."
        ctx.report(100, summary_msg)
        result["output"] = summary_msg
        result["summary"] = summary_msg

        try:
            from core.ui_server import get_ui_server
            srv = get_ui_server()
            if srv:
                srv.broadcast("content_display", {
                    "title": f"🔬 REA Clean-Room Rebuild: {result['domain']}",
                    "text": f"{summary_msg}\n\nRebuild Directory:\n{result.get('rebuild_dir', 'N/A')}\n\nEvidence Envelope:\n{result['evidence_path']}\n\nObligation Ledger:\n{result.get('ledger_path', 'N/A')}\n\nTarget URL: {result['url']}",
                })
        except Exception:
            pass

        return result
    finally:
        loop.close()


def reverse_engineer_action(
    parameters: Dict[str, Any],
    player: Optional[Any] = None,
    speak: Optional[Any] = None,
    session_memory: Optional[Any] = None,
    **kwargs: Any,
) -> str:
    """Action entrypoint invoked by Gemini Live or Assistant-UI dispatch."""
    import re
    raw_input = str(
        parameters.get("url")
        or parameters.get("target")
        or parameters.get("link")
        or parameters.get("task")
        or parameters.get("query")
        or ""
    ).strip()

    if not raw_input:
        return "Error: Please provide a valid website URL to reverse engineer."

    url_match = re.search(r"https?://[^\s\"'>]+", raw_input)
    if url_match:
        url = url_match.group(0).rstrip(".,;)\"'>")
    else:
        domain_match = re.search(
            r"\b([a-zA-Z0-9-]+\.(?:com|org|io|dev|app|net|co|ai|sh|site|xyz|tech|tv|me|cc|so)(?:/[^\s\"'>]*)?)\b",
            raw_input,
            re.IGNORECASE,
        )
        if domain_match:
            url = f"https://{domain_match.group(1).rstrip('.,;)\"\'>')}"
        else:
            url = raw_input if "://" in raw_input else f"https://{raw_input}"

    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "").strip()
    if not domain or " " in domain:
        clean_path = re.sub(r"[^\w.-]", "", parsed.path.split("/")[0]).strip(".-")
        domain = clean_path if clean_path and "." in clean_path else "target"

    tm = get_task_manager()

    # Use task_id as group_id so fleet subtasks properly merge into this card
    task_id = uuid.uuid4().hex[:8]
    group_id = task_id

    task_id = tm.submit(
        tool_name="reverse_engineer",
        fn=_teardown_task_worker,
        params={"url": url, "domain": domain, "focus": parameters.get("focus", "full")},
        group_id=group_id,
        group_title=f"REA capture for {domain}",
    )

    logger.info("[reverse_engineer] Submitted native REA capture for %s (task_id: %s, group_id: %s)", domain, task_id, group_id)

    return f"Official REA engine is capturing {domain} via isolated browser session to Desktop workspace (Task ID: {task_id})."


TOOL["handler"] = reverse_engineer_action
