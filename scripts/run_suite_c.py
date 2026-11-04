"""
scripts/run_suite_c.py — Live Autonomous Test Runner for Suite C: Agent Configuration.

Tests requirements:
  C01. Edit an existing agent (create a temp test agent first, do NOT mutate real core agents permanently).
  C02. Change its name.
  C03. Change its role and specialty.
  C04. Change its personality (prompt_prefix / soul_markdown / save_agent_soul).
  C05. Change its conversational model.
  C06. Change its task execution engine.
  C07. Change its permissions (risk_tier, L0_READ_ONLY vs L1_MUTATION vs L2_DESTRUCTIVE).
  C08. Change its tools (allowed_tools, default_tool).
  C09. Verify UI configuration matches backend configuration (via live REST endpoints /api/agents/state & /api/agents/agent).
  C10. Verify engine and default_tool consistency (auto-synchronization between engine and default_tool).
  C11. Verify invalid engine/model combinations are handled safely.
  C12. Restart ZEZO / registry reload and verify saved changes.
  C13. Verify editing one agent does not modify another agent.
  C14. Verify configuration reset behavior, without deleting real user data.
"""

import json
import logging
import os
import shutil
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Ensure repo root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.agents_manager import AgentManager
from core.agents.registry import AgentRegistry, AgentProfile, CORE_AGENT_IDS
from core.ui_server import ZezoUIServer

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("suite_c")

RESULTS_FILE = BASE_DIR / "qa_artifacts" / "suite_c_results.json"
TEST_AGENT_ID = "QA_TEMP_AGENT_C"
OTHER_AGENT_ID = "QA_BENCHMARK_AGENT"

results_data = {
    "suite": "Suite C: Agent Configuration",
    "timestamp": datetime.now().isoformat(),
    "test_agent_id": TEST_AGENT_ID,
    "tests": {},
    "summary": {
        "total": 14,
        "passed": 0,
        "failed": 0,
        "status": "IN_PROGRESS"
    }
}

def record_test(test_id: str, title: str, passed: bool, evidence: Dict[str, Any], notes: str = ""):
    results_data["tests"][test_id] = {
        "title": title,
        "passed": passed,
        "evidence": evidence,
        "notes": notes,
        "timestamp": datetime.now().isoformat()
    }
    if passed:
        results_data["summary"]["passed"] += 1
        logger.info(f"PASS: [{test_id}] {title}")
    else:
        results_data["summary"]["failed"] += 1
        logger.error(f"FAIL: [{test_id}] {title} - {notes}")


def main():
    logger.info("Starting Suite C Live Autonomous QA Test Execution...")
    
    # Snapshot real agents config before any operations to ensure strict zero-mutation policy
    real_config_path = BASE_DIR / "config" / "agents.json"
    with open(real_config_path, "r", encoding="utf-8") as f:
        original_real_agents_json = f.read()
    original_real_data = json.loads(original_real_agents_json)
    original_agent_keys = set(original_real_data.get("agents", {}).keys())
    logger.info(f"Existing live agents in config: {sorted(list(original_agent_keys))}")

    # We will test on a dedicated live AgentManager using an isolated config file to avoid touching production data,
    # as well as testing UI server integration on an isolated port.
    test_config_path = BASE_DIR / "config" / "agents_suite_c_live.json"
    shutil.copyfile(real_config_path, test_config_path)

    mgr = AgentManager(config_path=test_config_path)
    
    # Start live ZezoUIServer on port 8798 for UI endpoint validation
    ui_server = ZezoUIServer(port=8798)
    # Point UI server's agent_manager to mgr for the UI verification test
    import core.agents_manager as cm
    original_singleton = cm.agent_manager
    cm.agent_manager = mgr
    ui_server.start()
    time.sleep(2)
    api_base = "http://127.0.0.1:8798"

    try:
        # Pre-cleanup in case previous run left QA agent
        mgr.delete_agent(TEST_AGENT_ID)
        mgr.delete_agent(OTHER_AGENT_ID)

        # ---------------------------------------------------------------------
        # C01. Create & Edit an existing agent (create temp test agent first, do NOT mutate real core agents)
        # ---------------------------------------------------------------------
        logger.info("Executing C01: Create temp test agent and edit it...")
        # Step 1: Create initial agent
        init_res = mgr.save_agent_profile({
            "id": TEST_AGENT_ID,
            "name": "Suite C Alpha",
            "role": "QA Initial Specialist",
            "specialty": "Integration Verification",
            "risk_tier": "L0_READ_ONLY",
            "default_tool": "web_search",
            "prompt_prefix": "Initial QA prompt",
            "model_id": "gemini-3.8-flash-low",
            "color": "#10b981",
        })
        c01_created = init_res.get("success", False)
        agent_after_init = mgr.get_agent(TEST_AGENT_ID)

        # Step 2: Edit existing agent
        edit_res = mgr.save_agent_profile({
            "id": TEST_AGENT_ID,
            "name": "Suite C Alpha (Edited)",
            "role": "QA Senior Specialist",
            "specialty": "Deep Automated Diagnostics",
            "color": "#6366f1",
        })
        c01_edited = edit_res.get("success", False)
        agent_after_edit = mgr.get_agent(TEST_AGENT_ID)

        c01_pass = c01_created and c01_edited and agent_after_edit is not None and agent_after_edit.role == "QA Senior Specialist"
        record_test("C01", "Create & Edit existing agent without mutating core agents", c01_pass, {
            "initial_creation": init_res,
            "edited_result": edit_res,
            "profile_role": agent_after_edit.role if agent_after_edit else None,
            "core_agents_intact": all(c in mgr.agents for c in CORE_AGENT_IDS),
        }, notes="Successfully created temp test agent and verified in-place update.")

        # ---------------------------------------------------------------------
        # C02. Change its name
        # ---------------------------------------------------------------------
        logger.info("Executing C02: Change agent name...")
        c02_res = mgr.save_agent_profile({
            "id": TEST_AGENT_ID,
            "name": "Suite C Renamed Agent",
        })
        agent_c02 = mgr.get_agent(TEST_AGENT_ID)
        c02_pass = c02_res.get("success", False) and agent_c02.name == "Suite C Renamed Agent"
        record_test("C02", "Change agent name", c02_pass, {
            "name_after_save": agent_c02.name if agent_c02 else None,
            "id_retained": agent_c02.id if agent_c02 else None,
        })

        # ---------------------------------------------------------------------
        # C03. Change its role and specialty
        # ---------------------------------------------------------------------
        logger.info("Executing C03: Change role and specialty...")
        new_role = "Lead Architecture Inspector"
        new_specialty = "High-scale distributed systems and resiliency"
        c03_res = mgr.save_agent_profile({
            "id": TEST_AGENT_ID,
            "role": new_role,
            "specialty": new_specialty,
        })
        agent_c03 = mgr.get_agent(TEST_AGENT_ID)
        c03_pass = (
            c03_res.get("success", False)
            and agent_c03.role == new_role
            and agent_c03.specialty == new_specialty
        )
        record_test("C03", "Change role and specialty", c03_pass, {
            "role": agent_c03.role if agent_c03 else None,
            "specialty": agent_c03.specialty if agent_c03 else None,
        })

        # ---------------------------------------------------------------------
        # C04. Change its personality (prompt_prefix / soul_markdown / save_agent_soul)
        # ---------------------------------------------------------------------
        logger.info("Executing C04: Change personality & soul...")
        new_soul = "You are an elite QA Automation Operative with extreme precision and uncompromising quality standards."
        soul_res = mgr.save_agent_soul(TEST_AGENT_ID, new_soul)
        agent_c04 = mgr.get_agent(TEST_AGENT_ID)
        c04_pass = (
            soul_res.get("success", False)
            and agent_c04.prompt_prefix == new_soul
            and agent_c04.soul_markdown == new_soul
        )
        record_test("C04", "Change personality and soul markdown", c04_pass, {
            "save_agent_soul_result": soul_res,
            "prompt_prefix": agent_c04.prompt_prefix if agent_c04 else None,
            "soul_markdown": agent_c04.soul_markdown if agent_c04 else None,
        })

        # ---------------------------------------------------------------------
        # C05. Change its conversational model
        # ---------------------------------------------------------------------
        logger.info("Executing C05: Change conversational model...")
        new_model = "claude-sonnet-4-6"
        c05_res = mgr.save_agent_profile({
            "id": TEST_AGENT_ID,
            "model_id": new_model,
        })
        agent_c05 = mgr.get_agent(TEST_AGENT_ID)
        c05_pass = c05_res.get("success", False) and agent_c05.model_id == new_model
        record_test("C05", "Change conversational model", c05_pass, {
            "model_id": agent_c05.model_id if agent_c05 else None,
        })

        # ---------------------------------------------------------------------
        # C06. Change its task execution engine
        # ---------------------------------------------------------------------
        logger.info("Executing C06: Change task execution engine...")
        c06_res = mgr.save_agent_profile({
            "id": TEST_AGENT_ID,
            "engine": "opencode",
            "risk_tier": "L1_MUTATION",  # Engine opencode requires mutation tier to map to opencode_run
        })
        agent_c06 = mgr.get_agent(TEST_AGENT_ID)
        c06_pass = (
            c06_res.get("success", False)
            and agent_c06.engine == "opencode"
            and agent_c06.default_tool == "opencode_run"
        )
        record_test("C06", "Change task execution engine", c06_pass, {
            "engine": agent_c06.engine if agent_c06 else None,
            "default_tool": agent_c06.default_tool if agent_c06 else None,
        })

        # ---------------------------------------------------------------------
        # C07. Change its permissions (risk_tier, L0_READ_ONLY vs L1_MUTATION vs L2_DESTRUCTIVE)
        # ---------------------------------------------------------------------
        logger.info("Executing C07: Change permissions & risk tiers...")
        # Step 7a: Set to L0_READ_ONLY -> restricted mutation tools must be rejected or stripped
        mgr.save_agent_profile({
            "id": TEST_AGENT_ID,
            "risk_tier": "L0_READ_ONLY",
            "allowed_tools": ["web_search", "web_read_page", "opencode_run"],  # opencode_run is restricted
        })
        agent_l0 = mgr.get_agent(TEST_AGENT_ID)
        l0_perm_read_ok, _ = mgr.registry.check_agent_tool_permission(TEST_AGENT_ID, "web_search")
        l0_perm_mut_denied, l0_reason = mgr.registry.check_agent_tool_permission(TEST_AGENT_ID, "opencode_run")

        # Step 7b: Elevate to L1_MUTATION -> opencode_run should be permitted
        mgr.save_agent_profile({
            "id": TEST_AGENT_ID,
            "risk_tier": "L1_MUTATION",
            "allowed_tools": ["web_search", "opencode_run"],
            "engine": "opencode",
        })
        agent_l1 = mgr.get_agent(TEST_AGENT_ID)
        l1_perm_ok, _ = mgr.registry.check_agent_tool_permission(TEST_AGENT_ID, "opencode_run")

        # Step 7c: Elevate to L2_DESTRUCTIVE
        mgr.save_agent_profile({
            "id": TEST_AGENT_ID,
            "risk_tier": "L2_DESTRUCTIVE",
        })
        agent_l2 = mgr.get_agent(TEST_AGENT_ID)

        c07_pass = (
            agent_l0.risk_tier == "L0_READ_ONLY"
            and "opencode_run" not in agent_l0.allowed_tools
            and not l0_perm_mut_denied
            and agent_l1.risk_tier == "L1_MUTATION"
            and l1_perm_ok
            and agent_l2.risk_tier == "L2_DESTRUCTIVE"
        )
        record_test("C07", "Change permissions and enforce risk tiers", c07_pass, {
            "L0_risk_tier": agent_l0.risk_tier,
            "L0_allowed_tools": agent_l0.allowed_tools,
            "L0_mutation_blocked_reason": l0_reason,
            "L1_risk_tier": agent_l1.risk_tier,
            "L1_mutation_allowed": l1_perm_ok,
            "L2_risk_tier": agent_l2.risk_tier,
        })

        # ---------------------------------------------------------------------
        # C08. Change its tools (allowed_tools, default_tool)
        # ---------------------------------------------------------------------
        logger.info("Executing C08: Change tools...")
        target_tools = ["web_search", "web_read_page", "task_status"]
        c08_res = mgr.save_agent_profile({
            "id": TEST_AGENT_ID,
            "risk_tier": "L0_READ_ONLY",
            "allowed_tools": target_tools,
            "default_tool": "web_read_page",
        })
        agent_c08 = mgr.get_agent(TEST_AGENT_ID)
        c08_pass = (
            c08_res.get("success", False)
            and agent_c08.default_tool == "web_read_page"
            and set(target_tools).issubset(set(agent_c08.allowed_tools))
        )
        record_test("C08", "Change allowed_tools and default_tool", c08_pass, {
            "default_tool": agent_c08.default_tool if agent_c08 else None,
            "allowed_tools": agent_c08.allowed_tools if agent_c08 else None,
        })

        # ---------------------------------------------------------------------
        # C09. Verify UI configuration matches backend configuration
        # ---------------------------------------------------------------------
        logger.info("Executing C09: Verify UI REST endpoint matches backend state...")
        # Query /api/agents/state
        req_state = urllib.request.urlopen(f"{api_base}/api/agents/state")
        ui_state_data = json.loads(req_state.read().decode())
        ui_agents = {a["id"]: a for a in ui_state_data.get("agents", [])}

        # Query /api/agents/agent?id=...
        req_profile = urllib.request.urlopen(f"{api_base}/api/agents/agent?id={TEST_AGENT_ID}")
        ui_profile_data = json.loads(req_profile.read().decode())
        ui_profile_agent = ui_profile_data.get("agent", {})

        backend_agent = mgr.get_agent(TEST_AGENT_ID)
        c09_match_name = ui_agents.get(TEST_AGENT_ID, {}).get("name") == backend_agent.name
        c09_match_role = ui_profile_agent.get("role") == backend_agent.role
        c09_match_default_tool = ui_profile_agent.get("default_tool") == backend_agent.default_tool
        c09_match_risk = ui_profile_agent.get("risk_tier") == backend_agent.risk_tier

        c09_pass = c09_match_name and c09_match_role and c09_match_default_tool and c09_match_risk
        record_test("C09", "Verify UI REST endpoints match backend registry state", c09_pass, {
            "ui_state_agent": ui_agents.get(TEST_AGENT_ID),
            "ui_profile_agent": ui_profile_agent,
            "backend_agent": mgr.registry._agent_to_dict(backend_agent),
            "matches": {
                "name": c09_match_name,
                "role": c09_match_role,
                "default_tool": c09_match_default_tool,
                "risk_tier": c09_match_risk,
            }
        })

        # ---------------------------------------------------------------------
        # C10. Verify engine and default_tool consistency
        # ---------------------------------------------------------------------
        logger.info("Executing C10: Verify engine and default_tool consistency...")
        # Step 10a: Setting engine='antigravity' auto-aligns default_tool to 'antigravity_run' (in mutation tiers)
        mgr.save_agent_profile({
            "id": TEST_AGENT_ID,
            "risk_tier": "L1_MUTATION",
            "engine": "antigravity",
        })
        agent_ag = mgr.get_agent(TEST_AGENT_ID)
        ag_aligned = (agent_ag.engine == "antigravity" and agent_ag.default_tool == "antigravity_run")

        # Step 10b: Setting engine='kilo' updates default_tool to 'kilo_run'
        mgr.save_agent_profile({
            "id": TEST_AGENT_ID,
            "engine": "kilo",
        })
        agent_kilo = mgr.get_agent(TEST_AGENT_ID)
        kilo_aligned = (agent_kilo.engine == "kilo" and agent_kilo.default_tool == "kilo_run")

        # Step 10c: Creating a fresh agent with default_tool='opencode_run' auto-aligns engine to 'opencode'
        c10_fresh_id = "QA_C10_CONSISTENCY"
        mgr.save_agent_profile({
            "id": c10_fresh_id,
            "risk_tier": "L1_MUTATION",
            "default_tool": "opencode_run",
        })
        agent_fresh = mgr.get_agent(c10_fresh_id)
        tool_to_engine_aligned = (agent_fresh.engine == "opencode" and agent_fresh.default_tool == "opencode_run")
        mgr.delete_agent(c10_fresh_id)

        c10_pass = ag_aligned and kilo_aligned and tool_to_engine_aligned
        record_test("C10", "Verify engine and default_tool two-way consistency", c10_pass, {
            "engine_antigravity_aligned_tool": agent_ag.default_tool,
            "engine_kilo_aligned_tool": agent_kilo.default_tool,
            "tool_opencode_run_aligned_engine": agent_fresh.engine,
        })

        # ---------------------------------------------------------------------
        # C11. Verify invalid engine/model combinations are handled safely
        # ---------------------------------------------------------------------
        logger.info("Executing C11: Verify invalid engine/model combinations handled safely...")
        # Try saving with invalid engine and nonsensical model
        invalid_res = mgr.save_agent_profile({
            "id": TEST_AGENT_ID,
            "engine": "NON_EXISTENT_ENGINE_XYZ",
            "model_id": "invalid/non-existent-model-9999",
            "default_tool": "totally_fabricated_tool_123",
            "risk_tier": "INVALID_RISK_TIER_OVERFLOW",
        })
        agent_invalid = mgr.get_agent(TEST_AGENT_ID)
        # Verify system gracefully falls back and sanitized properties without crashing or corrupting
        c11_safe = (
            invalid_res.get("success", False)
            and agent_invalid.risk_tier in ("L0_READ_ONLY", "L1_MUTATION", "L2_DESTRUCTIVE")
            and agent_invalid.default_tool in ("web_search", "opencode_run", "kilo_run", "antigravity_run")
        )
        record_test("C11", "Verify invalid engine/model/risk combinations are sanitized safely", c11_safe, {
            "save_result": invalid_res,
            "sanitized_risk_tier": agent_invalid.risk_tier,
            "sanitized_default_tool": agent_invalid.default_tool,
            "model_id_recorded": agent_invalid.model_id,
        })

        # ---------------------------------------------------------------------
        # C12. Restart ZEZO / registry reload and verify saved changes
        # ---------------------------------------------------------------------
        logger.info("Executing C12: Simulate registry reload / restart and verify persistence...")
        # Step 1: Save distinct state
        mgr.save_agent_profile({
            "id": TEST_AGENT_ID,
            "name": "Suite C Reload Verifier",
            "role": "Cold Restart Specialist",
            "specialty": "Disk Persistence Verification",
            "risk_tier": "L1_MUTATION",
            "engine": "opencode",
            "model_id": "opencode/deepseek-coder",
        })
        # Step 2: Create a completely new fresh AgentManager instance pointing to the config file
        fresh_mgr = AgentManager(config_path=test_config_path)
        reloaded_agent = fresh_mgr.get_agent(TEST_AGENT_ID)

        c12_pass = (
            reloaded_agent is not None
            and reloaded_agent.name == "Suite C Reload Verifier"
            and reloaded_agent.role == "Cold Restart Specialist"
            and reloaded_agent.engine == "opencode"
            and reloaded_agent.model_id == "opencode/deepseek-coder"
        )
        record_test("C12", "Registry reload simulates restart and verifies persistence", c12_pass, {
            "reloaded_agent_id": reloaded_agent.id if reloaded_agent else None,
            "reloaded_name": reloaded_agent.name if reloaded_agent else None,
            "reloaded_role": reloaded_agent.role if reloaded_agent else None,
            "reloaded_engine": reloaded_agent.engine if reloaded_agent else None,
            "reloaded_model_id": reloaded_agent.model_id if reloaded_agent else None,
        })

        # ---------------------------------------------------------------------
        # C13. Verify editing one agent does not modify another agent
        # ---------------------------------------------------------------------
        logger.info("Executing C13: Verify isolation between agents during mutation...")
        # Create benchmark agent
        mgr.save_agent_profile({
            "id": OTHER_AGENT_ID,
            "name": "Benchmark Agent",
            "role": "Isolation Sentinel",
            "specialty": "Purity Check",
            "risk_tier": "L0_READ_ONLY",
            "model_id": "gemini-3.8-flash-low",
            "color": "#3b82f6",
        })
        bench_before = mgr.registry._agent_to_dict(mgr.get_agent(OTHER_AGENT_ID))

        # Mutate TEST_AGENT_ID heavily
        mgr.save_agent_profile({
            "id": TEST_AGENT_ID,
            "name": "Heavily Mutated Agent",
            "role": "Chaos Test Agent",
            "risk_tier": "L2_DESTRUCTIVE",
            "engine": "antigravity",
            "color": "#ff0000",
        })

        bench_after = mgr.registry._agent_to_dict(mgr.get_agent(OTHER_AGENT_ID))

        # Compare bench before and after
        bench_unchanged = (
            bench_before["name"] == bench_after["name"]
            and bench_before["role"] == bench_after["role"]
            and bench_before["risk_tier"] == bench_after["risk_tier"]
            and bench_before["color"] == bench_after["color"]
            and bench_before["model_id"] == bench_after["model_id"]
        )
        record_test("C13", "Verify editing one agent does not modify another agent", bench_unchanged, {
            "benchmark_before": bench_before,
            "benchmark_after": bench_after,
            "is_identical": bench_unchanged,
        })

        # ---------------------------------------------------------------------
        # C14. Verify configuration reset behavior, without deleting real user data
        # ---------------------------------------------------------------------
        logger.info("Executing C14: Verify configuration reset behavior...")
        # Reset / delete the temp agents from registry
        del_test_res = mgr.delete_agent(TEST_AGENT_ID)
        del_other_res = mgr.delete_agent(OTHER_AGENT_ID)

        # Confirm test agents are completely wiped from registry
        test_agent_gone = mgr.get_agent(TEST_AGENT_ID) is None
        other_agent_gone = mgr.get_agent(OTHER_AGENT_ID) is None

        # Verify all original pre-existing user agents remain intact
        current_agent_keys = set(mgr.agents.keys())
        all_real_preserved = original_agent_keys.issubset(current_agent_keys)

        c14_pass = del_test_res.get("success", False) and test_agent_gone and other_agent_gone and all_real_preserved
        record_test("C14", "Verify configuration reset behavior without deleting real user data", c14_pass, {
            "test_agent_deleted": del_test_res,
            "other_agent_deleted": del_other_res,
            "test_agent_gone": test_agent_gone,
            "other_agent_gone": other_agent_gone,
            "all_original_agents_preserved": all_real_preserved,
            "original_count": len(original_agent_keys),
            "current_count": len(current_agent_keys),
        })

    finally:
        # Stop UI Server and restore singletons
        ui_server.stop()
        cm.agent_manager = original_singleton

        # Clean up isolated test config
        if test_config_path.exists():
            test_config_path.unlink()

        # Sanity check: Ensure real config was never altered
        with open(real_config_path, "r", encoding="utf-8") as f:
            final_real_content = f.read()
        real_unchanged = (final_real_content.strip() == original_real_agents_json.strip())
        logger.info(f"Integrity Check: Real config/agents.json untouched: {real_unchanged}")

    # Mark overall summary status
    if results_data["summary"]["failed"] == 0 and results_data["summary"]["passed"] == 14:
        results_data["summary"]["status"] = "PASSED"
    else:
        results_data["summary"]["status"] = "FAILED"

    # Write output to qa_artifacts/suite_c_results.json
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results_data, f, indent=2)

    logger.info(f"Suite C QA execution finished. Results saved to {RESULTS_FILE}")
    print("\n" + "="*70)
    print(f"SUITE C SUMMARY: {results_data['summary']['passed']}/{results_data['summary']['total']} PASSED | Status: {results_data['summary']['status']}")
    print("="*70)
    return results_data["summary"]["status"] == "PASSED"


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
