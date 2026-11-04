"""
core/agents/runtime.py - Internal AgentRuntime Execution Loop for ZEZO.

Provides isolated, stateful agent execution:
1. Loads AgentProfile, system prompt / soul persona, conversation history, and working memory.
2. Uses ProviderAdapter for LLM calls with ContextBudget enforcement.
3. Routes ALL agent tool calls strictly through ToolExecutor (choke point) with CallerContext.AGENT.
4. Feeds tool outputs back into the conversation for iterative synthesis.
5. Persists conversation threads and messages in SQLite memory (agent_conversations, agent_messages).
6. Handles cancellations, timeouts, errors, and context limits safely without crashes.

Author: Hamza Bukhari
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.agents.context_budget import ContextBudget
from core.agents.provider_adapter import (
    NormalizedResponse,
    ProviderAdapter,
    ProviderError,
    ProviderType,
)
from core.agents.registry import AgentProfile, get_agent_registry
from core.tool_executor import CallerContext, SecurityAccessDenied, ToolExecutor, get_tool_executor
from memory.sqlite_memory import execute_write, query_db

logger = logging.getLogger("zezo.agent_runtime")


class AgentRuntime:
    """
    Execution engine for internal autonomous agents.
    Manages multi-turn conversation memory, prompt assembly, LLM execution,
    strict choke-point tool routing, and persistence in SQLite.
    """

    def __init__(
        self,
        agent_id: str,
        workspace_root: Optional[str] = None,
        conversation_id: Optional[str] = None,
        provider_adapter: Optional[ProviderAdapter] = None,
        tool_executor: Optional[ToolExecutor] = None,
        context_budget: Optional[ContextBudget] = None,
        engine_override: Optional[str] = None,
        model_override: Optional[str] = None,
    ):
        self.agent_id = (agent_id or "").strip()
        if not self.agent_id:
            raise ValueError("agent_id cannot be empty")

        self.workspace_root = workspace_root
        self.conversation_id = conversation_id
        self.tool_executor = tool_executor or get_tool_executor()

        # Load profile
        registry = get_agent_registry()
        self.profile: Optional[AgentProfile] = registry.get_agent(self.agent_id)
        if not self.profile:
            # Fallback profile if dynamic/unknown
            self.profile = AgentProfile(
                id=self.agent_id,
                name=self.agent_id,
                role="Autonomous Agent",
                specialty="General Assistant",
                risk_tier="L0_READ_ONLY",
            )

        # Detach from the registry's shared AgentProfile before applying overrides.
        # setattr on the registry-owned instance would leak this request's overrides
        # into every later request and into the next _save_agents() write.
        self.profile = replace(self.profile)

        # Apply overrides to runtime profile if provided
        if engine_override:
            clean_eng = engine_override.replace("_run", "").replace("_agent", "")
            setattr(self.profile, "engine", clean_eng)
            setattr(self.profile, "default_tool", f"{clean_eng}_run")
        if model_override:
            setattr(self.profile, "model_id", model_override)

        # Provider adapter
        if provider_adapter is not None:
            self.provider_adapter = provider_adapter
        else:
            # Determine provider & model from profile/defaults
            # AgentProfile exposes model_id, not model. Reading the wrong attribute
            # silently forced every agent onto Gemini regardless of configured model.
            model_name = (
                getattr(self.profile, "model_id", None)
                or getattr(self.profile, "model", None)
                or "gemini-2.5-flash"
            )
            p_type = ProviderType.GEMINI
            if "groq" in model_name.lower():
                p_type = ProviderType.GROQ
            elif "ollama" in model_name.lower():
                p_type = ProviderType.OLLAMA

            budget = context_budget or ContextBudget(provider=p_type.value, model_name=model_name)
            self.provider_adapter = ProviderAdapter(
                provider=p_type,
                model_name=model_name,
                context_budget=budget,
            )

    # -------------------------------------------------------------------------
    # Conversation Persistence
    # -------------------------------------------------------------------------

    def get_or_create_conversation(self, title: Optional[str] = None) -> str:
        """Ensure an active conversation thread exists for this agent."""
        if self.conversation_id:
            rows = query_db(
                "SELECT id FROM agent_conversations WHERE id = ? AND agent_id = ?",
                (self.conversation_id, self.agent_id),
            )
            if rows:
                return self.conversation_id

        # Create a new conversation
        new_id = f"conv_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        conv_title = (title or "New Conversation").strip()

        execute_write(
            """
            INSERT INTO agent_conversations (id, agent_id, title, created_at, updated_at, is_archived, metadata)
            VALUES (?, ?, ?, ?, ?, 0, ?)
            """,
            (new_id, self.agent_id, conv_title, now, now, json.dumps({"creator": "AgentRuntime"})),
        )
        self.conversation_id = new_id
        return new_id

    def load_messages(self, conversation_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Load message history from SQLite ordered by creation time."""
        cid = conversation_id or self.conversation_id
        if not cid:
            return []

        rows = query_db(
            """
            SELECT id, conversation_id, agent_id, role, content, tool_name, tool_args, tool_result, status, created_at
            FROM agent_messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (cid, limit),
        )
        messages = []
        for r in rows:
            messages.append({
                "id": r["id"],
                "conversation_id": r["conversation_id"],
                "agent_id": r["agent_id"],
                "role": r["role"],
                "content": r["content"],
                "tool_name": r["tool_name"],
                "tool_args": json.loads(r["tool_args"]) if r["tool_args"] else None,
                "tool_result": r["tool_result"],
                "status": r["status"],
                "created_at": r["created_at"],
            })
        return messages

    def append_message(
        self,
        role: str,
        content: str,
        tool_name: Optional[str] = None,
        tool_args: Optional[Dict[str, Any]] = None,
        tool_result: Optional[str] = None,
        status: Optional[str] = "completed",
        conversation_id: Optional[str] = None,
    ) -> str:
        """Append an exchange turn to agent_messages and bump updated_at."""
        cid = conversation_id or self.get_or_create_conversation()
        msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        args_json = json.dumps(tool_args) if tool_args is not None else None

        execute_write(
            """
            INSERT INTO agent_messages (
                id, conversation_id, agent_id, role, content,
                tool_name, tool_args, tool_result, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (msg_id, cid, self.agent_id, role, content, tool_name, args_json, tool_result, status, now),
        )

        execute_write(
            "UPDATE agent_conversations SET updated_at = ? WHERE id = ?",
            (now, cid),
        )
        return msg_id

    # -------------------------------------------------------------------------
    # System Persona & Context Assembly
    # -------------------------------------------------------------------------

    def build_system_prompt(self) -> str:
        """Assemble the system persona and runtime guardrails for this agent."""
        display_name = getattr(self.profile, "displayName", None) or getattr(self.profile, "name", self.agent_id)
        role = getattr(self.profile, "role", "") or "Autonomous Agent"
        specialty = getattr(self.profile, "specialty", "") or ""
        soul = getattr(self.profile, "soul_markdown", "") or getattr(self.profile, "prompt_prefix", "") or ""
        risk_tier = getattr(self.profile, "risk_tier", "L0_READ_ONLY")

        prompt = (
            f"You are {display_name}, {role} in the autonomous ZEZO OS fleet.\n"
            f"Your specialty: {specialty}.\n"
            f"Security Tier: {risk_tier}.\n"
        )
        if soul:
            prompt += f"\nPersona & Soul:\n{soul}\n"

        prompt += (
            "\nOperating Rules:\n"
            "- You are in a direct 1-on-1 interaction with Hamza Bukhari (Creator & Lead Architect of ZEZO).\n"
            "- Speak directly in first-person, professional, concise, sharp.\n"
            "- When tools are available and required, call them explicitly.\n"
            "- When tool results are returned, synthesize a helpful, precise response.\n"
            "- If a tool call is denied by security policy, explain the limitation clearly and suggest safe alternatives.\n"
        )
        if self.workspace_root:
            prompt += f"- Active Workspace: {self.workspace_root}\n"

        # Explicit awareness of assigned Task Execution Engine and Task Model
        raw_eng = str(getattr(self.profile, "engine", "") or getattr(self.profile, "default_tool", "") or "").lower()
        if "opencode" in raw_eng:
            engine_label = "OpenCode"
        elif "kilo" in raw_eng:
            engine_label = "Kilo Code"
        elif "antigravity" in raw_eng:
            engine_label = "Antigravity"
        elif raw_eng:
            engine_label = raw_eng.replace("_run", "").replace("_agent", "").title()
        else:
            engine_label = "Antigravity"

        model_label = getattr(self.profile, "model_id", None) or getattr(self.profile, "model", "") or "Default"

        prompt += (
            f"\nAssigned Execution Architecture:\n"
            f"- Assigned Task Execution Engine: {engine_label}\n"
            f"- Assigned Task Model: {model_label}\n"
            f"- Communication Channel: ZEZO Conversational Runtime\n"
            f"- Important: Answer naturally and conversantly according to the user's message. Do NOT dump your engine, model, security tier, workspace path, or architectural specs into your reply unless Hamza specifically asks about them. ONLY recite these details when explicitly asked 'what engine are you using', 'what model', or during system verification.\n"
        )

        return prompt

    # -------------------------------------------------------------------------
    # Core Step / Run Loop
    # -------------------------------------------------------------------------

    def step(
        self,
        user_input: str,
        conversation_id: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tool_iterations: int = 3,
    ) -> Dict[str, Any]:
        """
        Execute a single synchronous step of conversational reasoning with tool execution loop.
        """
        cid = conversation_id or self.get_or_create_conversation()

        # 1. Record user turn
        self.append_message(role="user", content=user_input, conversation_id=cid)

        # 2. Build history for provider adapter
        raw_history = self.load_messages(conversation_id=cid)
        messages: List[Dict[str, Any]] = []
        for m in raw_history:
            entry: Dict[str, Any] = {"role": m["role"], "content": m["content"]}
            if m.get("tool_name"):
                entry["tool_name"] = m["tool_name"]
            if m.get("tool_result"):
                entry["tool_result"] = m["tool_result"]
            messages.append(entry)

        system_prompt = self.build_system_prompt()
        tool_executions_log: List[Dict[str, Any]] = []
        final_reply = ""

        # Multi-turn tool feedback loop (bounded)
        for iteration in range(max_tool_iterations + 1):
            try:
                norm_resp = self.provider_adapter.execute(
                    messages=messages,
                    system_prompt=system_prompt,
                    tools=tools,
                )
            except ProviderError as pe:
                err_text = f"LLM Provider Error: {pe.message}"
                logger.error("[AgentRuntime] %s for agent %s", err_text, self.agent_id)
                self.append_message(role="assistant", content=err_text, status="failed", conversation_id=cid)
                return {
                    "success": False,
                    "agent_id": self.agent_id,
                    "conversation_id": cid,
                    "reply": err_text,
                    "error": pe.message,
                    "tool_executions": tool_executions_log,
                }
            except Exception as e:
                err_text = f"Unexpected execution error: {str(e)}"
                logger.exception("[AgentRuntime] %s", err_text)
                self.append_message(role="assistant", content=err_text, status="failed", conversation_id=cid)
                return {
                    "success": False,
                    "agent_id": self.agent_id,
                    "conversation_id": cid,
                    "reply": err_text,
                    "error": str(e),
                    "tool_executions": tool_executions_log,
                }

            final_reply = norm_resp.content

            # Check if LLM requested tool calls
            if not norm_resp.tool_calls or iteration >= max_tool_iterations:
                break

            # Execute tool calls strictly through centralized ToolExecutor
            for tc in norm_resp.tool_calls:
                t_name = tc.get("name") or tc.get("tool_name") or ""
                t_args = tc.get("args") or tc.get("parameters") or {}

                logger.info(
                    "[AgentRuntime] Executing tool '%s' via ToolExecutor choke point for agent %s",
                    t_name,
                    self.agent_id,
                )

                exec_res = self.tool_executor.execute(
                    tool_name=t_name,
                    parameters=t_args,
                    caller_context=CallerContext.AGENT,
                    agent_id=self.agent_id,
                    workspace=self.workspace_root,
                )

                # Format output
                if exec_res.success:
                    raw_out = exec_res.output
                    res_str = raw_out if isinstance(raw_out, str) else json.dumps(raw_out)
                else:
                    res_str = f"Tool Execution Failed: {exec_res.error or 'Blocked by policy'}"

                # Budget-safe truncation
                truncated_output = self.provider_adapter.context_budget.truncate_tool_output(
                    output=res_str,
                )

                tool_exec_entry = {
                    "tool_name": t_name,
                    "args": t_args,
                    "success": exec_res.success,
                    "blocked_by": exec_res.blocked_by,
                    "output": truncated_output,
                }
                tool_executions_log.append(tool_exec_entry)

                # Persist tool execution turn
                self.append_message(
                    role="tool",
                    content=truncated_output,
                    tool_name=t_name,
                    tool_args=t_args,
                    tool_result=truncated_output,
                    status="completed" if exec_res.success else "denied",
                    conversation_id=cid,
                )

                # Add to context for subsequent synthesis turn
                messages.append({
                    "role": "model",
                    "content": f"[Tool Call: {t_name}({json.dumps(t_args)})]",
                })
                messages.append({
                    "role": "tool",
                    "content": truncated_output,
                    "tool_name": t_name,
                })

        # Persist final assistant reply
        self.append_message(role="assistant", content=final_reply, conversation_id=cid)

        return {
            "success": True,
            "agent_id": self.agent_id,
            "conversation_id": cid,
            "reply": final_reply,
            "tool_executions": tool_executions_log,
        }

    async def step_async(
        self,
        user_input: str,
        conversation_id: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tool_iterations: int = 3,
    ) -> Dict[str, Any]:
        """Non-blocking asynchronous wrapper running step() in the default executor."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.step(
                user_input=user_input,
                conversation_id=conversation_id,
                tools=tools,
                max_tool_iterations=max_tool_iterations,
            ),
        )

    async def step_stream_async(
        self,
        user_input: str,
        conversation_id: Optional[str] = None,
    ):
        """Asynchronous generator yielding live text chunks and completion events."""
        cid = conversation_id or self.get_or_create_conversation()
        self.append_message(role="user", content=user_input, conversation_id=cid)

        raw_history = self.load_messages(conversation_id=cid)
        messages: List[Dict[str, Any]] = []
        for m in raw_history:
            messages.append({"role": m["role"], "content": m["content"]})

        system_prompt = self.build_system_prompt()
        full_prompt_parts = []
        for m in messages:
            role = "User" if m.get("role") == "user" else "Assistant"
            cnt = m.get("content", "")
            full_prompt_parts.append(f"{role}: {cnt}")

        query_text = "\n".join(full_prompt_parts)
        if system_prompt:
            query_text = f"System: {system_prompt}\n\n{query_text}"

        from core import gemini
        accumulated_chunks = []
        loop = asyncio.get_running_loop()

        def _do_stream():
            return list(gemini.stream_text(query_text, tier="fast", timeout_ms=30000))

        try:
            chunks = await loop.run_in_executor(None, _do_stream)
            for ch in chunks:
                accumulated_chunks.append(ch)
                yield {"event": "chunk", "text": ch, "conversation_id": cid}
                await asyncio.sleep(0.01)

            final_text = "".join(accumulated_chunks).strip()
            if not final_text:
                final_text = "Understood. Ready to collaborate."
                yield {"event": "chunk", "text": final_text, "conversation_id": cid}

            self.append_message(role="assistant", content=final_text, conversation_id=cid)
            yield {"event": "done", "reply": final_text, "conversation_id": cid}
        except Exception as e:
            err = f"Streaming error: {str(e)}"
            logger.exception("[AgentRuntime] step_stream_async error: %s", err)
            self.append_message(role="assistant", content=err, status="failed", conversation_id=cid)
            yield {"event": "error", "error": err, "conversation_id": cid}
