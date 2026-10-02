"""Layer-2 runtime verification for the AUDIO I/O panel wiring.

Starts the real ZezoUIServer, connects a real WebSocket client, and exercises
the actual init -> get_audio_devices -> save_audio_devices -> broadcast flow.
Restores config/api_keys.json afterwards.
"""
import asyncio
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import websockets  # noqa: E402
from core.ui_server import ZezoUIServer  # noqa: E402
import core.audio_devices as ad  # noqa: E402

CFG = pathlib.Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
PORT = 8799
FIRED = {"v": None}

async def main() -> None:
    original = CFG.read_text(encoding="utf-8")
    cfg = json.loads(original)
    orig_in, orig_out = cfg.get("input_device", ""), cfg.get("output_device", "")

    srv = ZezoUIServer(host="127.0.0.1", port=PORT)
    srv.get_initial_state = lambda: {"state": "OFFLINE", "tasks": [], "timestamp": 0}
    srv.on_audio_devices_changed = lambda i, o: FIRED.update(v=(i, o))
    srv.start()
    await asyncio.sleep(1.0)

    try:
        async with websockets.connect(f"ws://127.0.0.1:{PORT}/ws") as ws:
            init = json.loads(await asyncio.wait_for(ws.recv(), 20))
            assert init["type"] == "init", init["type"]
            d = init["data"]
            print("init has audio fields:",
                  all(k in d for k in ("input_device", "output_device",
                                       "input_devices", "output_devices",
                                       "default_input_device", "default_output_device",
                                       "input_available", "output_available")))
            print("  default_input_device :", d["default_input_device"])
            print("  default_output_device:", d["default_output_device"])
            print("  input_device   :", repr(d["input_device"]))
            print("  output_device  :", repr(d["output_device"]))
            print("  input_devices  :", d["input_devices"])
            print("  output_devices :", d["output_devices"])
            print("  input_available:", d["input_available"])
            print("  output_available:", d["output_available"])

            await ws.send(json.dumps({"type": "get_audio_devices"}))
            got = json.loads(await asyncio.wait_for(ws.recv(), 20))
            print("get_audio_devices -> type:", got["type"],
                  "| keys present:", "input_devices" in got["data"])

            await ws.send(json.dumps({"type": "save_audio_devices",
                                      "input_device": "__TEST__MIC__",
                                      "output_device": ""}))
            seen_types = []
            for _ in range(3):
                m = json.loads(await asyncio.wait_for(ws.recv(), 20))
                seen_types.append(m["type"])
                if m["type"] == "audio_devices_updated" and m["data"].get("input_device") == "__TEST__MIC__":
                    break
            print("save broadcast types:", seen_types)
            print("callback fired with:", FIRED["v"])
            saved = json.loads(CFG.read_text(encoding="utf-8"))
            print("config persisted input_device:", repr(saved.get("input_device")))
            assert FIRED["v"] == ("__TEST__MIC__", "")
            assert saved.get("input_device") == "__TEST__MIC__"
            print("RUNTIME: PASS")
    finally:
        CFG.write_text(original, encoding="utf-8")
        restored = json.loads(CFG.read_text(encoding="utf-8"))
        assert restored.get("input_device", "") == orig_in
        print("config restored:", repr(restored.get("input_device", "")))
        srv.stop()


if __name__ == "__main__":
    asyncio.run(main())
