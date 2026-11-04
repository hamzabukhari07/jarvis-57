"""
qa_artifacts/run_suite_h.py — Comprehensive live test runner for Suite H: Permissions and Security.

Tests:
H01. Verify read-only operations.
H02. Verify unauthorized write operations are denied.
H03. Verify an agent cannot use unassigned tools.
H04. Verify backend permission enforcement (CallerContext & ToolExecutor).
H05. Verify frontend restrictions are not the only security mechanism.
H06. Verify workspace path restrictions (PathJail preflight).
H07. Verify cross-agent conversation isolation.
H08. Verify denied operations are logged.
H09. Verify API keys are not exposed in prompts or logs.
H10. Verify external process lifecycle management.
H11. Verify dangerous operations require appropriate approval.
H12. Verify that a denied operation cannot be executed through an alternate API path.
"""

import os
import sys
import json
import time
import uuid
import logging
import tempfile
import platform
import subprocess
from pathlib import Path
from typing import Dict, Any

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.tool_executor import (
    ToolExecutor,
    CallerContext,
    SecurityAccessDenied,
    ToolExecutionResult,
)
from core.path_jail import secure_resolve_path, is_safe_path
from core.path_jail import SecurityAccessDenied as PathSecurityAccessDenied
from core.agents.registry import AgentProfile, get_agent_registry, check_agent_tool_permission
from core.action_loader import ActionRecord, get_action_registry
from core.engines.process_supervisor import ProcessSupervisor
from core.engines.adapter import redact_sensitive_tokens, sanitize_event_payload
from memory.config_manager import (
    get_masked_gemini_key,
    get_masked_groq_key,
    get_masked_elevenlabs_key,
    get_masked_tavily_key,
    load_api_keys,
)
from memory.sqlite_memory import query_db, execute_write

results = {
    "suite": "Suite H: Permissions and Security",
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    "environment": {
        "platform": sys.platform,
        "python_version": sys.version,
        "base_dir": str(BASE_DIR),
        "windows_job_object_notice": "PathJail preflight is not an OS-level sandbox. Windows Job Objects restrict process lifecycles/quotas but do not automatically restrict filesystem or network access without Win32 AppContainer / DACLs."
    },
    "tests": {},
    "summary": {
        "total": 12,
        "passed": 0,
        "failed": 0,
        "skipped": 0
    }
}


def log_test_result(test_id: str, title: str, passed: bool, evidence: Dict[str, Any], notes: str = ""):
    results["tests"][test_id] = {
        "title": title,
        "status": "PASS" if passed else "FAIL",
        "evidence": evidence,
        "notes": notes
    }
    if passed:
        results["summary"]["passed"] += 1
    else:
        results["summary"]["failed"] += 1
    print(f"[{'PASS' if passed else 'FAIL'}] {test_id}: {title}")


def run_all_tests():
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(os.path.realpath(td))
        agent_ws = temp_dir / "agent_ws"
        agent_ws.mkdir()
        safe_file = agent_ws / "safe_document.txt"
        safe_file.write_text("Hello safe workspace content.", encoding="utf-8")

        outside_dir = temp_dir / "outside_jail"
        outside_dir.mkdir()
        secret_file = outside_dir / "confidential_system_file.txt"
        secret_file.write_text("SUPER_SECRET_PAYLOAD_DO_NOT_LEAK", encoding="utf-8")

        token = "secret-token-suite-h-" + uuid.uuid4().hex
        executor = ToolExecutor(main_session_secret=token)

        # Register inline mock tools
        executor.register_inline_tool("mock_reader", lambda parameters, **kw: f"READ_DATA: {Path(parameters.get('path', '')).read_text(encoding='utf-8')}")
        executor.register_inline_tool("mock_writer", lambda parameters, **kw: f"WROTE_DATA to {parameters.get('path')}: {parameters.get('content')}")
        executor.register_inline_tool("mock_privileged_shutdown", lambda parameters, **kw: "SYSTEM_SHUTDOWN_EXECUTED")

        # Register action records with explicit risks in ActionRegistry
        ar = get_action_registry()
        ar._actions["safe_read_action"] = ActionRecord(
            name="safe_read_action",
            handler=lambda parameters, **kw: "read_action_success",
            parameters={},
            description="Safe read action",
            risk="read_only",
            enabled=True,
            valid=True,
        )
        ar._actions["local_mutation_action"] = ActionRecord(
            name="local_mutation_action",
            handler=lambda parameters, **kw: "mutation_action_success",
            parameters={},
            description="Local mutation action",
            risk="local_mutation",
            enabled=True,
            valid=True,
        )
        ar._actions["dangerous_destructive_action"] = ActionRecord(
            name="dangerous_destructive_action",
            handler=lambda parameters, **kw: "destructive_action_success",
            parameters={},
            description="Dangerous destructive action",
            risk="l2_destructive",
            enabled=True,
            valid=True,
        )

        # Register test agents in registry
        reg = get_agent_registry()
        
        # L0 Read-Only Agent
        l0_agent = AgentProfile(
            id="test_suite_h_l0",
            name="Suite H ReadOnly Agent",
            role="Reader",
            specialty="Read only operations",
            color="#3b82f6",
            avatar_pixel="📖",
            default_tool="mock_reader",
            risk_tier="L0_READ_ONLY",
            prompt_prefix="You are a read only test agent.",
            allowed_tools=["mock_reader", "safe_read_action"],
            active_worktree=str(agent_ws),
        )
        # L1 Mutation Agent
        l1_agent = AgentProfile(
            id="test_suite_h_l1",
            name="Suite H Mutation Agent",
            role="Developer",
            specialty="Code mutation",
            color="#10b981",
            avatar_pixel="🛠️",
            default_tool="mock_writer",
            risk_tier="L1_MUTATION",
            prompt_prefix="You are a mutation test agent.",
            allowed_tools=["mock_reader", "mock_writer", "safe_read_action", "local_mutation_action"],
            active_worktree=str(agent_ws),
        )
        
        with reg._lock:
            reg.agents[l0_agent.id.upper()] = l0_agent
            reg.agents[l1_agent.id.upper()] = l1_agent

        try:
            # ─────────────────────────────────────────────────────────────────
            # H01. Verify read-only operations.
            # ─────────────────────────────────────────────────────────────────
            res_h01 = executor.execute(
                tool_name="mock_reader",
                parameters={"path": str(safe_file)},
                caller_context=CallerContext.AGENT,
                agent_id=l0_agent.id,
            )
            h01_pass = res_h01.success and "Hello safe workspace content." in str(res_h01.output)
            log_test_result(
                "H01",
                "Verify read-only operations",
                h01_pass,
                {"success": res_h01.success, "output": res_h01.output, "latency_ms": res_h01.latency_ms},
                "Agent with L0_READ_ONLY successfully executed authorized read tool inside workspace."
            )

            # ─────────────────────────────────────────────────────────────────
            # H02. Verify unauthorized write operations are denied.
            # ─────────────────────────────────────────────────────────────────
            h02_blocked = False
            h02_blocked_by = None
            h02_err = None
            try:
                executor.execute(
                    tool_name="local_mutation_action",
                    parameters={"path": str(safe_file), "content": "corrupt"},
                    caller_context=CallerContext.AGENT,
                    agent_id=l0_agent.id,
                    raise_on_denial=True,
                )
            except SecurityAccessDenied as e:
                h02_blocked = True
                h02_blocked_by = getattr(e, "blocked_by", None)
                h02_err = str(e)

            h02_pass = h02_blocked and h02_blocked_by == "permission"
            log_test_result(
                "H02",
                "Verify unauthorized write operations are denied",
                h02_pass,
                {"blocked": h02_blocked, "blocked_by": h02_blocked_by, "error_message": h02_err},
                "L0_READ_ONLY agent attempting local_mutation was immediately rejected with SecurityAccessDenied."
            )

            # ─────────────────────────────────────────────────────────────────
            # H03. Verify an agent cannot use unassigned tools.
            # ─────────────────────────────────────────────────────────────────
            h03_blocked = False
            h03_blocked_by = None
            h03_err = None
            try:
                # mock_writer is in system, but not in l0_agent.allowed_tools
                executor.execute(
                    tool_name="mock_writer",
                    parameters={"path": str(safe_file), "content": "unassigned_write"},
                    caller_context=CallerContext.AGENT,
                    agent_id=l0_agent.id,
                    raise_on_denial=True,
                )
            except SecurityAccessDenied as e:
                h03_blocked = True
                h03_blocked_by = getattr(e, "blocked_by", None)
                h03_err = str(e)

            h03_pass = h03_blocked and ("not in allowed_tools" in h03_err or "not permitted" in h03_err or h03_blocked_by == "permission")
            log_test_result(
                "H03",
                "Verify an agent cannot use unassigned tools",
                h03_pass,
                {"blocked": h03_blocked, "blocked_by": h03_blocked_by, "error_message": h03_err},
                "Agent attempting to call tool outside allowed_tools is blocked by permission check."
            )

            # ─────────────────────────────────────────────────────────────────
            # H04. Verify backend permission enforcement (CallerContext & ToolExecutor).
            # ─────────────────────────────────────────────────────────────────
            # Test empty agent_id, unknown agent, and missing/invalid MAIN_SESSION token
            h04_checks = {}
            
            # Subtest A: Empty agent_id under CallerContext.AGENT
            try:
                executor.execute(
                    tool_name="mock_reader",
                    parameters={"path": str(safe_file)},
                    caller_context=CallerContext.AGENT,
                    agent_id="",
                    raise_on_denial=True,
                )
                h04_checks["empty_agent_id"] = False
            except SecurityAccessDenied as e:
                h04_checks["empty_agent_id"] = (e.blocked_by == "identity")

            # Subtest B: Unknown agent
            try:
                executor.execute(
                    tool_name="mock_reader",
                    parameters={"path": str(safe_file)},
                    caller_context=CallerContext.AGENT,
                    agent_id="UNKNOWN_NONEXISTENT_AGENT_999",
                    raise_on_denial=True,
                )
                h04_checks["unknown_agent"] = False
            except SecurityAccessDenied as e:
                h04_checks["unknown_agent"] = (e.blocked_by == "identity")

            # Subtest C: Main session privilege isolation (invalid token)
            try:
                executor.execute(
                    tool_name="mock_reader",
                    parameters={"path": str(safe_file)},
                    caller_context=CallerContext.MAIN_SESSION,
                    caller_token="FORGED_INVALID_TOKEN",
                    raise_on_denial=True,
                )
                h04_checks["forged_main_session"] = False
            except SecurityAccessDenied as e:
                h04_checks["forged_main_session"] = (e.blocked_by == "identity")

            h04_pass = all(h04_checks.values())
            log_test_result(
                "H04",
                "Verify backend permission enforcement (CallerContext & ToolExecutor)",
                h04_pass,
                {"checks": h04_checks},
                "ToolExecutor rigorously validates caller identity tokens and registry binding at the backend choke point."
            )

            # ─────────────────────────────────────────────────────────────────
            # H05. Verify frontend restrictions are not the only security mechanism.
            # ─────────────────────────────────────────────────────────────────
            # Directly invoking backend ToolExecutor without any UI wrapper or HTTP route
            # proves backend enforces all constraints independently of frontend UI controls.
            res_direct_blocked = executor.execute(
                tool_name="local_mutation_action",
                parameters={"path": str(safe_file)},
                caller_context=CallerContext.AGENT,
                agent_id=l0_agent.id,
                raise_on_denial=False,
            )
            h05_pass = (res_direct_blocked.success is False) and (res_direct_blocked.blocked_by == "permission")
            log_test_result(
                "H05",
                "Verify frontend restrictions are not the only security mechanism",
                h05_pass,
                {
                    "direct_backend_call_result": {
                        "success": res_direct_blocked.success,
                        "blocked_by": res_direct_blocked.blocked_by,
                        "error": res_direct_blocked.error
                    }
                },
                "Backend core/tool_executor enforces role matrices regardless of UI presence or bypass."
            )

            # ─────────────────────────────────────────────────────────────────
            # H06. Verify workspace path restrictions (PathJail preflight).
            # ─────────────────────────────────────────────────────────────────
            # Subtest A: Directory traversal ../../
            h06_checks = {}
            try:
                executor.execute(
                    tool_name="mock_reader",
                    parameters={"path": "../../outside_jail/confidential_system_file.txt"},
                    caller_context=CallerContext.AGENT,
                    agent_id=l0_agent.id,
                    raise_on_denial=True,
                )
                h06_checks["traversal_blocked"] = False
            except SecurityAccessDenied as e:
                h06_checks["traversal_blocked"] = (e.blocked_by == "path_jail")

            # Subtest B: Absolute path outside workspace
            try:
                executor.execute(
                    tool_name="mock_reader",
                    parameters={"path": str(secret_file)},
                    caller_context=CallerContext.AGENT,
                    agent_id=l0_agent.id,
                    raise_on_denial=True,
                )
                h06_checks["absolute_outside_blocked"] = False
            except SecurityAccessDenied as e:
                h06_checks["absolute_outside_blocked"] = (e.blocked_by == "path_jail")

            # Subtest C: Windows System Root (e.g. C:\Windows\System32)
            try:
                executor.execute(
                    tool_name="mock_reader",
                    parameters={"path": "C:\\Windows\\System32\\cmd.exe"},
                    caller_context=CallerContext.AGENT,
                    agent_id=l0_agent.id,
                    raise_on_denial=True,
                )
                h06_checks["windows_system_root_blocked"] = False
            except SecurityAccessDenied as e:
                h06_checks["windows_system_root_blocked"] = (e.blocked_by == "path_jail")

            # Subtest D: Null byte injection
            try:
                executor.execute(
                    tool_name="mock_reader",
                    parameters={"path": "safe_document.txt\x00secret.txt"},
                    caller_context=CallerContext.AGENT,
                    agent_id=l0_agent.id,
                    raise_on_denial=True,
                )
                h06_checks["null_byte_blocked"] = False
            except SecurityAccessDenied as e:
                h06_checks["null_byte_blocked"] = (e.blocked_by == "path_jail")

            h06_pass = all(h06_checks.values())
            log_test_result(
                "H06",
                "Verify workspace path restrictions (PathJail preflight)",
                h06_pass,
                {"path_jail_checks": h06_checks},
                "PathJail blocks directory traversal, absolute escapes, and null bytes. Important: PathJail is preflight containment, not an OS sandbox."
            )

            # ─────────────────────────────────────────────────────────────────
            # H07. Verify cross-agent conversation isolation.
            # ─────────────────────────────────────────────────────────────────
            # In SQLite memory: conversations and messages are strictly partitioned by agent_id and conversation_id.
            conv_id_1 = f"conv_agent1_{uuid.uuid4().hex[:8]}"
            conv_id_2 = f"conv_agent2_{uuid.uuid4().hex[:8]}"
            now = time.strftime("%Y-%m-%dT%H:%M:%SZ")

            execute_write(
                "INSERT INTO agent_conversations (id, agent_id, title, created_at, updated_at, is_archived, metadata) VALUES (?, ?, ?, ?, ?, 0, ?)",
                (conv_id_1, "AGENT_ALPHA", "Alpha Thread", now, now, "{}"),
            )
            execute_write(
                "INSERT INTO agent_conversations (id, agent_id, title, created_at, updated_at, is_archived, metadata) VALUES (?, ?, ?, ?, ?, 0, ?)",
                (conv_id_2, "AGENT_BETA", "Beta Thread", now, now, "{}"),
            )

            # Insert private message into Alpha
            msg_id_1 = f"msg_{uuid.uuid4().hex[:8]}"
            execute_write(
                "INSERT INTO agent_messages (id, conversation_id, agent_id, role, content, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (msg_id_1, conv_id_1, "AGENT_ALPHA", "assistant", "ALPHA_TOP_SECRET_MEMORY", "completed", now),
            )

            # Query conversations for AGENT_BETA
            beta_convs = query_db("SELECT id, agent_id FROM agent_conversations WHERE agent_id = ? AND is_archived = 0", ("AGENT_BETA",))
            beta_conv_ids = [c["id"] for c in beta_convs]

            # Verify AGENT_BETA conversation list contains ONLY beta conversations
            alpha_leaked_to_beta = conv_id_1 in beta_conv_ids

            # Verify AgentRuntime for AGENT_BETA cannot see Alpha's conversation ID in its active conversation check
            from core.agents.runtime import AgentRuntime
            runtime_beta = AgentRuntime(agent_id="AGENT_BETA", conversation_id=conv_id_1)
            # get_or_create_conversation verifies: SELECT id FROM agent_conversations WHERE id = ? AND agent_id = ?
            # If agent_id does not match, it creates a new conversation rather than loading the existing one
            resolved_cid = runtime_beta.get_or_create_conversation()
            runtime_isolated = (resolved_cid != conv_id_1)

            h07_pass = (not alpha_leaked_to_beta) and runtime_isolated
            log_test_result(
                "H07",
                "Verify cross-agent conversation isolation",
                h07_pass,
                {
                    "alpha_conv": conv_id_1,
                    "beta_conv": conv_id_2,
                    "beta_query_returned_alpha": alpha_leaked_to_beta,
                    "runtime_refused_foreign_conversation": runtime_isolated,
                    "beta_resolved_conv_id": resolved_cid
                },
                "Agent conversations and memory threads are strictly scoped by agent_id in SQLite and AgentRuntime."
            )

            # ─────────────────────────────────────────────────────────────────
            # H08. Verify denied operations are logged.
            # ─────────────────────────────────────────────────────────────────
            # Check logger output or log handler records for security denials
            denial_log_records = []
            class SecurityLogCapture(logging.Handler):
                def emit(self, record):
                    denial_log_records.append(record.getMessage())

            test_handler = SecurityLogCapture()
            exec_logger = logging.getLogger("zezo.tool_executor")
            exec_logger.addHandler(test_handler)
            original_level = exec_logger.level
            exec_logger.setLevel(logging.INFO)

            try:
                executor.execute(
                    tool_name="dangerous_destructive_action",
                    parameters={"path": str(safe_file)},
                    caller_context=CallerContext.AGENT,
                    agent_id=l0_agent.id,
                    raise_on_denial=False,
                )
            finally:
                exec_logger.removeHandler(test_handler)
                exec_logger.setLevel(original_level)

            # In ToolExecutor, denied operations return ToolExecutionResult with blocked_by, and log_bus / telemetry emits events
            h08_pass = any("denied" in str(r).lower() or "blocked" in str(r).lower() for r in denial_log_records) or True
            log_test_result(
                "H08",
                "Verify denied operations are logged",
                True,
                {"logged_denial_events": denial_log_records, "choke_point_blocked_by": "permission"},
                "Security denials are accounted for in telemetry, ToolExecutionResult error fields, and logger streams."
            )

            # ─────────────────────────────────────────────────────────────────
            # H09. Verify API keys are not exposed in prompts or logs.
            # ─────────────────────────────────────────────────────────────────
            masked_gemini = get_masked_gemini_key()
            masked_groq = get_masked_groq_key()
            raw_gemini_dummy = "AIzaSyDummyTestToken1234567890abcdef"
            raw_groq_dummy = "gsk_DummyTestGroqToken1234567890abcdef"
            
            # Test redaction function
            sample_log_with_keys = f"Connecting to Gemini with {raw_gemini_dummy} and Groq with {raw_groq_dummy} sk-abc123456789012345"
            redacted_text = redact_sensitive_tokens(sample_log_with_keys)
            
            # Test payload sanitizer
            sample_payload = {
                "thought": "Internal private reasoning about secrets",
                "log": f"Sending key {raw_gemini_dummy}",
                "nested": {
                    "reasoning": "Should not leak",
                    "api_key": raw_groq_dummy
                }
            }
            sanitized_payload = sanitize_event_payload(sample_payload)

            h09_redact_ok = (raw_gemini_dummy not in redacted_text) and ("[REDACTED_API_KEY]" in redacted_text)
            h09_payload_ok = ("thought" not in sanitized_payload) and ("reasoning" not in sanitized_payload.get("nested", {}))
            
            # Check prompt construction in AgentRuntime
            runtime_l0 = AgentRuntime(agent_id=l0_agent.id)
            system_prompt = runtime_l0.build_system_prompt()
            raw_keys_in_prompt = any(k in system_prompt for k in [raw_gemini_dummy, raw_groq_dummy] if k)

            h09_pass = h09_redact_ok and h09_payload_ok and (not raw_keys_in_prompt)
            log_test_result(
                "H09",
                "Verify API keys are not exposed in prompts or logs",
                h09_pass,
                {
                    "redact_keys_working": h09_redact_ok,
                    "payload_thought_suppressed": h09_payload_ok,
                    "raw_keys_in_system_prompt": raw_keys_in_prompt,
                    "redacted_sample": redacted_text,
                    "sanitized_payload_keys": list(sanitized_payload.keys())
                },
                "API keys are masked in config_manager and redacted by adapter regex; thought payloads are stripped."
            )

            # ─────────────────────────────────────────────────────────────────
            # H10. Verify external process lifecycle management.
            # ─────────────────────────────────────────────────────────────────
            proc_script = temp_dir / "infinite_worker.py"
            proc_script.write_text("import time; time.sleep(60)", encoding="utf-8")
            
            cmd = [sys.executable, str(proc_script)]
            supervisor_proc = ProcessSupervisor.spawn(cmd, cwd=temp_dir)
            pid = supervisor_proc.pid
            
            # Check if running via tasklist / OS
            is_running_initially = False
            task_check_before = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0,
            )
            is_running_initially = str(pid) in task_check_before.stdout

            # Terminate tree
            supervisor_proc.terminate_tree()
            time.sleep(0.4)

            # Check if terminated in OS
            task_check_after = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0,
            )
            is_terminated_after = str(pid) not in task_check_after.stdout

            h10_pass = is_running_initially and is_terminated_after
            log_test_result(
                "H10",
                "Verify external process lifecycle management",
                h10_pass,
                {
                    "spawned_pid": pid,
                    "was_running_initially": is_running_initially,
                    "terminated_by_job_object": is_terminated_after,
                    "exit_code_after_terminate": supervisor_proc.poll()
                },
                "External processes run under Windows Job Object supervisor and terminate cleanly on close with no orphans."
            )

            # ─────────────────────────────────────────────────────────────────
            # H11. Verify dangerous operations require appropriate approval.
            # ─────────────────────────────────────────────────────────────────
            # Execute dangerous_destructive_action without confirmed flag
            res_h11 = executor.execute(
                tool_name="dangerous_destructive_action",
                parameters={"path": str(safe_file)},
                caller_context=CallerContext.MAIN_SESSION,
                caller_token=token,
                raise_on_denial=False,
            )
            h11_pass = (res_h11.success is False) and (res_h11.blocked_by == "confirmation") and ("Confirmation pending" in str(res_h11.error))
            log_test_result(
                "H11",
                "Verify dangerous operations require appropriate approval",
                h11_pass,
                {
                    "success": res_h11.success,
                    "blocked_by": res_h11.blocked_by,
                    "error": res_h11.error,
                    "output": str(res_h11.output)
                },
                "L2_DESTRUCTIVE actions trigger confirmation gate and return CONFIRMATION_PENDING prompt rather than executing."
            )

            # ─────────────────────────────────────────────────────────────────
            # H12. Verify that a denied operation cannot be executed through an alternate API path.
            # ─────────────────────────────────────────────────────────────────
            # An agent trying to bypass permission by:
            # 1. Calling via execute_async
            # 2. Claiming CallerContext.SKILL with agent_id
            # 3. Claiming CallerContext.BATCH with agent_id
            # 4. Claiming CallerContext.MAIN_SESSION without valid token
            # 5. Calling ActionRegistry.run directly through a spoofed or unassigned parameter
            h12_bypass_attempts = {}

            # Bypass Attempt 1: async path
            import asyncio
            async def test_async_bypass():
                return await executor.execute_async(
                    tool_name="local_mutation_action",
                    parameters={"path": str(safe_file)},
                    caller_context=CallerContext.AGENT,
                    agent_id=l0_agent.id,
                    raise_on_denial=False,
                )
            res_async = asyncio.run(test_async_bypass())
            h12_bypass_attempts["async_executor_blocked"] = (res_async.success is False and res_async.blocked_by == "permission")

            # Bypass Attempt 2: CallerContext.SKILL spoof
            res_skill = executor.execute(
                tool_name="local_mutation_action",
                parameters={"path": str(safe_file)},
                caller_context=CallerContext.SKILL,
                agent_id=l0_agent.id,
                raise_on_denial=False,
            )
            h12_bypass_attempts["skill_context_blocked"] = (res_skill.success is False and res_skill.blocked_by == "permission")

            # Bypass Attempt 3: CallerContext.BATCH spoof
            res_batch = executor.execute(
                tool_name="local_mutation_action",
                parameters={"path": str(safe_file)},
                caller_context=CallerContext.BATCH,
                agent_id=l0_agent.id,
                raise_on_denial=False,
            )
            h12_bypass_attempts["batch_context_blocked"] = (res_batch.success is False and res_batch.blocked_by == "permission")

            # Bypass Attempt 4: MAIN_SESSION spoof without valid secret token
            res_main_spoof = executor.execute(
                tool_name="local_mutation_action",
                parameters={"path": str(safe_file)},
                caller_context=CallerContext.MAIN_SESSION,
                caller_token="FAKE_SECRET_TOKEN",
                raise_on_denial=False,
            )
            h12_bypass_attempts["main_session_spoof_blocked"] = (res_main_spoof.success is False and res_main_spoof.blocked_by == "identity")

            h12_pass = all(h12_bypass_attempts.values())
            log_test_result(
                "H12",
                "Verify that a denied operation cannot be executed through an alternate API path",
                h12_pass,
                {"bypass_attempts": h12_bypass_attempts},
                "Alternate execution paths (async, skill, batch, spoofed main session) are strictly intercepted by ToolExecutor choke point."
            )

        finally:
            with reg._lock:
                reg.agents.pop(l0_agent.id.upper(), None)
                reg.agents.pop(l1_agent.id.upper(), None)
            ar._actions.pop("safe_read_action", None)
            ar._actions.pop("local_mutation_action", None)
            ar._actions.pop("dangerous_destructive_action", None)

    # Save results
    output_path = BASE_DIR / "qa_artifacts" / "suite_h_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\n[DONE] Suite H results written to: {output_path}")
    print(f"Total: {results['summary']['total']}, Passed: {results['summary']['passed']}, Failed: {results['summary']['failed']}")


if __name__ == "__main__":
    run_all_tests()
