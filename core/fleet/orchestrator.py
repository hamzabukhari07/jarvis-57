from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.git_sandbox import git_sandbox

logger = logging.getLogger(__name__)

DELIVERABLE_ARCHETYPES = (
    "portfolio",
    "website",
    "landing page",
    "landing-page",
    "web app",
    "web-app",
    "webapp",
    "dashboard",
    "full-stack",
    "fullstack",
    "saas",
)

__all__ = ["FleetOrchestrator", "DELIVERABLE_ARCHETYPES"]


class FleetOrchestrator:
    """
    Coordinates multi-agent workflows, peer-to-peer task delegations,
    task decomposition (Michael orchestrator), and task completion lifecycle.
    """

    def __init__(self, registry: Any, dispatcher: Any) -> None:
        self.registry = registry
        self.dispatcher = dispatcher

    def _get_agent(self, agent_id: str) -> Any:
        if hasattr(self.registry, "get_agent"):
            return self.registry.get_agent(agent_id)
        if hasattr(self.registry, "agents") and isinstance(self.registry.agents, dict):
            return self.registry.agents.get(agent_id)
        return None

    def _resolve_agent(self, agent_id: str) -> Any:
        target = None
        if hasattr(self.registry, "resolve_agent_by_mention_or_capability"):
            target = self.registry.resolve_agent_by_mention_or_capability(agent_id)
        if not target:
            target = self._get_agent(agent_id)
        return target

    def _broadcast_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Thread-safe broadcast of fleet and task events to WebSocket UI and log bus."""
        if hasattr(self.dispatcher, "_broadcast_event"):
            try:
                self.dispatcher._broadcast_event(event_type, data)
                return
            except Exception:
                pass
        try:
            from core.ui_server import get_ui_server
            get_ui_server().broadcast(event_type, data)
        except Exception as e:
            logger.debug("[FleetOrchestrator] UI broadcast skipped: %s", e)
        try:
            from core.log_bus import emit_tool_micro_event
            emit_tool_micro_event(event_type, "fleet_orchestrator", data)
        except Exception:
            pass

    def _get_fleet_deck_state(self) -> List[Dict[str, Any]]:
        """Helper to obtain fleet deck state from registry or dispatcher."""
        if hasattr(self.registry, "get_fleet_deck_state"):
            return self.registry.get_fleet_deck_state()
        if hasattr(self.dispatcher, "get_fleet_deck_state"):
            return self.dispatcher.get_fleet_deck_state()
        return []

    def generate_peer_session_id(self, from_agent: str, to_agent: str) -> str:
        """Generates deterministic composite peer session ID for isolated P2P communication lineage."""
        src = from_agent.upper().strip()
        dst = to_agent.upper().strip()
        return f"peer:{src}->{dst}:{int(time.time())}"

    def delegate_peer_task(
        self,
        from_agent: str = "ZEZO",
        to_agent: str = "",
        prompt: str = "",
        path: Optional[str] = None,
        session_id: Optional[str] = None,
        model: Optional[str] = None,
        parent_task_id: Optional[str] = None,
        candidate_info: Optional[str] = None,
        design_spec: Optional[str] = None,
        project_type: Optional[str] = None,
        from_agent_id: Optional[str] = None,
        to_agent_id: Optional[str] = None,
        task: Optional[str] = None,
        upstream_deliverables: Optional[str] = None,
        call_chain: Optional[List[str]] = None,
        scope_type: Optional[str] = None,
        entity_content: Optional[str] = None,
        tech_stack: Optional[str] = None,
        color_theme: Optional[str] = None,
        key_sections: Optional[str] = None,
        confirmed: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Executes a peer-to-peer delegation from one specialist agent to another with circular loop detection.
        Injects upstream deliverables into the recipient's task payload.
        """
        src = (from_agent_id or from_agent or "ZEZO").upper().strip()
        dst_raw = to_agent_id or to_agent or ""
        task_text = task or prompt or ""
        upstream = upstream_deliverables or candidate_info or design_spec or None
        scope = scope_type or project_type or None

        chain = list(call_chain or [src])

        # Resolve recipient
        target = self._resolve_agent(dst_raw)
        if not target:
            return {"success": False, "error": f"Target peer agent '{dst_raw}' could not be resolved."}

        dst = target.id

        # 1. Max Depth & Circular Loop Detection Guards
        if len(chain) >= 4:
            return {
                "success": False,
                "error": f"Maximum peer delegation depth (3) exceeded: {' -> '.join(chain)}.",
            }

        if dst in chain:
            cycle_str = " -> ".join(chain + [dst])
            logger.warning("[FleetOrchestrator] Circular delegation loop blocked: %s", cycle_str)
            return {
                "success": False,
                "error": f"Circular peer delegation loop detected ({cycle_str}). Delegation blocked.",
            }

        new_chain = chain + [dst]
        sess_id = session_id or self.generate_peer_session_id(src, dst)

        # 2. Inject Upstream Deliverables Handoff
        handoff_header = f"[Peer Request from {src} to {target.name}]\n[Peer Session: {sess_id}]\n"
        if upstream:
            handoff_header += f"\n--- UPSTREAM DELIVERABLE HANDOFF FROM {src} ---\n{upstream.strip()}\n------------------------------------------------\n\n"

        portfolio_specs = []
        if scope:
            portfolio_specs.append(f"Scope: {scope}")
        if tech_stack:
            portfolio_specs.append(f"Stack: {tech_stack}")
        if color_theme:
            portfolio_specs.append(f"Theme: {color_theme}")
        if key_sections:
            portfolio_specs.append(f"Sections: {key_sections}")
        if entity_content:
            portfolio_specs.append(f"Entity/Content: {entity_content}")

        if portfolio_specs:
            handoff_header += f"\n--- SPECIFICATIONS & CONTENT HANDOFF ---\n" + "\n".join(portfolio_specs) + "\n----------------------------------------\n\n"

        full_task_prompt = f"{handoff_header}Directive: {task_text}"

        logger.info("[FleetOrchestrator] P2P Delegation: %s -> %s (Chain: %s)", src, dst, " -> ".join(new_chain))

        if hasattr(self.dispatcher, "dispatch_task"):
            res = self.dispatcher.dispatch_task(
                agent_id=dst,
                prompt=full_task_prompt,
                path=path,
                model_override=model,
                scope_type=scope,
                entity_content=entity_content,
                tech_stack=tech_stack,
                color_theme=color_theme,
                key_sections=key_sections,
                confirmed=confirmed,
                **{k: v for k, v in kwargs.items() if k not in ("agent_id", "prompt", "path", "model_override")},
            )
        elif callable(self.dispatcher):
            res = self.dispatcher(agent_id=dst, prompt=full_task_prompt, path=path)
        else:
            return {"success": False, "error": "Dispatcher not configured on FleetOrchestrator."}

        if isinstance(res, dict):
            res["peer_session_id"] = sess_id
            res["call_chain"] = new_chain
            res["from_agent"] = src
            res["to_agent"] = dst
            if parent_task_id and "parent_task_id" not in res:
                res["parent_task_id"] = parent_task_id
        return res

    def decompose_and_dispatch(
        self,
        prompt: str,
        path: Optional[str] = None,
        parent_task_id: Optional[str] = None,
        group_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """High-level Michael task decomposition into specialized subtasks with deliverable piping.

        When a complete deliverable archetype is detected in prompt, partitions the project
        concurrently across the Scranton Fleet Swarm (Verve, Flux, Ahmad, Dwight).
        Otherwise, routes to a targeted single-agent assignment.
        """
        low = prompt.lower()
        is_deliverable = any(arch in low for arch in DELIVERABLE_ARCHETYPES)

        if is_deliverable:
            shared_group_id = parent_task_id or group_id or f"swarm_{uuid.uuid4().hex[:8]}"
            subtasks = [
                (
                    "VERVE",
                    "Design and build core responsive page layout, hero section, navigation, and theme styling: " + prompt,
                    "frontend",
                ),
                (
                    "FLUX",
                    "Build interactive UI components, project showcase cards, skill badges, and micro-interactions: " + prompt,
                    "frontend/components",
                ),
                (
                    "AHMAD",
                    "Implement backend contact form API endpoint (/api/contact), input validation, and data schema: " + prompt,
                    "backend",
                ),
                (
                    "DWIGHT",
                    "Conduct end-to-end verification, link integrity check, and responsive breakpoint testing: " + prompt,
                    "tests",
                ),
            ]
        else:
            shared_group_id = parent_task_id or group_id
            if any(w in low for w in ("research", "scrape", "youtube", "investigate", "find")):
                subtasks = [("KELLY", "Perform deep research and gather key technical requirements: " + prompt, "research")]
            elif any(w in low for w in ("ui", "frontend", "css", "html", "react", "view", "component", "styling", "page")):
                frontend_id = "VERVE" if self._get_agent("VERVE") else ("FLUX" if self._get_agent("FLUX") else "ALI")
                subtasks = [(frontend_id, "Design and build responsive frontend user interface: " + prompt, "frontend")]
            elif any(w in low for w in ("api", "backend", "database", "crud", "endpoint", "server", "model", "auth")):
                subtasks = [("AHMAD", "Implement robust backend APIs, database schemas, and service logic: " + prompt, "backend")]
            elif any(w in low for w in ("test", "qa", "verify", "audit", "security", "bug", "check", "lint")):
                subtasks = [("DWIGHT", "Conduct end-to-end test verification, security review, and edge case audit: " + prompt, "tests")]
            else:
                subtasks = [("AHMAD", prompt, "")]

        if path:
            base_dir = Path(path).resolve()
        else:
            from core.repo_context import get_unique_project_dir
            base_dir = Path(get_unique_project_dir(prompt)).resolve()

        inferred_scope = None
        if any(w in low for w in ("portfolio", "resume", "cv")):
            inferred_scope = "portfolio"
        elif any(w in low for w in ("landing", "waitlist", "saas")):
            inferred_scope = "landing_page"
        elif any(w in low for w in ("dashboard", "admin", "metrics")):
            inferred_scope = "dashboard"
        elif any(w in low for w in ("web app", "webapp", "web-app", "website", "full-stack", "fullstack")):
            inferred_scope = "web_app"

        dispatched = []
        for target_id, sub_prompt, sub_folder in subtasks:
            target_agent = self._resolve_agent(target_id)
            if not target_agent and hasattr(self.registry, "agents") and isinstance(self.registry.agents, dict) and self.registry.agents:
                target_agent = list(self.registry.agents.values())[0]

            agent_id = target_agent.id if target_agent else target_id

            if len(subtasks) > 1 and sub_folder:
                sub_path = str((base_dir / sub_folder).resolve())
                try:
                    Path(sub_path).mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    logger.warning("[FleetOrchestrator] Could not create subtask dir %s: %s", sub_path, e)
            else:
                sub_path = str(base_dir)

            dispatch_kwargs: Dict[str, Any] = {
                "is_subtask": True,
                "scope_type": inferred_scope,
            }
            if shared_group_id:
                dispatch_kwargs["group_id"] = shared_group_id
                dispatch_kwargs["parent_task_id"] = shared_group_id

            if hasattr(self.dispatcher, "dispatch_task"):
                res = self.dispatcher.dispatch_task(
                    agent_id,
                    sub_prompt,
                    path=sub_path,
                    **dispatch_kwargs,
                )
            elif callable(self.dispatcher):
                try:
                    res = self.dispatcher(agent_id, sub_prompt, path=sub_path, **dispatch_kwargs)
                except TypeError:
                    res = self.dispatcher(agent_id, sub_prompt, path=sub_path, is_subtask=True)
            else:
                res = {"success": False, "error": "Dispatcher not configured on FleetOrchestrator.", "agent_id": agent_id}

            if isinstance(res, dict):
                res["path"] = sub_path
                if shared_group_id:
                    res.setdefault("group_id", shared_group_id)
                    res.setdefault("parent_task_id", shared_group_id)
            dispatched.append(res)

        result: Dict[str, Any] = {
            "success": True,
            "orchestrator": "MICHAEL",
            "decomposed_count": len(dispatched),
            "tasks": dispatched,
            "base_path": str(base_dir),
        }
        if shared_group_id:
            result["group_id"] = shared_group_id
            result["parent_task_id"] = shared_group_id
        return result

    def complete_task(
        self,
        agent_id: str,
        task_id: str,
        merge_changes: bool = False,
        worktree_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Mark agent task complete and teardown worktree."""
        agent = self._get_agent(agent_id)
        if not agent:
            return {"success": False, "error": f"Agent '{agent_id}' not found."}

        wt_id = worktree_id
        if not wt_id and getattr(agent, "active_worktree", None):
            try:
                wt_id = Path(agent.active_worktree).name
            except Exception:
                wt_id = task_id
        if not wt_id:
            wt_id = task_id

        merge_msg = ""
        if merge_changes and getattr(agent, "active_worktree", None):
            success, merge_msg = git_sandbox.merge_worktree(wt_id)
            if not success:
                logger.warning(f"[FleetOrchestrator] Merge failed: {merge_msg}")

        if getattr(agent, "active_worktree", None):
            teardown_msg = git_sandbox.safe_teardown(wt_id)
            logger.info(f"[FleetOrchestrator] {teardown_msg}")

        lock = getattr(self.registry, "_lock", None)

        def _update_agent_state() -> None:
            agent.status = "idle"
            agent.current_task_id = None
            agent.current_task_title = None
            agent.task_progress = 0
            agent.active_worktree = None
            agent.completed_tasks = getattr(agent, "completed_tasks", 0) + 1
            if not hasattr(agent, "recent_logs") or agent.recent_logs is None:
                agent.recent_logs = []
            agent.recent_logs.append(f"[COMPLETED] Task {task_id} finished")
            if len(agent.recent_logs) > 30:
                agent.recent_logs = agent.recent_logs[-30:]

        if lock is not None:
            with lock:
                _update_agent_state()
        else:
            _update_agent_state()

        self._broadcast_event("fleet_updated", {"fleet": self._get_fleet_deck_state()})

        return {
            "success": True,
            "agent_name": getattr(agent, "name", agent_id),
            "status": "idle",
            "merge_result": merge_msg,
        }
