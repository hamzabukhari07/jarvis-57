"""
Action discovery, validation, and dispatch — the built-in twin of plugin_loader.

Every actions/*.py that exposes a module-level ``TOOL`` dict is auto-discovered
here, exactly like a drop-in plugin, so main.py never has to hardcode a tool
declaration or a dispatch branch for it. Adding a new bundled action is then the
same one-file operation as writing a plugin: define ``TOOL`` and a handler.

``TOOL`` shape (see actions/open_app.py for a live example):

    TOOL = {
        "name":        "open_app",              # unique, ^[a-zA-Z_][a-zA-Z0-9_]{0,63}$
        "description":  "...",                   # what Gemini reads to route the call
        "parameters":  {"type": "OBJECT", ...}, # Gemini function-declaration schema
        "handler":      open_app,                # the callable to run
    }

The handler is invoked through signature introspection: it receives ``parameters``
plus whichever of ``player`` / ``speak`` / ``response`` / ``session_memory`` it
actually declares — so existing action signatures work unchanged.

Discovery runs once at startup; import errors, validation errors, and name
collisions are logged and the offending file is skipped — they NEVER raise out
of discover_actions() and never abort the scan of the remaining files.
"""
from __future__ import annotations

import importlib.util
import inspect
import re
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import time
import uuid

from collections import deque

_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,63}$")
_DEFAULT_PARAMS = {"type": "OBJECT", "properties": {}}
_CTX_KEYS = ("player", "speak", "response", "session_memory", "context")


# A tool may declare that the model should NOT be held up waiting for it.
# `behavior` goes to the API with the declaration; `scheduling` decides when the
# eventual result is allowed back into the conversation:
#   WHEN_IDLE  — wait for a gap in the speech (the sane default)
#   SILENT     — record it, do not prompt a reply (the tool already announced)
#   INTERRUPT  — cut in immediately (only when the answer cannot wait)
_BEHAVIORS = ("BLOCKING", "NON_BLOCKING")
_SCHEDULING = ("WHEN_IDLE", "SILENT", "INTERRUPT")


def _opt_upper(value, allowed: tuple[str, ...]) -> Optional[str]:
    v = str(value or "").strip().upper()
    return v if v in allowed else None


@dataclass
class ActionRecord:
    name: str
    description: str = ""
    parameters: dict = field(default_factory=lambda: dict(_DEFAULT_PARAMS))
    handler: Optional[Callable] = None
    file: str = ""
    valid: bool = False
    error: str = ""
    behavior: Optional[str] = None     # None = the API's default (blocking)
    scheduling: Optional[str] = None   # None = the API's default (WHEN_IDLE)
    risk: str = "local_mutation"       # Default fallback risk tier
    enabled: bool = True


class ActionRegistry:
    def __init__(self, actions: dict[str, ActionRecord], logger: Callable[[str], None]):
        self._actions = actions          # name -> ActionRecord, VALID entries only
        self._all_records: list[ActionRecord] = []
        self._logger = logger
        self._key_history: deque = deque(maxlen=20)

    # -- called by main.py at LiveConnectConfig build time & agent scoping --
    def get_tool_declarations(self, agent_id: Optional[str] = None, mode: Optional[str] = None) -> list[dict]:
        """
        Returns Gemini function-declarations, optionally filtered by agent allowed_tools or execution mode.
        If agent_id is provided, checks agent's allowed_tools from FleetManager.
        """
        allowed_set: Optional[set[str]] = None
        if agent_id:
            try:
                from core.fleet_manager import fleet_manager
                agent = fleet_manager.get_agent(agent_id)
                if agent and agent.allowed_tools:
                    allowed_set = set(agent.allowed_tools)
            except Exception as e:
                self._logger(f"[ActionRegistry] Failed resolving agent tool permissions for {agent_id}: {e}")

        # Mode-based filtering heuristics (e.g. 'coding', 'research', 'safe')
        mode_str = (mode or "").lower().strip()
        mode_denied: set[str] = set()
        if mode_str == "coding":
            mode_denied = {"weather_report", "flight_finder", "youtube_video", "game_updater"}
        elif mode_str == "safe" or mode_str == "readonly":
            mode_denied = {rec.name for rec in self._actions.values() if rec.risk in ("external_mutation", "destructive", "privileged_os")}

        out = []
        for rec in self._actions.values():
            if not rec.enabled:
                continue
            if allowed_set is not None and rec.name not in allowed_set:
                continue
            if rec.name in mode_denied:
                continue
            decl = {"name": rec.name, "description": rec.description,
                    "parameters": rec.parameters}
            if rec.behavior:
                decl["behavior"] = rec.behavior
            out.append(decl)
        return out

    def filter_tools(self, agent_id: Optional[str] = None, mode: Optional[str] = None) -> dict[str, Any]:
        """Diagnostic inspection of allowed and filtered tools with reasons."""
        allowed = []
        filtered = []

        allowed_set: Optional[set[str]] = None
        agent_name = None
        if agent_id:
            try:
                from core.fleet_manager import fleet_manager
                agent = fleet_manager.get_agent(agent_id)
                if agent:
                    agent_name = agent.name
                    if agent.allowed_tools:
                        allowed_set = set(agent.allowed_tools)
            except Exception as e:
                self._logger(f"[ActionRegistry] Error fetching agent {agent_id}: {e}")

        mode_str = (mode or "").lower().strip()
        mode_denied: set[str] = set()
        if mode_str == "coding":
            mode_denied = {"weather_report", "flight_finder", "youtube_video", "game_updater"}
        elif mode_str in ("safe", "readonly"):
            mode_denied = {rec.name for rec in self._actions.values() if rec.risk in ("external_mutation", "destructive", "privileged_os")}

        for rec in self._actions.values():
            if not rec.enabled:
                filtered.append({"tool": rec.name, "risk": rec.risk, "reason": "tool_disabled"})
                continue
            if allowed_set is not None and rec.name not in allowed_set:
                filtered.append({"tool": rec.name, "risk": rec.risk, "reason": f"not_in_agent_permissions ({agent_name or agent_id})"})
                continue
            if rec.name in mode_denied:
                filtered.append({"tool": rec.name, "risk": rec.risk, "reason": f"denied_by_mode ({mode_str})"})
                continue
            allowed.append({"tool": rec.name, "risk": rec.risk, "behavior": rec.behavior})

        return {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "mode": mode,
            "allowed_count": len(allowed),
            "filtered_count": len(filtered),
            "allowed_tools": allowed,
            "filtered_tools": filtered,
        }

    def has(self, name: str) -> bool:
        return name in self._actions

    def get(self, name: str) -> Optional[ActionRecord]:
        return self._actions.get(name)

    def get_risk(self, name: str) -> Optional[str]:
        rec = self._actions.get(name)
        return rec.risk if rec else None

    def scheduling(self, name: str) -> Optional[str]:
        """How this action's result should re-enter the conversation, if it said."""
        rec = self._actions.get(name)
        return rec.scheduling if rec else None

    def names(self) -> set[str]:
        return set(self._actions.keys())

    # -- called by main.py from _execute_tool --
    def run(self, name: str, parameters: dict, ctx: dict | None = None) -> str:
        rec = self._actions.get(name)
        if rec is None or not rec.valid:
            return f"Action '{name}' is not available."

        # Hotkey Anti-Loop Circuit Breaker (stops repetitive keystroke spam)
        now = time.monotonic()
        p = parameters or {}
        act = str(p.get("action", "")).lower().strip()
        key_target = str(p.get("keys", "") or p.get("key", "") or p.get("hotkey", "") or p.get("text", "")).lower().strip()

        is_key_action = (
            name == "computer_control" and (
                act in ("hotkey", "shortcut", "press_hotkey", "send_hotkey", "press", "key", "press_key", "keypress", "key_press", "send_key", "enter", "escape", "space", "backspace", "tab", "delete")
                or key_target != ""
            )
        )
        if is_key_action:
            sig = f"{act}:{key_target}"
            while self._key_history and (now - self._key_history[0][0]) > 10.0:
                self._key_history.popleft()
            recent_count = sum(1 for ts, s in self._key_history if s == sig)
            if recent_count >= 4:
                msg = f"Aborted: Repetitive hotkey loop detected (>4 calls in 10s for '{sig}'). Use spatial coordinate clicks or inspect the UI state."
                print(f"[CircuitBreaker] ⚠️ {msg}")
                return msg
            self._key_history.append((now, sig))

        from core.circuit_breaker import circuit_breaker
        can_run, block_msg = circuit_breaker.can_execute(name)
        if not can_run:
            print(f"[CircuitBreaker] [WARN] {block_msg}")
            return str(block_msg)

        # Loop Gates & Doom-Loop Steering Evaluation
        from core.loop_gates import GateDecision, loop_gates
        sess_id = (ctx or {}).get("session_id") or "global"
        gate_res = loop_gates.evaluate(name, parameters, session_id=sess_id)
        if gate_res.decision == GateDecision.BLOCK:
            msg = f"LoopGate Blocked: {gate_res.reason}"
            print(f"[LoopGates] 🛑 {msg}")
            return msg
        elif gate_res.decision == GateDecision.INTERRUPT:
            print(f"[LoopGates] ⚠️ {gate_res.reason}")
            # Steer the agent with corrective feedback instead of executing identical failed loop
            return gate_res.coaching_feedback or gate_res.reason or "Loop interrupted."

        from core.task_manager import ToolExecutionContext
        from core.log_bus import emit_tool_micro_event

        task_id = uuid.uuid4().hex[:8]
        exec_ctx = ToolExecutionContext(task_id=task_id, tool_name=name, timeout_seconds=30.0)
        run_ctx = dict(ctx or {})
        run_ctx["context"] = exec_ctx

        emit_tool_micro_event("started", name, {"task_id": task_id, "params": list((parameters or {}).keys())})
        t0 = time.perf_counter()

        try:
            res = _call_handler(rec.handler, parameters, run_ctx) or "Done."
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
            if isinstance(res, str) and res.startswith(f"Tool '{name}' failed:"):
                circuit_breaker.record_failure(name, res)
            else:
                circuit_breaker.record_success(name)
            emit_tool_micro_event("completed", name, {"task_id": task_id, "latency_ms": f"{elapsed_ms}ms"})
            return res
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
            circuit_breaker.record_failure(name, str(e))
            emit_tool_micro_event("failed", name, {"task_id": task_id, "error": str(e), "latency_ms": f"{elapsed_ms}ms"}, level="ERROR")
            self._logger(f"Action '{name}' crashed during run(): {e}")
            traceback.print_exc()
            return f"Tool '{name}' failed: {e}"


def _call_handler(fn: Callable, parameters: dict, ctx: dict) -> str:
    """Invoke the handler passing only the context kwargs it actually declares
    (or all of them if it has **kwargs), so each action's existing signature
    works unchanged."""
    sig = inspect.signature(fn)
    has_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
    kwargs = {}
    for key in _CTX_KEYS:
        if has_var_kw or key in sig.parameters:
            kwargs[key] = ctx.get(key)
    return fn(parameters=parameters, **kwargs)


def _validate(module, filename: str) -> ActionRecord:
    """Returns an ActionRecord; .valid=False + .error set on any problem. Never raises."""
    tool = getattr(module, "TOOL", None)
    if not isinstance(tool, dict):
        return ActionRecord(name=Path(filename).stem, file=filename,
                            error="No module-level TOOL dict (not a discoverable action).")

    name = tool.get("name")
    if not isinstance(name, str) or not _NAME_RE.match(name):
        return ActionRecord(name=str(name or Path(filename).stem), file=filename,
                            error="TOOL['name'] missing or not a valid identifier.")

    description = tool.get("description")
    if not isinstance(description, str) or not description.strip():
        return ActionRecord(name=name, file=filename,
                            error="TOOL['description'] missing or empty.")

    parameters = tool.get("parameters", _DEFAULT_PARAMS)
    if not isinstance(parameters, dict) or parameters.get("type") != "OBJECT":
        return ActionRecord(name=name, file=filename,
                            error="TOOL['parameters'] must be a dict with \"type\": \"OBJECT\".")

    handler = tool.get("handler")
    if not callable(handler):
        return ActionRecord(name=name, file=filename,
                            error="TOOL['handler'] missing or not callable.")

    if "risk" not in tool:
        return ActionRecord(name=name, file=filename,
                            error="TOOL['risk'] missing. Every action must declare a valid ToolRisk tier.")

    raw_risk = str(tool.get("risk", "")).lower().strip()
    valid_risks = {
        "read_only": "read_only",
        "local_mutation": "local_mutation",
        "external_mutation": "external_mutation",
        "code_execution": "code_execution",
        "privileged_os": "privileged_os",
    }
    if raw_risk not in valid_risks:
        return ActionRecord(name=name, file=filename,
                            error=f"TOOL['risk'] '{raw_risk}' is invalid. Must be one of: {list(valid_risks.keys())}.")

    norm_risk = valid_risks[raw_risk]
    enabled = bool(tool.get("enabled", True))

    return ActionRecord(name=name, description=description.strip(), parameters=parameters,
                        handler=handler, file=filename, valid=True, error="",
                        behavior=_opt_upper(tool.get("behavior"), _BEHAVIORS),
                        scheduling=_opt_upper(tool.get("scheduling"), _SCHEDULING),
                        risk=norm_risk, enabled=enabled)


def discover_actions(actions_dir: Path, reserved_names: set[str] | None = None,
                     logger: Callable[[str], None] = print) -> ActionRegistry:
    """
    Scans actions_dir for *.py files (skips files starting with '_'). A file is
    only treated as an action if it exposes a module-level TOOL dict; files
    without one (shared helpers, capture-only modules) are silently ignored.
    Import/validation errors and name collisions are logged and the file is
    skipped — they NEVER raise out of this function.
    """
    reserved = reserved_names or set()
    actions_dir.mkdir(parents=True, exist_ok=True)
    valid: dict[str, ActionRecord] = {}
    all_records: list[ActionRecord] = []

    files = sorted(actions_dir.glob("*.py"), key=lambda p: p.name)  # deterministic order
    for path in files:
        if path.name.startswith("_"):
            continue
        try:
            module_name = f"actions.{path.stem}"
            # Reuse the already-imported module when present so handlers are the
            # same objects the rest of the app holds.
            module = sys.modules.get(module_name)
            if module is None:
                spec = importlib.util.spec_from_file_location(module_name, path)
                if spec is None or spec.loader is None:
                    raise ImportError("could not build import spec")
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                try:
                    spec.loader.exec_module(module)
                except Exception:
                    sys.modules.pop(module_name, None)
                    raise

            if getattr(module, "TOOL", None) is None:
                continue   # not an action file — a helper/capture-only module

            rec = _validate(module, path.name)

            if rec.valid and rec.name in reserved:
                rec = ActionRecord(name=rec.name, file=path.name,
                                   error=f"Name '{rec.name}' collides with a reserved core tool — rejected.")
            elif rec.valid and rec.name in valid:
                other = valid[rec.name].file
                rec = ActionRecord(name=rec.name, file=path.name,
                                   error=f"Name '{rec.name}' already used by action '{other}' — rejected.")

        except Exception as e:
            rec = ActionRecord(name=path.stem, file=path.name,
                               error=f"Failed to load: {e}")
            traceback.print_exc()

        all_records.append(rec)
        if rec.valid:
            valid[rec.name] = rec
            logger(f"Action loaded: {rec.name} ({path.name})")
        else:
            logger(f"Action rejected: {path.name} — {rec.error}")

    global _GLOBAL_REGISTRY
    registry = ActionRegistry(valid, logger)
    registry._all_records = all_records
    _GLOBAL_REGISTRY = registry
    logger(f"Action discovery complete: {len(valid)} active.")
    return registry


_GLOBAL_REGISTRY: Optional[ActionRegistry] = None


def get_action_registry() -> ActionRegistry:
    """Returns the globally discovered action registry, auto-discovering if not yet initialized."""
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        actions_dir = Path(__file__).resolve().parent.parent / "actions"
        _GLOBAL_REGISTRY = discover_actions(actions_dir, logger=lambda m: None)
    return _GLOBAL_REGISTRY
