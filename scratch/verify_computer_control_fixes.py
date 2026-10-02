"""Scratch (Layer 2 runtime): verify click targeting + open_app launch honesty."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import actions.computer_control as cc
import actions.open_app as oa

# ── computer_control dispatch ────────────────────────────────────────────────
calls = []
cc._screen_find = lambda desc: (10, 20) if "file" in desc.lower() else None
cc._click = lambda x=None, y=None, button="left", clicks=1: (
    calls.append((x, y, button, clicks)) or f"clicked {x},{y} x{clicks}"
)

def run(params):
    calls.clear()
    return cc.computer_control(params)

print("smart_click(desc):        ", run({"action": "smart_click", "description": "the report file"}))
print("double_click(desc only):  ", run({"action": "double_click", "description": "the report file"}))
print("screen_double_click(desc):", run({"action": "screen_double_click", "description": "the report file"}))
print("click(desc not found):    ", run({"action": "click", "description": "spaceship"}))
print("click with coords:        ", run({"action": "click", "x": 5, "y": 6}))
print("bogus action:             ", run({"action": "nonsense"}))

print("\nASSERTIONS")
ok = True
def check(c, m):
    global ok
    print(("  PASS  " if c else "  FAIL  ") + m); ok = ok and c

check(calls is not None, "no crash")
c = run({"action": "smart_click", "description": "the report file"}); check(c == "clicked 10,20 x1", f"smart_click -> single click at found coords ({c})")
c = run({"action": "double_click", "description": "the report file"}); check(c == "clicked 10,20 x2", f"double_click desc -> double click ({c})")
c = run({"action": "screen_double_click", "description": "the report file"}); check(c == "clicked 10,20 x2", f"screen_double_click -> double ({c})")
c = run({"action": "click", "description": "spaceship"}); check("not found" in c.lower(), f"unfound element is honest ({c})")
c = run({"action": "nonsense"}); check("Unknown action" in c, f"unknown still reported ({c})")

# ── open_app path launch (subprocess stubbed) ───────────────────────────────
launched = []
class FakeProc:
    def poll(self):
        return None  # alive
    pid = 4242

oa.subprocess.Popen = lambda args, **kw: (launched.append(args), FakeProc())[1]
oa.time.sleep = lambda *_: None
oa.os.startfile = lambda p: launched.append(("DEFAULT_APP", p))

tmp = ROOT / "scratch" / "sample_report.md"
tmp.write_text("# test", encoding="utf-8")
res = oa.open_app({"app_name": "Visual Studio Code", "path": str(tmp)})
print("\nopen_app ->", res)
print("launched argv:", launched)

check(launched and isinstance(launched[0], list) and launched[0][0].lower().endswith(("code.exe", "code.cmd")),
      "open_app launches real Code executable with the file")
check("Opened" in res and "Visual Studio Code" in res, "reports honest success")
check("startfile" not in str(launched[0]), "did NOT fall back to default app for VS Code")

# Not-a-real-app path -> must fall back to default app and say so honestly
launched.clear()
res2 = oa.open_app({"app_name": "Totally Fake Editor XYZ", "path": str(tmp)})
print("\nopen_app (fake app) ->", res2)
check("default application" in res2.lower(), "unresolvable app is honest about default-app fallback")

tmp.unlink(missing_ok=True)
print("\nRESULT:", "ALL PASS" if ok else "FAILURES")
sys.exit(0 if ok else 1)
