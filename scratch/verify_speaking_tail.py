"""Verify the echo-tail arming fix: idle polls must NOT re-arm the tail."""
import sys
import threading
import time
import types

sys.path.insert(0, ".")
import main  # noqa: E402


class _FakeUI:
    muted = False

    def set_state(self, _s):
        pass


def _obj():
    o = types.SimpleNamespace()
    o._speaking_lock = threading.Lock()
    o._is_speaking = False
    o._tail_until = 0.0
    o._out_latency = 0.213
    o._out_level = 0.0
    o.ui = _FakeUI()
    return o


# 1) Simulate the idle playback loop polling set_speaking(False) every 200 ms
#    while nothing is playing. The tail must stay expired.
o = _obj()
for _ in range(10):
    main.ZezoLive.set_speaking(o, False)
    time.sleep(0.2)
assert not (time.monotonic() < o._tail_until), "BUG: idle polls re-armed the tail"
print("idle polls keep tail INACTIVE: PASS  (tail_until =", o._tail_until, ")")

# 2) A real speaking -> idle transition must still arm the tail once.
o = _obj()
main.ZezoLive.set_speaking(o, True)
main.ZezoLive.set_speaking(o, False)
armed = time.monotonic() < o._tail_until
print("speaking->idle arms tail once:", armed)
assert armed, "regression: real end-of-speech no longer arms the echo tail"
print("TAIL FIX: PASS")
