"""
core/skill_runner.py — Dual-AI Skill Runner Subsystem.

Creator & Lead Architect: Hamza Bukhari

Executes procedural declarative skills (skills/<skill_name>/SKILL.md) through
an intelligent, dual-engine tool orchestration architecture:
  - Smart Tool Scoping: Selects 3-5 atomic action tools referenced in `required_tools`
    or in the body of `SKILL.md` rather than exposing all 30+ tools.
  - Primary Engine: Groq LPU (llama-3.3-70b-versatile) for ultra-fast sequential tool calls.
  - Stateful Fallback: Tracks `completed_steps = []`. If Groq experiences rate limits (429)
    or network dropouts, seamlessly transfers state to Gemini (gemini-3.8-flash) to resume
    from the current step without repeating step 1.
  - Memory Guard: Truncates large tool responses (max 1500 chars) before feeding back into LLM.
  - Progress Telemetry: Emits real-time progress updates to TaskManager.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)


def truncate_tool_output(output: str, max_chars: int = 1500) -> str:
    """Summarize/truncate oversized tool execution output to safeguard LLM context window."""
    if not output:
        return ""
    text = str(output).strip()
    if len(text) <= max_chars:
        return text

    head = (max_chars // 2) - 45
    tail = (max_chars // 2) - 45
    omitted = len(text) - head - tail
    return (
        f"{text[:head]}\n\n"
        f"... [Memory Guard: Output truncated ({len(text)} chars total, omitted {omitted} chars)] ...\n\n"
        f"{text[-tail:]}"
    )


class SkillRunner:
    """Orchestrates procedural skills with Dual-AI Groq + Gemini fallback."""

    def __init__(
        self,
        skill_name: str,
        user_params: Optional[dict] = None,
        context: Optional[dict] = None,
        task_ctx: Optional[Any] = None,
        task_id: Optional[str] = None,
    ) -> None:
        self.skill_name = (skill_name or "").strip()
        self.user_params = user_params or {}
        self.context = context or {}
        self.task_ctx = task_ctx or self.context.get("task_ctx")
        self.task_id = (
            task_id
            or (getattr(self.task_ctx, "task_id", None) if self.task_ctx else None)
            or self.context.get("task_id")
        )
        self.completed_steps: list[dict] = []
        self.active_engine: str = "groq"
        self.skill_content: str = ""
        self.required_tools: list[str] = []

    def report_progress(self, progress: int, message: str = "") -> None:
        """Report live execution progress to TaskManager."""
        clean_msg = (message or "").strip()
        if self.task_ctx and hasattr(self.task_ctx, "report"):
            try:
                self.task_ctx.report(progress, clean_msg)
                return
            except Exception:
                pass
        if self.task_id:
            try:
                from core.task_manager import get_task_manager
                get_task_manager()._report(self.task_id, progress, clean_msg)
            except Exception:
                pass

    def _load_skill(self) -> tuple[str, list[str]]:
        """Ingests SKILL.md content via SkillRegistry and parses required_tools."""
        from core.skill_loader import get_skill_registry

        registry = get_skill_registry()
        skill_text = registry.read_skill(self.skill_name)
        required_tools: list[str] = []

        # Inspect registry records for explicit required_tools attribute
        if hasattr(registry, "_skills"):
            target_record = None
            if self.skill_name in registry._skills:
                target_record = registry._skills[self.skill_name]
            else:
                for k, s in registry._skills.items():
                    if self.skill_name.lower() in k.lower() or k.lower() in self.skill_name.lower():
                        target_record = s
                        break
            if target_record and getattr(target_record, "required_tools", None):
                required_tools.extend(target_record.required_tools)

        # Check YAML frontmatter in skill_text for required_tools
        frontmatter_match = re.match(r"^---\s*\n(.*?)\n---", skill_text, re.DOTALL)
        if frontmatter_match:
            block = frontmatter_match.group(1)
            for line in block.splitlines():
                if "required_tools" in line.lower() and ":" in line:
                    _, val = line.split(":", 1)
                    val = val.strip()
                    if val.startswith("[") and val.endswith("]"):
                        items = [x.strip().strip("'\"") for x in val[1:-1].split(",") if x.strip()]
                        required_tools.extend(items)

        return skill_text, list(dict.fromkeys(required_tools))

    def _resolve_scoped_tools(
        self,
        skill_content: str,
        required_tools: list[str],
    ) -> list[dict]:
        """Extracts tool names mentioned in required_tools or body of SKILL.md (3-5 tools)."""
        from core.action_loader import get_action_registry

        act_reg = get_action_registry()
        all_actions = act_reg.names()
        scoped_names: set[str] = set()

        # 1. Add tools declared in required_tools
        for rt in required_tools:
            if rt in all_actions:
                scoped_names.add(rt)

        # 2. Extract tools mentioned in the body of SKILL.md
        for action_name in all_actions:
            if re.search(r"\b" + re.escape(action_name) + r"\b", skill_content, re.IGNORECASE):
                scoped_names.add(action_name)

        # 3. Sensible fallbacks if no specific tools are discovered
        if not scoped_names:
            for fallback in ("run_command", "read_file", "write_file", "browser_control"):
                if fallback in all_actions:
                    scoped_names.add(fallback)

        # Build declaration schema for each scoped tool
        scoped_declarations: list[dict] = []
        for name in sorted(scoped_names):
            rec = act_reg.get(name)
            if rec and rec.valid and rec.enabled:
                scoped_declarations.append({
                    "name": rec.name,
                    "description": rec.description,
                    "parameters": rec.parameters,
                })

        return scoped_declarations

    def _call_gemini_step(
        self,
        step_idx: int,
        scoped_declarations: list[dict],
        system_prompt: str,
    ) -> dict:
        """Resumes execution from current step using Gemini (gemini-3.8-flash) without repeating step 1."""
        from core.gemini import client as get_gemini_client
        from google.genai import types as gtypes

        cl = get_gemini_client(timeout_ms=30000)

        # Build stateful resume prompt highlighting already completed steps
        completed_summary = ""
        if self.completed_steps:
            completed_summary = "ALREADY COMPLETED STEPS (DO NOT REPEAT ANY OF THESE):\n"
            for s in self.completed_steps:
                completed_summary += (
                    f"- Step {s['step']}: Tool `{s['tool']}` with args {json.dumps(s['arguments'])} "
                    f"-> Output: {s['result']}\n"
                )
            completed_summary += "\n"

        prompt = (
            f"User Task Request: {json.dumps(self.user_params)}\n\n"
            f"{completed_summary}"
            f"You are resuming execution at Step {step_idx}.\n"
            "CRITICAL PROTOCOL: Do NOT re-execute any of the steps listed above.\n"
            "Call the next required tool to advance the skill workflow, OR if all goals are accomplished, "
            "output your final clear summary answer."
        )

        cfg = gtypes.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=[{"function_declarations": scoped_declarations}],
            temperature=0.1,
        )

        target_models = ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-3-flash-preview"]
        last_exc: Optional[Exception] = None
        for m in target_models:
            try:
                resp = cl.models.generate_content(
                    model=m,
                    contents=prompt,
                    config=cfg,
                )
                if resp:
                    parsed_tools: list[dict] = []
                    if getattr(resp, "function_calls", None):
                        for fc in resp.function_calls:
                            fn_args = dict(fc.args) if getattr(fc, "args", None) else {}
                            parsed_tools.append({
                                "id": f"call_gemini_{step_idx}_{fc.name}",
                                "name": fc.name,
                                "arguments": fn_args,
                            })
                    text_out = getattr(resp, "text", "") or ""
                    return {
                        "content": text_out.strip(),
                        "tool_calls": parsed_tools,
                        "role": "assistant",
                    }
            except Exception as e:
                last_exc = e
                logger.warning("[SkillRunner] Gemini model %s failed: %s", m, e)
                continue

        raise RuntimeError(f"All Gemini candidate models failed: {last_exc}")

    def run(self, max_steps: int = 10) -> dict:
        """Executes the skill workflow sequentially using Dual-AI Groq + Gemini fallback."""
        from core.action_loader import get_action_registry

        act_reg = get_action_registry()
        self.report_progress(5, f"Initializing skill runner for '{self.skill_name}'...")

        self.skill_content, self.required_tools = self._load_skill()
        if not self.skill_content or "not found" in self.skill_content.lower():
            err_msg = f"Skill '{self.skill_name}' could not be located in registry."
            self.report_progress(100, err_msg)
            return {"success": False, "error": err_msg}

        scoped_declarations = self._resolve_scoped_tools(self.skill_content, self.required_tools)
        tool_names = [d["name"] for d in scoped_declarations]
        logger.info("[SkillRunner] Scoped %d tools for skill '%s': %s", len(tool_names), self.skill_name, tool_names)

        system_prompt = (
            "You are an autonomous procedural skill runner on ZEZO (Creator: Hamza Bukhari).\n"
            f"Executing Skill: {self.skill_name}\n\n"
            f"=== SKILL PROTOCOL & INSTRUCTIONS ===\n"
            f"{self.skill_content}\n"
            f"====================================\n\n"
            "EXECUTION DIRECTIVES:\n"
            "1. Execute each atomic step sequentially using the scoped tools available to you.\n"
            "2. Never hallucinate tools; only call tools explicitly provided in declarations.\n"
            "3. When all required steps of the skill have completed, provide a concise final summary.\n"
            "4. Do NOT execute tools if the task has already been fully completed."
        )

        groq_messages: list[dict] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Execute skill '{self.skill_name}' with parameters: {json.dumps(self.user_params)}"},
        ]

        self.active_engine = "groq"
        self.completed_steps = []

        for step_idx in range(1, max_steps + 1):
            progress_pct = min(90, int(15 + ((step_idx - 1) / max_steps) * 75))
            self.report_progress(progress_pct, f"Step {step_idx}: Consulting {self.active_engine.upper()}...")

            response: dict = {}

            # ── 1. PRIMARY ENGINE: GROQ LPU ─────────────────────────────────
            if self.active_engine == "groq":
                try:
                    from core.llm_client import call_groq_tools
                    response = call_groq_tools(
                        messages=groq_messages,
                        tools=scoped_declarations,
                        model="llama-3.3-70b-versatile",
                        timeout=25.0,
                    )
                except Exception as groq_err:
                    logger.warning(
                        "[SkillRunner] Groq failed at step %d (%s). Seamless handover to Gemini (gemini-3.8-flash)...",
                        step_idx,
                        groq_err,
                    )
                    self.active_engine = "gemini"
                    self.report_progress(
                        progress_pct,
                        f"Groq unavailable ({type(groq_err).__name__}). Handing over to Gemini (gemini-3.8-flash)...",
                    )

            # ── 2. STATEFUL FALLBACK ENGINE: GEMINI ─────────────────────────
            if self.active_engine == "gemini":
                try:
                    response = self._call_gemini_step(
                        step_idx=step_idx,
                        scoped_declarations=scoped_declarations,
                        system_prompt=system_prompt,
                    )
                except Exception as gemini_err:
                    logger.error("[SkillRunner] Gemini fallback failed at step %d: %s", step_idx, gemini_err)
                    self.report_progress(100, f"Skill execution failed at step {step_idx}.")
                    return {
                        "success": False,
                        "error": f"Dual-AI execution failed: Groq and Gemini both failed at step {step_idx}: {gemini_err}",
                        "completed_steps": self.completed_steps,
                        "engine": self.active_engine,
                    }

            tool_calls = response.get("tool_calls") or []
            content = response.get("content") or ""

            # When model returns no tool calls, it has finished the skill workflow
            if not tool_calls:
                self.report_progress(100, f"Skill '{self.skill_name}' finished successfully.")
                return {
                    "success": True,
                    "skill": self.skill_name,
                    "completed_steps": self.completed_steps,
                    "final_output": content or "Skill execution completed successfully.",
                    "engine": self.active_engine,
                }

            # Sequential execution of atomic tools requested by model
            for tc in tool_calls:
                t_name = tc.get("name", "")
                t_args = tc.get("arguments") or {}

                self.report_progress(progress_pct, f"Step {step_idx}: Executing tool '{t_name}'...")
                raw_out = act_reg.run(t_name, t_args, ctx=self.context)
                clean_out = truncate_tool_output(str(raw_out), max_chars=1500)

                step_data = {
                    "step": step_idx,
                    "tool": t_name,
                    "arguments": t_args,
                    "result": clean_out,
                    "engine": self.active_engine,
                    "timestamp": time.time(),
                }
                self.completed_steps.append(step_data)

                # Append message pair to groq_messages if still on Groq
                if self.active_engine == "groq":
                    call_id = tc.get("id") or f"call_{step_idx}_{t_name}"
                    groq_messages.append({
                        "role": "assistant",
                        "content": content or "",
                        "tool_calls": [
                            {
                                "id": call_id,
                                "type": "function",
                                "function": {
                                    "name": t_name,
                                    "arguments": json.dumps(t_args) if isinstance(t_args, dict) else str(t_args),
                                },
                            }
                        ],
                    })
                    groq_messages.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "name": t_name,
                        "content": clean_out,
                    })

        self.report_progress(100, f"Skill '{self.skill_name}' reached maximum steps ({max_steps}).")
        return {
            "success": True,
            "skill": self.skill_name,
            "completed_steps": self.completed_steps,
            "final_output": f"Executed {len(self.completed_steps)} steps. Completed max allotted steps.",
            "engine": self.active_engine,
        }
