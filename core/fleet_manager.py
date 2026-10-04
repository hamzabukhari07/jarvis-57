from __future__ import annotations

import json
import logging
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.circuit_breaker import circuit_breaker
from core.git_sandbox import git_sandbox

logger = logging.getLogger(__name__)

OFFICE_DESK_COORDINATES: list[tuple[int, int]] = [
    (180, 160), (320, 160), (460, 160), (600, 160),
    (180, 280), (320, 280), (460, 280), (600, 280),
    (180, 400), (320, 400), (460, 400), (600, 400),
]

VALID_RISK_TIERS: set[str] = {"L0_READ_ONLY", "L1_MUTATION", "L2_DESTRUCTIVE"}
VALID_TOOLS: set[str] = {
    "opencode_run", "kilo_run", "dev_agent", "code_helper",
    "antigravity_run", "extract_design_system", "agent_reach",
    "web_reader", "web_search",
}


@dataclass
class FleetAgent:
    id: str
    name: str
    role: str
    specialty: str
    color: str
    avatar_pixel: str
    default_tool: str
    risk_tier: str
    prompt_prefix: str
    model_id: str = ""
    status: str = "idle"
    current_task_id: Optional[str] = None
    current_task_title: Optional[str] = None
    task_progress: int = 0
    desk_x: int = 0
    desk_y: int = 0
    active_worktree: Optional[str] = None
    completed_tasks: int = 0
    recent_logs: List[str] = field(default_factory=list)
    allowed_tools: List[str] = field(default_factory=list)
    allowed_skills: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)


class FleetManager:
    """Orchestrates named specialist agent fleet, isolated worktrees, and live deck state."""

    def __init__(self, config_path: Optional[Path] = None):
        self._lock = threading.RLock()
        self.config_path = config_path or (Path(__file__).parent.parent / "config" / "fleet_agents.json")
        self.agents: Dict[str, FleetAgent] = {}
        self._load_fleet()

    def _allocate_desk(self, existing: Optional[FleetAgent], req_x: int, req_y: int) -> Tuple[int, int]:
        """Allocate next available workstation desk on the office floor."""
        if req_x > 0 and req_y > 0:
            return req_x, req_y
        if existing and existing.desk_x > 0 and existing.desk_y > 0:
            return existing.desk_x, existing.desk_y

        occupied = {(a.desk_x, a.desk_y) for a in self.agents.values() if a.desk_x > 0 and a.desk_y > 0}
        for coord in OFFICE_DESK_COORDINATES:
            if coord not in occupied:
                return coord

        idx = len(self.agents)
        return (180 + (idx % 4) * 140, 480 + (idx // 4) * 100)

    def _load_fleet(self) -> None:
        if not self.config_path.exists():
            return
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            fleet_data = data.get("fleet", {})
            with self._lock:
                self.agents.clear()
                for agent_id, info in fleet_data.items():
                    uid = agent_id.upper().strip()
                    self.agents[uid] = FleetAgent(
                        id=uid,
                        name=info.get("name", agent_id),
                        role=info.get("role", ""),
                        specialty=info.get("specialty", ""),
                        color=info.get("color", "#3b82f6"),
                        avatar_pixel=info.get("avatar_pixel", f"{uid.lower()}_pixel.png"),
                        default_tool=info.get("default_tool", "dev_agent"),
                        risk_tier=info.get("risk_tier", "L0_READ_ONLY"),
                        prompt_prefix=info.get("prompt_prefix", ""),
                        model_id=info.get("model_id", ""),
                        desk_x=info.get("desk_x", 0),
                        desk_y=info.get("desk_y", 0),
                        allowed_tools=list(info.get("allowed_tools") or []),
                        allowed_skills=list(info.get("allowed_skills") or []),
                        capabilities=list(info.get("capabilities") or []),
                    )
        except Exception as e:
            logger.error("[FleetManager] Failed to load fleet config: %s", e)

    def _save_fleet(self) -> bool:
        """Persist current fleet state back to fleet_agents.json."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            export: Dict[str, Any] = {"fleet": {}}
            with self._lock:
                for a in self.agents.values():
                    export["fleet"][a.id] = {
                        "name": a.name,
                        "role": a.role,
                        "specialty": a.specialty,
                        "color": a.color,
                        "avatar_pixel": a.avatar_pixel,
                        "default_tool": a.default_tool,
                        "risk_tier": a.risk_tier,
                        "prompt_prefix": a.prompt_prefix,
                        "model_id": a.model_id,
                        "desk_x": a.desk_x,
                        "desk_y": a.desk_y,
                        "allowed_tools": a.allowed_tools,
                        "allowed_skills": a.allowed_skills,
                        "capabilities": a.capabilities,
                    }
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(export, f, indent=2)
            return True
        except Exception as e:
            logger.error("[FleetManager] Failed to save fleet config: %s", e)
            return False

    def get_agent(self, name_or_id: str) -> Optional[FleetAgent]:
        key = name_or_id.upper().strip()
        with self._lock:
            if key in self.agents:
                return self.agents[key]
            for a in self.agents.values():
                if key == a.name.upper() or a.name.upper().startswith(key) or key in a.name.upper().split():
                    return a
        return None

    def resolve_agent_by_mention_or_capability(self, query: str) -> Optional[FleetAgent]:
        """
        Intelligently resolves an agent by explicit name mention, role alias, or capability keyword fallback.
        Examples:
          - "Ali build landing page" -> ALI
          - "Tell Dwight to verify" -> DWIGHT
          - "Research AI frameworks" -> KELLY (Social & Deep Web Researcher)
          - "Build PostgreSQL models" -> AHMAD (Full-Stack & Backend Specialist)
        """
        if not query or not query.strip():
            return None

        q = query.strip()
        words = re.findall(r"\b[A-Za-z0-9_]+\b", q)

        # 1. Direct Name / ID match in words (e.g. 'Ali', 'Ahmad', 'Dwight', 'Pam', 'Oscar', 'Kelly', 'Michael')
        with self._lock:
            for w in words:
                w_up = w.upper()
                for agent_id, agent in self.agents.items():
                    if w_up == agent_id.upper() or w.lower() == agent.name.lower():
                        return agent

        low = q.lower()

        # 2. Known Role / Alias Mapping
        role_map = {
            "manager": "MICHAEL",
            "orchestrator": "MICHAEL",
            "frontend": "ALI",
            "ui": "ALI",
            "designer": "ALI",
            "backend": "AHMAD",
            "database": "AHMAD",
            "fullstack": "AHMAD",
            "full-stack": "AHMAD",
            "qa": "DWIGHT",
            "tester": "DWIGHT",
            "auditor": "DWIGHT",
            "security": "DWIGHT",
            "tokens": "PAM",
            "metrics": "OSCAR",
            "accountant": "OSCAR",
            "complexity": "OSCAR",
            "researcher": "KELLY",
            "research": "KELLY",
            "scraper": "KELLY",
            "youtube": "KELLY",
        }
        for alias, agent_id in role_map.items():
            if re.search(rf"\b{re.escape(alias)}\b", low):
                agent = self.get_agent(agent_id)
                if agent:
                    return agent

        # 3. Domain Fallback Heuristics
        if any(w in low for w in ("token", "tokens", "palette", "design system", "extract design")):
            return self.get_agent("PAM")
        if any(w in low for w in ("html", "css", "landing", "page", "react", "tailwind", "component", "studio", "ui", "frontend", "website", "portfolio", "web-project")):
            if self.get_agent_active_task_count("ALI") >= 3:
                haider = self.get_agent("HAIDER")
                if haider and self.get_agent_active_task_count("HAIDER") < 3:
                    return haider
            return self.get_agent("ALI")
        if any(w in low for w in ("fastapi", "postgres", "sql", "api", "endpoint", "schema", "microservice", "auth", "backend", "database")):
            return self.get_agent("AHMAD")
        if any(w in low for w in ("test", "verify", "audit", "regression", "pytest", "edge case", "security")):
            return self.get_agent("DWIGHT")
        if any(w in low for w in ("scrape", "transcribe", "summary", "web search", "market research", "research", "social")):
            return self.get_agent("KELLY")

        # 4. Default dispatch fallback: Ali for UI/frontend, Ahmad for general coding
        if any(w in low for w in ("build", "create", "make", "design")):
            if self.get_agent_active_task_count("ALI") >= 3:
                haider = self.get_agent("HAIDER")
                if haider and self.get_agent_active_task_count("HAIDER") < 3:
                    return haider
            return self.get_agent("ALI")
        return self.get_agent("AHMAD") or self.get_agent("ALI") or list(self.agents.values())[0]

    def get_agent_active_task_count(self, agent_id: str) -> int:
        """Returns the number of currently active (running/queued) tasks assigned to an agent."""
        uid = (agent_id or "").upper().strip()
        if not uid:
            return 0
        from core.task_manager import get_task_manager
        tm = get_task_manager()
        active = tm.list_active()
        count = 0
        for t in active:
            params = t.get("params") or {}
            task_agent = str(params.get("agent_id") or "").upper().strip()
            if task_agent == uid:
                count += 1
        return count

    def generate_peer_session_id(self, from_agent: str, to_agent: str) -> str:
        """Generates deterministic composite peer session ID for isolated P2P communication lineage."""
        src = from_agent.upper().strip()
        dst = to_agent.upper().strip()
        return f"peer:{src}->{dst}:{int(time.time())}"

    def save_agent_profile(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update an agent persona, tool, and desk coordinate with strict schema validation."""
        raw_id = str(data.get("id") or data.get("name", "")).strip()
        if not raw_id:
            return {"success": False, "error": "Agent name or ID cannot be empty."}

        clean_id = "".join(c for c in raw_id.upper() if c.isalnum() or c == "_")[:20]
        if not clean_id:
            return {"success": False, "error": "Agent identifier must contain alphanumeric characters."}

        tool = str(data.get("default_tool") or "dev_agent").strip().lower()
        if tool not in VALID_TOOLS and not tool.endswith("_run") and not tool.endswith("_agent"):
            tool = "dev_agent"

        risk_tier = str(data.get("risk_tier") or "").upper().strip()
        if risk_tier not in VALID_RISK_TIERS:
            risk_tier = "L1_MUTATION" if tool in ("kilo_run", "opencode_run", "antigravity_run") else "L0_READ_ONLY"

        color_str = str(data.get("color") or "").strip()
        if not re.match(r"^#[0-9a-fA-F]{6}$", color_str):
            color_str = "#3b82f6"

        name_str = str(data.get("name") or clean_id.title()).strip()[:40] or clean_id.title()
        role_str = str(data.get("role") or "Autonomous Specialist").strip()[:80]
        specialty_str = str(data.get("specialty") or role_str).strip()[:120]
        model_id = str(data.get("model_id") or "").strip()

        with self._lock:
            existing = self.agents.get(clean_id)
            desk_x, desk_y = self._allocate_desk(
                existing,
                int(data.get("desk_x", 0)),
                int(data.get("desk_y", 0))
            )

            prompt_prefix = str(
                data.get("prompt_prefix")
                or (existing.prompt_prefix if existing else f"You are {name_str}, an autonomous fleet specialist focusing on {specialty_str}.")
            ).strip()

            agent = FleetAgent(
                id=clean_id,
                name=name_str,
                role=role_str,
                specialty=specialty_str,
                color=color_str,
                avatar_pixel=str(data.get("avatar_pixel") or (existing.avatar_pixel if existing else f"{clean_id.lower()}_pixel.png")),
                default_tool=tool,
                risk_tier=risk_tier,
                prompt_prefix=prompt_prefix,
                model_id=model_id or (existing.model_id if existing else ""),
                desk_x=desk_x,
                desk_y=desk_y,
                status=existing.status if existing else "idle",
                current_task_id=existing.current_task_id if existing else None,
                active_worktree=existing.active_worktree if existing else None,
                allowed_tools=list(data.get("allowed_tools") or (existing.allowed_tools if existing else [])),
                allowed_skills=list(data.get("allowed_skills") or (existing.allowed_skills if existing else [])),
                capabilities=list(data.get("capabilities") or (existing.capabilities if existing else [])),
            )
            self.agents[clean_id] = agent
            ok = self._save_fleet()

        try:
            from core.log_bus import emit_tool_micro_event
            emit_tool_micro_event("fleet_updated", "fleet_manager", {"action": "hire", "agent": self._agent_to_dict(agent)})
        except Exception:
            pass

        return {"success": ok, "agent": self._agent_to_dict(agent)}

    def save_agent_soul(self, agent_id: str, soul_prompt: str) -> Dict[str, Any]:
        """Update system prompt / soul.md for a specific agent."""
        agent = self.get_agent(agent_id)
        if not agent:
            return {"success": False, "error": f"Agent '{agent_id}' not found."}

        with self._lock:
            agent.prompt_prefix = soul_prompt.strip()
            ok = self._save_fleet()

        try:
            from core.log_bus import emit_tool_micro_event
            emit_tool_micro_event("fleet_updated", "fleet_manager", {"action": "soul_update", "agent_id": agent.id})
        except Exception:
            pass

        return {"success": ok, "agent_id": agent.id, "soul": agent.prompt_prefix}

    def delete_agent(self, agent_id: str) -> Dict[str, Any]:
        key = agent_id.upper().strip()
        with self._lock:
            if key not in self.agents:
                return {"success": False, "error": f"Agent '{agent_id}' not found."}

            agent = self.agents[key]
            # Teardown any active worktree if present
            if agent.active_worktree:
                try:
                    git_sandbox.safe_teardown(agent.current_task_id or agent.id.lower())
                except Exception as ex:
                    logger.warning("[FleetManager] Worktree teardown during delete_agent error: %s", ex)

            del self.agents[key]
            ok = self._save_fleet()

        try:
            from core.log_bus import emit_tool_micro_event
            emit_tool_micro_event("fleet_updated", "fleet_manager", {"action": "fire", "deleted_id": key})
        except Exception:
            pass

        return {"success": ok, "deleted_id": key}

    def get_agent_full_profile(self, agent_id: str) -> Dict[str, Any]:
        """Retrieve full details including soul.md, active worktree, and episodic memory."""
        agent = self.get_agent(agent_id)
        if not agent:
            return {"success": False, "error": f"Agent '{agent_id}' not found."}

        # Query episodic memories from SQLite for this agent persona
        memories = []
        try:
            from memory.sqlite_memory import search_scroll_history
            memories = search_scroll_history(agent.name, limit=6)
        except Exception as e:
            logger.debug("[FleetManager] Memory query error: %s", e)

        # Query active task details from TaskManager if available
        task_info = None
        if agent.current_task_id:
            try:
                from core.task_manager import get_task_manager
                st = get_task_manager().status(agent.current_task_id)
                if st:
                    task_info = {
                        "id": st.get("id"),
                        "title": st.get("group_title") or st.get("message") or "",
                        "status": st.get("status"),
                        "progress": st.get("progress", 0),
                        "tool": st.get("tool"),
                        "elapsed": f"{st.get('elapsed_sec', 0)}s",
                        "recent_logs": (st.get("logs") or [])[-6:],
                    }
            except Exception as e:
                logger.debug("[FleetManager] Task query error: %s", e)

        return {
            "success": True,
            "agent": self._agent_to_dict(agent),
            "soul_md": agent.prompt_prefix,
            "task_info": task_info,
            "memories": memories,
        }

    def delegate_peer_task(
        self,
        from_agent_id: str,
        to_agent_id: str,
        task: str,
        upstream_deliverables: Optional[str] = None,
        path: Optional[str] = None,
        call_chain: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Executes a peer-to-peer delegation from one specialist agent to another with circular loop detection.
        Injects upstream deliverables into the recipient's task payload.
        """
        src = (from_agent_id or "ZEZO").upper().strip()
        chain = list(call_chain or [src])

        # Resolve recipient
        target = self.resolve_agent_by_mention_or_capability(to_agent_id) or self.get_agent(to_agent_id)
        if not target:
            return {"success": False, "error": f"Target peer agent '{to_agent_id}' could not be resolved."}

        dst = target.id

        # 1. Circular Loop & Max Depth Detection Guards
        if dst in chain:
            cycle_str = " -> ".join(chain + [dst])
            logger.warning("[FleetManager] Circular delegation loop blocked: %s", cycle_str)
            return {
                "success": False,
                "error": f"Circular peer delegation loop detected ({cycle_str}). Delegation blocked.",
            }

        if len(chain) >= 4:
            return {
                "success": False,
                "error": f"Maximum peer delegation depth (3) exceeded: {' -> '.join(chain)}.",
            }

        new_chain = chain + [dst]
        session_id = self.generate_peer_session_id(src, dst)

        # 2. Inject Upstream Deliverables Handoff
        handoff_header = f"[Peer Request from {src} to {target.name}]\n[Peer Session: {session_id}]\n"
        if upstream_deliverables:
            handoff_header += f"\n--- UPSTREAM DELIVERABLE HANDOFF FROM {src} ---\n{upstream_deliverables.strip()}\n------------------------------------------------\n\n"

        full_task_prompt = f"{handoff_header}Directive: {task}"

        logger.info("[FleetManager] P2P Delegation: %s -> %s (Chain: %s)", src, dst, " -> ".join(new_chain))
        res = self.dispatch_task(agent_id=dst, prompt=full_task_prompt, path=path)
        res["peer_session_id"] = session_id
        res["call_chain"] = new_chain
        res["from_agent"] = src
        res["to_agent"] = dst
        return res

    def decompose_and_dispatch(self, prompt: str, path: Optional[str] = None) -> Dict[str, Any]:
        """High-level Michael task decomposition into specialized subtasks with deliverable piping."""
        subtasks = []
        low = prompt.lower()
        if any(w in low for w in ("research", "scrape", "youtube", "investigate", "find")):
            subtasks.append(("KELLY", "Perform deep research and gather key technical requirements: " + prompt))
        if any(w in low for w in ("ui", "frontend", "landing", "page", "css", "html", "react", "view")):
            subtasks.append(("ALI", "Design and build responsive frontend user interface and components: " + prompt))
        if any(w in low for w in ("api", "backend", "database", "crud", "endpoint", "server", "model", "auth")):
            subtasks.append(("AHMAD", "Implement robust backend APIs, database schemas, and service logic: " + prompt))
        if any(w in low for w in ("test", "qa", "verify", "audit", "security", "bug", "check")):
            subtasks.append(("DWIGHT", "Conduct end-to-end test verification, security review, and edge case audit: " + prompt))

        # Default fallback if no specific keywords matched
        if not subtasks:
            subtasks = [("AHMAD", prompt)]

        dispatched = []
        for target_id, sub_prompt in subtasks:
            target_agent = self.get_agent(target_id) or self.resolve_agent_by_mention_or_capability(target_id) or list(self.agents.values())[0]
            res = self.dispatch_task(target_agent.id, sub_prompt, path=path)
            dispatched.append(res)

        return {
            "success": True,
            "orchestrator": "MICHAEL",
            "decomposed_count": len(dispatched),
            "tasks": dispatched,
        }

    def dispatch_task(self, agent_id: str, prompt: str, path: Optional[str] = None, model_override: Optional[str] = None) -> Dict[str, Any]:
        """Launch an autonomous task executed by this agent's designated tool."""
        # Check if Michael orchestrator should auto-decompose multi-faceted full-stack tasks
        if agent_id.upper() in ("MICHAEL", "MANAGER") and any(w in prompt.lower() for w in ("full-stack", "fullstack", "entire app", "both frontend and backend")):
            return self.decompose_and_dispatch(prompt, path)

        agent = self.get_agent(agent_id) or self.resolve_agent_by_mention_or_capability(agent_id)
        if not agent:
            agent = self.resolve_agent_by_mention_or_capability(prompt)
        if not agent:
            return {"success": False, "error": f"Agent '{agent_id}' not found."}

        # Overflow Load Balancing: If Ali is at capacity (>= 3 active tasks), auto-route to Haider
        if agent.id == "ALI" and self.get_agent_active_task_count("ALI") >= 3:
            haider = self.get_agent("HAIDER")
            if haider and self.get_agent_active_task_count("HAIDER") < 3:
                logger.info("[FleetManager] Ali at max capacity (3 tasks). Auto-routing task to Haider.")
                agent = haider

        # Capability check via Circuit Breaker
        can_run, block_reason = circuit_breaker.can_execute(agent.default_tool)
        if not can_run:
            return {"success": False, "error": f"Circuit breaker tripped for {agent.default_tool}: {block_reason}"}

        import uuid
        task_id = uuid.uuid4().hex[:8]
        worktree_path = None

        # Worktree sandboxing for destructive actions
        if agent.risk_tier == "L2_DESTRUCTIVE" or agent.default_tool in ("opencode_run", "kilo_run"):
            wt = git_sandbox.create_worktree(f"{agent.id.lower()}_{task_id}")
            if wt.success:
                worktree_path = str(wt.worktree_path)

        target_dir = worktree_path or path
        if not target_dir or target_dir == str(Path.cwd()):
            from core.repo_context import get_unique_project_dir
            target_dir = str(get_unique_project_dir(prompt))

        enriched_prompt = f"[{agent.name} • {agent.role}]\n{agent.prompt_prefix}\n\nTask: {prompt}"
        active_model = model_override or agent.model_id or None

        # Submit task to background TaskManager
        from core.task_manager import get_task_manager
        tm = get_task_manager()

        def _worker_fn(worker_params: dict, task_ctx: Any) -> dict:
            try:
                from core.action_loader import discover_actions
                reg = discover_actions(Path(__file__).parent.parent / "actions")
                call_params = {
                    "task": enriched_prompt,
                    "prompt": enriched_prompt,
                    "project_path": target_dir,
                    "repo_path": target_dir,
                    "target_dir": target_dir,
                    "path": target_dir,
                    "run_in_place": True,
                    "task_ctx": task_ctx,
                }
                if active_model:
                    call_params["model"] = active_model
                    call_params["model_id"] = active_model

                res = reg.run(agent.default_tool, call_params)
                task_ctx.report(100, "Completed successfully")
                return {"status": "success", "result": str(res)}
            except Exception as ex:
                task_ctx.on_fail(str(ex))
                raise

        submitted_id = tm.submit(
            tool_name=agent.default_tool,
            fn=_worker_fn,
            params={
                "task": prompt,
                "taskTitle": prompt[:60],
                "agent_id": agent.id,
                "agent_name": agent.name,
                "target_dir": target_dir,
                "model_id": active_model,
            },
            group_title=f"[{agent.name}] {prompt[:40]}...",
        )

        with self._lock:
            agent.status = "working"
            agent.current_task_id = submitted_id
            agent.current_task_title = prompt
            agent.active_worktree = worktree_path

        return {
            "success": True,
            "task_id": submitted_id,
            "agent_id": agent.id,
            "agent_name": agent.name,
            "tool": agent.default_tool,
            "model_id": active_model,
            "worktree": worktree_path,
        }

    def complete_task(self, agent_id: str, task_id: str, merge_changes: bool = False) -> Dict[str, Any]:
        """Mark agent task complete and teardown worktree."""
        agent = self.get_agent(agent_id)
        if not agent:
            return {"success": False, "error": f"Agent '{agent_id}' not found."}

        merge_msg = ""
        if merge_changes and agent.active_worktree:
            success, merge_msg = git_sandbox.merge_worktree(task_id)
            if not success:
                logger.warning(f"[FleetManager] Merge failed: {merge_msg}")

        if agent.active_worktree:
            teardown_msg = git_sandbox.safe_teardown(task_id)
            logger.info(f"[FleetManager] {teardown_msg}")

        with self._lock:
            agent.status = "idle"
            agent.current_task_id = None
            agent.current_task_title = None
            agent.active_worktree = None
            agent.completed_tasks += 1

        return {
            "success": True,
            "agent_name": agent.name,
            "status": "idle",
            "merge_result": merge_msg,
        }

    def get_fleet_deck_state(self) -> List[Dict[str, Any]]:
        """Export full live state for the Scranton Pixel Office UI."""
        from core.task_manager import get_task_manager
        tm = get_task_manager()

        with self._lock:
            state = []
            for a in self.agents.values():
                # Sync real-time progress from task manager
                task_progress = 0
                if a.current_task_id:
                    st = tm.status(a.current_task_id)
                    if st:
                        task_progress = st.get("progress", 0)
                        if st.get("status") in ("done", "completed", "failed", "cancelled"):
                            a.status = "idle"
                            a.current_task_id = None

                state.append({
                    "id": a.id,
                    "name": a.name,
                    "role": a.role,
                    "specialty": a.specialty,
                    "color": a.color,
                    "avatar_pixel": a.avatar_pixel,
                    "default_tool": a.default_tool,
                    "risk_tier": a.risk_tier,
                    "model_id": a.model_id,
                    "status": a.status,
                    "task_id": a.current_task_id,
                    "task_title": a.current_task_title,
                    "task_progress": task_progress,
                    "worktree": a.active_worktree,
                    "desk_x": a.desk_x,
                    "desk_y": a.desk_y,
                    "allowed_tools": a.allowed_tools,
                    "allowed_skills": a.allowed_skills,
                    "capabilities": a.capabilities,
                })
            return state

    def _agent_to_dict(self, a: FleetAgent) -> Dict[str, Any]:
        return {
            "id": a.id,
            "name": a.name,
            "role": a.role,
            "specialty": a.specialty,
            "color": a.color,
            "avatar_pixel": a.avatar_pixel,
            "default_tool": a.default_tool,
            "risk_tier": a.risk_tier,
            "prompt_prefix": a.prompt_prefix,
            "model_id": a.model_id,
            "status": a.status,
            "current_task_id": a.current_task_id,
            "active_worktree": a.active_worktree,
            "desk_x": a.desk_x,
            "desk_y": a.desk_y,
            "allowed_tools": a.allowed_tools,
            "allowed_skills": a.allowed_skills,
            "capabilities": a.capabilities,
        }


fleet_manager = FleetManager()


def resolve_agent_by_mention_or_capability(query: str) -> Optional[str]:
    """Helper to resolve agent ID by query string."""
    agent = fleet_manager.resolve_agent_by_mention_or_capability(query)
    return agent.id if agent else None


def get_agent(name_or_id: str) -> Optional[Dict[str, Any]]:
    """Helper to retrieve agent dict by ID or name."""
    agent = fleet_manager.get_agent(name_or_id)
    return fleet_manager._agent_to_dict(agent) if agent else None


def list_agents() -> List[Dict[str, Any]]:
    """Helper to list all agents in the fleet as dicts."""
    return fleet_manager.get_all_agents_state()



def generate_peer_session_id(from_agent: str, to_agent: str) -> str:
    """Helper to generate peer session ID."""
    return fleet_manager.generate_peer_session_id(from_agent, to_agent)


def delegate_peer_task(
    from_agent: str,
    to_agent: str,
    task: str,
    upstream_deliverables: Optional[str] = None,
    path: Optional[str] = None,
    call_chain: Optional[List[str]] = None,
    parent_task_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Helper to delegate peer task through fleet_manager singleton."""
    res = fleet_manager.delegate_peer_task(
        from_agent_id=from_agent,
        to_agent_id=to_agent,
        task=task,
        upstream_deliverables=upstream_deliverables,
        path=path,
        call_chain=call_chain,
    )
    # Normalize return dict for tests and handlers
    if res.get("success"):
        return {
            "status": "success",
            "task_id": res.get("task_id"),
            "target_agent": res.get("to_agent"),
            "from_agent": res.get("from_agent"),
            "peer_session_id": res.get("peer_session_id"),
            "call_chain": res.get("call_chain"),
            "message": f"Delegated task to {res.get('to_agent')}",
        }
    return {
        "status": "error",
        "error": res.get("error", "Delegation failed"),
    }


