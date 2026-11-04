"""
Suite L Automation Runner: Persistence and Restart Recovery
Tests:
L01. Create a test agent.
L02. Create a conversation.
L03. Send multiple messages.
L04. Execute a tool call.
L05. Verify database persistence (sqlite tables: agent_conversations, agent_messages, turns).
L06. Simulate closing ZEZO normally (flush DB / reload state).
L07. Restart ZEZO (reinitialize registry, reload DB connection).
L08. Verify the agent remains available.
L09. Verify conversation history remains available.
L10. Verify message ordering (chronological).
L11. Verify the agent can recall the test conversation.
L12. Verify another agent cannot access that conversation (conversation ownership).
L13. Verify no duplicate messages were created.
L14. Verify interrupted operations are handled safely (interrupted task ledger).
L15. Verify task statuses remain consistent.
"""

import sys
import os
import json
import uuid
import time
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import MagicMock

# Add project root to sys.path
sys.path.insert(0, os.path.abspath("."))

import memory.sqlite_memory as sm
from core.agents.registry import AgentRegistry, get_agent_registry
from core.agents_manager import agent_manager
from core.agents.runtime import AgentRuntime
from core.agents.provider_adapter import (
    ProviderAdapter,
    NormalizedResponse,
    ProviderUsage,
)
from core.agents.context_budget import ContextBudget
from core.tool_executor import ToolExecutor, ToolExecutionResult, CallerContext
from core.task_manager import (
    reconcile_interrupted_tasks,
    get_interrupted_tasks,
    restart_interrupted_task,
)


def run_suite_l():
    run_uuid = uuid.uuid4().hex[:6]
    test_agent_id = f"QA_L_{run_uuid}".upper()[:20]  # clean_id max 20 chars
    test_agent_name = f"PersistBot_{run_uuid}"
    other_agent_id = f"QA_OTH_{run_uuid}".upper()[:20]
    other_agent_name = f"OtherBot_{run_uuid}"
    task_crashed_id = f"task_crash_{run_uuid}"

    results = {
        "suite": "Suite L: Persistence and Restart Recovery",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": run_uuid,
        "test_agent_id": test_agent_id,
        "other_agent_id": other_agent_id,
        "tests": {},
        "summary": {"total": 15, "passed": 0, "failed": 0, "errors": []}
    }

    conversation_id = None
    created_msg_ids = []
    created_task_ids = [task_crashed_id]

    print("================================================================")
    print(f"Starting Suite L Test Run with Agent ID: {test_agent_id}")
    print("================================================================")

    try:
        # L01: Create a test agent
        print("\n--- L01: Create a test agent ---")
        hire_data = {
            "id": test_agent_id,
            "name": test_agent_name,
            "role": "Persistence Test Agent",
            "specialty": "Automated QA Verification",
            "default_tool": "web_search",
            "risk_tier": "L0_READ_ONLY",
            "prompt_prefix": f"You are {test_agent_name}, a specialized persistence tester.",
            "allowed_tools": ["web_search", "web_read_page", "task_status"],
        }
        res_hire = agent_manager.save_agent_profile(hire_data)
        agent_saved = agent_manager.get_agent(test_agent_id)
        if res_hire.get("success") and agent_saved and agent_saved.id == test_agent_id:
            results["tests"]["L01"] = {
                "status": "PASS",
                "description": "Create a test agent",
                "evidence": {
                    "agent_id": agent_saved.id,
                    "name": agent_saved.name,
                    "role": agent_saved.role,
                    "risk_tier": agent_saved.risk_tier,
                    "default_tool": agent_saved.default_tool,
                    "config_path": str(agent_manager.config_path)
                }
            }
            results["summary"]["passed"] += 1
            print(f"L01 PASS: Created agent {test_agent_id}")
        else:
            raise AssertionError(f"Failed to create agent: {res_hire}")

        # L02: Create a conversation
        print("\n--- L02: Create a conversation ---")
        runtime = AgentRuntime(agent_id=test_agent_id)
        conv_title = f"Suite L Verification {run_uuid}"
        conversation_id = runtime.get_or_create_conversation(title=conv_title)
        
        # Verify in memory
        if conversation_id and conversation_id.startswith("conv_"):
            results["tests"]["L02"] = {
                "status": "PASS",
                "description": "Create a conversation",
                "evidence": {
                    "conversation_id": conversation_id,
                    "agent_id": test_agent_id,
                    "title": conv_title
                }
            }
            results["summary"]["passed"] += 1
            print(f"L02 PASS: Created conversation {conversation_id}")
        else:
            raise AssertionError(f"Invalid conversation_id returned: {conversation_id}")

        # L03: Send multiple messages
        print("\n--- L03: Send multiple messages ---")
        # Turn 1: user
        m1 = runtime.append_message(
            role="user",
            content="Hello test agent! Please verify storage.",
            conversation_id=conversation_id,
        )
        created_msg_ids.append(m1)
        time.sleep(0.05)

        # Turn 2: assistant
        m2 = runtime.append_message(
            role="assistant",
            content="Understood. Storage pipeline active.",
            conversation_id=conversation_id,
        )
        created_msg_ids.append(m2)
        time.sleep(0.05)

        # Turn 3: user
        m3 = runtime.append_message(
            role="user",
            content="Proceed with step verification.",
            conversation_id=conversation_id,
        )
        created_msg_ids.append(m3)

        msgs = runtime.load_messages(conversation_id)
        if len(msgs) == 3 and all(m["id"] in created_msg_ids for m in msgs):
            results["tests"]["L03"] = {
                "status": "PASS",
                "description": "Send multiple messages",
                "evidence": {
                    "message_count": len(msgs),
                    "message_ids": [m["id"] for m in msgs],
                    "roles": [m["role"] for m in msgs]
                }
            }
            results["summary"]["passed"] += 1
            print(f"L03 PASS: Appended 3 messages to conversation {conversation_id}")
        else:
            raise AssertionError(f"Expected 3 messages, got {len(msgs)}")

        # L04: Execute a tool call
        print("\n--- L04: Execute a tool call ---")
        mock_adapter = MagicMock(spec=ProviderAdapter)
        mock_adapter.context_budget = ContextBudget(provider="gemini", model_name="gemini-2.5-flash")
        mock_adapter.execute.side_effect = [
            NormalizedResponse(
                content="Checking status via tool...",
                tool_calls=[{"name": "web_search", "args": {"query": f"persistence verification {run_uuid}"}}],
                usage=ProviderUsage(prompt_tokens=15, completion_tokens=10, total_tokens=25, is_estimated=False),
            ),
            NormalizedResponse(
                content="Search completed. System state verified successfully.",
                tool_calls=[],
                usage=ProviderUsage(prompt_tokens=25, completion_tokens=12, total_tokens=37, is_estimated=False),
            ),
        ]
        mock_executor = MagicMock(spec=ToolExecutor)
        mock_executor.execute.return_value = ToolExecutionResult(
            success=True,
            output=f"Results for query: persistence verification {run_uuid} -> 100% OK",
        )

        runtime_tool = AgentRuntime(
            agent_id=test_agent_id,
            conversation_id=conversation_id,
            provider_adapter=mock_adapter,
            tool_executor=mock_executor,
        )
        step_res = runtime_tool.step(user_input="Execute tool call test.")
        
        # Verify step execution and tool execution
        tool_msgs = runtime.load_messages(conversation_id)
        tool_turns = [m for m in tool_msgs if m["role"] == "tool"]
        if step_res["success"] and len(step_res["tool_executions"]) == 1 and len(tool_turns) >= 1:
            tool_call_info = step_res["tool_executions"][0]
            for m in tool_msgs:
                if m["id"] not in created_msg_ids:
                    created_msg_ids.append(m["id"])
            results["tests"]["L04"] = {
                "status": "PASS",
                "description": "Execute a tool call",
                "evidence": {
                    "tool_name": tool_call_info["tool_name"],
                    "tool_args": tool_call_info["args"],
                    "success": tool_call_info["success"],
                    "output": tool_call_info["output"],
                    "final_reply": step_res["reply"]
                }
            }
            results["summary"]["passed"] += 1
            print(f"L04 PASS: Executed tool {tool_call_info['tool_name']} and logged tool turn")
        else:
            raise AssertionError(f"Tool execution failed: {step_res}")

        # L05: Verify database persistence (agent_conversations, agent_messages, turns)
        print("\n--- L05: Verify database persistence ---")
        # Also log a verbatim turn to turns table to verify all 3 tables
        sm.log_turn(
            role="user",
            content=f"Verbatim turn test for {run_uuid}",
            tool_name="web_search",
            tool_args={"query": f"turn_query_{run_uuid}"},
            tool_result="verbatim_success",
            session_id=f"{test_agent_id}:sess_{run_uuid}",
        )
        sm.flush_write_queue(timeout=2.0)

        db_convs = sm.query_db("SELECT * FROM agent_conversations WHERE id = ?", (conversation_id,))
        db_msgs = sm.query_db("SELECT * FROM agent_messages WHERE conversation_id = ? ORDER BY created_at ASC", (conversation_id,))
        db_turns = sm.query_db("SELECT * FROM turns WHERE session_id LIKE ?", (f"{test_agent_id}%",))

        if len(db_convs) == 1 and len(db_msgs) >= 5 and len(db_turns) >= 1:
            results["tests"]["L05"] = {
                "status": "PASS",
                "description": "Verify database persistence (agent_conversations, agent_messages, turns)",
                "evidence": {
                    "agent_conversations_row": dict(db_convs[0]),
                    "agent_messages_count": len(db_msgs),
                    "agent_messages_sample": [dict(m) for m in db_msgs[:2]],
                    "turns_count": len(db_turns),
                    "turns_sample": dict(db_turns[0])
                }
            }
            results["summary"]["passed"] += 1
            print("L05 PASS: DB persistence confirmed in agent_conversations, agent_messages, and turns")
        else:
            raise AssertionError(f"Persistence check failed. convs={len(db_convs)}, msgs={len(db_msgs)}, turns={len(db_turns)}")

        # L06: Simulate closing ZEZO normally (flush DB / reload state)
        print("\n--- L06: Simulate closing ZEZO normally ---")
        flushed = sm.flush_write_queue(timeout=3.0)
        q_size_before = sm.get_writer_queue_size()
        sm.shutdown_db_writer(timeout=3.0)
        writer_alive_after_shutdown = sm.is_writer_alive()

        if flushed and not writer_alive_after_shutdown:
            results["tests"]["L06"] = {
                "status": "PASS",
                "description": "Simulate closing ZEZO normally (flush DB / reload state)",
                "evidence": {
                    "queue_flushed": flushed,
                    "queue_size_before_shutdown": q_size_before,
                    "writer_alive_after_shutdown": writer_alive_after_shutdown
                }
            }
            results["summary"]["passed"] += 1
            print("L06 PASS: Flushed DB queue and completed normal shutdown")
        else:
            raise AssertionError(f"Shutdown flush failed: flushed={flushed}, writer_alive={writer_alive_after_shutdown}")

        # L07: Restart ZEZO (reinitialize registry, reload DB connection)
        print("\n--- L07: Restart ZEZO ---")
        # Reinitialize DB writer cleanly simulating app restart
        sm.reset_db_writer_for_test()
        sm._ensure_writer_started()
        writer_restarted = sm.is_writer_alive()
        # Re-initialize new AgentRegistry instance from config file
        fresh_registry = AgentRegistry(config_path=agent_manager.config_path)
        fresh_registry._load_agents()

        if writer_restarted and fresh_registry.config_path.exists():
            results["tests"]["L07"] = {
                "status": "PASS",
                "description": "Restart ZEZO (reinitialize registry, reload DB connection)",
                "evidence": {
                    "writer_restarted": writer_restarted,
                    "writer_thread_name": sm._writer_thread.name if sm._writer_thread else None,
                    "registry_agents_count": len(fresh_registry.get_all_agents())
                }
            }
            results["summary"]["passed"] += 1
            print("L07 PASS: Restarted DB connection and reinitialized AgentRegistry")
        else:
            raise AssertionError(f"Restart failed: writer_restarted={writer_restarted}")

        # L08: Verify the agent remains available
        print("\n--- L08: Verify the agent remains available ---")
        reloaded_agent = fresh_registry.get_agent(test_agent_id)
        if reloaded_agent is not None and reloaded_agent.id == test_agent_id:
            results["tests"]["L08"] = {
                "status": "PASS",
                "description": "Verify the agent remains available",
                "evidence": {
                    "agent_id": reloaded_agent.id,
                    "name": reloaded_agent.name,
                    "role": reloaded_agent.role,
                    "specialty": reloaded_agent.specialty,
                    "risk_tier": reloaded_agent.risk_tier,
                    "default_tool": reloaded_agent.default_tool
                }
            }
            results["summary"]["passed"] += 1
            print(f"L08 PASS: Agent {test_agent_id} successfully retrieved from reloaded registry")
        else:
            raise AssertionError(f"Agent {test_agent_id} not found in reloaded registry")

        # L09: Verify conversation history remains available
        print("\n--- L09: Verify conversation history remains available ---")
        fresh_runtime = AgentRuntime(agent_id=test_agent_id, conversation_id=conversation_id)
        reloaded_msgs = fresh_runtime.load_messages(conversation_id)
        if len(reloaded_msgs) == len(db_msgs) and len(reloaded_msgs) >= 5:
            results["tests"]["L09"] = {
                "status": "PASS",
                "description": "Verify conversation history remains available",
                "evidence": {
                    "conversation_id": conversation_id,
                    "persisted_message_count": len(reloaded_msgs),
                    "first_message": reloaded_msgs[0]["content"],
                    "last_message": reloaded_msgs[-1]["content"]
                }
            }
            results["summary"]["passed"] += 1
            print(f"L09 PASS: Loaded {len(reloaded_msgs)} messages from reloaded DB connection")
        else:
            raise AssertionError(f"Reloaded messages count mismatch: expected {len(db_msgs)}, got {len(reloaded_msgs)}")

        # L10: Verify message ordering (chronological)
        print("\n--- L10: Verify message ordering (chronological) ---")
        timestamps = [m["created_at"] for m in reloaded_msgs]
        is_sorted = all(timestamps[i] <= timestamps[i + 1] for i in range(len(timestamps) - 1))
        if is_sorted and len(timestamps) > 1:
            results["tests"]["L10"] = {
                "status": "PASS",
                "description": "Verify message ordering (chronological)",
                "evidence": {
                    "timestamps": timestamps,
                    "is_chronologically_sorted": is_sorted
                }
            }
            results["summary"]["passed"] += 1
            print(f"L10 PASS: All {len(timestamps)} messages verified in chronological order")
        else:
            raise AssertionError(f"Timestamps not chronological: {timestamps}")

        # L11: Verify the agent can recall the test conversation
        print("\n--- L11: Verify the agent can recall the test conversation ---")
        # Direct conversation lookup for this agent via SQLite query used by UI and runtime
        agent_convs = sm.query_db(
            "SELECT * FROM agent_conversations WHERE id = ? AND agent_id = ?",
            (conversation_id, test_agent_id),
        )
        if len(agent_convs) == 1 and agent_convs[0]["id"] == conversation_id:
            results["tests"]["L11"] = {
                "status": "PASS",
                "description": "Verify the agent can recall the test conversation",
                "evidence": {
                    "conversation_id": agent_convs[0]["id"],
                    "agent_id": agent_convs[0]["agent_id"],
                    "title": agent_convs[0]["title"],
                    "created_at": agent_convs[0]["created_at"],
                    "updated_at": agent_convs[0]["updated_at"]
                }
            }
            results["summary"]["passed"] += 1
            print(f"L11 PASS: Agent {test_agent_id} successfully recalled conversation {conversation_id}")
        else:
            raise AssertionError(f"Agent failed to recall conversation: {agent_convs}")

        # L12: Verify another agent cannot access that conversation (conversation ownership)
        print("\n--- L12: Verify another agent cannot access that conversation (conversation ownership) ---")
        # Create second agent
        agent_manager.save_agent_profile({
            "id": other_agent_id,
            "name": other_agent_name,
            "role": "Unauthorized Peer Agent",
            "specialty": "Isolation Testing",
            "default_tool": "web_search",
            "risk_tier": "L0_READ_ONLY",
        })
        
        # Test 1: Conversation lookup scoped by agent_id (as done in AgentRuntime.get_or_create_conversation & UI server)
        scoped_convs = sm.query_db(
            "SELECT id FROM agent_conversations WHERE id = ? AND agent_id = ?",
            (conversation_id, other_agent_id),
        )
        # Test 2: In runtime, when other agent instantiates runtime with conv_id owned by someone else:
        other_runtime = AgentRuntime(agent_id=other_agent_id, conversation_id=conversation_id)
        # get_or_create_conversation checks ownership (lines 123-128 of runtime.py) and creates new conv if not owner
        returned_conv_id = other_runtime.get_or_create_conversation()

        # Test 3: Messages scoped to other agent
        other_msgs_scoped = sm.query_db(
            "SELECT id FROM agent_messages WHERE conversation_id = ? AND agent_id = ?",
            (conversation_id, other_agent_id),
        )

        ownership_protected = (
            len(scoped_convs) == 0 and
            returned_conv_id != conversation_id and
            len(other_msgs_scoped) == 0
        )

        if ownership_protected:
            results["tests"]["L12"] = {
                "status": "PASS",
                "description": "Verify another agent cannot access that conversation (conversation ownership)",
                "evidence": {
                    "original_agent": test_agent_id,
                    "intruder_agent": other_agent_id,
                    "target_conversation_id": conversation_id,
                    "scoped_query_found": len(scoped_convs),
                    "intruder_runtime_assigned_new_conversation": returned_conv_id,
                    "intruder_can_claim_ownership": False
                }
            }
            results["summary"]["passed"] += 1
            print(f"L12 PASS: Conversation ownership enforced. {other_agent_id} cannot hijack {conversation_id}")
        else:
            raise AssertionError(f"Conversation ownership leak! returned_conv_id={returned_conv_id}")

        # L13: Verify no duplicate messages were created
        print("\n--- L13: Verify no duplicate messages were created ---")
        all_conv_msgs = sm.query_db("SELECT id, content FROM agent_messages WHERE conversation_id = ?", (conversation_id,))
        msg_ids = [m["id"] for m in all_conv_msgs]
        unique_ids = set(msg_ids)
        has_duplicate_ids = len(msg_ids) != len(unique_ids)

        # Check content duplicates for initial distinct messages
        initial_contents = ["Hello test agent! Please verify storage.", "Understood. Storage pipeline active.", "Proceed with step verification."]
        content_counts = {c: sum(1 for m in all_conv_msgs if m["content"] == c) for c in initial_contents}
        no_duplicate_content = all(count == 1 for count in content_counts.values())

        if not has_duplicate_ids and no_duplicate_content:
            results["tests"]["L13"] = {
                "status": "PASS",
                "description": "Verify no duplicate messages were created",
                "evidence": {
                    "total_messages": len(msg_ids),
                    "unique_ids": len(unique_ids),
                    "content_counts": content_counts,
                    "duplicates_detected": False
                }
            }
            results["summary"]["passed"] += 1
            print(f"L13 PASS: No duplicate messages detected (total={len(msg_ids)}, unique={len(unique_ids)})")
        else:
            raise AssertionError(f"Duplicate messages found! counts={content_counts}, has_dup_ids={has_duplicate_ids}")

        # L14: Verify interrupted operations are handled safely (interrupted task ledger)
        print("\n--- L14: Verify interrupted operations are handled safely ---")
        # Seed an active task in WORKING state
        now_iso = datetime.now(timezone.utc).isoformat()
        sm.execute_write(
            """
            INSERT INTO internal_task_ledger (
                id, agent_id, conversation_id, title, prompt, status, risk_tier,
                touched_files, error, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'WORKING', 'L1_MUTATION', '["test.py"]', NULL, ?, ?)
            """,
            (task_crashed_id, test_agent_id, conversation_id, "Critical File Sync", "Run sync script", now_iso, now_iso),
        )

        # Reconcile interrupted tasks
        reconciled_count = reconcile_interrupted_tasks()
        interrupted_list = get_interrupted_tasks()
        target_interrupted = next((t for t in interrupted_list if t["id"] == task_crashed_id), None)

        if reconciled_count >= 1 and target_interrupted is not None:
            results["tests"]["L14"] = {
                "status": "PASS",
                "description": "Verify interrupted operations are handled safely (interrupted task ledger)",
                "evidence": {
                    "reconciled_count": reconciled_count,
                    "task_id": target_interrupted["id"],
                    "status": target_interrupted["status"],
                    "interrupted_at": target_interrupted["interrupted_at"],
                    "risk_tier": target_interrupted["risk_tier"]
                }
            }
            results["summary"]["passed"] += 1
            print(f"L14 PASS: Task {task_crashed_id} safely transitioned to INTERRUPTED state on recovery")
        else:
            raise AssertionError(f"Interrupted task reconciliation failed: reconciled={reconciled_count}, found={target_interrupted}")

        # L15: Verify task statuses remain consistent
        print("\n--- L15: Verify task statuses remain consistent ---")
        # Test 1: Unconfirmed restart must be blocked to prevent duplicated side effects
        unconfirmed_res = restart_interrupted_task(task_crashed_id, confirmed=False)
        assert unconfirmed_res["success"] is False
        assert unconfirmed_res["requires_confirmation"] is True

        # Test 2: Confirmed restart transitions old task to RESTARTED and creates new WORKING task
        confirmed_res = restart_interrupted_task(task_crashed_id, confirmed=True)
        assert confirmed_res["success"] is True
        new_task_id = confirmed_res["new_task_id"]
        created_task_ids.append(new_task_id)

        # Query DB to verify consistency
        old_task_row = sm.query_db("SELECT status, updated_at FROM internal_task_ledger WHERE id = ?", (task_crashed_id,))
        new_task_row = sm.query_db("SELECT status, prompt, risk_tier FROM internal_task_ledger WHERE id = ?", (new_task_id,))

        if (
            len(old_task_row) == 1 and old_task_row[0]["status"] == "RESTARTED" and
            len(new_task_row) == 1 and new_task_row[0]["status"] == "WORKING"
        ):
            results["tests"]["L15"] = {
                "status": "PASS",
                "description": "Verify task statuses remain consistent",
                "evidence": {
                    "unconfirmed_restart_blocked": unconfirmed_res,
                    "confirmed_restart": confirmed_res,
                    "old_task_status": old_task_row[0]["status"],
                    "new_task_status": new_task_row[0]["status"]
                }
            }
            results["summary"]["passed"] += 1
            print("L15 PASS: Task state transitions are strictly consistent (RESTARTED -> WORKING)")
        else:
            raise AssertionError(f"Task status inconsistency: old={old_task_row}, new={new_task_row}")

    except Exception as exc:
        results["summary"]["failed"] += 1
        results["summary"]["errors"].append(str(exc))
        print(f"\n❌ SUITE L FAILURE: {exc}")
        import traceback
        traceback.print_exc()

    finally:
        # CLEANUP: Only test data created
        print("\n--- Cleaning up test artifacts ---")
        try:
            # 1. Clean test agents from config
            agent_manager.delete_agent(test_agent_id)
            agent_manager.delete_agent(other_agent_id)
            print(f"Cleaned up test agents {test_agent_id}, {other_agent_id}")

            # 2. Clean messages and conversation from sqlite
            if conversation_id:
                sm.execute_write("DELETE FROM agent_messages WHERE conversation_id = ?", (conversation_id,))
                sm.execute_write("DELETE FROM agent_conversations WHERE id = ?", (conversation_id,))
                print(f"Cleaned up conversation {conversation_id} and messages")

            # 3. Clean turns created during test
            sm.execute_write("DELETE FROM turns WHERE session_id LIKE ?", (f"{test_agent_id}%",))
            print("Cleaned up test turns")

            # 4. Clean task ledger entries created
            for tid in created_task_ids:
                sm.execute_write("DELETE FROM internal_task_ledger WHERE id = ?", (tid,))
            print(f"Cleaned up task ledger entries: {created_task_ids}")

            sm.flush_write_queue(timeout=2.0)
        except Exception as clean_err:
            print(f"⚠️ Error during cleanup: {clean_err}")

    # Write results to qa_artifacts/suite_l_results.json
    out_path = Path("qa_artifacts/suite_l_results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults successfully written to {out_path.resolve()}")
    print(f"Passed: {results['summary']['passed']}/{results['summary']['total']}")
    return results


if __name__ == "__main__":
    res = run_suite_l()
    sys.exit(0 if res["summary"]["failed"] == 0 else 1)
