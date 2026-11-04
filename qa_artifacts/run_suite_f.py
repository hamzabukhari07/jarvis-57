"""
qa_artifacts/run_suite_f.py - Live Verification Runner for Suite F: Independent Agent Conversations.
Tests:
  F01. Create two test agents (or use two existing distinct agents e.g. MICHAEL and ATLAS/VERVE).
  F02. Start a conversation with Agent A.
  F03. Start a separate conversation with Agent B.
  F04. Give each agent different private test information.
  F05. Ask Agent A about Agent B's information.
  F06. Ask Agent B about Agent A's information.
  F07. Verify that conversations remain isolated.
  F08. Create multiple conversations for the same agent.
  F09. Switch between conversations.
  F10. Verify each conversation loads its own history.
  F11. Verify conversation IDs are correctly associated with agents.
  F12. Verify archived/deleted conversation behavior where supported.
  F13. Restart ZEZO / registry reload and repeat conversation selection.

CRITICAL: Never delete existing user conversations. Clean up ONLY our own test-generated conversations.
"""

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

# Ensure repo root is on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# ZEZO core imports
from core.agents.registry import get_agent_registry, AgentProfile
from core.agents.runtime import AgentRuntime
from core.agents.provider_adapter import ProviderAdapter, NormalizedResponse, ProviderUsage
from core.agents.context_budget import ContextBudget
from core.ui_server import ZezoUIServer
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from memory.sqlite_memory import query_db, execute_write

RESULTS = {
    "suite": "Suite F: Independent Agent Conversations",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "summary": {"total": 13, "passed": 0, "failed": 0},
    "tests": {},
    "cleanup_log": []
}

CREATED_TEST_CONVERSATIONS = set()
CREATED_TEST_AGENTS = set()

def create_mock_adapter(agent_name: str, memory_store: dict):
    """
    Creates a mock ProviderAdapter that reflects real LLM behavior:
    It constructs an answer using ONLY the messages passed in the runtime conversation context!
    If private information from another agent is NOT in the conversation messages, it cannot know it.
    """
    mock = MagicMock(spec=ProviderAdapter)
    mock.context_budget = ContextBudget(provider="gemini", model_name="gemini-2.5-flash")
    
    def side_effect(messages, tools=None, system_prompt="", **kwargs):
        # Scan messages in conversation (excluding the current user prompt at the end)
        history_msgs = messages[:-1] if len(messages) > 1 else []
        history_text = " ".join([m.get("content", "") for m in history_msgs if isinstance(m, dict)])
        
        # Determine the last user query
        last_msg = messages[-1]["content"] if messages else ""
        
        reply = f"[{agent_name}] Processed: {last_msg[:40]}."
        
        # If user is asking about Orion / Atlas secret:
        if "what is atlas" in last_msg.lower() or ("orion" in last_msg.lower() and "?" in last_msg):
            if "SECRET_ORION" in history_text:
                reply = f"[{agent_name}] Yes, Orion secret is in our conversation: SECRET_ORION_CODE_7712_CLASSIFIED"
            else:
                reply = f"[{agent_name}] I have no knowledge or record of any Project Orion or Atlas secret in this session."
                
        # If user is asking about Pegasus / Michael secret:
        elif "what is michael" in last_msg.lower() or ("pegasus" in last_msg.lower() and "?" in last_msg):
            if "SECRET_PEGASUS" in history_text:
                reply = f"[{agent_name}] Yes, Pegasus secret is in our conversation: SECRET_PEGASUS_KEY_9941_TOP_SECRET"
            else:
                reply = f"[{agent_name}] I have no knowledge or record of any Project Pegasus or Michael secret in this session."

        return NormalizedResponse(
            content=reply,
            tool_calls=[],
            usage=ProviderUsage(prompt_tokens=25, completion_tokens=15, total_tokens=40, is_estimated=False)
        )
        
    mock.execute.side_effect = side_effect
    return mock


async def run_suite_f():
    print("=" * 70)
    print("STARTING SUITE F: INDEPENDENT AGENT CONVERSATIONS TEST RUN")
    print("=" * 70)
    
    # Setup Test Client for UI endpoints
    ui = ZezoUIServer(None)
    app = web.Application()
    app.router.add_get('/api/agents/conversations', ui._agent_conversations_get_handler)
    app.router.add_post('/api/agents/conversations', ui._agent_conversations_create_handler)
    app.router.add_delete('/api/agents/conversations', ui._agent_conversations_delete_handler)
    app.router.add_get('/api/agents/messages', ui._agent_messages_handler)
    app.router.add_post('/api/agents/chat', ui._agent_chat_handler)
    
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    
    try:
        registry = get_agent_registry()
        
        # -------------------------------------------------------------
        # F01. Create two test agents (or use two existing distinct agents)
        # -------------------------------------------------------------
        print("\n[F01] Testing Agent Profiles / Creation...")
        agent_a_id = "MICHAEL"
        agent_b_id = "ATLAS"
        
        # Ensure ATLAS exists or create it
        atlas_profile = registry.get_agent("ATLAS")
        if not atlas_profile:
            atlas_profile = AgentProfile(
                id="ATLAS",
                name="Atlas",
                role="Autonomous Infrastructure Specialist",
                specialty="Cloud & DevOps",
                color="#00BCD4",
                avatar_pixel="devops_lead",
                default_tool="antigravity_run",
                risk_tier="L0_READ_ONLY",
                prompt_prefix="You are Atlas, autonomous infrastructure specialist.",
                model_id="gemini-2.5-flash",
                engine="antigravity",
                soul_markdown="You are Atlas, lead DevOps engineer."
            )
            registry.save_agent_profile(atlas_profile.__dict__)
            CREATED_TEST_AGENTS.add("ATLAS")
            
        profile_a = registry.get_agent(agent_a_id)
        profile_b = registry.get_agent(agent_b_id)
        
        f01_pass = profile_a is not None and profile_b is not None and profile_a.id != profile_b.id
        RESULTS["tests"]["F01"] = {
            "name": "Create two test agents (or use two existing distinct agents e.g. MICHAEL and ATLAS)",
            "passed": f01_pass,
            "evidence": {
                "agent_a": {"id": profile_a.id, "name": profile_a.name, "role": profile_a.role},
                "agent_b": {"id": profile_b.id, "name": profile_b.name, "role": profile_b.role}
            }
        }
        print(f"  F01 Status: {'PASS' if f01_pass else 'FAIL'}")
        
        # -------------------------------------------------------------
        # F02. Start a conversation with Agent A (MICHAEL)
        # -------------------------------------------------------------
        print("\n[F02] Starting conversation with Agent A...")
        title_a = f"QA_SuiteF_Michael_{uuid.uuid4().hex[:6]}"
        runtime_a = AgentRuntime(agent_id=agent_a_id)
        conv_a_id = runtime_a.get_or_create_conversation(title=title_a)
        CREATED_TEST_CONVERSATIONS.add(conv_a_id)
        
        # Verify via DB
        conv_a_db = query_db("SELECT * FROM agent_conversations WHERE id = ?", (conv_a_id,))
        f02_pass = len(conv_a_db) == 1 and conv_a_db[0]["agent_id"] == agent_a_id and conv_a_db[0]["title"] == title_a
        RESULTS["tests"]["F02"] = {
            "name": "Start a conversation with Agent A",
            "passed": f02_pass,
            "evidence": {"conversation_id": conv_a_id, "agent_id": agent_a_id, "title": title_a, "db_row": dict(conv_a_db[0])}
        }
        print(f"  F02 Status: {'PASS' if f02_pass else 'FAIL'} (conv_id: {conv_a_id})")

        # -------------------------------------------------------------
        # F03. Start a separate conversation with Agent B (ATLAS)
        # -------------------------------------------------------------
        print("\n[F03] Starting separate conversation with Agent B...")
        title_b = f"QA_SuiteF_Atlas_{uuid.uuid4().hex[:6]}"
        runtime_b = AgentRuntime(agent_id=agent_b_id)
        conv_b_id = runtime_b.get_or_create_conversation(title=title_b)
        CREATED_TEST_CONVERSATIONS.add(conv_b_id)
        
        # Verify via DB and verify separation
        conv_b_db = query_db("SELECT * FROM agent_conversations WHERE id = ?", (conv_b_id,))
        f03_pass = (
            len(conv_b_db) == 1 and 
            conv_b_db[0]["agent_id"] == agent_b_id and 
            conv_b_db[0]["title"] == title_b and 
            conv_b_id != conv_a_id
        )
        RESULTS["tests"]["F03"] = {
            "name": "Start a separate conversation with Agent B",
            "passed": f03_pass,
            "evidence": {"conversation_id": conv_b_id, "agent_id": agent_b_id, "title": title_b, "db_row": dict(conv_b_db[0])}
        }
        print(f"  F03 Status: {'PASS' if f03_pass else 'FAIL'} (conv_id: {conv_b_id})")

        # -------------------------------------------------------------
        # F04. Give each agent different private test information
        # -------------------------------------------------------------
        print("\n[F04] Giving each agent different private test information...")
        secret_a = "SECRET_PEGASUS_KEY_9941_TOP_SECRET"
        secret_b = "SECRET_ORION_CODE_7712_CLASSIFIED"
        
        msg_a_user = f"Michael, please keep this safe: Project Pegasus code is {secret_a}."
        msg_b_user = f"Atlas, here is your classified info: Project Orion secret is {secret_b}."
        
        mock_a = create_mock_adapter("MICHAEL", {})
        mock_b = create_mock_adapter("ATLAS", {})
        
        runtime_a.provider_adapter = mock_a
        runtime_b.provider_adapter = mock_b
        
        step_a1 = runtime_a.step(user_input=msg_a_user, conversation_id=conv_a_id)
        step_b1 = runtime_b.step(user_input=msg_b_user, conversation_id=conv_b_id)
        
        msgs_a = runtime_a.load_messages(conv_a_id)
        msgs_b = runtime_b.load_messages(conv_b_id)
        
        f04_pass = (
            step_a1["success"] is True and
            step_b1["success"] is True and
            any(secret_a in m["content"] for m in msgs_a) and
            not any(secret_b in m["content"] for m in msgs_a) and
            any(secret_b in m["content"] for m in msgs_b) and
            not any(secret_a in m["content"] for m in msgs_b)
        )
        RESULTS["tests"]["F04"] = {
            "name": "Give each agent different private test information",
            "passed": f04_pass,
            "evidence": {
                "agent_a_messages_count": len(msgs_a),
                "agent_b_messages_count": len(msgs_b),
                "secret_a_in_conv_a": any(secret_a in m["content"] for m in msgs_a),
                "secret_b_in_conv_a": any(secret_b in m["content"] for m in msgs_a),
                "secret_b_in_conv_b": any(secret_b in m["content"] for m in msgs_b),
                "secret_a_in_conv_b": any(secret_a in m["content"] for m in msgs_b),
            }
        }
        print(f"  F04 Status: {'PASS' if f04_pass else 'FAIL'}")

        # -------------------------------------------------------------
        # F05. Ask Agent A about Agent B's information
        # -------------------------------------------------------------
        print("\n[F05] Asking Agent A about Agent B's private information...")
        query_a_for_b = "Michael, what is Atlas's secret code for Project Orion?"
        step_a2 = runtime_a.step(user_input=query_a_for_b, conversation_id=conv_a_id)
        
        # Agent A's reply must NOT leak Agent B's secret
        f05_pass = (
            step_a2["success"] is True and
            secret_b not in step_a2.get("reply", "") and
            "no knowledge" in step_a2.get("reply", "").lower()
        )
        RESULTS["tests"]["F05"] = {
            "name": "Ask Agent A about Agent B's information",
            "passed": f05_pass,
            "evidence": {
                "prompt": query_a_for_b,
                "reply": step_a2.get("reply"),
                "secret_b_leaked": secret_b in step_a2.get("reply", "")
            }
        }
        print(f"  F05 Status: {'PASS' if f05_pass else 'FAIL'} (Reply: {step_a2.get('reply')})")

        # -------------------------------------------------------------
        # F06. Ask Agent B about Agent A's information
        # -------------------------------------------------------------
        print("\n[F06] Asking Agent B about Agent A's private information...")
        query_b_for_a = "Atlas, what is Michael's secret key for Project Pegasus?"
        step_b2 = runtime_b.step(user_input=query_b_for_a, conversation_id=conv_b_id)
        
        # Agent B's reply must NOT leak Agent A's secret
        f06_pass = (
            step_b2["success"] is True and
            secret_a not in step_b2.get("reply", "") and
            "no knowledge" in step_b2.get("reply", "").lower()
        )
        RESULTS["tests"]["F06"] = {
            "name": "Ask Agent B about Agent A's information",
            "passed": f06_pass,
            "evidence": {
                "prompt": query_b_for_a,
                "reply": step_b2.get("reply"),
                "secret_a_leaked": secret_a in step_b2.get("reply", "")
            }
        }
        print(f"  F06 Status: {'PASS' if f06_pass else 'FAIL'} (Reply: {step_b2.get('reply')})")

        # -------------------------------------------------------------
        # F07. Verify that conversations remain isolated
        # -------------------------------------------------------------
        print("\n[F07] Verifying complete conversation isolation...")
        # Inspect raw SQLite database records for both conversations
        conv_a_msgs = query_db("SELECT * FROM agent_messages WHERE conversation_id = ? ORDER BY created_at ASC", (conv_a_id,))
        conv_b_msgs = query_db("SELECT * FROM agent_messages WHERE conversation_id = ? ORDER BY created_at ASC", (conv_b_id,))
        
        # Cross-conversation checks
        conv_a_agent_ids = set(m["agent_id"] for m in conv_a_msgs)
        conv_b_agent_ids = set(m["agent_id"] for m in conv_b_msgs)
        
        all_conv_a_content = " ".join(m["content"] for m in conv_a_msgs)
        all_conv_b_content = " ".join(m["content"] for m in conv_b_msgs)
        
        f07_pass = (
            conv_a_agent_ids == {agent_a_id} and
            conv_b_agent_ids == {agent_b_id} and
            secret_a in all_conv_a_content and
            secret_b not in all_conv_a_content and
            secret_b in all_conv_b_content and
            secret_a not in all_conv_b_content
        )
        RESULTS["tests"]["F07"] = {
            "name": "Verify that conversations remain isolated",
            "passed": f07_pass,
            "evidence": {
                "conv_a_messages_count": len(conv_a_msgs),
                "conv_b_messages_count": len(conv_b_msgs),
                "conv_a_agent_ids": list(conv_a_agent_ids),
                "conv_b_agent_ids": list(conv_b_agent_ids),
                "secret_b_in_conv_a_db": secret_b in all_conv_a_content,
                "secret_a_in_conv_b_db": secret_a in all_conv_b_content,
            }
        }
        print(f"  F07 Status: {'PASS' if f07_pass else 'FAIL'}")

        # -------------------------------------------------------------
        # F08. Create multiple conversations for the same agent
        # -------------------------------------------------------------
        print("\n[F08] Creating multiple conversations for the same agent...")
        # Create thread 2 and thread 3 for MICHAEL
        title_a2 = f"QA_SuiteF_Michael_Thread2_{uuid.uuid4().hex[:6]}"
        title_a3 = f"QA_SuiteF_Michael_Thread3_{uuid.uuid4().hex[:6]}"
        
        resp_c2 = await client.post('/api/agents/conversations', json={"agent_id": agent_a_id, "title": title_a2})
        data_c2 = await resp_c2.json()
        conv_a2_id = data_c2["conversation_id"]
        CREATED_TEST_CONVERSATIONS.add(conv_a2_id)
        
        resp_c3 = await client.post('/api/agents/conversations', json={"agent_id": agent_a_id, "title": title_a3})
        data_c3 = await resp_c3.json()
        conv_a3_id = data_c3["conversation_id"]
        CREATED_TEST_CONVERSATIONS.add(conv_a3_id)
        
        f08_pass = (
            resp_c2.status == 200 and data_c2.get("success") is True and
            resp_c3.status == 200 and data_c3.get("success") is True and
            len({conv_a_id, conv_a2_id, conv_a3_id}) == 3
        )
        RESULTS["tests"]["F08"] = {
            "name": "Create multiple conversations for the same agent",
            "passed": f08_pass,
            "evidence": {
                "thread_1_id": conv_a_id,
                "thread_2_id": conv_a2_id,
                "thread_3_id": conv_a3_id,
                "agent_id": agent_a_id
            }
        }
        print(f"  F08 Status: {'PASS' if f08_pass else 'FAIL'} (Threads: {conv_a_id}, {conv_a2_id}, {conv_a3_id})")

        # -------------------------------------------------------------
        # F09. Switch between conversations
        # -------------------------------------------------------------
        print("\n[F09] Switching between conversations and posting distinct content...")
        # Post turn to conv_a2
        runtime_a2 = AgentRuntime(agent_id=agent_a_id, conversation_id=conv_a2_id, provider_adapter=mock_a)
        msg_a2 = "Thread 2: Exploring microservice decomposition patterns."
        step_a2_res = runtime_a2.step(user_input=msg_a2)
        
        # Post turn to conv_a3
        runtime_a3 = AgentRuntime(agent_id=agent_a_id, conversation_id=conv_a3_id, provider_adapter=mock_a)
        msg_a3 = "Thread 3: Reviewing database sharding strategies."
        step_a3_res = runtime_a3.step(user_input=msg_a3)
        
        # Switch back to thread 1 (conv_a_id) and post turn
        msg_a1_new = "Thread 1 update: Checking back on Pegasus status."
        step_a1_new = runtime_a.step(user_input=msg_a1_new, conversation_id=conv_a_id)
        
        f09_pass = (
            step_a2_res["success"] is True and
            step_a3_res["success"] is True and
            step_a1_new["success"] is True
        )
        RESULTS["tests"]["F09"] = {
            "name": "Switch between conversations",
            "passed": f09_pass,
            "evidence": {
                "thread_2_step": step_a2_res.get("reply"),
                "thread_3_step": step_a3_res.get("reply"),
                "thread_1_return_step": step_a1_new.get("reply"),
            }
        }
        print(f"  F09 Status: {'PASS' if f09_pass else 'FAIL'}")

        # -------------------------------------------------------------
        # F10. Verify each conversation loads its own history
        # -------------------------------------------------------------
        print("\n[F10] Verifying each conversation loads its own isolated history...")
        # Query endpoint /api/agents/messages for each thread
        resp_m1 = await client.get(f'/api/agents/messages?conversation_id={conv_a_id}')
        data_m1 = await resp_m1.json()
        messages_1 = data_m1.get("messages", [])
        
        resp_m2 = await client.get(f'/api/agents/messages?conversation_id={conv_a2_id}')
        data_m2 = await resp_m2.json()
        messages_2 = data_m2.get("messages", [])
        
        resp_m3 = await client.get(f'/api/agents/messages?conversation_id={conv_a3_id}')
        data_m3 = await resp_m3.json()
        messages_3 = data_m3.get("messages", [])
        
        content_1 = " ".join(m.get("content", "") for m in messages_1)
        content_2 = " ".join(m.get("content", "") for m in messages_2)
        content_3 = " ".join(m.get("content", "") for m in messages_3)
        
        f10_pass = (
            "Pegasus" in content_1 and "microservice" not in content_1 and "sharding" not in content_1 and
            "microservice" in content_2 and "Pegasus" not in content_2 and "sharding" not in content_2 and
            "sharding" in content_3 and "Pegasus" not in content_3 and "microservice" not in content_3
        )
        RESULTS["tests"]["F10"] = {
            "name": "Verify each conversation loads its own history",
            "passed": f10_pass,
            "evidence": {
                "thread_1_msg_count": len(messages_1),
                "thread_2_msg_count": len(messages_2),
                "thread_3_msg_count": len(messages_3),
                "thread_1_has_own_content": "Pegasus" in content_1,
                "thread_1_has_thread_2_content": "microservice" in content_1,
                "thread_2_has_own_content": "microservice" in content_2,
                "thread_2_has_thread_1_content": "Pegasus" in content_2,
                "thread_3_has_own_content": "sharding" in content_3,
            }
        }
        print(f"  F10 Status: {'PASS' if f10_pass else 'FAIL'}")

        # -------------------------------------------------------------
        # F11. Verify conversation IDs are correctly associated with agents
        # -------------------------------------------------------------
        print("\n[F11] Verifying conversation IDs are correctly associated with agents...")
        resp_michael_convs = await client.get(f'/api/agents/conversations?agent_id={agent_a_id}')
        data_michael_convs = await resp_michael_convs.json()
        michael_conv_ids = [c["id"] for c in data_michael_convs.get("conversations", [])]
        
        resp_atlas_convs = await client.get(f'/api/agents/conversations?agent_id={agent_b_id}')
        data_atlas_convs = await resp_atlas_convs.json()
        atlas_conv_ids = [c["id"] for c in data_atlas_convs.get("conversations", [])]
        
        f11_pass = (
            conv_a_id in michael_conv_ids and
            conv_a2_id in michael_conv_ids and
            conv_a3_id in michael_conv_ids and
            conv_b_id not in michael_conv_ids and
            conv_b_id in atlas_conv_ids and
            conv_a_id not in atlas_conv_ids
        )
        RESULTS["tests"]["F11"] = {
            "name": "Verify conversation IDs are correctly associated with agents",
            "passed": f11_pass,
            "evidence": {
                "michael_conv_contains_own_threads": all(x in michael_conv_ids for x in [conv_a_id, conv_a2_id, conv_a3_id]),
                "michael_conv_contains_atlas_thread": conv_b_id in michael_conv_ids,
                "atlas_conv_contains_own_thread": conv_b_id in atlas_conv_ids,
                "atlas_conv_contains_michael_threads": any(x in atlas_conv_ids for x in [conv_a_id, conv_a2_id, conv_a3_id])
            }
        }
        print(f"  F11 Status: {'PASS' if f11_pass else 'FAIL'}")

        # -------------------------------------------------------------
        # F12. Verify archived/deleted conversation behavior where supported
        # -------------------------------------------------------------
        print("\n[F12] Verifying archived/deleted conversation behavior...")
        # Create a disposable conversation specifically for testing deletion
        title_del = f"QA_SuiteF_Disposable_{uuid.uuid4().hex[:6]}"
        resp_cdel = await client.post('/api/agents/conversations', json={"agent_id": agent_a_id, "title": title_del})
        data_cdel = await resp_cdel.json()
        conv_del_id = data_cdel["conversation_id"]
        
        # Verify it exists in GET
        resp_before_del = await client.get(f'/api/agents/conversations?agent_id={agent_a_id}')
        data_before = await resp_before_del.json()
        ids_before = [c["id"] for c in data_before.get("conversations", [])]
        assert conv_del_id in ids_before
        
        # Delete via DELETE /api/agents/conversations
        resp_del = await client.delete(f'/api/agents/conversations?conversation_id={conv_del_id}')
        data_del = await resp_del.json()
        
        # Verify it no longer appears in GET
        resp_after_del = await client.get(f'/api/agents/conversations?agent_id={agent_a_id}')
        data_after = await resp_after_del.json()
        ids_after = [c["id"] for c in data_after.get("conversations", [])]
        
        # Also verify archival flag support in DB (is_archived = 1)
        # In sqlite_memory: DELETE /api/agents/conversations deletes from agent_conversations.
        # Let's also test archiving via UPDATE agent_conversations SET is_archived = 1
        title_arch = f"QA_SuiteF_Archived_{uuid.uuid4().hex[:6]}"
        runtime_arch = AgentRuntime(agent_id=agent_a_id)
        conv_arch_id = runtime_arch.get_or_create_conversation(title=title_arch)
        CREATED_TEST_CONVERSATIONS.add(conv_arch_id)
        
        # Set is_archived = 1
        execute_write("UPDATE agent_conversations SET is_archived = 1 WHERE id = ?", (conv_arch_id,))
        
        # GET /api/agents/conversations filters WHERE is_archived = 0!
        resp_arch_check = await client.get(f'/api/agents/conversations?agent_id={agent_a_id}')
        data_arch_check = await resp_arch_check.json()
        archived_ids = [c["id"] for c in data_arch_check.get("conversations", [])]
        
        f12_pass = (
            resp_del.status == 200 and
            data_del.get("success") is True and
            conv_del_id not in ids_after and
            conv_arch_id not in archived_ids
        )
        RESULTS["tests"]["F12"] = {
            "name": "Verify archived/deleted conversation behavior where supported",
            "passed": f12_pass,
            "evidence": {
                "deleted_conversation_id": conv_del_id,
                "delete_response": data_del,
                "deleted_absent_from_list": conv_del_id not in ids_after,
                "archived_conversation_id": conv_arch_id,
                "archived_absent_from_active_list": conv_arch_id not in archived_ids
            }
        }
        print(f"  F12 Status: {'PASS' if f12_pass else 'FAIL'}")

        # -------------------------------------------------------------
        # F13. Restart ZEZO / registry reload and repeat conversation selection
        # -------------------------------------------------------------
        print("\n[F13] Simulating ZEZO restart / registry reload and repeating conversation selection...")
        # Force re-initialization of registry singleton from disk
        import core.agents.registry as reg_module
        reg_module._REGISTRY = None
        reloaded_registry = reg_module.get_agent_registry()
        
        # Verify agents loaded cleanly after registry reload
        reloaded_michael = reloaded_registry.get_agent(agent_a_id)
        assert reloaded_michael is not None
        
        # Instantiate fresh runtime with existing conversation ID (simulating cold boot load)
        fresh_runtime = AgentRuntime(agent_id=agent_a_id, conversation_id=conv_a_id)
        selected_conv_id = fresh_runtime.get_or_create_conversation()
        
        # Load messages in fresh runtime
        reloaded_messages = fresh_runtime.load_messages()
        
        f13_pass = (
            selected_conv_id == conv_a_id and
            len(reloaded_messages) >= 3 and
            reloaded_messages[0]["content"] == msg_a_user and
            secret_a in reloaded_messages[0]["content"]
        )
        RESULTS["tests"]["F13"] = {
            "name": "Restart ZEZO / registry reload and repeat conversation selection",
            "passed": f13_pass,
            "evidence": {
                "reloaded_agent_id": reloaded_michael.id,
                "selected_conversation_id": selected_conv_id,
                "expected_conversation_id": conv_a_id,
                "messages_retained_count": len(reloaded_messages),
                "secret_a_retained": any(secret_a in m["content"] for m in reloaded_messages)
            }
        }
        print(f"  F13 Status: {'PASS' if f13_pass else 'FAIL'} (Retained {len(reloaded_messages)} msgs)")

    finally:
        # Clean up our test server
        await client.close()
        
        # -------------------------------------------------------------
        # CLEANUP: Only remove our test conversations, NEVER user conversations!
        # -------------------------------------------------------------
        print("\n[CLEANUP] Cleaning up test-generated conversations...")
        for cid in CREATED_TEST_CONVERSATIONS:
            try:
                execute_write("DELETE FROM agent_messages WHERE conversation_id = ?", (cid,))
                execute_write("DELETE FROM agent_conversations WHERE id = ?", (cid,))
                RESULTS["cleanup_log"].append(f"Deleted test conversation {cid}")
            except Exception as e:
                RESULTS["cleanup_log"].append(f"Failed deleting {cid}: {e}")
                
        # Clean up test agent if created by us
        for aid in CREATED_TEST_AGENTS:
            try:
                get_agent_registry().delete_agent(aid)
                RESULTS["cleanup_log"].append(f"Deleted test agent {aid}")
            except Exception as e:
                RESULTS["cleanup_log"].append(f"Failed deleting agent {aid}: {e}")
                
    # Calculate totals
    passed_count = sum(1 for t in RESULTS["tests"].values() if t.get("passed") is True)
    failed_count = sum(1 for t in RESULTS["tests"].values() if t.get("passed") is False)
    RESULTS["summary"]["passed"] = passed_count
    RESULTS["summary"]["failed"] = failed_count
    
    # Save to qa_artifacts/suite_f_results.json
    out_file = os.path.abspath("qa_artifacts/suite_f_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, indent=2)
        
    print("\n" + "=" * 70)
    print(f"SUITE F RUN COMPLETE: {passed_count}/{len(RESULTS['tests'])} PASSED. (Failed: {failed_count})")
    print(f"Results written to: {out_file}")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_suite_f())
