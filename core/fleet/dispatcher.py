"""
core/fleet/dispatcher.py — Task Dispatcher & Worktree Execution Engine for ZEZO Fleet.

Creator & Lead Architect: Hamza Bukhari
Project: ZEZO (Autonomous Desktop AI Operating System v2)

Handles autonomous task dispatching, risk-tier enforcement, git worktree isolation,
declarative skill injection, circuit breaker verification, background TaskManager
worker execution, and rate-limited WebSocket event broadcasting.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from core.fleet_manager import FleetAgent, FleetManager

logger = logging.getLogger("zezo.fleet.dispatcher")

VALID_RISK_TIERS: set[str] = {"L0_READ_ONLY", "L1_MUTATION", "L2_DESTRUCTIVE"}


def _setup_worktree(worktree_name: str) -> Any:
    """Set up git worktree isolation sandbox."""
    try:
        from core.git_sandbox import git_sandbox
        if hasattr(git_sandbox, "setup_worktree"):
            return git_sandbox.setup_worktree(worktree_name)
        elif hasattr(git_sandbox, "create_worktree"):
            return git_sandbox.create_worktree(worktree_name)
    except Exception as e:
        logger.warning("[FleetDispatcher] Failed to setup worktree %s: %s", worktree_name, e)
    return None


def _teardown_worktree(worktree_name: str) -> Any:
    """Safely tear down git worktree sandbox."""
    try:
        from core.git_sandbox import git_sandbox
        if hasattr(git_sandbox, "teardown_worktree"):
            return git_sandbox.teardown_worktree(worktree_name)
        elif hasattr(git_sandbox, "safe_teardown"):
            return git_sandbox.safe_teardown(worktree_name)
    except Exception as e:
        logger.warning("[FleetDispatcher] Failed to teardown worktree %s: %s", worktree_name, e)
    return None


class FleetDispatcher:
    """
    Autonomous task dispatcher for the ZEZO agent fleet.
    Coordinates risk tiers, circuit breaker checks, git worktree isolation,
    declarative skill injection, and execution via TaskManager.
    """

    def __init__(self, registry: Any = None) -> None:
        self.registry = registry
        self._lock = threading.Lock()

    def _get_agent(self, agent_id: str) -> Optional[Any]:
        """Resolve agent from registry or local registry agents map."""
        if not self.registry:
            return None
        agent = None
        if hasattr(self.registry, "get_agent"):
            agent = self.registry.get_agent(agent_id)
        if not agent and hasattr(self.registry, "resolve_agent_by_mention_or_capability"):
            agent = self.registry.resolve_agent_by_mention_or_capability(agent_id)
        if not agent and hasattr(self.registry, "agents") and isinstance(self.registry.agents, dict):
            agent = self.registry.agents.get(agent_id)
        return agent

    def _get_agent_active_task_count(self, agent_id: str) -> int:
        """Get active task count for an agent."""
        if hasattr(self.registry, "get_agent_active_task_count"):
            return int(self.registry.get_agent_active_task_count(agent_id))
        return 0

    def _broadcast_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Thread-safe broadcast of fleet and task events to WebSocket UI and log bus."""
        if hasattr(self.registry, "_broadcast_event"):
            try:
                self.registry._broadcast_event(event_type, data)
                return
            except Exception as e:
                logger.debug("[FleetDispatcher] Registry broadcast failed: %s", e)

        try:
            from core.ui_server import get_ui_server
            get_ui_server().broadcast(event_type, data)
        except Exception as e:
            logger.debug("[FleetDispatcher] UI broadcast skipped: %s", e)

        try:
            from core.log_bus import emit_tool_micro_event
            emit_tool_micro_event(event_type, "fleet_dispatcher", data)
        except Exception:
            pass

    def _get_fleet_deck_state(self) -> List[Dict[str, Any]]:
        """Retrieve current fleet deck state for broadcasts."""
        if hasattr(self.registry, "get_fleet_deck_state"):
            return self.registry.get_fleet_deck_state()
        agents = getattr(self.registry, "agents", {})
        if isinstance(agents, dict):
            return [
                a.to_dict() if hasattr(a, "to_dict") else vars(a)
                for a in agents.values()
            ]
        return []

    def complete_task(
        self,
        agent_id: str,
        task_id: str,
        merge_changes: bool = False,
        worktree_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Mark agent task complete and teardown worktree."""
        if hasattr(self.registry, "complete_task"):
            return self.registry.complete_task(
                agent_id,
                task_id,
                merge_changes=merge_changes,
                worktree_id=worktree_id,
            )

        agent = self._get_agent(agent_id)
        if not agent:
            return {"success": False, "error": f"Agent '{agent_id}' not found."}

        wt_id = worktree_id or getattr(agent, "active_worktree", None) or f"{agent.id.lower()}_{task_id}"
        merge_msg = "No worktree to merge."
        if merge_changes and wt_id:
            try:
                from core.git_sandbox import git_sandbox
                if hasattr(git_sandbox, "merge_worktree"):
                    _, merge_msg = git_sandbox.merge_worktree(wt_id)
            except Exception as e:
                merge_msg = f"Worktree merge error: {e}"

        lock = getattr(self.registry, "_lock", None) or self._lock
        with lock:
            agent.status = "idle"
            agent.current_task_id = None
            agent.current_task_title = None
            agent.active_worktree = None
            if merge_changes:
                agent.completed_tasks = getattr(agent, "completed_tasks", 0) + 1
            agent.recent_logs.append(f"[COMPLETED] Task {task_id[:8]} - {merge_msg[:40]}")
            if len(agent.recent_logs) > 30:
                agent.recent_logs = agent.recent_logs[-30:]

        return {"success": True, "agent_id": agent.id, "merge": merge_msg}

    def dispatch_task(
        self,
        agent_id: str,
        prompt: str,
        path: Optional[str] = None,
        sync: bool = False,
        model: Optional[str] = None,
        session_memory: Optional[Dict[str, Any]] = None,
        parent_task_id: Optional[str] = None,
        task_id: Optional[str] = None,
        candidate_info: Optional[str] = None,
        design_spec: Optional[str] = None,
        project_type: Optional[str] = None,
        skip_git: bool = False,
        model_override: Optional[str] = None,
        is_subtask: bool = False,
        group_id: Optional[str] = None,
        scope_type: Optional[str] = None,
        entity_content: Optional[str] = None,
        tech_stack: Optional[str] = None,
        color_theme: Optional[str] = None,
        key_sections: Optional[str] = None,
        confirmed: bool = False,
        **extra_kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Launch an autonomous task executed by this agent's designated tool.
        
        Implements:
          - Risk tier verification (L0_READ_ONLY, L1_MUTATION, L2_DESTRUCTIVE)
          - Circuit breaker execution authorization
          - Git worktree sandboxing and isolation
          - Declarative skill injection (agent.allowed_skills)
          - Background worker thread execution via TaskManager
          - Rate-limited WebSocket fleet_updated event broadcasting (>= 1.0s or prog >= 100)
          - Complete failure / cancellation / completion lifecycle hooks
        """
        effective_subtask = is_subtask or bool(parent_task_id)

        # Check if orchestrator agent should auto-decompose multi-faceted full-stack tasks
        target_pre = self._get_agent(agent_id)
        is_orchestrator = target_pre and (
            getattr(target_pre, "is_core", False)
            or any(cap in (getattr(target_pre, "capabilities", []) or []) for cap in ("task_decomposition", "fleet_orchestration"))
            or any(w in (getattr(target_pre, "role", "") or "").lower() for w in ("orchestrator", "architect", "manager"))
        )
        if not effective_subtask and is_orchestrator and any(
            w in prompt.lower() for w in ("full-stack", "fullstack", "entire app", "both frontend and backend")
        ):
            if hasattr(self.registry, "decompose_and_dispatch"):
                return self.registry.decompose_and_dispatch(prompt, path)

        agent = self._get_agent(agent_id)
        if not agent:
            agents_dict = getattr(self.registry, "agents", {})
            registered_names: List[str] = []
            if isinstance(agents_dict, dict):
                registered_names = [f"{getattr(a, 'name', a)} ({getattr(a, 'id', a)})" for a in agents_dict.values()]
            return {
                "success": False,
                "error": f"Agent '{agent_id}' is not in the active fleet. Registered agents: {', '.join(registered_names)}",
            }

        # Dynamic Overflow Load Balancing: If agent is at capacity (>= 3 active tasks), auto-route to another active specialist
        if self._get_agent_active_task_count(agent.id) >= 3:
            agents_dict = getattr(self.registry, "agents", {})
            if isinstance(agents_dict, dict):
                agent_skills = set(getattr(agent, "allowed_skills", []) or [])
                agent_caps = set(getattr(agent, "capabilities", []) or [])
                for alt_agent in agents_dict.values():
                    if alt_agent.id != agent.id and self._get_agent_active_task_count(alt_agent.id) < 3:
                        if (agent_skills and set(alt_agent.allowed_skills or []) & agent_skills) or (
                            agent_caps and set(alt_agent.capabilities or []) & agent_caps
                        ) or (getattr(agent, "default_tool", None) and alt_agent.default_tool == agent.default_tool):
                            logger.info("[FleetDispatcher] Agent %s at capacity (>=3 tasks). Auto-routing to %s.", agent.name, alt_agent.name)
                            agent = alt_agent
                            break

        # Capability check via Circuit Breaker
        from core.circuit_breaker import circuit_breaker
        check_tool = getattr(agent, "default_tool", None)
        if not check_tool and getattr(agent, "engine", None):
            check_tool = f"{agent.engine}_run"

        if check_tool:
            can_run, block_reason = circuit_breaker.can_execute(check_tool)
            if not can_run:
                return {
                    "success": False,
                    "error": f"Circuit breaker tripped for {check_tool}: {block_reason}",
                }

        # Validate Risk Tier taxonomy: L0_READ_ONLY, L1_MUTATION, L2_DESTRUCTIVE
        risk_tier = (getattr(agent, "risk_tier", "L0_READ_ONLY") or "L0_READ_ONLY").upper().strip()
        if risk_tier not in VALID_RISK_TIERS:
            risk_tier = "L1_MUTATION" if getattr(agent, "default_tool", "") in ("kilo_run", "opencode_run", "antigravity_run") else "L0_READ_ONLY"

        import uuid
        dispatch_task_id = task_id or uuid.uuid4().hex[:8]
        worktree_name = f"{agent.id.lower()}_{dispatch_task_id}"
        worktree_path: Optional[str] = None

        # Worktree sandboxing for destructive actions (L2_DESTRUCTIVE or engine runners)
        if not skip_git and (risk_tier == "L2_DESTRUCTIVE" or getattr(agent, "default_tool", "") in ("opencode_run", "kilo_run")):
            wt = _setup_worktree(worktree_name)
            if wt and getattr(wt, "success", False) and getattr(wt, "worktree_path", None):
                worktree_path = str(wt.worktree_path)

        target_dir = worktree_path or path
        if not target_dir or target_dir == str(Path.cwd()):
            from core.repo_context import get_unique_project_dir
            target_dir = str(get_unique_project_dir(prompt))

        # Ensure target_dir exists physically on disk before subprocess execution
        try:
            Path(target_dir).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning("[FleetDispatcher] Could not ensure directory %s: %s", target_dir, e)

        # Resolve active procedural skills from agent.allowed_skills
        skills_context = ""
        try:
            from core.skill_loader import get_skill_registry
            skill_reg = get_skill_registry()
            for sk in (getattr(agent, "allowed_skills", []) or []):
                skill_obj = getattr(skill_reg, "get_skill", lambda s: getattr(skill_reg, "_skills", {}).get(s))(sk)
                if not skill_obj and hasattr(skill_reg, "_skills"):
                    for k, s in skill_reg._skills.items():
                        if k.lower() == str(sk).lower():
                            skill_obj = s
                            break
                if skill_obj and getattr(skill_obj, "instructions", None):
                    skills_context += f"\n\n[ACTIVE SKILL: {skill_obj.name}]\n{skill_obj.instructions}\n"
        except Exception as e:
            logger.debug("[FleetDispatcher] Skill resolution error: %s", e)

        # Build context enrichment
        memory_context = ""
        if session_memory:
            try:
                mem_str = json.dumps(session_memory, indent=2) if isinstance(session_memory, dict) else str(session_memory)
                memory_context = f"\n\n[SESSION MEMORY]\n{mem_str}\n"
            except Exception:
                pass

        candidate_context = f"\n\n[CANDIDATE INFO: {candidate_info}]" if candidate_info else ""
        spec_context = f"\n\n[DESIGN SPEC: {design_spec}]" if design_spec else ""
        proj_context = f"\n\n[PROJECT TYPE: {project_type}]" if project_type else ""

        agent_prefix = getattr(agent, "prompt_prefix", "") or ""
        agent_role = getattr(agent, "role", "Fleet Specialist")
        agent_name = getattr(agent, "name", agent.id)

        enriched_prompt = (
            f"[{agent_name} • {agent_role}]\n"
            f"{agent_prefix}{skills_context}{memory_context}{candidate_context}{spec_context}{proj_context}\n\n"
            f"Task: {prompt}"
        )
        active_model = model or model_override or getattr(agent, "model_id", None) or None

        from core.action_loader import discover_actions
        actions_dir = Path(__file__).resolve().parent.parent.parent / "actions"
        reg = discover_actions(actions_dir)
        effective_tool = ""
        agent_engine = getattr(agent, "engine", None)
        agent_default_tool = getattr(agent, "default_tool", None)

        if agent_engine and reg.has(f"{agent_engine}_run"):
            effective_tool = f"{agent_engine}_run"
        elif agent_default_tool and reg.has(agent_default_tool):
            effective_tool = agent_default_tool
        else:
            low_prompt = prompt.lower()
            if "code" in low_prompt or "build" in low_prompt or "app" in low_prompt:
                effective_tool = "opencode_run"
            elif any(k in low_prompt for k in ("research", "transcript", "video", "youtube", "media", "search", "http")):
                effective_tool = "agent_reach" if reg.has("agent_reach") else "web_search"
            else:
                effective_tool = "quick_snippet" if reg.has("quick_snippet") else "opencode_run"

        # Submit task to background TaskManager
        from core.task_manager import get_task_manager
        tm = get_task_manager()

        sync_done_event = threading.Event()
        sync_result_holder: Dict[str, Any] = {}

        def _worker_fn(worker_params: dict, task_ctx: Any) -> dict:
            params = worker_params or {}
            w_task_id = getattr(task_ctx, "task_id", None) or params.get("task_id") or dispatch_task_id
            w_agent_id = params.get("agent_id") or agent.id
            w_agent = self._get_agent(w_agent_id) or agent
            w_agent_name = params.get("agent_name") or getattr(w_agent, "name", w_agent_id)
            w_prompt = params.get("task") or prompt
            w_enriched_prompt = params.get("enriched_prompt") or enriched_prompt
            w_target_dir = params.get("target_dir") or target_dir
            w_model = params.get("model_id") or active_model
            wt_name = params.get("worktree_name") or (worktree_name if worktree_path else None)
            wt_path = params.get("worktree_path") or worktree_path
            w_tool = params.get("tool") or effective_tool
            w_scope_type = params.get("scope_type") or scope_type
            w_entity_content = params.get("entity_content") or entity_content
            w_tech_stack = params.get("tech_stack") or tech_stack
            w_color_theme = params.get("color_theme") or color_theme
            w_key_sections = params.get("key_sections") or key_sections
            w_confirmed = params.get("confirmed", confirmed)

            try:
                # Wrap task_ctx.report to synchronize agent progress and activity logs
                orig_report = getattr(task_ctx, "report", None)
                last_fleet_broadcast = 0.0

                def _reporting_wrapper(prog: int, msg: str = "") -> None:
                    nonlocal last_fleet_broadcast
                    if hasattr(task_ctx, "cancelled") and task_ctx.cancelled():
                        return
                    if orig_report:
                        try:
                            orig_report(prog, msg)
                        except Exception:
                            pass

                    lock = getattr(self.registry, "_lock", None) or self._lock
                    with lock:
                        w_agent.task_progress = max(0, min(100, prog))
                        if msg:
                            clean_msg = f"[{prog}%] {msg}"
                            if not w_agent.recent_logs or w_agent.recent_logs[-1] != clean_msg:
                                w_agent.recent_logs.append(clean_msg)
                                if len(w_agent.recent_logs) > 30:
                                    w_agent.recent_logs = w_agent.recent_logs[-30:]

                    self._broadcast_event("task_progress", {
                        "task_id": w_task_id,
                        "agent_id": w_agent.id,
                        "agent": w_agent_name,
                        "progress": prog,
                        "message": msg,
                    })

                    now = time.time()
                    if now - last_fleet_broadcast >= 1.0 or prog >= 100:
                        last_fleet_broadcast = now
                        self._broadcast_event("fleet_updated", {"fleet": self._get_fleet_deck_state()})

                task_ctx.report = _reporting_wrapper

                # Extract URL or target query from prompt if present for specialized tools
                url_match = re.search(r'https?://[^\s]+', w_prompt)
                extracted_url = url_match.group(0) if url_match else None
                extracted_target = extracted_url or w_prompt

                call_params = {
                    "task": w_enriched_prompt,
                    "prompt": w_enriched_prompt,
                    "target": extracted_target,
                    "url": extracted_url,
                    "query": extracted_target,
                    "project_path": w_target_dir,
                    "repo_path": w_target_dir,
                    "target_dir": w_target_dir,
                    "path": w_target_dir,
                    "run_in_place": True,
                    "task_ctx": task_ctx,
                }
                if session_memory:
                    call_params["session_memory"] = session_memory
                if design_spec:
                    call_params["design_spec"] = design_spec
                if project_type:
                    call_params["project_type"] = project_type

                spec_items: List[str] = []
                if w_scope_type and f"Scope: {w_scope_type}" not in w_enriched_prompt:
                    spec_items.append(f"Scope: {w_scope_type}")
                if w_tech_stack and f"Stack: {w_tech_stack}" not in w_enriched_prompt:
                    spec_items.append(f"Stack: {w_tech_stack}")
                if w_color_theme and f"Theme: {w_color_theme}" not in w_enriched_prompt:
                    spec_items.append(f"Theme: {w_color_theme}")
                if w_key_sections and f"Sections: {w_key_sections}" not in w_enriched_prompt:
                    spec_items.append(f"Sections: {w_key_sections}")
                if w_entity_content and f"Entity/Content: {w_entity_content}" not in w_enriched_prompt:
                    spec_items.append(f"Entity/Content: {w_entity_content}")

                if spec_items:
                    spec_block = "\n[" + ", ".join(spec_items) + "]"
                    call_params["task"] = w_enriched_prompt + spec_block
                    call_params["prompt"] = call_params["task"]

                # Synthesize tailored skill prompt for autonomous coding engines
                if w_tool in ("antigravity_run", "opencode_run", "kilo_run"):
                    try:
                        agent_skills = getattr(w_agent, "allowed_skills", []) or []
                        primary_skill = None
                        if agent_skills:
                            p_lower = (w_prompt or "").lower()
                            matched = next((s for s in agent_skills if s in p_lower or s.replace("_", " ") in p_lower), None)
                            primary_skill = matched or agent_skills[0]
                        else:
                            p_lower = (w_prompt or "").lower()
                            if "clone" in p_lower:
                                primary_skill = "website_clone"
                            elif "design" in p_lower:
                                primary_skill = "generate_design_md"
                            elif "website" in p_lower:
                                primary_skill = "website_build"

                        if primary_skill:
                            from core.skill_loader import get_skill_registry
                            from core.skill_prompt_engineer import craft_skill_engine_prompt

                            skill_reg = get_skill_registry()
                            skill_sop = skill_reg.read_skill(primary_skill) if skill_reg else ""

                            context_dict = {
                                "scope_type": w_scope_type,
                                "tech_stack": w_tech_stack,
                                "color_theme": w_color_theme,
                                "entity_content": w_entity_content,
                                "key_sections": w_key_sections,
                            }
                            if primary_skill == "generate_design_md":
                                req_prompt = w_prompt or prompt or ""
                                url_match = re.search(r'https?://[^\s\'"<>]+', req_prompt)
                                if url_match:
                                    found_url = url_match.group(0)
                                    from core.url_prefetch import prefetch_url_assets
                                    manifest = prefetch_url_assets(
                                        found_url,
                                        Path(w_target_dir) if w_target_dir else Path("."),
                                        task_ctx,
                                    )
                                    context_dict["mode"] = "url"
                                    context_dict["url"] = found_url
                                    context_dict["prefetched_assets"] = manifest
                                else:
                                    context_dict["mode"] = "local"
                                    context_dict["target_dir"] = w_target_dir
                            engine_name = getattr(w_agent, "engine", "antigravity") or "antigravity"
                            crafted = craft_skill_engine_prompt(
                                skill_name=primary_skill,
                                skill_sop=skill_sop,
                                user_task=w_prompt,
                                target_dir=w_target_dir or ".",
                                context=context_dict,
                                engine=engine_name,
                            )
                            if crafted:
                                w_enriched_prompt = crafted
                                call_params["task"] = crafted
                                call_params["prompt"] = crafted
                    except Exception as pe_err:
                        logger.warning(
                            "[FleetDispatcher] craft_skill_engine_prompt failed for %s, falling back: %s",
                            getattr(w_agent, "name", w_agent_id),
                            pe_err,
                        )

                if w_tool == "antigravity_run":
                    call_params["scope_type"] = w_scope_type
                    call_params["entity_content"] = w_entity_content
                    call_params["tech_stack"] = w_tech_stack
                    call_params["color_theme"] = w_color_theme
                    call_params["key_sections"] = w_key_sections
                    call_params["confirmed"] = w_confirmed

                if w_model:
                    call_params["model"] = w_model
                    call_params["model_id"] = w_model

                res = reg.run(w_tool, call_params)

                # Check if task was cancelled during action execution
                if hasattr(task_ctx, "cancelled") and task_ctx.cancelled():
                    self.complete_task(agent.id, w_task_id, merge_changes=False, worktree_id=wt_name)
                    self._broadcast_event("task_cancelled", {
                        "task_id": w_task_id,
                        "agent_id": agent.id,
                        "agent": agent.name,
                    })
                    self._broadcast_event("fleet_updated", {"fleet": self._get_fleet_deck_state()})
                    if wt_path:
                        _teardown_worktree(wt_name or worktree_name)
                    ret = {"status": "cancelled"}
                    sync_result_holder["res"] = ret
                    return ret

                # Inspect result for explicit errors, missing parameters, or failures
                is_error = False
                err_msg = ""
                if isinstance(res, dict):
                    if res.get("status") in ("error", "failed") or res.get("success") is False:
                        is_error = True
                        err_msg = str(res.get("error") or res.get("message") or "Task execution failed")
                    elif res.get("status") == "cancelled":
                        self.complete_task(agent.id, w_task_id, merge_changes=False, worktree_id=wt_name)
                        self._broadcast_event("task_cancelled", {
                            "task_id": w_task_id,
                            "agent_id": agent.id,
                            "agent": agent.name,
                        })
                        self._broadcast_event("fleet_updated", {"fleet": self._get_fleet_deck_state()})
                        if wt_path:
                            _teardown_worktree(wt_name or worktree_name)
                        ret = {"status": "cancelled"}
                        sync_result_holder["res"] = ret
                        return ret
                elif isinstance(res, str):
                    low_res = res.lower().strip()
                    if low_res.startswith("{") and low_res.endswith("}"):
                        try:
                            parsed_json = json.loads(res)
                            if isinstance(parsed_json, dict):
                                if parsed_json.get("status") in ("error", "failed") or parsed_json.get("success") is False:
                                    is_error = True
                                    err_msg = str(parsed_json.get("error") or parsed_json.get("message") or "Task execution failed")
                        except Exception:
                            pass
                    if not is_error and (
                        low_res.startswith("error:")
                        or low_res.startswith("failed:")
                        or low_res.startswith("tool '")
                        or low_res.startswith("tool \"")
                        or "failed:" in low_res
                        or "exception" in low_res
                        or "winerror" in low_res
                        or "is not installed" in low_res
                        or "refusing to use" in low_res
                        or low_res.startswith("please provide")
                    ):
                        is_error = True
                        err_msg = res

                if is_error:
                    circuit_breaker.record_failure(w_tool, err_msg)
                    if hasattr(task_ctx, "on_fail"):
                        task_ctx.on_fail(err_msg)
                    self.complete_task(agent.id, w_task_id, merge_changes=False, worktree_id=wt_name)
                    self._broadcast_event("task_failed", {
                        "task_id": w_task_id,
                        "agent_id": agent.id,
                        "agent": agent.name,
                        "error": err_msg,
                    })
                    self._broadcast_event("fleet_updated", {"fleet": self._get_fleet_deck_state()})
                    if wt_path:
                        _teardown_worktree(wt_name or worktree_name)
                    ret = {"status": "error", "error": err_msg}
                    sync_result_holder["res"] = ret
                    return ret

                # Success path
                circuit_breaker.record_success(w_tool)
                _reporting_wrapper(100, "Completed successfully")
                self.complete_task(agent.id, w_task_id, merge_changes=True, worktree_id=wt_name)
                self._broadcast_event("task_done", {
                    "task_id": w_task_id,
                    "agent_id": agent.id,
                    "agent": agent.name,
                    "summary": f"Completed: {prompt[:60]}",
                })
                self._broadcast_event("fleet_updated", {"fleet": self._get_fleet_deck_state()})
                if wt_path:
                    _teardown_worktree(wt_name or worktree_name)
                ret = {"status": "success", "result": str(res)}
                sync_result_holder["res"] = ret
                return ret

            except Exception as ex:
                circuit_breaker.record_failure(w_tool, str(ex))
                if hasattr(task_ctx, "on_fail"):
                    task_ctx.on_fail(str(ex))
                self.complete_task(agent.id, w_task_id, merge_changes=False, worktree_id=wt_name)
                self._broadcast_event("task_failed", {
                    "task_id": w_task_id,
                    "agent_id": agent.id,
                    "agent": agent.name,
                    "error": str(ex),
                })
                self._broadcast_event("fleet_updated", {"fleet": self._get_fleet_deck_state()})
                if wt_path:
                    _teardown_worktree(wt_name or worktree_name)
                sync_result_holder["err"] = str(ex)
                raise
            finally:
                sync_done_event.set()

        # Handle subtask grouping
        parent_group_id = None
        parent_group_title = None
        effective_group = group_id or parent_task_id

        if effective_subtask and effective_group:
            try:
                parent_state = tm._tasks.get(effective_group)
                if parent_state:
                    parent_group_id = parent_state.group_id or parent_state.id
                    parent_group_title = parent_state.group_title or parent_state.group_id or "Subtask"
            except Exception:
                pass

        submit_params = {
            "task": prompt,
            "taskTitle": prompt[:60],
            "enriched_prompt": enriched_prompt,
            "agent_id": agent.id,
            "agent_name": agent.name,
            "target_dir": target_dir,
            "model_id": active_model,
            "model": active_model,
            "is_subtask": effective_subtask,
            "worktree_name": worktree_name if worktree_path else None,
            "worktree_path": worktree_path,
            "tool": effective_tool,
            "scope_type": scope_type,
            "entity_content": entity_content,
            "tech_stack": tech_stack,
            "color_theme": color_theme,
            "key_sections": key_sections,
            "confirmed": confirmed,
            "candidate_info": candidate_info,
            "design_spec": design_spec,
            "project_type": project_type,
        }

        submit_fn = getattr(tm, "submit_task", getattr(tm, "submit", None))
        if not submit_fn:
            return {"success": False, "error": "TaskManager does not support task submission"}

        submitted_id = submit_fn(
            tool_name=effective_tool,
            fn=_worker_fn,
            params=submit_params,
            group_id=parent_group_id or effective_group if effective_subtask else None,
            group_title=parent_group_title or (f"[{agent.name}] {prompt[:40]}..." if not effective_subtask else None),
            parent_id=effective_group if effective_subtask else None,
        )

        lock = getattr(self.registry, "_lock", None) or self._lock
        with lock:
            agent.status = "working"
            agent.current_task_id = submitted_id
            agent.current_task_title = prompt
            agent.task_progress = 0
            agent.active_worktree = worktree_path
            agent.recent_logs.append(f"[TASK STARTED] {prompt[:80]}")
            if len(agent.recent_logs) > 30:
                agent.recent_logs = agent.recent_logs[-30:]

        self._broadcast_event("agent_task_started", {
            "task_id": submitted_id,
            "agent_id": agent.id,
            "agent": agent.name,
            "task": prompt,
            "title": prompt[:60],
            "tool": effective_tool,
            "target_dir": target_dir,
        })
        self._broadcast_event("fleet_updated", {"fleet": self._get_fleet_deck_state()})

        # Synchronous execution wait if sync requested
        if sync:
            timeout_sec = float(extra_kwargs.get("timeout", 600.0))
            finished = sync_done_event.wait(timeout=timeout_sec)
            if not finished:
                return {
                    "success": False,
                    "error": f"Synchronous execution timed out after {timeout_sec}s",
                    "task_id": submitted_id,
                    "agent_id": agent.id,
                }
            if "err" in sync_result_holder:
                return {
                    "success": False,
                    "error": sync_result_holder["err"],
                    "task_id": submitted_id,
                    "agent_id": agent.id,
                }
            return {
                "success": True,
                "task_id": submitted_id,
                "agent_id": agent.id,
                "agent_name": agent.name,
                "tool": effective_tool,
                "model_id": active_model,
                "worktree": worktree_path,
                "result": sync_result_holder.get("res"),
            }

        return {
            "success": True,
            "task_id": submitted_id,
            "agent_id": agent.id,
            "agent_name": agent.name,
            "tool": effective_tool,
            "model_id": active_model,
            "worktree": worktree_path,
        }
