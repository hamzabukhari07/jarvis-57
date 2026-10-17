"""
tests/test_wake_word_registry.py — pure-function tests for the selectable
wake-word registry. No model loading and no audio are involved.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from core import wake_word


def test_presets_present():
    names = {p["name"] for p in wake_word.list_wake_presets()}
    assert {"Zezo", "Nova", "Jarvis"} <= names


def test_preset_entries_have_required_keys():
    for p in wake_word.list_wake_presets():
        assert set(p) >= {"id", "name", "phrase", "model", "available"}


def test_phrase_for_name():
    assert wake_word.phrase_for_name("Nova") == "Hey Nova"
    assert wake_word.phrase_for_name("") == "Hey Zezo"


@pytest.mark.skipif(not wake_word.is_installed(), reason="openwakeword not installed")
def test_default_model_resolves():
    model = wake_word.default_wake_model()
    assert wake_word.resolve_model(model) is not None


@pytest.mark.skipif(not wake_word.is_installed(), reason="openwakeword not installed")
def test_model_for_name_falls_back_to_resolvable_model():
    # hey_zezo/hey_nova are not shipped by default -> must fall back, never break.
    model = wake_word.model_for_name("Nova")
    assert wake_word.resolve_model(model) is not None


@pytest.mark.skipif(not wake_word.is_installed(), reason="openwakeword not installed")
def test_is_ready_accepts_a_model_id():
    assert wake_word.is_ready("hey_jarvis") is True
