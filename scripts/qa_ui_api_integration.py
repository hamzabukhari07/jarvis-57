"""
Live UI Server & Office View API Integration QA Test Suite.
Tests all /api/agents/* endpoints on a live ZezoUIServer instance.
Produces qa_artifacts/subagent_16_ui_api_results.json.
"""

import asyncio
import json
import logging
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import aiohttp

# Ensure root directory is on python path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from core.ui_server import ZezoUIServer
from memory.sqlite_memory import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("qa_subagent_16")

TEST_PORT = 18765
BASE_URL = f"http://127.0.0.1:{TEST_PORT}"
ARTIFACT_PATH = REPO_ROOT / "qa_artifacts" / "subagent_16_ui_api_results.json"
AGENTS_CONFIG_PATH = REPO_ROOT / "config" / "agents.json"


async def test_endpoint(
    session: aiohttp.ClientSession,
    method: str,
    path: str,
    name: str,
    json_data: Any = None,
    params: Dict[str, str] = None,
    headers: Dict[str, str] = None,
    expected_status: int = 200,
    expected_keys: List[str] = None,
    validate_func=None,
    timeout_sec: float = 35.0,
) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    start_time = time.perf_counter()
    result = {
        "test_name": name,
        "endpoint": path,
        "method": method,
        "payload": json_data,
        "params": params,
        "expected_status": expected_status,
        "passed": False,
        "status_code": None,
        "response_headers": {},
        "response_data": None,
        "latency_ms": 0.0,
        "notes": "",
    }

    try:
        req_headers = headers or {}
        async with session.request(
            method=method,
            url=url,
            json=json_data,
            params=params,
            headers=req_headers,
            timeout=aiohttp.ClientTimeout(total=timeout_sec),
        ) as resp:
            result["latency_ms"] = round((time.perf_counter() - start_time) * 1000, 2)
            result["status_code"] = resp.status
            result["response_headers"] = dict(resp.headers)

            content_type = resp.headers.get("Content-Type", "")
            if "application/json" in content_type:
                data = await resp.json()
            else:
                data = await resp.text()
            result["response_data"] = data

            # Check status code
            status_match = (resp.status == expected_status)
            if not status_match:
                result["notes"] = f"Expected HTTP {expected_status}, got {resp.status}."
                return result

            # Check expected keys in json response
            if expected_keys and isinstance(data, dict):
                missing = [k for k in expected_keys if k not in data]
                if missing:
                    result["notes"] = f"Missing expected keys: {missing}"
                    return result

            # Custom validation function
            if validate_func:
                valid, reason = validate_func(data, resp)
                if not valid:
                    result["notes"] = reason
                    return result

            result["passed"] = True
            result["notes"] = "All assertions passed."

    except Exception as exc:
        result["latency_ms"] = round((time.perf_counter() - start_time) * 1000, 2)
        result["notes"] = f"Exception occurred: {str(exc)}"

    return result


async def test_sse_stream(
    session: aiohttp.ClientSession,
    path: str,
    name: str,
    json_data: Any,
    expected_events: List[str],
    timeout_sec: float = 35.0,
) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    start_time = time.perf_counter()
    result = {
        "test_name": name,
        "endpoint": path,
        "method": "POST",
        "payload": json_data,
        "expected_status": 200,
        "passed": False,
        "status_code": None,
        "response_headers": {},
        "events_received": [],
        "latency_ms": 0.0,
        "notes": "",
    }

    try:
        async with session.post(
            url,
            json=json_data,
            headers={"Accept": "text/event-stream"},
            timeout=aiohttp.ClientTimeout(total=timeout_sec),
        ) as resp:
            result["latency_ms"] = round((time.perf_counter() - start_time) * 1000, 2)
            result["status_code"] = resp.status
            result["response_headers"] = dict(resp.headers)

            if resp.status != 200:
                result["notes"] = f"Expected HTTP 200, got {resp.status}."
                return result

            content_type = resp.headers.get("Content-Type", "")
            if "text/event-stream" not in content_type:
                result["notes"] = f"Expected text/event-stream content type, got {content_type}."
                return result

            current_event = "message"
            async for raw_line in resp.content:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue
                if line.startswith("event:"):
                    current_event = line.replace("event:", "").strip()
                elif line.startswith("data:"):
                    data_str = line.replace("data:", "").strip()
                    try:
                        parsed_data = json.loads(data_str)
                    except Exception:
                        parsed_data = data_str
                    result["events_received"].append({"event": current_event, "data": parsed_data})

            rec_events = [e["event"] for e in result["events_received"]]
            missing = [ev for ev in expected_events if ev not in rec_events]
            if missing:
                result["notes"] = f"Missing expected SSE events: {missing}. Received: {rec_events}"
            else:
                result["passed"] = True
                result["notes"] = f"Received SSE stream with events: {rec_events}"

    except Exception as exc:
        result["latency_ms"] = round((time.perf_counter() - start_time) * 1000, 2)
        result["notes"] = f"Exception occurred during streaming: {str(exc)}"

    return result


async def run_all_tests():
    logger.info("Initializing SQLite database...")
    init_db()

    # Backup config/agents.json
    agents_backup = None
    if AGENTS_CONFIG_PATH.exists():
        with open(AGENTS_CONFIG_PATH, "r", encoding="utf-8") as f:
            agents_backup = f.read()

    test_results = []
    created_conversation_id = None
    test_agent_id = "QA_TEST_AGENT_16"

    logger.info("Starting test ZezoUIServer on port %d...", TEST_PORT)
    server = ZezoUIServer(host="127.0.0.1", port=TEST_PORT)
    server.start()
    ready = server._ready_event.wait(timeout=10.0)
    if not ready:
        logger.error("Failed to start UI Server on port %d within timeout.", TEST_PORT)
        return

    logger.info("ZezoUIServer ready! Commencing API tests against %s", BASE_URL)

    try:
        async with aiohttp.ClientSession() as session:
            # -------------------------------------------------------------
            # 1. GET /api/agents/state
            # -------------------------------------------------------------
            res = await test_endpoint(
                session, "GET", "/api/agents/state",
                name="GET /api/agents/state - State of all agents",
                expected_status=200,
                expected_keys=["status", "agents"],
                validate_func=lambda d, r: (
                    (d.get("status") == "success" and isinstance(d.get("agents"), list) and len(d.get("agents")) > 0),
                    f"Invalid agents list: {d.get('agents')}"
                )
            )
            test_results.append(res)

            # -------------------------------------------------------------
            # 2. GET /api/agents/agent?id=MICHAEL
            # -------------------------------------------------------------
            res = await test_endpoint(
                session, "GET", "/api/agents/agent",
                name="GET /api/agents/agent - Existing agent MICHAEL profile",
                params={"id": "MICHAEL"},
                expected_status=200,
                expected_keys=["success", "agent"],
                validate_func=lambda d, r: (
                    d.get("success") is True and d.get("agent", {}).get("id") == "MICHAEL",
                    f"Agent profile structure mismatch: {d}"
                )
            )
            test_results.append(res)

            # 2b. GET /api/agents/agent without id parameter
            # Observational note: when id is omitted, registry currently matches first agent
            res = await test_endpoint(
                session, "GET", "/api/agents/agent",
                name="GET /api/agents/agent - Default behavior when id param is omitted",
                expected_status=200,
                validate_func=lambda d, r: (
                    "agent" in d or d.get("success") is False,
                    f"Response structure: {d}"
                )
            )
            test_results.append(res)

            # 2c. Validation: GET /api/agents/agent with non-existent id
            res = await test_endpoint(
                session, "GET", "/api/agents/agent",
                name="GET /api/agents/agent - Validation non-existent id",
                params={"id": "NON_EXISTENT_AGENT_XYZ"},
                expected_status=200,
                validate_func=lambda d, r: (
                    d.get("success") is False and "not found" in d.get("error", "").lower(),
                    f"Expected failure for non-existent agent, got: {d}"
                )
            )
            test_results.append(res)

            # -------------------------------------------------------------
            # 3. POST /api/agents/save_agent
            # -------------------------------------------------------------
            new_agent_payload = {
                "id": test_agent_id,
                "name": "QA Specialist 16",
                "role": "Autonomous QA Engineer",
                "specialty": "Integration testing and system validation",
                "color": "#10b981",
                "model_id": "gemini-3.8-flash-low",
                "engine": "antigravity",
                "soul_markdown": "You are QA Specialist 16, testing UI Server APIs.",
            }
            res = await test_endpoint(
                session, "POST", "/api/agents/save_agent",
                name="POST /api/agents/save_agent - Create new test agent",
                json_data=new_agent_payload,
                expected_status=200,
                expected_keys=["success", "agent"],
                validate_func=lambda d, r: (
                    d.get("success") is True and d.get("agent", {}).get("id") == test_agent_id,
                    f"Save agent failed: {d}"
                ),
                timeout_sec=35.0,
            )
            test_results.append(res)

            # 3b. Validation: POST /api/agents/save_agent with empty payload
            res = await test_endpoint(
                session, "POST", "/api/agents/save_agent",
                name="POST /api/agents/save_agent - Validation empty body",
                json_data={},
                expected_status=200,
                validate_func=lambda d, r: (
                    d.get("success") is False and "error" in d,
                    f"Expected validation failure for empty body, got: {d}"
                )
            )
            test_results.append(res)

            # Verify saved agent via GET /api/agents/agent?id=QA_TEST_AGENT_16
            res = await test_endpoint(
                session, "GET", "/api/agents/agent",
                name="GET /api/agents/agent - Verify newly saved QA_TEST_AGENT_16",
                params={"id": test_agent_id},
                expected_status=200,
                validate_func=lambda d, r: (
                    d.get("success") is True and d.get("agent", {}).get("id") == test_agent_id and d.get("agent", {}).get("name") == "QA Specialist 16",
                    f"Verified saved agent profile mismatch: {d}"
                )
            )
            test_results.append(res)

            # -------------------------------------------------------------
            # 4. POST /api/agents/save_soul
            # -------------------------------------------------------------
            res = await test_endpoint(
                session, "POST", "/api/agents/save_soul",
                name="POST /api/agents/save_soul - Update agent soul prompt",
                json_data={
                    "agent_id": test_agent_id,
                    "soul_prompt": "You are QA Specialist 16 updated soul prompt for integration tests.",
                },
                expected_status=200,
                expected_keys=["success", "agent_id", "soul"],
                validate_func=lambda d, r: (
                    d.get("success") is True and "updated soul prompt" in d.get("soul", ""),
                    f"Soul update failed: {d}"
                )
            )
            test_results.append(res)

            # 4b. Validation: POST /api/agents/save_soul non-existent agent
            res = await test_endpoint(
                session, "POST", "/api/agents/save_soul",
                name="POST /api/agents/save_soul - Validation non-existent agent",
                json_data={"agent_id": "GHOST_AGENT_XYZ", "soul_prompt": "Ghost prompt"},
                expected_status=200,
                validate_func=lambda d, r: (
                    d.get("success") is False and "not found" in d.get("error", "").lower(),
                    f"Expected 'not found' error, got: {d}"
                )
            )
            test_results.append(res)

            # 4c. Behavior: POST /api/agents/save_soul with missing agent_id
            res = await test_endpoint(
                session, "POST", "/api/agents/save_soul",
                name="POST /api/agents/save_soul - Payload validation observation (missing agent_id)",
                json_data={"soul_prompt": "No agent target"},
                expected_status=200,
                validate_func=lambda d, r: (
                    "success" in d,
                    f"Expected JSON response with success field: {d}"
                )
            )
            test_results.append(res)

            # -------------------------------------------------------------
            # 5. POST /api/agents/conversations
            # -------------------------------------------------------------
            res = await test_endpoint(
                session, "POST", "/api/agents/conversations",
                name="POST /api/agents/conversations - Create new conversation thread",
                json_data={"agent_id": "MICHAEL", "title": "QA Test Architecture Discussion"},
                expected_status=200,
                expected_keys=["success", "conversation_id", "title", "agent_id"],
                validate_func=lambda d, r: (
                    d.get("success") is True and d.get("conversation_id", "").startswith("conv_"),
                    f"Conversation creation failed: {d}"
                )
            )
            test_results.append(res)
            if res["passed"] and isinstance(res["response_data"], dict):
                created_conversation_id = res["response_data"].get("conversation_id")

            # 5b. Validation: POST /api/agents/conversations missing agent_id -> 400
            res = await test_endpoint(
                session, "POST", "/api/agents/conversations",
                name="POST /api/agents/conversations - Validation missing agent_id (HTTP 400)",
                json_data={"title": "Missing Agent"},
                expected_status=400,
                expected_keys=["success", "error"],
                validate_func=lambda d, r: (
                    d.get("success") is False and "agent_id is required" in d.get("error", ""),
                    f"Expected agent_id required error, got: {d}"
                )
            )
            test_results.append(res)

            # -------------------------------------------------------------
            # 6. GET /api/agents/conversations
            # -------------------------------------------------------------
            res = await test_endpoint(
                session, "GET", "/api/agents/conversations",
                name="GET /api/agents/conversations - List all active conversations",
                expected_status=200,
                expected_keys=["success", "conversations"],
                validate_func=lambda d, r: (
                    d.get("success") is True and isinstance(d.get("conversations"), list),
                    f"List conversations failed: {d}"
                )
            )
            test_results.append(res)

            # 6b. Filtered GET /api/agents/conversations?agent_id=MICHAEL
            res = await test_endpoint(
                session, "GET", "/api/agents/conversations",
                name="GET /api/agents/conversations?agent_id=MICHAEL - Filtered conversations",
                params={"agent_id": "MICHAEL"},
                expected_status=200,
                expected_keys=["success", "conversations"],
                validate_func=lambda d, r: (
                    d.get("success") is True and any(c.get("id") == created_conversation_id for c in d.get("conversations", [])),
                    f"Created conversation {created_conversation_id} not found in filtered list: {d}"
                )
            )
            test_results.append(res)

            # -------------------------------------------------------------
            # 7. GET /api/agents/messages
            # -------------------------------------------------------------
            res = await test_endpoint(
                session, "GET", "/api/agents/messages",
                name="GET /api/agents/messages - Get messages for created conversation",
                params={"conversation_id": created_conversation_id},
                expected_status=200,
                expected_keys=["success", "conversation_id", "messages"],
                validate_func=lambda d, r: (
                    d.get("success") is True and isinstance(d.get("messages"), list),
                    f"Get messages failed: {d}"
                )
            )
            test_results.append(res)

            # 7b. Validation: GET /api/agents/messages missing conversation_id -> 400
            res = await test_endpoint(
                session, "GET", "/api/agents/messages",
                name="GET /api/agents/messages - Validation missing conversation_id (HTTP 400)",
                expected_status=400,
                expected_keys=["success", "error"],
                validate_func=lambda d, r: (
                    d.get("success") is False and "conversation_id is required" in d.get("error", ""),
                    f"Expected conversation_id required error, got: {d}"
                )
            )
            test_results.append(res)

            # -------------------------------------------------------------
            # 8. POST /api/agents/chat
            # -------------------------------------------------------------
            # 8a. Validation: empty prompt -> 400
            res = await test_endpoint(
                session, "POST", "/api/agents/chat",
                name="POST /api/agents/chat - Validation empty prompt (HTTP 400)",
                json_data={"agent_id": "MICHAEL", "prompt": ""},
                expected_status=400,
                expected_keys=["success", "error"],
                validate_func=lambda d, r: (
                    d.get("success") is False and "cannot be empty" in d.get("error", "").lower(),
                    f"Expected prompt empty error, got: {d}"
                )
            )
            test_results.append(res)

            # 8b. Validation: non-existent agent -> 404
            res = await test_endpoint(
                session, "POST", "/api/agents/chat",
                name="POST /api/agents/chat - Validation non-existent agent (HTTP 404)",
                json_data={"agent_id": "UNKNOWN_AGENT_999", "prompt": "Hello"},
                expected_status=404,
                expected_keys=["success", "error"],
                validate_func=lambda d, r: (
                    d.get("success") is False and "not found" in d.get("error", "").lower(),
                    f"Expected agent not found error, got: {d}"
                )
            )
            test_results.append(res)

            # 8c. Explicit task dispatch (/task)
            res = await test_endpoint(
                session, "POST", "/api/agents/chat",
                name="POST /api/agents/chat - Explicit task dispatch (/task command)",
                json_data={
                    "agent_id": "MICHAEL",
                    "prompt": "/task inspect system architecture integrity",
                    "conversation_id": created_conversation_id,
                },
                expected_status=200,
                expected_keys=["success", "agent_id", "reply"],
                validate_func=lambda d, r: (
                    d.get("success") is True and d.get("agent_id") == "MICHAEL" and "task" in d.get("reply", "").lower(),
                    f"Task dispatch chat response invalid: {d}"
                )
            )
            test_results.append(res)

            # -------------------------------------------------------------
            # 9. POST /api/agents/chat/stream
            # -------------------------------------------------------------
            # 9a. Validation: empty prompt returns SSE error
            res = await test_sse_stream(
                session,
                path="/api/agents/chat/stream",
                name="POST /api/agents/chat/stream - Validation empty prompt (SSE error)",
                json_data={"agent_id": "MICHAEL", "prompt": ""},
                expected_events=["error", "done"],
            )
            test_results.append(res)

            # 9b. Validation: non-existent agent returns SSE error
            res = await test_sse_stream(
                session,
                path="/api/agents/chat/stream",
                name="POST /api/agents/chat/stream - Validation non-existent agent (SSE error)",
                json_data={"agent_id": "NON_EXISTENT_AGENT", "prompt": "Test streaming"},
                expected_events=["error", "done"],
            )
            test_results.append(res)

            # 9c. Valid explicit task dispatch SSE stream
            res = await test_sse_stream(
                session,
                path="/api/agents/chat/stream",
                name="POST /api/agents/chat/stream - Explicit task dispatch stream",
                json_data={"agent_id": "MICHAEL", "prompt": "/task run performance benchmark"},
                expected_events=["status", "chunk", "done"],
            )
            test_results.append(res)

            # -------------------------------------------------------------
            # 10. GET /api/agents/tasks/interrupted
            # -------------------------------------------------------------
            res = await test_endpoint(
                session, "GET", "/api/agents/tasks/interrupted",
                name="GET /api/agents/tasks/interrupted - Fetch interrupted tasks list",
                expected_status=200,
                expected_keys=["success", "interrupted_tasks"],
                validate_func=lambda d, r: (
                    d.get("success") is True and isinstance(d.get("interrupted_tasks"), list),
                    f"Interrupted tasks response invalid: {d}"
                )
            )
            test_results.append(res)

            # -------------------------------------------------------------
            # 11. POST /api/agents/tasks/restart
            # -------------------------------------------------------------
            # 11a. Validation: missing task_id -> 400
            res = await test_endpoint(
                session, "POST", "/api/agents/tasks/restart",
                name="POST /api/agents/tasks/restart - Validation missing task_id (HTTP 400)",
                json_data={"confirmed": False},
                expected_status=400,
                expected_keys=["success", "error"],
                validate_func=lambda d, r: (
                    d.get("success") is False and "task_id is required" in d.get("error", ""),
                    f"Expected task_id required error, got: {d}"
                )
            )
            test_results.append(res)

            # 11b. Valid call with non-existent task_id (testing execution logic)
            res = await test_endpoint(
                session, "POST", "/api/agents/tasks/restart",
                name="POST /api/agents/tasks/restart - Unconfirmed restart check on test task",
                json_data={"task_id": "task_qa_test_999", "confirmed": False},
                expected_status=200,
                validate_func=lambda d, r: (
                    "success" in d,
                    f"Unexpected restart response format: {d}"
                )
            )
            test_results.append(res)

            # -------------------------------------------------------------
            # 12. DELETE /api/agents/conversations
            # -------------------------------------------------------------
            # 12a. Validation: missing conversation_id -> 400
            res = await test_endpoint(
                session, "DELETE", "/api/agents/conversations",
                name="DELETE /api/agents/conversations - Validation missing conversation_id (HTTP 400)",
                expected_status=400,
                expected_keys=["success", "error"],
                validate_func=lambda d, r: (
                    d.get("success") is False and "conversation_id is required" in d.get("error", ""),
                    f"Expected conversation_id required error, got: {d}"
                )
            )
            test_results.append(res)

            # 12b. Delete created conversation
            res = await test_endpoint(
                session, "DELETE", "/api/agents/conversations",
                name="DELETE /api/agents/conversations - Delete created test thread",
                params={"conversation_id": created_conversation_id},
                expected_status=200,
                expected_keys=["success", "conversation_id"],
                validate_func=lambda d, r: (
                    d.get("success") is True and d.get("conversation_id") == created_conversation_id,
                    f"Delete conversation failed: {d}"
                )
            )
            test_results.append(res)

            # Verify conversation was deleted
            res = await test_endpoint(
                session, "GET", "/api/agents/conversations",
                name="GET /api/agents/conversations - Verify deleted conversation no longer returned",
                expected_status=200,
                validate_func=lambda d, r: (
                    all(c.get("id") != created_conversation_id for c in d.get("conversations", [])),
                    f"Deleted conversation still exists: {d}"
                )
            )
            test_results.append(res)

            # -------------------------------------------------------------
            # 13. POST /api/agents/delete_agent
            # -------------------------------------------------------------
            # 13a. Validation: attempting to delete core agent MICHAEL
            res = await test_endpoint(
                session, "POST", "/api/agents/delete_agent",
                name="POST /api/agents/delete_agent - Protection against deleting core agent",
                json_data={"agent_id": "MICHAEL"},
                expected_status=200,
                validate_func=lambda d, r: (
                    d.get("success") is False and "cannot decommission core" in d.get("error", "").lower(),
                    f"Expected protection error for core agent, got: {d}"
                )
            )
            test_results.append(res)

            # 13b. Validation: non-existent agent
            res = await test_endpoint(
                session, "POST", "/api/agents/delete_agent",
                name="POST /api/agents/delete_agent - Validation non-existent agent",
                json_data={"agent_id": "NON_EXISTENT_AGENT_XYZ"},
                expected_status=200,
                validate_func=lambda d, r: (
                    d.get("success") is False and "not found" in d.get("error", "").lower(),
                    f"Expected not found error, got: {d}"
                )
            )
            test_results.append(res)

            # 13c. Delete test agent QA_TEST_AGENT_16
            res = await test_endpoint(
                session, "POST", "/api/agents/delete_agent",
                name="POST /api/agents/delete_agent - Decommission QA_TEST_AGENT_16",
                json_data={"agent_id": test_agent_id},
                expected_status=200,
                expected_keys=["success"],
                validate_func=lambda d, r: (
                    d.get("success") is True,
                    f"Delete agent failed: {d}"
                )
            )
            test_results.append(res)

            # 13d. Verify test agent is deleted
            res = await test_endpoint(
                session, "GET", "/api/agents/agent",
                name="GET /api/agents/agent - Verify QA_TEST_AGENT_16 removed",
                params={"id": test_agent_id},
                expected_status=200,
                validate_func=lambda d, r: (
                    d.get("success") is False or "error" in d,
                    f"Deleted agent still returned: {d}"
                )
            )
            test_results.append(res)

            # -------------------------------------------------------------
            # 14. Additional Office View & Headers / CORS verification
            # -------------------------------------------------------------
            # 14a. GET /office
            res = await test_endpoint(
                session, "GET", "/office",
                name="GET /office - Office view HTML route",
                expected_status=200,
                validate_func=lambda d, r: (
                    "text/html" in r.headers.get("Content-Type", "") and len(d) > 0,
                    f"Expected text/html content type, got: {r.headers.get('Content-Type')}"
                )
            )
            test_results.append(res)

            # 14b. HTTP OPTIONS / CORS probing
            # Note: Server currently returns 405 Method Not Allowed because no CORS preflight handler is registered
            res = await test_endpoint(
                session, "OPTIONS", "/api/agents/state",
                name="OPTIONS /api/agents/state - CORS preflight check (Observational 405)",
                expected_status=405,
                validate_func=lambda d, r: (
                    r.status == 405,
                    f"Received unexpected status for OPTIONS: {r.status}"
                )
            )
            test_results.append(res)

    finally:
        logger.info("Stopping test ZezoUIServer...")
        server.stop()

        # Restore original agents.json if needed
        if agents_backup is not None and AGENTS_CONFIG_PATH.exists():
            with open(AGENTS_CONFIG_PATH, "r", encoding="utf-8") as f:
                current_config = f.read()
            if current_config != agents_backup:
                logger.info("Restoring original config/agents.json...")
                with open(AGENTS_CONFIG_PATH, "w", encoding="utf-8") as f:
                    f.write(agents_backup)

    # Compute overall stats
    total_tests = len(test_results)
    passed_tests = sum(1 for r in test_results if r["passed"])
    failed_tests = total_tests - passed_tests
    success_rate = round((passed_tests / total_tests) * 100, 2) if total_tests > 0 else 0

    evidence = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "subagent": "Subagent 16 - UI Server & Office View API Integration QA",
        "target_server": BASE_URL,
        "summary": {
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "success_rate_percent": success_rate,
        },
        "endpoints_verified": [
            "GET /api/agents/state",
            "GET /api/agents/agent?id=...",
            "POST /api/agents/save_agent",
            "POST /api/agents/save_soul",
            "POST /api/agents/chat",
            "POST /api/agents/chat/stream",
            "GET /api/agents/conversations",
            "POST /api/agents/conversations",
            "DELETE /api/agents/conversations",
            "GET /api/agents/messages",
            "GET /api/agents/tasks/interrupted",
            "POST /api/agents/tasks/restart",
            "POST /api/agents/delete_agent",
            "GET /office",
            "OPTIONS CORS inspection",
        ],
        "test_results": test_results,
    }

    # Ensure qa_artifacts directory exists
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ARTIFACT_PATH, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2)

    logger.info("Test results saved to %s", ARTIFACT_PATH)
    logger.info("Summary: %d / %d tests passed (%.1f%%)", passed_tests, total_tests, success_rate)
    return evidence


if __name__ == "__main__":
    asyncio.run(run_all_tests())
