"""Verify the startup auto-default normalisation (exact logic main.py runs)."""
import json
import pathlib
import sys

sys.path.insert(0, ".")
from core import audio_devices  # noqa: E402
from memory.config_manager import (  # noqa: E402
    get_input_device, get_output_device, save_input_device, save_output_device,
)

CFG = pathlib.Path("config/api_keys.json")
original = CFG.read_text(encoding="utf-8")
try:
    save_input_device("Microphone (3- USB PnP Sound Device)")  # stale saved device
    cleared = []
    for kind, get, set_ in (("input", get_input_device, save_input_device),
                            ("output", get_output_device, save_output_device)):
        name = get()
        if name and audio_devices.resolve(name, kind) is None:
            set_("")
            cleared.append(kind)
    print("cleared stale kinds:", cleared)
    print("input after normalisation:", repr(get_input_device()))
    assert "input" in cleared and get_input_device() == ""
    print("AUTO-DEFAULT LOGIC: PASS")
finally:
    CFG.write_text(original, encoding="utf-8")
    print("restored input_device:", repr(json.loads(CFG.read_text(encoding='utf-8'))["input_device"]))
