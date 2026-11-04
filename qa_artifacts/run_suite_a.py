"""
qa_artifacts/run_suite_a.py — Automated QA test harness for Suite A: Agent Creation.

Covers:
A01. Create a new custom agent.
A02. Assign a unique name.
A03. Configure its role.
A04. Configure its specialty.
A05. Set custom personality/system instructions.
A06. Select a conversational model.
A07. Select a task execution engine.
A08. Configure available tools.
A09. Configure agent permissions (risk_tier and governance).
A10. Save the agent.
A11. Verify that the agent appears in the UI (via live UI server /api/agents/state).
A12. Verify that its configuration is persisted (in config/agents.json and memory).
A13. Restart ZEZO / registry refresh and verify the agent still exists.
A14. Create multiple agents with different identities.
A15. Verify duplicate or invalid configurations are handled correctly.

Author: Hamza Bukhari (Architect) / Subagent 1 (Autonomous QA)
"""

import asyncio
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, List

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from core.agents_manager import AgentManager, agent_manager
from core.agents.registry import AgentRegistry, AgentProfile
from core.ui_server import ZezoUIServer, get_ui_server
from memory.sqlite_memory import execute_write, query_db


TEST_PORT = 8991
UI_STATE_URL = f"http://127.0.0.1:{TEST_PORT}/api/agents/state"
UI_SAVE_URL = f"http://127.0.0.1:{TEST_PORT}/api/agents/save_agent"
UI_PROFILE_URL = f"http://127.0.0.1:{TEST_PORT}/api/agents/agent"
UI_SOUL_URL = f"http://127.0.0.1:{TEST_PORT}/api/agents/save_soul"
UI_DELETE_URL = f"http://127.0.0.1:{TEST_PORT}/api/agents/delete_agent"

RESULTS: Dict[str, Any] = {
    "suite": "Suite A: Agent Creation",
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "total_tests": 15,
    "passed": 0,
    "failed": 0,
    "test_cases": {}
}


def log_test_result(test_id: str, name: str, status: str, evidence: Dict[str, Any], notes: str = ""):
    RESULTS["test_cases"][test_id] = {
        "name": name,
        "status": status,
        "notes": notes,
        "evidence": evidence
    }
    if status == "PASSED":
        RESULTS["passed"] += 1
        print(f"[{test_id}] PASSED: {name}")
    else:
        RESULTS["failed"] += 1
        print(f"[{test_id}] FAILED: {name} - Notes: {notes}")


def http_get(url: str) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "ZEZO-QA-Suite-A"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_post(url: str, data: Dict[str, Any]) -> Dict[str, Any]:
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "ZEZO-QA-Suite-A"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_all_tests():
    print("=== Starting Suite A (Agent Creation) QA Automated Execution ===")

    # Start an isolated UI Server on dedicated QA port 8991
    qa_server = ZezoUIServer(host="127.0.0.1", port=TEST_PORT)
    qa_server.start()
    print(f"[*] Started ZezoUIServer on 127.0.0.1:{TEST_PORT}")
    time.sleep(1.5)

    created_agent_ids = []

    try:
        # -------------------------------------------------------------
        # A01 & A02 & A03 & A04 & A05 & A06 & A07 & A08 & A09 & A10:
        # Comprehensive Agent Creation via UI Server endpoint
        # -------------------------------------------------------------
        agent_a1_payload = {
            "id": "CYBER_SENTINEL",
            "name": "Cyber Sentinel",
            "role": "Security Auditing & Threat Detection Specialist",
            "specialty": "Vulnerability scanning, AST audit, secure architecture validation",
            "prompt_prefix": "You are Cyber Sentinel, an elite cybersecurity autonomous auditor for ZEZO.",
            "soul_markdown": "# Cyber Sentinel Soul\nAutonomous security auditing agent.",
            "model_id": "gemini-2.5-pro",
            "engine": "opencode",
            "default_tool": "opencode_run",
            "allowed_tools": ["opencode_run", "task_status", "web_search"],
            "risk_tier": "L1_MUTATION",
            "color": "#10b981",
            "capabilities": ["security_audit", "code_review"]
        }

        save_resp = http_post(UI_SAVE_URL, agent_a1_payload)
        created_agent_ids.append("CYBER_SENTINEL")
        
        # Test A01: Create a new custom agent
        if save_resp.get("success") is True and save_resp.get("agent", {}).get("id") == "CYBER_SENTINEL":
            log_test_result("A01", "Create a new custom agent", "PASSED", {
                "endpoint": UI_SAVE_URL,
                "response": save_resp
            })
        else:
            log_test_result("A01", "Create a new custom agent", "FAILED", {
                "response": save_resp
            }, "Agent creation returned failure or wrong agent id")

        # Test A02: Assign a unique name
        agent_data = save_resp.get("agent", {})
        if agent_data.get("name") == "Cyber Sentinel" and agent_data.get("id") == "CYBER_SENTINEL":
            log_test_result("A02", "Assign a unique name", "PASSED", {
                "assigned_name": agent_data.get("name"),
                "assigned_id": agent_data.get("id")
            })
        else:
            log_test_result("A02", "Assign a unique name", "FAILED", {
                "agent_data": agent_data
            }, "Name or ID mismatch")

        # Test A03: Configure its role
        if agent_data.get("role") == "Security Auditing & Threat Detection Specialist":
            log_test_result("A03", "Configure its role", "PASSED", {
                "role": agent_data.get("role")
            })
        else:
            log_test_result("A03", "Configure its role", "FAILED", {
                "agent_data": agent_data
            }, "Configured role did not match expected value")

        # Test A04: Configure its specialty
        if agent_data.get("specialty") == "Vulnerability scanning, AST audit, secure architecture validation":
            log_test_result("A04", "Configure its specialty", "PASSED", {
                "specialty": agent_data.get("specialty")
            })
        else:
            log_test_result("A04", "Configure its specialty", "FAILED", {
                "agent_data": agent_data
            }, "Configured specialty did not match expected value")

        # Test A05: Set custom personality/system instructions
        soul_update_payload = {
            "id": "CYBER_SENTINEL",
            "soul_prompt": "You are Cyber Sentinel. Never bypass security boundaries. Audit rigorously."
        }
        soul_resp = http_post(UI_SOUL_URL, soul_update_payload)
        profile_resp = http_get(f"{UI_PROFILE_URL}?id=CYBER_SENTINEL")
        if soul_resp.get("success") is True and "Audit rigorously" in profile_resp.get("soul_md", ""):
            log_test_result("A05", "Set custom personality/system instructions", "PASSED", {
                "soul_resp": soul_resp,
                "verified_soul_md": profile_resp.get("soul_md")
            })
        else:
            log_test_result("A05", "Set custom personality/system instructions", "FAILED", {
                "soul_resp": soul_resp,
                "profile_resp": profile_resp
            }, "Soul markdown not updated or retrieved properly")

        # Test A06: Select a conversational model
        if agent_data.get("model_id") == "gemini-2.5-pro":
            log_test_result("A06", "Select a conversational model", "PASSED", {
                "model_id": agent_data.get("model_id")
            })
        else:
            log_test_result("A06", "Select a conversational model", "FAILED", {
                "agent_data": agent_data
            }, "Selected model_id was not retained")

        # Test A07: Select a task execution engine
        if agent_data.get("engine") == "opencode" and agent_data.get("default_tool") == "opencode_run":
            log_test_result("A07", "Select a task execution engine", "PASSED", {
                "engine": agent_data.get("engine"),
                "default_tool": agent_data.get("default_tool")
            })
        else:
            log_test_result("A07", "Select a task execution engine", "FAILED", {
                "agent_data": agent_data
            }, "Task execution engine or tool mapping incorrect")

        # Test A08: Configure available tools
        expected_tools = ["opencode_run", "task_status", "web_search"]
        actual_tools = agent_data.get("allowed_tools", [])
        if all(tool in actual_tools for tool in expected_tools):
            log_test_result("A08", "Configure available tools", "PASSED", {
                "allowed_tools": actual_tools
            })
        else:
            log_test_result("A08", "Configure available tools", "FAILED", {
                "expected": expected_tools,
                "actual": actual_tools
            }, "Allowed tools list does not match configuration")

        # Test A09: Configure agent permissions (risk_tier and governance enforcement)
        perm_check1 = agent_manager.registry.check_agent_tool_permission("CYBER_SENTINEL", "opencode_run")
        perm_check2 = agent_manager.registry.check_agent_tool_permission("CYBER_SENTINEL", "file_controller")
        
        # Test L0 permission stripping on an L0 agent
        l0_agent_payload = {
            "id": "AUDIT_OBSERVER",
            "name": "Audit Observer",
            "role": "Read-Only Observer",
            "risk_tier": "L0_READ_ONLY",
            "allowed_tools": ["file_controller", "web_search", "task_status"] # file_controller should be stripped for L0
        }
        l0_save = http_post(UI_SAVE_URL, l0_agent_payload)
        created_agent_ids.append("AUDIT_OBSERVER")
        l0_agent = l0_save.get("agent", {})
        l0_tools = l0_agent.get("allowed_tools", [])

        if (agent_data.get("risk_tier") == "L1_MUTATION" and
            perm_check1[0] is True and 
            perm_check2[0] is False and # file_controller was not granted to CYBER_SENTINEL
            "file_controller" not in l0_tools): # file_controller stripped on L0
            log_test_result("A09", "Configure agent permissions", "PASSED", {
                "CYBER_SENTINEL_risk_tier": agent_data.get("risk_tier"),
                "allowed_tool_granted_check": perm_check1,
                "unallowed_tool_denied_check": perm_check2,
                "L0_sanitized_tools": l0_tools
            })
        else:
            log_test_result("A09", "Configure agent permissions", "FAILED", {
                "risk_tier": agent_data.get("risk_tier"),
                "perm_check1": perm_check1,
                "perm_check2": perm_check2,
                "l0_tools": l0_tools
            }, "Risk tier and tool permissions not properly enforced")

        # Test A10: Save the agent
        # Verification that save_agent returned success and registered into memory state
        in_memory_agent = agent_manager.get_agent("CYBER_SENTINEL")
        if save_resp.get("success") is True and in_memory_agent is not None:
            log_test_result("A10", "Save the agent", "PASSED", {
                "save_response": save_resp.get("success"),
                "in_memory_id": in_memory_agent.id,
                "desk_coordinates": (in_memory_agent.desk_x, in_memory_agent.desk_y)
            })
        else:
            log_test_result("A10", "Save the agent", "FAILED", {
                "save_resp": save_resp,
                "in_memory_agent": str(in_memory_agent)
            }, "Agent saving did not persist into live agent_manager")

        # Test A11: Verify that the agent appears in the UI (via live UI server /api/agents/state)
        state_resp = http_get(UI_STATE_URL)
        agents_in_state = state_resp.get("agents", [])
        state_agent_ids = [a.get("id") for a in agents_in_state]
        found_in_ui = "CYBER_SENTINEL" in state_agent_ids and "AUDIT_OBSERVER" in state_agent_ids

        if state_resp.get("status") == "success" and found_in_ui:
            matched_ui_agent = next(a for a in agents_in_state if a.get("id") == "CYBER_SENTINEL")
            log_test_result("A11", "Verify that the agent appears in the UI (via live UI server /api/agents/state)", "PASSED", {
                "total_agents_in_ui_state": len(agents_in_state),
                "matched_agent_in_ui": matched_ui_agent
            })
        else:
            log_test_result("A11", "Verify that the agent appears in the UI (via live UI server /api/agents/state)", "FAILED", {
                "status": state_resp.get("status"),
                "found_in_ui": found_in_ui,
                "state_agent_ids": state_agent_ids
            }, "Created agents not found in live /api/agents/state output")

        # Test A12: Verify that its configuration is persisted (in config/agents.json and memory)
        config_file = REPO_ROOT / "config" / "agents.json"
        with open(config_file, "r", encoding="utf-8") as f:
            disk_config = json.load(f).get("agents", {})
        
        persisted_in_disk = "CYBER_SENTINEL" in disk_config
        disk_data = disk_config.get("CYBER_SENTINEL", {})

        # Test memory integration: conversation / memory table accessibility for this agent
        memory_test_conv_id = f"conv_test_{int(time.time())}"
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        execute_write(
            "INSERT INTO agent_conversations (id, agent_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (memory_test_conv_id, "CYBER_SENTINEL", "QA Suite A Memory Test", now_iso, now_iso)
        )
        mem_rows = query_db("SELECT * FROM agent_conversations WHERE id = ?", (memory_test_conv_id,))
        persisted_in_mem = len(mem_rows) > 0 and mem_rows[0]["agent_id"] == "CYBER_SENTINEL"
        
        # Clean up test conversation row
        execute_write("DELETE FROM agent_conversations WHERE id = ?", (memory_test_conv_id,))

        if persisted_in_disk and persisted_in_mem and disk_data.get("name") == "Cyber Sentinel":
            log_test_result("A12", "Verify that its configuration is persisted (in config/agents.json and memory)", "PASSED", {
                "persisted_in_disk": persisted_in_disk,
                "disk_entry": disk_data,
                "persisted_in_memory_db": persisted_in_mem
            })
        else:
            log_test_result("A12", "Verify that its configuration is persisted (in config/agents.json and memory)", "FAILED", {
                "persisted_in_disk": persisted_in_disk,
                "persisted_in_mem": persisted_in_mem,
                "disk_data": disk_data
            }, "Agent not correctly persisted to disk or sqlite memory")

        # Test A13: Restart ZEZO / registry refresh and verify the agent still exists
        fresh_registry = AgentRegistry()
        fresh_registry._load_agents()
        reloaded_agent = fresh_registry.get_agent("CYBER_SENTINEL")

        if reloaded_agent is not None and reloaded_agent.name == "Cyber Sentinel" and reloaded_agent.role == "Security Auditing & Threat Detection Specialist":
            log_test_result("A13", "Restart ZEZO / registry refresh and verify the agent still exists", "PASSED", {
                "reloaded_agent_id": reloaded_agent.id,
                "reloaded_agent_name": reloaded_agent.name,
                "reloaded_agent_role": reloaded_agent.role,
                "reloaded_agent_desk": (reloaded_agent.desk_x, reloaded_agent.desk_y)
            })
        else:
            log_test_result("A13", "Restart ZEZO / registry refresh and verify the agent still exists", "FAILED", {
                "reloaded_agent": str(reloaded_agent)
            }, "Agent did not survive fresh registry reload from disk")

        # Test A14: Create multiple agents with different identities
        multi_agents_payloads = [
            {
                "id": "PIXEL_ARTIST",
                "name": "Pixel Artist",
                "role": "Visual Designer & SVG Illustrator",
                "specialty": "Styling, themes, vector graphics",
                "engine": "antigravity",
                "default_tool": "antigravity_run",
                "risk_tier": "L1_MUTATION",
                "model_id": "gemini-2.5-flash",
                "color": "#ec4899"
            },
            {
                "id": "DATA_ARCHEOLOGIST",
                "name": "Data Archeologist",
                "role": "Dataset Extractor & Schema Normalizer",
                "specialty": "ETL pipelines, json parsing, web research",
                "engine": "kilo",
                "default_tool": "kilo_run",
                "risk_tier": "L1_MUTATION",
                "model_id": "kilo-auto/free",
                "color": "#eab308"
            },
            {
                "id": "DOCS_SCRIBE",
                "name": "Docs Scribe",
                "role": "Technical Writer & API Documenter",
                "specialty": "Markdown documentation, docstrings, release notes",
                "engine": "custom",
                "default_tool": "web_search",
                "risk_tier": "L0_READ_ONLY",
                "model_id": "gemini-3.7-flash-medium",
                "color": "#8b5cf6"
            }
        ]

        multi_results = []
        for p in multi_agents_payloads:
            res = http_post(UI_SAVE_URL, p)
            created_agent_ids.append(p["id"])
            multi_results.append(res)

        all_created_ok = all(r.get("success") is True for r in multi_results)
        
        # Verify in fresh registry
        fresh_registry_multi = AgentRegistry()
        fresh_registry_multi._load_agents()
        all_found = all(fresh_registry_multi.get_agent(p["id"]) is not None for p in multi_agents_payloads)

        # Verify desk coordinates are distinct
        allocated_desks = [
            (fresh_registry_multi.get_agent(p["id"]).desk_x, fresh_registry_multi.get_agent(p["id"]).desk_y)
            for p in multi_agents_payloads
        ]
        unique_desks = len(set(allocated_desks)) == len(allocated_desks)

        if all_created_ok and all_found and unique_desks:
            log_test_result("A14", "Create multiple agents with different identities", "PASSED", {
                "created_count": len(multi_results),
                "created_identities": [p["id"] for p in multi_agents_payloads],
                "distinct_desk_coordinates": allocated_desks
            })
        else:
            log_test_result("A14", "Create multiple agents with different identities", "FAILED", {
                "all_created_ok": all_created_ok,
                "all_found": all_found,
                "allocated_desks": allocated_desks,
                "unique_desks": unique_desks
            }, "Failed creating multiple distinct agents or desk collision occurred")

        # Test A15: Verify duplicate or invalid configurations are handled correctly
        # 1. Empty ID / name
        invalid_empty = http_post(UI_SAVE_URL, {"id": "", "name": ""})
        empty_handled = invalid_empty.get("success") is False and "cannot be empty" in invalid_empty.get("error", "").lower()

        # 2. Invalid non-alphanumeric ID
        invalid_chars = http_post(UI_SAVE_URL, {"id": "$$$@@@###", "name": "Bad Agent"})
        chars_handled = invalid_chars.get("success") is False and "alphanumeric" in invalid_chars.get("error", "").lower()

        # 3. Duplicate ID (updating existing agent safely without creating clone or corrupting)
        original_agent = agent_manager.get_agent("CYBER_SENTINEL")
        original_desk = (original_agent.desk_x, original_agent.desk_y)
        
        update_dup_payload = {
            "id": "CYBER_SENTINEL",
            "name": "Cyber Sentinel Upgraded",
            "role": "Lead Security Architect & Auditor",
            "risk_tier": "L1_MUTATION"
        }
        dup_resp = http_post(UI_SAVE_URL, update_dup_payload)
        updated_agent = agent_manager.get_agent("CYBER_SENTINEL")
        dup_desk = (updated_agent.desk_x, updated_agent.desk_y)
        
        # Verify no duplicate key appeared
        all_ids = [a.id for a in agent_manager.get_all_agents()]
        sentinel_count = all_ids.count("CYBER_SENTINEL")
        
        dup_handled = (
            dup_resp.get("success") is True and
            sentinel_count == 1 and
            updated_agent.name == "Cyber Sentinel Upgraded" and
            original_desk == dup_desk # Maintained desk allocation without duplication
        )

        # 4. Attempt to delete core builtin agent (e.g. MICHAEL)
        michael_del_resp = http_post(UI_DELETE_URL, {"id": "MICHAEL"})
        michael_protected = michael_del_resp.get("success") is False and "core" in michael_del_resp.get("error", "").lower()

        if empty_handled and chars_handled and dup_handled and michael_protected:
            log_test_result("A15", "Verify duplicate or invalid configurations are handled correctly", "PASSED", {
                "empty_id_rejected": invalid_empty,
                "invalid_chars_rejected": invalid_chars,
                "duplicate_id_safe_update": dup_resp,
                "core_agent_protected": michael_del_resp
            })
        else:
            log_test_result("A15", "Verify duplicate or invalid configurations are handled correctly", "FAILED", {
                "empty_handled": empty_handled,
                "chars_handled": chars_handled,
                "dup_handled": dup_handled,
                "michael_protected": michael_protected,
                "invalid_empty": invalid_empty,
                "invalid_chars": invalid_chars,
                "michael_del_resp": michael_del_resp
            }, "Invalid config or duplicate handling failed expectation")

    finally:
        # Cleanup temporary test agents from config/agents.json and registry
        print("[*] Cleaning up created test agents...")
        for aid in created_agent_ids:
            try:
                agent_manager.delete_agent(aid)
            except Exception as e:
                print(f"[!] Warning cleaning up agent {aid}: {e}")

        # Stop the test UI Server
        try:
            qa_server.stop()
            print("[*] Stopped QA UI Server.")
        except Exception:
            pass

    # Save artifacts
    artifacts_path = REPO_ROOT / "qa_artifacts" / "suite_a_results.json"
    artifacts_path.parent.mkdir(parents=True, exist_ok=True)
    with open(artifacts_path, "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, indent=2)

    print(f"\n=== Suite A Execution Finished: {RESULTS['passed']}/{RESULTS['total_tests']} PASSED ===")
    print(f"Results written to: {artifacts_path}")
    return RESULTS


if __name__ == "__main__":
    run_all_tests()
