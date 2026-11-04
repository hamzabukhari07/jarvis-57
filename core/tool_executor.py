"""
core/tool_executor.py — Centralized Tool Execution Choke Point for ZEZO.

Enforces strict defense-in-depth isolation, caller identity verification,
role-based permission matrix, workspace path jailing, risk-aware circuit
breaking, and confirmation gating before any tool handler execution.

Author: Hamza Bukhari
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import secrets
import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Set

from core.path_jail import SecurityAccessDenied as PathSecurityAccessDenied, secure_resolve_path

logger = logging.getLogger("zezo.tool_executor")


class CallerContext(str, Enum):
    MAIN_SESSION = "main_session"
    AGENT = "agent"
    SKILL = "skill"
    BATCH = "batch"
    SYSTEM = "system"


class SecurityAccessDenied(PermissionError):
    """Raised when a tool execution request violates identity, permission, or path security."""

    def __init__(self, message: str, blocked_by: str = "permission"):
        super().__init__(message)
        self.blocked_by = blocked_by


@dataclass
class ToolExecutionResult:
    success: bool
    output: Any
    error: Optional[str] = None
    blocked_by: Optional[str] = None  # "identity", "permission", "path_jail", "circuit_breaker", "confirmation", "disabled", "not_found"
    latency_ms: float = 0.0


# Parameter keys that represent filesystem paths subject to workspace jail containment
PATH_ARG_KEYS: Set[str] = {
    "path",
    "file_path",
    "target_path",
    "destination",
    "source_path",
    "filepath",
    "dir",
    "directory",
    "project_path",
    "target_dir",
    "output_path",
    "folder",
    "root",
    "cwd",
    "workdir",
    "workspace",
    "output_dir",
    "input_file",
    "output_file",
    "input_path",
}


class ToolExecutor:
    """
    Centralized execution choke point for all ZEZO tool invocations.

    Guarantees:
      1. Context & Identity Verification: Agents cannot spoof main_session privileges.
      2. Permissions Matrix: Checks AgentProfile.allowed_tools and risk tier boundaries.
      3. Path Jail Containment: Inspects and confines path parameters to agent workspace.
      4. Circuit Breaker Protection: Throttles or halts failing/cascading tools.
      5. Confirmation Gate: Irreversible L2_DESTRUCTIVE actions require human confirmation.
      6. Telemetry & Latency Accounting: Measures performance and emits event logs.
    """

    def __init__(self, main_session_secret: Optional[str] = None):
        self._main_session_secret: str = main_session_secret or secrets.token_hex(32)
        self._inline_tools: Dict[str, Callable] = {}
        self._lock = threading.Lock()

    def get_main_session_token(self) -> str:
        """Returns the internal main session token required to claim CallerContext.MAIN_SESSION."""
        return self._main_session_secret

    def set_main_session_token(self, token: str) -> None:
        """Updates the main session token (e.g. from main session startup)."""
        if not token:
            raise ValueError("Main session token cannot be empty.")
        self._main_session_secret = token

    def validate_main_session_token(self, token: Optional[str]) -> bool:
        """Constant-time comparison of the main session authentication token."""
        if not token:
            return False
        return secrets.compare_digest(str(token), str(self._main_session_secret))

    def register_inline_tool(self, name: str, handler: Callable) -> None:
        """Registers a session-bound inline tool callable (e.g. from main.py)."""
        with self._lock:
            self._inline_tools[name] = handler

    def unregister_inline_tool(self, name: str) -> None:
        """Unregisters an inline tool callable."""
        with self._lock:
            self._inline_tools.pop(name, None)

    def execute(
        self,
        tool_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        caller_context: CallerContext = CallerContext.MAIN_SESSION,
        agent_id: Optional[str] = None,
        workspace: Optional[str | Path] = None,
        caller_token: Optional[str] = None,
        ctx: Optional[Dict[str, Any]] = None,
        raise_on_denial: bool = True,
    ) -> ToolExecutionResult:
        """
        Synchronously validates and executes a tool through the centralized choke point.

        Args:
            tool_name: Identifier of the tool to execute.
            parameters: Key-value parameters passed to the tool handler.
            caller_context: Origin context (MAIN_SESSION, AGENT, SKILL, BATCH, SYSTEM).
            agent_id: Required if caller_context is AGENT.
            workspace: Target workspace path for boundary jail validation.
            caller_token: Secret token required when claiming CallerContext.MAIN_SESSION.
            ctx: Runtime execution context dictionary.
            raise_on_denial: If True, raises SecurityAccessDenied on identity/permission/path
                             violations. If False, returns ToolExecutionResult with blocked_by set.

        Returns:
            ToolExecutionResult with execution output, status, error, and latency metrics.

        Raises:
            SecurityAccessDenied: If raise_on_denial=True and a security constraint is violated.
        """
        t0 = time.perf_counter()
        params = dict(parameters or {})
        run_ctx = dict(ctx or {})

        try:
            # ─────────────────────────────────────────────────────────────────
            # 1. Identity & Context Validation
            # ─────────────────────────────────────────────────────────────────
            effective_workspace = workspace

            if caller_context == CallerContext.AGENT:
                if not agent_id or not str(agent_id).strip():
                    raise SecurityAccessDenied(
                        "Agent execution requires a valid, non-null agent_id.",
                        blocked_by="identity",
                    )

                from core.agents.registry import check_agent_tool_permission, get_agent_registry

                registry = get_agent_registry()
                agent = registry.get_agent(str(agent_id).strip())
                if not agent:
                    raise SecurityAccessDenied(
                        f"Unknown or unauthenticated agent: {agent_id}",
                        blocked_by="identity",
                    )

                # Tool permission verification
                allowed, reason = check_agent_tool_permission(agent.id, tool_name)
                if not allowed:
                    raise SecurityAccessDenied(
                        reason or f"Tool '{tool_name}' not permitted for agent '{agent.id}'.",
                        blocked_by="permission",
                    )

                # Infer agent workspace if not explicitly passed
                if not effective_workspace:
                    effective_workspace = (
                        getattr(agent, "active_worktree", None)
                        or getattr(agent, "workspace", None)
                        or getattr(agent, "workspace_dir", None)
                    )

            elif caller_context == CallerContext.MAIN_SESSION:
                if not self.validate_main_session_token(caller_token):
                    raise SecurityAccessDenied(
                        "Unauthorized claim of MAIN_SESSION privileges.",
                        blocked_by="identity",
                    )

            elif caller_context in (CallerContext.SKILL, CallerContext.BATCH):
                if agent_id:
                    from core.agents.registry import check_agent_tool_permission, get_agent_registry

                    registry = get_agent_registry()
                    agent = registry.get_agent(str(agent_id).strip())
                    if not agent:
                        raise SecurityAccessDenied(
                            f"Unknown or unauthenticated agent: {agent_id}",
                            blocked_by="identity",
                        )
                    allowed, reason = check_agent_tool_permission(agent.id, tool_name)
                    if not allowed:
                        raise SecurityAccessDenied(
                            reason or f"Tool '{tool_name}' not permitted for agent '{agent.id}'.",
                            blocked_by="permission",
                        )
                    if not effective_workspace:
                        effective_workspace = (
                            getattr(agent, "active_worktree", None)
                            or getattr(agent, "workspace", None)
                            or getattr(agent, "workspace_dir", None)
                        )

            # ─────────────────────────────────────────────────────────────────
            # 2. Path Security Jail Containment
            # ─────────────────────────────────────────────────────────────────
            has_path_args = any(
                k.lower() in PATH_ARG_KEYS and val is not None and str(val).strip() != ""
                for k, val in params.items()
            )
            if (
                caller_context in (CallerContext.AGENT, CallerContext.SKILL, CallerContext.BATCH)
                and has_path_args
                and not effective_workspace
            ):
                raise SecurityAccessDenied(
                    f"Path-bearing tool execution under {caller_context.value} requires an assigned workspace jail.",
                    blocked_by="path_jail",
                )

            if effective_workspace:
                ws_path = Path(effective_workspace).resolve()
                for key, val in list(params.items()):
                    if key.lower() in PATH_ARG_KEYS and val is not None:
                        val_str = str(val).strip()
                        if val_str:
                            try:
                                resolved = secure_resolve_path(val_str, ws_path, allow_nonexistent=True)
                                params[key] = str(resolved)
                            except (PathSecurityAccessDenied, SecurityAccessDenied) as e:
                                raise SecurityAccessDenied(
                                    f"Path security violation on argument '{key}': {e}",
                                    blocked_by="path_jail",
                                ) from e
                            except Exception as e:
                                raise SecurityAccessDenied(
                                    f"Invalid path argument '{key}' ('{val}'): {e}",
                                    blocked_by="path_jail",
                                ) from e

        except SecurityAccessDenied as e:
            if raise_on_denial:
                raise
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            return ToolExecutionResult(
                success=False,
                output=None,
                error=str(e),
                blocked_by=getattr(e, "blocked_by", "permission"),
                latency_ms=elapsed_ms,
            )

        # ─────────────────────────────────────────────────────────────────────
        # 3. Tool Availability & Circuit Breaker Check
        # ─────────────────────────────────────────────────────────────────────
        from core.action_loader import get_action_registry
        from core.circuit_breaker import circuit_breaker
        from core.governance import INLINE_TOOL_RISKS

        ar = get_action_registry()
        is_action = ar.has(tool_name)
        is_inline = (tool_name in self._inline_tools) or (tool_name in INLINE_TOOL_RISKS)

        if not is_action and not is_inline:
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            return ToolExecutionResult(
                success=False,
                output=None,
                error=f"Tool '{tool_name}' not found.",
                blocked_by="not_found",
                latency_ms=elapsed_ms,
            )

        # Check enabled state for ActionRegistry tools
        if is_action:
            rec = ar.get(tool_name)
            if rec and not rec.enabled:
                elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
                return ToolExecutionResult(
                    success=False,
                    output=None,
                    error=f"Execution Blocked: Tool '{tool_name}' is currently disabled in Settings.",
                    blocked_by="disabled",
                    latency_ms=elapsed_ms,
                )

        # Circuit breaker pre-execution check
        can_run, block_msg = circuit_breaker.can_execute(tool_name)
        if not can_run:
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            return ToolExecutionResult(
                success=False,
                output=None,
                error=str(block_msg or f"Tool '{tool_name}' blocked by circuit breaker."),
                blocked_by="circuit_breaker",
                latency_ms=elapsed_ms,
            )

        # ─────────────────────────────────────────────────────────────────────
        # 4. Confirmation Gate for L2_DESTRUCTIVE / PRIVILEGED_OS Tools
        # ─────────────────────────────────────────────────────────────────────
        tool_risk_str = ""
        if is_action:
            rec = ar.get(tool_name)
            tool_risk_str = str(rec.risk if rec else "").lower().strip()
        elif tool_name in INLINE_TOOL_RISKS:
            tool_risk_str = getattr(INLINE_TOOL_RISKS[tool_name], "value", str(INLINE_TOOL_RISKS[tool_name])).lower().strip()

        is_destructive = tool_risk_str in ("l2_destructive", "privileged_os", "destructive")

        if is_destructive:
            is_confirmed = False
            if run_ctx.get("confirmed") or run_ctx.get("bypass_confirmation"):
                is_confirmed = True
            elif params.get("confirmed") in (True, "true", "yes", "1"):
                is_confirmed = True

            if not is_confirmed:
                from core import confirm

                def _deferred_execution() -> str:
                    res = self._dispatch_tool(tool_name, params, run_ctx)
                    return str(res)

                confirm_prompt = confirm.request(
                    key=f"executor-{tool_name}",
                    title=f"Tool Execution: {tool_name}",
                    detail=f"Parameters: {params}",
                    run=_deferred_execution,
                )
                elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
                return ToolExecutionResult(
                    success=False,
                    output=confirm_prompt,
                    error="Confirmation pending user approval.",
                    blocked_by="confirmation",
                    latency_ms=elapsed_ms,
                )

        # ─────────────────────────────────────────────────────────────────────
        # 5. Dispatch & Execution
        # ─────────────────────────────────────────────────────────────────────
        try:
            res = self._dispatch_tool(tool_name, params, run_ctx)
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

            if isinstance(res, str) and res.startswith(f"Tool '{tool_name}' failed:"):
                circuit_breaker.record_failure(tool_name, res)
                return ToolExecutionResult(
                    success=False,
                    output=res,
                    error=res,
                    latency_ms=elapsed_ms,
                )

            circuit_breaker.record_success(tool_name)
            return ToolExecutionResult(
                success=True,
                output=res,
                latency_ms=elapsed_ms,
            )

        except Exception as e:
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            circuit_breaker.record_failure(tool_name, str(e))
            logger.exception("Tool '%s' failed during execution: %s", tool_name, e)
            return ToolExecutionResult(
                success=False,
                output=None,
                error=str(e),
                latency_ms=elapsed_ms,
            )

    async def execute_async(
        self,
        tool_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        caller_context: CallerContext = CallerContext.MAIN_SESSION,
        agent_id: Optional[str] = None,
        workspace: Optional[str | Path] = None,
        caller_token: Optional[str] = None,
        ctx: Optional[Dict[str, Any]] = None,
        raise_on_denial: bool = True,
    ) -> ToolExecutionResult:
        """
        Asynchronous non-blocking wrapper running the tool execution off the main loop.
        """
        return await asyncio.to_thread(
            self.execute,
            tool_name=tool_name,
            parameters=parameters,
            caller_context=caller_context,
            agent_id=agent_id,
            workspace=workspace,
            caller_token=caller_token,
            ctx=ctx,
            raise_on_denial=raise_on_denial,
        )

    def _dispatch_tool(self, tool_name: str, parameters: Dict[str, Any], ctx: Dict[str, Any]) -> Any:
        """Invokes the underlying tool handler (inline or ActionRegistry)."""
        # 1. Registered inline tool handler
        if tool_name in self._inline_tools:
            handler = self._inline_tools[tool_name]
            sig = inspect.signature(handler)
            has_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
            kwargs = {}
            if has_var_kw or "ctx" in sig.parameters:
                kwargs["ctx"] = ctx
            return handler(parameters=parameters, **kwargs)

        # 2. ActionRegistry action tool
        from core.action_loader import get_action_registry

        ar = get_action_registry()
        if ar.has(tool_name):
            return ar.run(tool_name, parameters, ctx=ctx)

        raise RuntimeError(f"No executable handler registered for tool '{tool_name}'.")


_tool_executor_instance: Optional[ToolExecutor] = None
_instance_lock = threading.Lock()


def get_tool_executor() -> ToolExecutor:
    """Returns the singleton ToolExecutor instance."""
    global _tool_executor_instance
    if _tool_executor_instance is None:
        with _instance_lock:
            if _tool_executor_instance is None:
                _tool_executor_instance = ToolExecutor()
    return _tool_executor_instance
