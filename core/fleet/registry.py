from __future__ import annotations

import json
import logging
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
    allowed_tools: List[str] = field(default_factory=list)
    allowed_skills: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    is_core: bool = False
    engine: str = ""
    status: str = "idle"
    current_task_id: Optional[str] = None
    current_task_title: Optional[str] = None
    task_progress: int = 0
    desk_x: int = 0
    desk_y: int = 0
    active_worktree: Optional[str] = None
    completed_tasks: int = 0
    recent_logs: List[str] = field(default_factory=list)
    chat_history: List[Dict[str, Any]] = field(default_factory=list)
    soul_markdown: str = ""

    def __post_init__(self):
        if not self.soul_markdown and self.prompt_prefix:
            self.soul_markdown = self.prompt_prefix
        elif self.soul_markdown and not self.prompt_prefix:
            self.prompt_prefix = self.soul_markdown


class FleetRegistry:
    """Manages fleet registry, agent configurations, personas, desk assignments, and persistence."""

    def __init__(self, config_path: Optional[Path] = None):
        self._lock = threading.RLock()
        if config_path:
            self.config_path = Path(config_path)
        else:
            self.config_path = Path(__file__).resolve().parent.parent.parent / "config" / "fleet_agents.json"
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
                    prompt_prefix = info.get("prompt_prefix", "")
                    soul_markdown = info.get("soul_markdown") or prompt_prefix
                    self.agents[uid] = FleetAgent(
                        id=uid,
                        name=info.get("name", agent_id),
                        role=info.get("role", ""),
                        specialty=info.get("specialty", ""),
                        color=info.get("color", "#3b82f6"),
                        avatar_pixel=info.get("avatar_pixel", f"{uid.lower()}_pixel.png"),
                        default_tool=info.get("default_tool", "opencode_run"),
                        risk_tier=info.get("risk_tier", "L0_READ_ONLY"),
                        prompt_prefix=prompt_prefix,
                        model_id=info.get("model_id", ""),
                        desk_x=info.get("desk_x", 0),
                        desk_y=info.get("desk_y", 0),
                        active_worktree=info.get("active_worktree") or info.get("worktree"),
                        allowed_tools=list(info.get("allowed_tools") or []),
                        allowed_skills=list(info.get("allowed_skills") or []),
                        capabilities=list(info.get("capabilities") or []),
                        is_core=bool(info.get("is_core", uid in CORE_AGENT_IDS)),
                        engine=str(info.get("engine", "")),
                        chat_history=list(info.get("chat_history") or []),
                        soul_markdown=soul_markdown,
                    )
        except Exception as e:
            logger.error("[FleetRegistry] Failed to load fleet config: %s", e)

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
                        "soul_markdown": a.soul_markdown or a.prompt_prefix,
                    }
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(export, f, indent=2)
            return True
        except Exception as e:
            logger.error("[FleetRegistry] Failed to save fleet config: %s", e)
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
        try:
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
        except Exception as e:
            logger.debug("[FleetRegistry] Error checking active tasks: %s", e)
            return 0

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

            soul_md = str(data.get("soul_markdown") or prompt_prefix).strip()

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
                chat_history=existing.chat_history if existing else [],
                soul_markdown=soul_md,
            )
            self.agents[clean_id] = agent
            ok = self._save_fleet()

        self._broadcast_event("fleet_updated", {"action": "hire", "agent": self._agent_to_dict(agent)})

        return {"success": ok, "agent": self._agent_to_dict(agent)}

    def save_agent_soul(self, agent_id: str, soul_prompt: str) -> Dict[str, Any]:
        """Update system prompt / soul.md for a specific agent."""
        agent = self.get_agent(agent_id)
        if not agent:
            return {"success": False, "error": f"Agent '{agent_id}' not found."}

        with self._lock:
            agent.prompt_prefix = soul_prompt.strip()
            agent.soul_markdown = soul_prompt.strip()
            ok = self._save_fleet()

        self._broadcast_event("fleet_updated", {"action": "soul_update", "agent_id": agent.id})

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
                    logger.warning("[FleetRegistry] Worktree teardown during delete_agent error: %s", ex)

            del self.agents[key]
            ok = self._save_fleet()

        self._broadcast_event("fleet_updated", {"action": "fire", "deleted_id": key})

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
            logger.debug("[FleetRegistry] Memory query error: %s", e)

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
                logger.debug("[FleetRegistry] Task query error: %s", e)

        return {
            "success": True,
            "agent": self._agent_to_dict(agent),
            "soul_md": agent.soul_markdown or agent.prompt_prefix,
            "task_info": task_info,
            "memories": memories,
        }

    def get_fleet_deck_state(self) -> List[Dict[str, Any]]:
        """Export full live state for the Scranton Pixel Office UI."""
        try:
            from core.task_manager import get_task_manager
            tm = get_task_manager()
        except Exception as e:
            logger.debug("[FleetRegistry] Failed to obtain task manager: %s", e)
            tm = None

        with self._lock:
            self.refresh_if_modified()
            state = []
            for a in self.agents.values():
                # Sync real-time progress from task manager
                task_progress = 0
                if tm and a.current_task_id:
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
                    "soul_markdown": a.soul_markdown or a.prompt_prefix,
                    "chat_history": a.chat_history,
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
            "soul_markdown": a.soul_markdown or a.prompt_prefix,
            "chat_history": a.chat_history,
        }

    def _broadcast_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Thread-safe broadcast of fleet and task events to WebSocket UI and log bus."""
        try:
            from core.ui_server import get_ui_server
            get_ui_server().broadcast(event_type, data)
        except Exception as e:
            logger.debug("[FleetRegistry] UI broadcast skipped: %s", e)
        try:
            from core.log_bus import emit_tool_micro_event
            emit_tool_micro_event(event_type, "fleet_manager", data)
        except Exception:
            pass


fleet_registry = FleetRegistry()
