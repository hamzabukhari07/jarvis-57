"""
actions/run_tool_batch.py — Sequential Multi-Tool Pipeline Runner.

Executes a sequence of sub-tool calls in an atomic batch with variable substitution
(${steps.0.result}), governance risk checks, and a hard step limit cap (<= 10).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _substitute_variables(param_val: Any, step_results: List[Any]) -> Any:
    """Recursively substitute `${steps.N.result}` or `${steps.N}` tokens."""
    if isinstance(param_val, str):
        pattern = re.compile(r"\$\{steps\.(\d+)(?:\.result)?\}")

        def _replace_match(m):
            idx = int(m.group(1))
            if 0 <= idx < len(step_results):
                res = step_results[idx]
                return str(res)
            return m.group(0)

        return pattern.sub(_replace_match, param_val)
    elif isinstance(param_val, dict):
        return {k: _substitute_variables(v, step_results) for k, v in param_val.items()}
    elif isinstance(param_val, list):
        return [_substitute_variables(x, step_results) for x in param_val]
    return param_val


def run_tool_batch(parameters: Dict[str, Any], **kwargs: Any) -> str:
    """
    Execute a sequential batch of tool calls.
    parameters = {
        "steps": [
            {"tool": "web_search", "parameters": {"query": "python 3.12 release notes"}},
            {"tool": "code_helper", "parameters": {"instruction": "Summarize ${steps.0.result}"}}
        ],
        "stop_on_error": True
    }
    """
    steps = parameters.get("steps") or []
    stop_on_error = bool(parameters.get("stop_on_error", True))

    if not isinstance(steps, list):
        return "Error: 'steps' parameter must be a list of step objects."

    if not steps:
        return "Error: No steps provided in batch."

    if len(steps) > 10:
        return f"Error: Tool batch exceeds maximum allowed limit of 10 steps (got {len(steps)})."

    from core.action_loader import get_action_registry
    registry = get_action_registry()

    results: List[Any] = []
    summary_lines: List[str] = [f"Executed batch of {len(steps)} step(s):"]

    for idx, step in enumerate(steps):
        if not isinstance(step, dict):
            err_msg = f"Step #{idx} is invalid (expected object)."
            summary_lines.append(f"• Step #{idx}: [FAILED] {err_msg}")
            if stop_on_error:
                return "\n".join(summary_lines)
            results.append(err_msg)
            continue

        tool_name = str(step.get("tool") or "").strip()
        raw_params = step.get("parameters") or {}

        if not tool_name:
            err_msg = f"Step #{idx} missing 'tool' name."
            summary_lines.append(f"• Step #{idx}: [FAILED] {err_msg}")
            if stop_on_error:
                return "\n".join(summary_lines)
            results.append(err_msg)
            continue

        # Prevent recursive batch execution to stop nested batch explosion
        if tool_name == "run_tool_batch":
            err_msg = f"Step #{idx}: Nested 'run_tool_batch' is prohibited."
            summary_lines.append(f"• Step #{idx}: [DENIED] {err_msg}")
            if stop_on_error:
                return "\n".join(summary_lines)
            results.append(err_msg)
            continue

        resolved_params = _substitute_variables(raw_params, results)
        
        try:
            step_output = registry.run(tool_name, resolved_params, ctx=kwargs)
            results.append(step_output)
            
            # Check if output indicates an error
            is_fail = isinstance(step_output, str) and (
                step_output.startswith(f"Tool '{tool_name}' failed:")
                or step_output.startswith("Aborted:")
                or step_output.startswith("CircuitBreaker:")
            )
            
            status_tag = "[FAILED]" if is_fail else "[OK]"
            preview = str(step_output)[:80].replace("\n", " ")
            summary_lines.append(f"• Step #{idx} ({tool_name}): {status_tag} {preview}")
            
            if is_fail and stop_on_error:
                summary_lines.append(f"Batch halted at step #{idx} due to error.")
                break
        except Exception as e:
            err_msg = f"Exception executing {tool_name}: {e}"
            results.append(err_msg)
            summary_lines.append(f"• Step #{idx} ({tool_name}): [ERROR] {err_msg}")
            if stop_on_error:
                summary_lines.append(f"Batch halted at step #{idx} due to exception.")
                break

    return "\n".join(summary_lines)


TOOL = {
    "name": "run_tool_batch",
    "description": (
        "Execute an ordered pipeline of up to 10 tool calls sequentially with variable substitution. "
        "Allows passing outputs from prior steps using '${steps.0.result}' inside subsequent step parameters. "
        "Useful for multi-step data gathering and processing workflows."
    ),
    "risk": "local_mutation",
    "enabled": True,
    "behavior": "BLOCKING",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "steps": {
                "type": "ARRAY",
                "description": "List of step objects: [{'tool': 'tool_name', 'parameters': {...}}, ...]",
            },
            "stop_on_error": {
                "type": "BOOLEAN",
                "description": "If true, halts batch execution upon first step failure (default True).",
            },
        },
        "required": ["steps"],
    },
    "handler": run_tool_batch,
}

handler = run_tool_batch
