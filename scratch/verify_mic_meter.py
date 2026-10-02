"""Layer-2 verification for the live mic meter (broadcast + throttle)."""
import asyncio
import json
import sys
import types

sys.path.insert(0, ".")
import ui  # noqa: E402
from core.ui_server import ZezoUIServer  # noqa: E402
import websockets  # noqa: E402


async def main() -> None:
    # 1) set_mic_level must exist, not raise, and throttle without touching _win.
    d = types.SimpleNamespace()
    ui.ZezoUI.set_mic_level(d, 0.42)
    first = d._last_mic_bc
    ui.ZezoUI.set_mic_level(d, 0.99)          # within 80 ms -> throttled
    print("set_mic_level ok, throttled:", d._last_mic_bc == first)

    # 2) real WebSocket transport of the mic_level event.
    srv = ZezoUIServer(host="127.0.0.1", port=8801)
    srv.get_initial_state = lambda: {"state": "OFFLINE", "tasks": []}
    srv.start()
    await asyncio.sleep(1.0)
    try:
        async with websockets.connect("ws://127.0.0.1:8801/ws") as ws:
            await ws.recv()  # init
            srv.broadcast("mic_level", {"level": 0.42})
            msg = None
            for _ in range(6):
                m = json.loads(await asyncio.wait_for(ws.recv(), 10))
                if m.get("type") == "mic_level":
                    msg = m
                    break
            print("broadcast received:", msg)
            assert msg and msg["type"] == "mic_level"
            assert abs(msg["data"]["level"] - 0.42) < 1e-6
            print("MIC METER TRANSPORT: PASS")
    finally:
        srv.stop()


if __name__ == "__main__":
    asyncio.run(main())
