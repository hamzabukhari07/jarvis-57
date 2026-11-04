"""
tests/test_fix2_prompt_isolation.py - Verification tests for FIX 2:
Context Isolation & Prompt Contamination.

1. Test A: User introduces self as Alex building SaaS for dentists. Agent recalls Alex & dentists.
2. Test B: A completely separate conversation conv_beta with a different user (e.g. Sarah, building an iOS photography app).
   Agent recalls Sarah & photography app, with zero mention of Alex or dentists.
3. Test C: Start a third conversation with zero personal information given. Ask: "What do you know about me? What is my name and profession?"
   Verify:
   - Agent does NOT assume user is Hamza Bukhari.
   - Agent acknowledges that the user has not provided their name or profession yet.
   - Agent does not invent or assume personal facts.
   - Platform creator context ("Built on ZEZO OS platform created by Hamza Bukhari") is maintained without confusing the current user for Hamza.
"""

import pytest
from core.agents.runtime import AgentRuntime
from memory.sqlite_memory import reset_db_writer_for_test


@pytest.fixture(autouse=True)
def setup_teardown_test_db(tmp_path, monkeypatch):
    test_db = tmp_path / "test_fix2_isolation.db"
    monkeypatch.setattr("memory.sqlite_memory.get_db_path", lambda: test_db)
    monkeypatch.setattr("memory.sqlite_memory.DB_PATH", test_db)
    from memory.sqlite_memory import init_db
    init_db()
    yield
    reset_db_writer_for_test()


def test_fix2_prompt_isolation_and_context():
    runtime_a = AgentRuntime(agent_id="MICHAEL")

    # ---------------------------------------------------------
    # Test A: Conversation Alpha - Alex building SaaS for dentists
    # ---------------------------------------------------------
    cid_alpha = runtime_a.get_or_create_conversation(title="Alex Dentistry SaaS")
    
    # User introduces self
    res_a1 = runtime_a.step(
        user_input="Hi, my name is Alex and I am building a SaaS platform for dentists.",
        conversation_id=cid_alpha,
    )
    assert res_a1["success"] is True

    # User asks for recall
    res_a2 = runtime_a.step(
        user_input="Who am I and what am I building?",
        conversation_id=cid_alpha,
    )
    assert res_a2["success"] is True
    reply_a2 = res_a2["reply"].lower()

    # Agent recalls Alex and dentistry SaaS
    assert "alex" in reply_a2, f"Expected 'Alex' in reply: {res_a2['reply']}"
    assert "dentist" in reply_a2 or "dental" in reply_a2 or "saas" in reply_a2, (
        f"Expected dental/SaaS context in reply: {res_a2['reply']}"
    )

    # ---------------------------------------------------------
    # Test B: Conversation Beta - Sarah building iOS photography app
    # ---------------------------------------------------------
    runtime_b = AgentRuntime(agent_id="MICHAEL")
    cid_beta = runtime_b.get_or_create_conversation(title="Sarah iOS Photography")
    assert cid_beta != cid_alpha

    res_b1 = runtime_b.step(
        user_input="Hello! I am Sarah, an iOS developer creating a photography portfolio app.",
        conversation_id=cid_beta,
    )
    assert res_b1["success"] is True

    res_b2 = runtime_b.step(
        user_input="What is my name and what project am I working on?",
        conversation_id=cid_beta,
    )
    assert res_b2["success"] is True
    reply_b2 = res_b2["reply"].lower()

    # Agent recalls Sarah and photography / iOS app
    assert "sarah" in reply_b2, f"Expected 'Sarah' in reply: {res_b2['reply']}"
    assert "photograph" in reply_b2 or "photo" in reply_b2 or "ios" in reply_b2, (
        f"Expected photography/iOS context in reply: {res_b2['reply']}"
    )

    # Zero contamination from Conversation Alpha
    assert "alex" not in reply_b2, f"Contamination detected! 'Alex' found in conv_beta reply: {res_b2['reply']}"
    assert "dentist" not in reply_b2 and "dental" not in reply_b2, (
        f"Contamination detected! Dental context found in conv_beta reply: {res_b2['reply']}"
    )

    # ---------------------------------------------------------
    # Test C: Conversation Gamma - Zero personal info given
    # ---------------------------------------------------------
    runtime_c = AgentRuntime(agent_id="MICHAEL")
    cid_gamma = runtime_c.get_or_create_conversation(title="Anonymous User")
    assert cid_gamma not in (cid_alpha, cid_beta)

    res_c = runtime_c.step(
        user_input="What do you know about me? What is my name and profession?",
        conversation_id=cid_gamma,
    )
    assert res_c["success"] is True
    reply_c = res_c["reply"]
    reply_c_lower = reply_c.lower()

    # 1. Agent does NOT assume user is Hamza Bukhari
    # (Checking that it does not say "You are Hamza Bukhari" or address user as Hamza)
    assert not (
        "you are hamza" in reply_c_lower
        or "your name is hamza" in reply_c_lower
        or reply_c_lower.startswith("hamza,")
        or reply_c_lower.startswith("hello hamza")
        or reply_c_lower.startswith("hi hamza")
    ), f"Agent improperly assumed user is Hamza: {reply_c}"

    # 2. Agent acknowledges that the user has not provided their name or profession yet
    acknowledged_unknown = any(
        phrase in reply_c_lower
        for phrase in [
            "haven't", "have not", "didn't", "did not", "do not know", "don't know",
            "not mentioned", "not provided", "not shared", "not told", "not introduced",
            "no information", "unknown", "you haven't told", "haven't shared"
        ]
    )
    assert acknowledged_unknown, (
        f"Agent did not acknowledge lack of personal information: {reply_c}"
    )

    # 3. Agent does not invent or assume personal facts (no Alex, dentists, Sarah, photography)
    assert "alex" not in reply_c_lower, f"Contamination: Alex found in conv_gamma: {reply_c}"
    assert "dentist" not in reply_c_lower and "dental" not in reply_c_lower, (
        f"Contamination: Dental found in conv_gamma: {reply_c}"
    )
    assert "sarah" not in reply_c_lower, f"Contamination: Sarah found in conv_gamma: {reply_c}"

    # 4. Check system prompt verification: platform creator context maintained without confusion
    sys_prompt = runtime_c.build_system_prompt()
    assert "Built on ZEZO OS platform created by Hamza Bukhari" in sys_prompt
    assert "Do not assume the current user is Hamza Bukhari" in sys_prompt
