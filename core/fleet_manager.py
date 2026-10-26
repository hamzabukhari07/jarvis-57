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
CORE_AGENT_IDS: set[str] = {"MICHAEL"}
VALID_TOOLS: set[str] = {
    "opencode_run", "kilo_run", "quick_snippet", "code_helper",
    "antigravity_run", "groq", "extract_design_system", "agent_reach",
    "web_read_page", "web_reader", "web_search", "browser_control",
    "file_processor", "file_controller", "fleet_control", "task_status",
    "reverse_engineer",
}


def _infer_agent_defaults(role: str, specialty: str) -> Dict[str, Any]:
    """Smartly infers default tool, permissions, and skills from persona keywords."""
    text = f"{role} {specialty}".lower()

    if any(k in text for k in ("research", "web", "scrape", "transcript", "video", "youtube", "media", "search")):
        return {
            "engine": "",
            "default_tool": "agent_reach",
            "allowed_tools": ["agent_reach", "web_search", "web_read_page", "web_reader", "file_processor"],
            "allowed_skills": ["web_scraper", "social_research", "web_research_pipeline"],
            "capabilities": ["web_research", "media_extraction", "content_analysis"],
        }
    if any(k in text for k in ("frontend", "ui", "design", "css", "tailwind", "layout", "animation", "react", "html")):
        return {
            "engine": "antigravity",
            "default_tool": "antigravity_run",
            "allowed_tools": ["antigravity_run", "extract_design_system", "browser_control", "file_processor", "file_controller"],
            "allowed_skills": ["website_build", "multi_agent_collaboration", "make_plan"],
            "capabilities": ["web_design", "frontend_coding", "ui_refactor", "animations"],
        }
    if any(k in text for k in ("refactor", "qa", "test", "audit", "clean code", "bug hunt")):
        return {
            "engine": "kilo",
            "default_tool": "kilo_run",
            "allowed_tools": ["kilo_run", "quick_snippet", "file_processor", "file_controller"],
            "allowed_skills": ["kilo_code", "multi_agent_collaboration", "make_plan", "git_workflow"],
            "capabilities": ["code_refactor", "qa_testing", "security_audit", "complexity_reduction"],
        }
    return {
        "engine": "opencode",
        "default_tool": "opencode_run",
        "allowed_tools": ["opencode_run", "quick_snippet", "file_processor", "file_controller"],
        "allowed_skills": ["opencode", "multi_agent_collaboration", "make_plan", "git_workflow"],
        "capabilities": ["backend_architecture", "api_development", "database_design"],
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
    is_core: bool = False
    engine: str = ""


class FleetManager:
    """Orchestrates named specialist agent fleet, isolated worktrees, and live deck state."""

    def __init__(self, config_path: Optional[Path] = None):
        self._lock = threading.RLock()
        self.config_path = config_path or (Path(__file__).parent.parent / "config" / "fleet_agents.json")
        self.agents: Dict[str, FleetAgent] = {}
        self._last_mtime: float = 0.0
        self._load_fleet()

    def refresh_if_modified(self) -> bool:
        """Reload fleet config if fleet_agents.json was modified on disk."""
        if not self.config_path.exists():
            return False
        try:
            mtime = self.config_path.stat().st_mtime
            if mtime != self._last_mtime:
                self._load_fleet()
                return True
        except OSError:
            pass
        return False

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
            self._last_mtime = self.config_path.stat().st_mtime
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
                        default_tool=info.get("default_tool", "opencode_run"),
                        risk_tier=info.get("risk_tier", "L0_READ_ONLY"),
                        prompt_prefix=info.get("prompt_prefix", ""),
                        model_id=info.get("model_id", ""),
                        desk_x=info.get("desk_x", 0),
                        desk_y=info.get("desk_y", 0),
                        active_worktree=info.get("active_worktree") or info.get("worktree"),
                        allowed_tools=list(info.get("allowed_tools") or []),
                        allowed_skills=list(info.get("allowed_skills") or []),
                        capabilities=list(info.get("capabilities") or []),
                        is_core=bool(info.get("is_core", uid in CORE_AGENT_IDS)),
                        engine=str(info.get("engine", "")),
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
                        "worktree": a.active_worktree,
                        "active_worktree": a.active_worktree,
                        "allowed_tools": a.allowed_tools,
                        "allowed_skills": a.allowed_skills,
                        "capabilities": a.capabilities,
                        "is_core": a.is_core or (a.id in CORE_AGENT_IDS),
                        "engine": a.engine,
                    }
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(export, f, indent=2)
            return True
        except Exception as e:
            logger.error("[FleetManager] Failed to save fleet config: %s", e)
            return False

    def get_agent(self, name_or_id: str) -> Optional[FleetAgent]:
        key = name_or_id.upper().strip()
        alias_map = {"ALI": "VERVE", "HAIDER": "FLUX"}
        lookup_key = alias_map.get(key, key)
        with self._lock:
            self.refresh_if_modified()
            if lookup_key in self.agents:
                return self.agents[lookup_key]
            if key in self.agents:
                return self.agents[key]
            for a in self.agents.values():
                if lookup_key == a.name.upper() or lookup_key.startswith(a.name.upper()) or lookup_key in a.name.upper().split():
                    return a
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

        # 1. Direct Name / ID match in words (e.g. 'Ali', 'Ahmad', 'Dwight', 'Pam', 'Oscar', 'Kelly', 'Michael', 'Jim')
        stop_words = {"agent", "agents", "app", "file", "task", "tasks", "tool", "tools", "the", "a", "an", "is", "for", "to", "in", "on", "and", "or", "not"}
        with self._lock:
            self.refresh_if_modified()
            for w in words:
                if w.lower() in stop_words:
                    continue
                w_up = w.upper()
                for agent_id, agent in self.agents.items():
                    if w_up == agent_id.upper() or w.lower() == agent.name.lower():
                        return agent
                if w_up in ("OSCAR", "JIM", "STANLEY", "CREED", "ANGELA", "TOBY", "ANDY", "RYAN", "DARRELL", "KELLY"):
                    return FleetAgent(id=w_up, name=w.title(), role="Fleet Specialist", specialty="General task execution", color="#eab308", avatar_pixel="pixel.png", default_tool="agent_reach" if w_up == "KELLY" else "opencode_run", risk_tier="L0_READ_ONLY", prompt_prefix="")

        low = q.lower()

        # 2. Known Role / Alias Mapping
        role_map = {
            "manager": "MICHAEL",
            "orchestrator": "MICHAEL",
            "frontend": "VERVE",
            "ui": "VERVE",
            "designer": "VERVE",
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
            "developer": "DEVDYNAMO",
            "scaffold": "DEVDYNAMO",
            "rebuild": "DEVDYNAMO",
        }
        for alias, agent_id in role_map.items():
            if re.search(r"\b" + re.escape(alias) + r"\b", low):
                agent = self.get_agent(agent_id)
                if agent:
                    return agent
                if agent_id in ("OSCAR", "JIM", "STANLEY", "CREED", "ANGELA", "TOBY", "KELLY"):
                    return FleetAgent(id=agent_id, name=agent_id.title(), role="Specialist", specialty="General", color="#eab308", avatar_pixel="pixel.png", default_tool="opencode_run", risk_tier="L0_READ_ONLY", prompt_prefix="")

        # 3. Domain Fallback Heuristics
        if any(w in low for w in ("token", "tokens", "palette", "design system", "extract design")):
            return self.get_agent("PAM")
        if any(w in low for w in ("html", "css", "landing", "page", "react", "tailwind", "component", "studio", "ui", "frontend", "website", "portfolio", "web-project")):
            verve = self.get_agent("VERVE") or self.get_agent("ALI")
            flux = self.get_agent("FLUX") or self.get_agent("HAIDER")
            if verve and self.get_agent_active_task_count(verve.id) >= 3:
                if flux and self.get_agent_active_task_count(flux.id) < 3:
                    return flux
            return verve or flux
        if any(w in low for w in ("fastapi", "postgres", "sql", "api", "endpoint", "schema", "microservice", "auth", "backend", "database")):
            return self.get_agent("AHMAD")
        if any(w in low for w in ("test", "verify", "audit", "regression", "pytest", "edge case", "security")):
            return self.get_agent("DWIGHT")
        if any(w in low for w in ("scrape", "transcribe", "summary", "web search", "market research", "research", "social", "trend", "trends")):
            return self.get_agent("KELLY") or FleetAgent(id="KELLY", name="Kelly", role="Research Specialist", specialty="Research", color="#e11d48", avatar_pixel="pixel.png", default_tool="agent_reach", risk_tier="L0_READ_ONLY", prompt_prefix="")

        # 4. Default dispatch fallback: Verve for UI/frontend, Ahmad for general coding
        if any(w in low for w in ("build", "create", "make", "design", "develop", "code", "program")):
            verve = self.get_agent("VERVE") or self.get_agent("ALI")
            flux = self.get_agent("FLUX") or self.get_agent("HAIDER")
            if verve and self.get_agent_active_task_count(verve.id) >= 3:
                if flux and self.get_agent_active_task_count(flux.id) < 3:
                    return flux
            return verve or flux or self.get_agent("AHMAD")
        return None

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

        name_str = str(data.get("name") or clean_id.title()).strip()[:40] or clean_id.title()
        role_str = str(data.get("role") or "Autonomous Specialist").strip()[:80]
        specialty_str = str(data.get("specialty") or role_str).strip()[:120]
        model_id = str(data.get("model_id") or "").strip()

        inferred = _infer_agent_defaults(role_str, specialty_str)

        engine_to_tool = {
            "antigravity": "antigravity_run",
            "opencode": "opencode_run",
            "kilo": "kilo_run",
        }
        tool_to_engine = {
            "antigravity_run": "antigravity",
            "opencode_run": "opencode",
            "kilo_run": "kilo",
        }

        raw_engine = str(data.get("engine") or "").strip().lower()
        raw_tool = str(data.get("default_tool") or "").strip().lower()

        if raw_engine in tool_to_engine:
            if not raw_tool:
                raw_tool = raw_engine
            raw_engine = tool_to_engine[raw_engine]

        if raw_tool in engine_to_tool:
            if not raw_engine:
                raw_engine = raw_tool
            raw_tool = engine_to_tool[raw_tool]

        tool = raw_tool
        if tool not in VALID_TOOLS and not tool.endswith("_run") and not tool.endswith("_agent"):
            tool = ""

        with self._lock:
            existing = self.agents.get(clean_id)
            engine = raw_engine
            if not engine:
                engine = inferred.get("engine", "")
                if not engine and tool in tool_to_engine:
                    engine = tool_to_engine[tool]
                elif existing and existing.engine:
                    engine = existing.engine
                else:
                    engine = ""

            if not tool:
                if engine and engine in engine_to_tool:
                    tool = engine_to_tool[engine]
                elif existing and existing.default_tool:
                    tool = existing.default_tool
                else:
                    tool = inferred["default_tool"]

            risk_tier = str(data.get("risk_tier") or (existing.risk_tier if existing else "")).upper().strip()
            if risk_tier not in VALID_RISK_TIERS:
                risk_tier = "L1_MUTATION" if tool in ("kilo_run", "opencode_run", "antigravity_run") else "L0_READ_ONLY"

            color_str = str(data.get("color") or (existing.color if existing else "")).strip()
            if not re.match(r"^#[0-9a-fA-F]{6}$", color_str):
                color_str = "#3b82f6"

            desk_x, desk_y = self._allocate_desk(
                existing,
                int(data.get("desk_x", 0)),
                int(data.get("desk_y", 0))
            )

            prompt_prefix = str(
                data.get("prompt_prefix")
                or (existing.prompt_prefix if existing else f"You are {name_str}, an autonomous fleet specialist focusing on {specialty_str}.")
            ).strip()

            raw_allowed_tools = data.get("allowed_tools")
            if raw_allowed_tools is not None and len(raw_allowed_tools) > 0:
                allowed_tools = list(raw_allowed_tools)
            elif existing and existing.allowed_tools:
                allowed_tools = list(existing.allowed_tools)
            else:
                allowed_tools = list(inferred["allowed_tools"])

            raw_allowed_skills = data.get("allowed_skills")
            if raw_allowed_skills is not None and len(raw_allowed_skills) > 0:
                allowed_skills = list(raw_allowed_skills)
            elif existing and existing.allowed_skills:
                allowed_skills = list(existing.allowed_skills)
            else:
                allowed_skills = list(inferred["allowed_skills"])

            raw_capabilities = data.get("capabilities")
            if raw_capabilities is not None and len(raw_capabilities) > 0:
                capabilities = list(raw_capabilities)
            elif existing and existing.capabilities:
                capabilities = list(existing.capabilities)
            else:
                capabilities = list(inferred["capabilities"])

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
                active_worktree=str(data.get("active_worktree") or data.get("worktree") or data.get("path") or (existing.active_worktree if existing else "")).strip() or None,
                allowed_tools=allowed_tools,
                allowed_skills=allowed_skills,
                capabilities=capabilities,
                is_core=existing.is_core if existing else (clean_id in CORE_AGENT_IDS),
                engine=engine,
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
            matched_key = None
            if key in self.agents:
                matched_key = key
            else:
                for k, a in self.agents.items():
                    if a.name.upper().strip() == key or a.id.upper().strip() == key or k.upper().strip() == key:
                        matched_key = k
                        break

            if not matched_key:
                return {"success": False, "error": f"Agent '{agent_id}' not found."}

            key = matched_key
            if key in CORE_AGENT_IDS:
                return {"success": False, "error": f"Cannot decommission core builtin agent '{key}'."}

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
        scope_type: Optional[str] = None,
        entity_content: Optional[str] = None,
        tech_stack: Optional[str] = None,
        color_theme: Optional[str] = None,
        key_sections: Optional[str] = None,
        confirmed: bool = False,
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

        # 1. Max Depth & Circular Loop Detection Guards
        if len(chain) >= 4:
            return {
                "success": False,
                "error": f"Maximum peer delegation depth (3) exceeded: {' -> '.join(chain)}.",
            }

        if dst in chain:
            cycle_str = " -> ".join(chain + [dst])
            logger.warning("[FleetManager] Circular delegation loop blocked: %s", cycle_str)
            return {
                "success": False,
                "error": f"Circular peer delegation loop detected ({cycle_str}). Delegation blocked.",
            }

        new_chain = chain + [dst]
        session_id = self.generate_peer_session_id(src, dst)

        # 2. Inject Upstream Deliverables Handoff
        handoff_header = f"[Peer Request from {src} to {target.name}]\n[Peer Session: {session_id}]\n"
        if upstream_deliverables:
            handoff_header += f"\n--- UPSTREAM DELIVERABLE HANDOFF FROM {src} ---\n{upstream_deliverables.strip()}\n------------------------------------------------\n\n"

        full_task_prompt = f"{handoff_header}Directive: {task}"

        logger.info("[FleetManager] P2P Delegation: %s -> %s (Chain: %s)", src, dst, " -> ".join(new_chain))
        res = self.dispatch_task(
            agent_id=dst,
            prompt=full_task_prompt,
            path=path,
            scope_type=scope_type,
            entity_content=entity_content,
            tech_stack=tech_stack,
            color_theme=color_theme,
            key_sections=key_sections,
            confirmed=confirmed,
        )
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
            frontend_id = "VERVE" if self.get_agent("VERVE") else ("FLUX" if self.get_agent("FLUX") else "ALI")
            subtasks.append((frontend_id, "Design and build responsive frontend user interface and components: " + prompt))
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
            res = self.dispatch_task(target_agent.id, sub_prompt, path=path, is_subtask=True)
            dispatched.append(res)

        return {
            "success": True,
            "orchestrator": "MICHAEL",
            "decomposed_count": len(dispatched),
            "tasks": dispatched,
        }

    def _broadcast_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Thread-safe broadcast of fleet and task events to WebSocket UI and log bus."""
        try:
            from core.ui_server import get_ui_server
            get_ui_server().broadcast(event_type, data)
        except Exception as e:
            logger.debug("[FleetManager] UI broadcast skipped: %s", e)
        try:
            from core.log_bus import emit_tool_micro_event
            emit_tool_micro_event(event_type, "fleet_manager", data)
        except Exception:
            pass

    def dispatch_task(
        self,
        agent_id: str,
        prompt: str,
        path: Optional[str] = None,
        model_override: Optional[str] = None,
        is_subtask: bool = False,
        group_id: Optional[str] = None,
        scope_type: Optional[str] = None,
        entity_content: Optional[str] = None,
        tech_stack: Optional[str] = None,
        color_theme: Optional[str] = None,
        key_sections: Optional[str] = None,
        confirmed: bool = False,
    ) -> Dict[str, Any]:
        """Launch an autonomous task executed by this agent's designated tool."""
        # Check if Michael orchestrator should auto-decompose multi-faceted full-stack tasks
        if not is_subtask and agent_id.upper() in ("MICHAEL", "MANAGER") and any(w in prompt.lower() for w in ("full-stack", "fullstack", "entire app", "both frontend and backend")):
            return self.decompose_and_dispatch(prompt, path)

        agent = self.get_agent(agent_id) or self.resolve_agent_by_mention_or_capability(agent_id)
        if not agent:
            registered_names = [f"{a.name} ({a.id})" for a in self.agents.values()]
            return {
                "success": False,
                "error": f"Agent '{agent_id}' is not in the active fleet. Registered agents: {', '.join(registered_names)}",
            }

        # Overflow Load Balancing: If Verve is at capacity (>= 3 active tasks), auto-route to Flux
        if agent.id in ("VERVE", "ALI") and self.get_agent_active_task_count(agent.id) >= 3:
            flux = self.get_agent("FLUX") or self.get_agent("HAIDER")
            if flux and self.get_agent_active_task_count(flux.id) < 3:
                logger.info("[FleetManager] Verve at max capacity (3 tasks). Auto-routing task to Flux.")
                agent = flux

        # Capability check via Circuit Breaker
        check_tool = agent.default_tool
        if not check_tool and agent.engine:
            check_tool = f"{agent.engine}_run"
        can_run, block_reason = circuit_breaker.can_execute(check_tool)
        if not can_run:
            return {"success": False, "error": f"Circuit breaker tripped for {check_tool}: {block_reason}"}

        import uuid
        task_id = uuid.uuid4().hex[:8]
        worktree_name = f"{agent.id.lower()}_{task_id}"
        worktree_path = None

        # Worktree sandboxing for destructive actions
        if agent.risk_tier == "L2_DESTRUCTIVE" or agent.default_tool in ("opencode_run", "kilo_run"):
            wt = git_sandbox.create_worktree(worktree_name)
            if wt.success:
                worktree_path = str(wt.worktree_path)

        target_dir = worktree_path or path
        if not target_dir or target_dir == str(Path.cwd()):
            from core.repo_context import get_unique_project_dir
            target_dir = str(get_unique_project_dir(prompt))

        # Ensure target_dir exists physically on disk before subprocess execution
        try:
            Path(target_dir).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning("[FleetManager] Could not ensure directory %s: %s", target_dir, e)

        # Resolve active procedural skills from agent.allowed_skills
        skills_context = ""
        try:
            from core.skill_loader import get_skill_registry
            registry = get_skill_registry()
            for sk in (agent.allowed_skills or []):
                skill_obj = getattr(registry, "get_skill", lambda s: getattr(registry, "_skills", {}).get(s))(sk)
                if not skill_obj and hasattr(registry, "_skills"):
                    for k, s in registry._skills.items():
                        if k.lower() == str(sk).lower():
                            skill_obj = s
                            break
                if skill_obj and getattr(skill_obj, "instructions", None):
                    skills_context += f"\n\n[ACTIVE SKILL: {skill_obj.name}]\n{skill_obj.instructions}\n"
        except Exception as e:
            logger.debug("[FleetManager] Skill resolution error: %s", e)

        enriched_prompt = f"[{agent.name} • {agent.role}]\n{agent.prompt_prefix}{skills_context}\n\nTask: {prompt}"
        active_model = model_override or agent.model_id or None

        from core.action_loader import discover_actions
        reg = discover_actions(Path(__file__).parent.parent / "actions")
        effective_tool = ""
        if agent.engine and reg.has(f"{agent.engine}_run"):
            effective_tool = f"{agent.engine}_run"
        elif agent.default_tool and reg.has(agent.default_tool):
            effective_tool = agent.default_tool
        else:
            if "code" in prompt.lower() or "build" in prompt.lower() or "app" in prompt.lower():
                effective_tool = "opencode_run"
            elif any(k in prompt.lower() for k in ("research", "transcript", "video", "youtube", "media", "search", "http")):
                effective_tool = "agent_reach" if reg.has("agent_reach") else "web_search"
            else:
                effective_tool = "quick_snippet" if reg.has("quick_snippet") else "opencode_run"

        # Submit task to background TaskManager
        from core.task_manager import get_task_manager
        tm = get_task_manager()

        def _worker_fn(worker_params: dict, task_ctx: Any) -> dict:
            params = worker_params or {}
            task_id = getattr(task_ctx, "task_id", None) or params.get("task_id") or submitted_id
            w_agent_id = params.get("agent_id") or agent.id
            w_agent = self.get_agent(w_agent_id) or agent
            w_agent_name = params.get("agent_name") or w_agent.name
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

                def _reporting_wrapper(prog: int, msg: str = "") -> None:
                    if hasattr(task_ctx, "cancelled") and task_ctx.cancelled():
                        return
                    if orig_report:
                        try:
                            orig_report(prog, msg)
                        except Exception:
                            pass
                    with self._lock:
                        w_agent.task_progress = max(0, min(100, prog))
                        if msg:
                            clean_msg = f"[{prog}%] {msg}"
                            if not w_agent.recent_logs or w_agent.recent_logs[-1] != clean_msg:
                                w_agent.recent_logs.append(clean_msg)
                                if len(w_agent.recent_logs) > 30:
                                    w_agent.recent_logs = w_agent.recent_logs[-30:]
                    self._broadcast_event("task_progress", {
                        "task_id": task_id,
                        "agent_id": w_agent.id,
                        "agent": w_agent_name,
                        "progress": prog,
                        "message": msg,
                    })

                task_ctx.report = _reporting_wrapper

                # Extract URL or target query from prompt if present for specialized tools (agent_reach, web_reader, etc.)
                url_match = re.search(r'https?://[^\s]+', w_prompt)
                extracted_url = url_match.group(0) if url_match else None
                extracted_target = extracted_url or w_prompt

                call_params = {
                    "task": enriched_prompt,
                    "prompt": enriched_prompt,
                    "target": extracted_target,
                    "url": extracted_url,
                    "query": extracted_target,
                    "project_path": target_dir,
                    "repo_path": target_dir,
                    "target_dir": target_dir,
                    "path": target_dir,
                    "run_in_place": True,
                    "task_ctx": task_ctx,
                }
                spec_items = []
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

                if w_tool == "antigravity_run":
                    call_params["scope_type"] = w_scope_type
                    call_params["entity_content"] = w_entity_content
                    call_params["tech_stack"] = w_tech_stack
                    call_params["color_theme"] = w_color_theme
                    call_params["key_sections"] = w_key_sections
                    call_params["confirmed"] = w_confirmed
                if effective_tool == "extract_design_system":
                    call_params["target_file"] = extracted_target
                    call_params["file_path"] = extracted_target
                    call_params["path"] = extracted_target
                    call_params["output_path"] = target_dir

                if active_model:
                    call_params["model"] = active_model
                    call_params["model_id"] = active_model

                res = reg.run(effective_tool, call_params)

                # Check if task was cancelled during action execution
                if hasattr(task_ctx, "cancelled") and task_ctx.cancelled():
                    self.complete_task(agent.id, submitted_id, merge_changes=False, worktree_id=wt_name)
                    self._broadcast_event("task_cancelled", {
                        "task_id": submitted_id,
                        "agent_id": agent.id,
                        "agent": agent.name,
                    })
                    self._broadcast_event("fleet_updated", {"fleet": self.get_fleet_deck_state()})
                    if worktree_path:
                        try:
                            git_sandbox.safe_teardown(wt_name or worktree_name)
                        except Exception:
                            pass
                    return {"status": "cancelled"}

                # Inspect result for explicit errors, missing parameters, or failures
                is_error = False
                err_msg = ""
                if isinstance(res, dict):
                    if res.get("status") in ("error", "failed") or res.get("success") is False:
                        is_error = True
                        err_msg = str(res.get("error") or res.get("message") or "Task execution failed")
                    elif res.get("status") == "cancelled":
                        self.complete_task(agent.id, submitted_id, merge_changes=False, worktree_id=wt_name)
                        self._broadcast_event("task_cancelled", {
                            "task_id": submitted_id,
                            "agent_id": agent.id,
                            "agent": agent.name,
                        })
                        self._broadcast_event("fleet_updated", {"fleet": self.get_fleet_deck_state()})
                        if worktree_path:
                            try:
                                git_sandbox.safe_teardown(wt_name or worktree_name)
                            except Exception:
                                pass
                        return {"status": "cancelled"}
                elif isinstance(res, str):
                    low_res = res.lower().strip()
                    if low_res.startswith("error:") or low_res.startswith("failed:") or low_res.startswith("please provide"):
                        is_error = True
                        err_msg = res

                if is_error:
                    if hasattr(task_ctx, "on_fail"):
                        task_ctx.on_fail(err_msg)
                    self.complete_task(agent.id, submitted_id, merge_changes=False, worktree_id=wt_name)
                    self._broadcast_event("task_failed", {
                        "task_id": submitted_id,
                        "agent_id": agent.id,
                        "agent": agent.name,
                        "error": err_msg,
                    })
                    self._broadcast_event("fleet_updated", {"fleet": self.get_fleet_deck_state()})
                    if worktree_path:
                        try:
                            git_sandbox.safe_teardown(wt_name or worktree_name)
                        except Exception:
                            pass
                    return {"status": "error", "error": err_msg}

                _reporting_wrapper(100, "Completed successfully")
                self.complete_task(agent.id, submitted_id, merge_changes=True, worktree_id=wt_name)
                self._broadcast_event("task_done", {
                    "task_id": submitted_id,
                    "agent_id": agent.id,
                    "agent": agent.name,
                    "summary": f"Completed: {prompt[:60]}",
                })
                self._broadcast_event("fleet_updated", {"fleet": self.get_fleet_deck_state()})
                if worktree_path:
                    try:
                        git_sandbox.safe_teardown(wt_name or worktree_name)
                    except Exception:
                        pass
                return {"status": "success", "result": str(res)}
            except Exception as ex:
                if hasattr(task_ctx, "on_fail"):
                    task_ctx.on_fail(str(ex))
                self.complete_task(agent.id, submitted_id, merge_changes=False, worktree_id=wt_name)
                self._broadcast_event("task_failed", {
                    "task_id": submitted_id,
                    "agent_id": agent.id,
                    "agent": agent.name,
                    "error": str(ex),
                })
                self._broadcast_event("fleet_updated", {"fleet": self.get_fleet_deck_state()})
                if worktree_path:
                    try:
                        git_sandbox.safe_teardown(wt_name or worktree_name)
                    except Exception:
                        pass
                raise

        # If this is a subtask (e.g. Verve scaffolding after REA capture), inherit parent's group for UI merging
        parent_group_id = None
        parent_group_title = None
        if is_subtask and group_id:
            try:
                from core.task_manager import get_task_manager
                _tm = get_task_manager()
                parent_state = _tm._tasks.get(group_id)
                if parent_state:
                    parent_group_id = parent_state.group_id or parent_state.id
                    parent_group_title = parent_state.group_title or parent_state.group_id or "REA Capture"
            except Exception:
                pass

        from core.action_loader import discover_actions
        reg = discover_actions(Path(__file__).parent.parent / "actions")
        effective_tool = ""
        if agent.engine and reg.has(f"{agent.engine}_run"):
            effective_tool = f"{agent.engine}_run"
        elif agent.default_tool and reg.has(agent.default_tool):
            effective_tool = agent.default_tool
        else:
            if "code" in prompt.lower() or "build" in prompt.lower() or "app" in prompt.lower():
                effective_tool = "opencode_run"
            elif any(k in prompt.lower() for k in ("research", "transcript", "video", "youtube", "media", "search", "http")):
                effective_tool = "agent_reach" if reg.has("agent_reach") else "web_search"
            else:
                effective_tool = "quick_snippet" if reg.has("quick_snippet") else "opencode_run"

        submitted_id = tm.submit(
            tool_name=effective_tool,
            fn=_worker_fn,
            params={
                "task": prompt,
                "taskTitle": prompt[:60],
                "enriched_prompt": enriched_prompt,
                "agent_id": agent.id,
                "agent_name": agent.name,
                "target_dir": target_dir,
                "model_id": active_model,
                "is_subtask": is_subtask,
                "worktree_name": worktree_name if worktree_path else None,
                "worktree_path": worktree_path,
                "tool": effective_tool,
                "scope_type": scope_type,
                "entity_content": entity_content,
                "tech_stack": tech_stack,
                "color_theme": color_theme,
                "key_sections": key_sections,
                "confirmed": confirmed,
            },
            group_id=parent_group_id or group_id if is_subtask else None,
            group_title=parent_group_title or (f"[{agent.name}] {prompt[:40]}..." if not is_subtask else None),
            parent_id=group_id if is_subtask else None,
        )

        with self._lock:
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
        self._broadcast_event("fleet_updated", {"fleet": self.get_fleet_deck_state()})

        return {
            "success": True,
            "task_id": submitted_id,
            "agent_id": agent.id,
            "agent_name": agent.name,
            "tool": effective_tool,
            "model_id": active_model,
            "worktree": worktree_path,
        }

    def complete_task(self, agent_id: str, task_id: str, merge_changes: bool = False, worktree_id: Optional[str] = None) -> Dict[str, Any]:
        """Mark agent task complete and teardown worktree."""
        agent = self.get_agent(agent_id)
        if not agent:
            return {"success": False, "error": f"Agent '{agent_id}' not found."}

        wt_id = worktree_id
        if not wt_id and agent.active_worktree:
            try:
                wt_id = Path(agent.active_worktree).name
            except Exception:
                wt_id = task_id
        if not wt_id:
            wt_id = task_id

        merge_msg = ""
        if merge_changes and agent.active_worktree:
            success, merge_msg = git_sandbox.merge_worktree(wt_id)
            if not success:
                logger.warning(f"[FleetManager] Merge failed: {merge_msg}")

        if agent.active_worktree:
            teardown_msg = git_sandbox.safe_teardown(wt_id)
            logger.info(f"[FleetManager] {teardown_msg}")

        with self._lock:
            agent.status = "idle"
            agent.current_task_id = None
            agent.current_task_title = None
            agent.task_progress = 0
            agent.active_worktree = None
            agent.completed_tasks += 1
            agent.recent_logs.append(f"[COMPLETED] Task {task_id} finished")
            if len(agent.recent_logs) > 30:
                agent.recent_logs = agent.recent_logs[-30:]

        self._broadcast_event("fleet_updated", {"fleet": self.get_fleet_deck_state()})

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
            self.refresh_if_modified()
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

                logs = list(a.recent_logs)
                if not logs:
                    logs = [
                        f"[READY] Agent '{a.name}' registered into autonomous fleet",
                        f"[MODEL] Engine: {a.default_tool} | Model: {a.model_id or 'default'}",
                        f"[STATUS] Standby on office deck — ready for task assignment",
                    ]
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
                    "logs": logs,
                    "recent_logs": logs,
                    "allowed_tools": a.allowed_tools,
                    "allowed_skills": a.allowed_skills,
                    "capabilities": a.capabilities,
                    "is_core": a.is_core or (a.id in CORE_AGENT_IDS),
                    "engine": a.engine,
                })
            return state

    def _agent_to_dict(self, a: FleetAgent) -> Dict[str, Any]:
        logs = list(a.recent_logs)
        if not logs:
            logs = [
                f"[READY] Agent '{a.name}' registered into autonomous fleet",
                f"[MODEL] Engine: {a.default_tool} | Model: {a.model_id or 'default'}",
                f"[STATUS] Standby on office deck — ready for task assignment",
            ]
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
            "logs": logs,
            "recent_logs": logs,
            "allowed_tools": a.allowed_tools,
            "allowed_skills": a.allowed_skills,
            "capabilities": a.capabilities,
            "is_core": a.is_core or (a.id in CORE_AGENT_IDS),
            "engine": a.engine,
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
    return fleet_manager.get_fleet_deck_state()



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


