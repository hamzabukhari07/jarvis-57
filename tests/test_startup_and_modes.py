"""
Targeted tests for startup optimization, dynamic obsidian graph, and dual operational modes.
"""
import sys
import math
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def test_action_loader_memory_tool():
    from core.action_loader import discover_actions
    reg = discover_actions(ROOT / "actions", reserved_names=set(), logger=print)
    mem_rec = reg.get("memory")
    assert mem_rec is not None, "Memory action was not discovered"
    assert mem_rec.valid, f"Memory action failed validation: {mem_rec.error}"
    assert callable(mem_rec.handler), "Memory action handler is not callable"


def test_audio_devices_single_flight():
    import core.audio_devices as ad
    assert ad._PROBE_SECONDS["output"] <= 0.2
    assert ad._PROBE_SECONDS["input"] <= 0.2
    assert hasattr(ad, "_prefetch_done")
    assert hasattr(ad, "_query_lock")


def test_vault_dynamic_graph_scaling():
    from memory.vault_engine import vault_engine
    graph = vault_engine.get_graph()
    assert "nodes" in graph
    assert "links" in graph
    for n in graph["nodes"]:
        deg = n.get("degree", 0)
        size = n.get("size", 10)
        expected_size = max(10, min(34, int(10 + 8 * math.log1p(deg))))
        assert size == expected_size, f"Node {n['id']} size {size} != expected {expected_size}"


def test_operational_mode_audio_gate():
    # Verify main.py drop assistant audio behavior
    from unittest.mock import MagicMock
    from main import ZezoLive

    # Create dummy instance with mocked dependencies
    instance = object.__new__(ZezoLive)
    instance._interrupted = False
    instance.ui = MagicMock()
    instance.ui.speaker_muted = False
    instance._operational_mode = "live"

    # In live mode without interruption: should NOT drop audio
    assert ZezoLive._drop_assistant_audio(instance) is False

    # In chat mode: should drop audio completely
    instance._operational_mode = "chat"
    assert ZezoLive._drop_assistant_audio(instance) is True

    # If speaker muted: should drop audio regardless of mode
    instance._operational_mode = "live"
    instance.ui.speaker_muted = True
    assert ZezoLive._drop_assistant_audio(instance) is True


if __name__ == "__main__":
    test_action_loader_memory_tool()
    print("✓ test_action_loader_memory_tool passed")
    test_audio_devices_single_flight()
    print("✓ test_audio_devices_single_flight passed")
    test_vault_dynamic_graph_scaling()
    print("✓ test_vault_dynamic_graph_scaling passed")
    test_operational_mode_audio_gate()
    print("✓ test_operational_mode_audio_gate passed")
    print("ALL VERIFICATION CHECKS PASSED!")
