"""tests/test_agent_settings.py — Test CLI & Coding Agent Preferences persistence & schema."""

import pytest
from memory.config_manager import (
    get_preferred_creation_agent, save_preferred_creation_agent,
    get_preferred_edit_agent, save_preferred_edit_agent,
    CREATION_AGENTS, EDIT_AGENTS, DEFAULT_CREATION_AGENT, DEFAULT_EDIT_AGENT,
)

def test_agent_preference_defaults():
    assert DEFAULT_CREATION_AGENT in CREATION_AGENTS
    assert DEFAULT_EDIT_AGENT in EDIT_AGENTS
    assert get_preferred_creation_agent() in CREATION_AGENTS
    assert get_preferred_edit_agent() in EDIT_AGENTS

def test_agent_preference_roundtrip():
    orig_c = get_preferred_creation_agent()
    orig_e = get_preferred_edit_agent()
    try:
        save_preferred_creation_agent("antigravity")
        assert get_preferred_creation_agent() == "antigravity"

        save_preferred_creation_agent("kilo")
        assert get_preferred_creation_agent() == "kilo"

        save_preferred_creation_agent("invalid_agent")
        assert get_preferred_creation_agent() == DEFAULT_CREATION_AGENT

        save_preferred_edit_agent("kilo")
        assert get_preferred_edit_agent() == "kilo"

        save_preferred_edit_agent("groq_helper")
        assert get_preferred_edit_agent() == "groq_helper"

        save_preferred_edit_agent("invalid_edit")
        assert get_preferred_edit_agent() == DEFAULT_EDIT_AGENT
    finally:
        save_preferred_creation_agent(orig_c)
        save_preferred_edit_agent(orig_e)
