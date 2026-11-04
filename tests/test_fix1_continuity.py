"""
tests/test_fix1_continuity.py - Verification test for FIX 1: Frontend-to-Backend Conversation Continuity.

Simulates the exact frontend-backend interaction across multi-turn messages:
1. Turn 1: Client sends agent_id='MICHAEL', message='My name is Alex. I am building a SaaS product for dentists. Remember this context.', conversation_id=None.
   - Verifies SSE stream yields status/chunk events and a done event containing 'conversation_id: conv_...'.
   - Records conv_id.
2. Turn 2: Client sends message with the captured conversation_id=conv_id:
   message='What is my name, what product am I building, and who is my target audience?'.
   - Verifies Turn 2 uses the exact same conversation_id.
   - Verifies the SSE stream yields the answer.
   - Verifies response contains 'Alex', 'SaaS', and 'dentist' (or 'dental').
   - In SQLite (agent_messages), verifies both turn 1 and turn 2 messages are saved under the SAME conversation_id.
3. Restart Simulation: Re-instantiate runtime and load messages from SQLite to verify history preservation across application restarts.
"""

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import patch

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from core.agents.runtime import AgentRuntime
from core.ui_server import ZezoUIServer
from memory.sqlite_memory import init_db, query_db, reset_db_writer_for_test


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    """Isolate SQLite database to a temporary directory for each test run."""
    test_db = tmp_path / "test_fix1_continuity.db"
    monkeypatch.setattr("memory.sqlite_memory.get_db_path", lambda: test_db)
    monkeypatch.setattr("memory.sqlite_memory.DB_PATH", test_db)
    init_db()
    yield
    reset_db_writer_for_test()


def parse_sse_events(raw_body: str) -> list[dict]:
    """Parse raw SSE body text into structured events matching frontend EventSource/fetch parser."""
    events = []
    blocks = raw_body.strip().split("\n\n")
    for block in blocks:
        if not block.strip():
            continue
        event_type = "message"
        data_str = ""
        for line in block.split("\n"):
            line = line.strip()
            if line.startswith("event: "):
                event_type = line[7:].strip()
            elif line.startswith("data: "):
                data_str = line[6:].strip()
        if data_str:
            try:
                data = json.loads(data_str)
            except Exception:
                data = {"raw": data_str}
            events.append({"event": event_type, "data": data})
        else:
            events.append({"event": event_type, "data": {}})
    return events


def test_frontend_to_backend_conversation_continuity():
    """Verify multi-turn conversation continuity through SSE streaming and SQLite persistence."""
    async def _async_test():
        server = ZezoUIServer()
        app = web.Application()
        app.router.add_post("/api/agents/chat/stream", server._agent_chat_stream_handler)

        test_server = TestServer(app)
        client = TestClient(test_server)
        await client.start_server()

        # Generator simulating LLM answers using actual prompt/history sent to stream_text
        def mock_gemini_stream(query_text: str, **kwargs):
            lower_query = query_text.lower()
            if "what is my name" in lower_query:
                # Multi-turn context check: inspect query_text to confirm Turn 1 history was included
                if "alex" in lower_query and "saas" in lower_query and "dentist" in lower_query:
                    yield "Your name is Alex. "
                    yield "You are building a SaaS product "
                    yield "for dentists and dental practices."
                else:
                    yield "I do not have your name or project in context."
            else:
                yield "Understood, Alex! "
                yield "I have recorded that you are building a SaaS product for dentists."

        try:
            with patch("core.gemini.stream_text", side_effect=mock_gemini_stream):
                # -----------------------------------------------------------------
                # Turn 1: Client sends initial introduction with conversation_id=None
                # -----------------------------------------------------------------
                t1_payload = {
                    "agent_id": "MICHAEL",
                    "message": "My name is Alex. I am building a SaaS product for dentists. Remember this context.",
                    "conversation_id": None,
                }
                res1 = await client.post("/api/agents/chat/stream", json=t1_payload)
                assert res1.status == 200
                body1 = await res1.text()
                events1 = parse_sse_events(body1)

                # Verify Turn 1 yields chunks and a done event with conv_id
                chunk_events1 = [e for e in events1 if e["event"] == "chunk"]
                assert len(chunk_events1) > 0, "Turn 1 must stream chunk events"

                done_events1 = [e for e in events1 if e["event"] == "done"]
                assert len(done_events1) == 1, "Turn 1 must produce a done event"
                done_data1 = done_events1[0]["data"]
                conv_id = done_data1.get("conversation_id")

                assert conv_id is not None, "Turn 1 done event must contain conversation_id"
                assert conv_id.startswith("conv_"), f"conversation_id '{conv_id}' must start with conv_"
                assert done_data1.get("agent_id") == "MICHAEL"

                # -----------------------------------------------------------------
                # Turn 2: Client sends follow-up with the captured conversation_id
                # -----------------------------------------------------------------
                t2_payload = {
                    "agent_id": "MICHAEL",
                    "message": "What is my name, what product am I building, and who is my target audience?",
                    "conversation_id": conv_id,
                }
                res2 = await client.post("/api/agents/chat/stream", json=t2_payload)
                assert res2.status == 200
                body2 = await res2.text()
                events2 = parse_sse_events(body2)

                # Verify Turn 2 uses exact same conversation_id
                done_events2 = [e for e in events2 if e["event"] == "done"]
                assert len(done_events2) == 1, "Turn 2 must produce a done event"
                done_data2 = done_events2[0]["data"]
                turn2_conv_id = done_data2.get("conversation_id")
                assert turn2_conv_id == conv_id, f"Turn 2 conv_id '{turn2_conv_id}' must match Turn 1 conv_id '{conv_id}'"

                # Verify SSE stream chunks yield the answer
                chunk_events2 = [e for e in events2 if e["event"] == "chunk"]
                assert len(chunk_events2) > 0, "Turn 2 must stream chunk events"
                reply_text = done_data2.get("reply", "")

                # Verify response contains 'Alex', 'SaaS', and 'dentist' (or 'dental')
                lower_reply = reply_text.lower()
                assert "alex" in lower_reply, f"Expected 'Alex' in reply: {reply_text}"
                assert "saas" in lower_reply, f"Expected 'SaaS' in reply: {reply_text}"
                assert ("dentist" in lower_reply or "dental" in lower_reply), f"Expected 'dentist' or 'dental' in reply: {reply_text}"

                # -----------------------------------------------------------------
                # Database Verification: agent_messages under the SAME conversation_id
                # -----------------------------------------------------------------
                rows = query_db(
                    "SELECT id, conversation_id, agent_id, role, content FROM agent_messages WHERE conversation_id = ? ORDER BY created_at ASC",
                    (conv_id,),
                )
                assert len(rows) == 4, f"Expected 4 messages (2 user + 2 assistant), found {len(rows)}"

                assert rows[0]["role"] == "user"
                assert "Alex" in rows[0]["content"] and "dentists" in rows[0]["content"]
                assert rows[0]["agent_id"] == "MICHAEL"
                assert rows[0]["conversation_id"] == conv_id

                assert rows[1]["role"] == "assistant"
                assert rows[1]["agent_id"] == "MICHAEL"
                assert rows[1]["conversation_id"] == conv_id

                assert rows[2]["role"] == "user"
                assert "What is my name" in rows[2]["content"]
                assert rows[2]["agent_id"] == "MICHAEL"
                assert rows[2]["conversation_id"] == conv_id

                assert rows[3]["role"] == "assistant"
                assert "Alex" in rows[3]["content"] and "SaaS" in rows[3]["content"]
                assert rows[3]["agent_id"] == "MICHAEL"
                assert rows[3]["conversation_id"] == conv_id

                # -----------------------------------------------------------------
                # Application Restart Simulation: Re-instantiate runtime and load messages from SQLite
                # -----------------------------------------------------------------
                restarted_runtime = AgentRuntime(agent_id="MICHAEL")
                loaded_history = restarted_runtime.load_messages(conversation_id=conv_id)
                assert len(loaded_history) == 4, f"Restarted runtime expected 4 messages, found {len(loaded_history)}"
                assert loaded_history[0]["content"] == rows[0]["content"]
                assert loaded_history[1]["content"] == rows[1]["content"]
                assert loaded_history[2]["content"] == rows[2]["content"]
                assert loaded_history[3]["content"] == rows[3]["content"]

        finally:
            await client.close()

    asyncio.run(_async_test())
