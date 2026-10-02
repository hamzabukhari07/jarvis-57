"""Scratch (Layer 2 runtime): exercise the REAL antigravity _run_worker branch routing
by stubbing subprocess.Popen / agy lookup, and capture the exact CLI prompt sent."""
import os
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import actions.antigravity_agent as aa


class FakeStdout:
    def readline(self):
        return ""


class FakeProc:
    def __init__(self, cmd):
        self.cmd = cmd
        self.pid = 999999
        self.stdout = FakeStdout()
        self.returncode = 0

    def poll(self):
        return 0

    def wait(self, timeout=None):
        return 0

    def terminate(self):
        pass

    def kill(self):
        pass


class FakeCtx:
    task_id = "scratch-test"

    def __init__(self):
        self.payload = None
        self.err = None

    def report(self, pct, msg):
        pass

    def set_pid(self, pid):
        pass

    def cancelled(self):
        return False

    def on_complete(self, payload):
        self.payload = payload

    def on_fail(self, err):
        self.err = err


captured = {}


def fake_popen(cmd, **kwargs):
    captured["cmd"] = cmd
    return FakeProc(cmd)


def run_case(label, task, existing_react_project):
    captured.clear()
    aa.subprocess = types.SimpleNamespace(
        Popen=fake_popen,
        DEVNULL=-3,
        PIPE=-1,
        STDOUT=-2,
        CREATE_NO_WINDOW=0,
        BELOW_NORMAL_PRIORITY_CLASS=0,
    )
    aa._find_antigravity_bin = lambda: "C:/fake/agy.exe"
    aa._create_throttled_job = lambda *a, **k: None

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "proj"
        repo.mkdir()
        if existing_react_project:
            (repo / "index.html").write_text("<!DOCTYPE html><html><body>old react</body></html>", encoding="utf-8")
            (repo / "package.json").write_text('{"name":"old-react","dependencies":{"react":"^18"}}', encoding="utf-8")

        ctx = FakeCtx()
        aa._run_worker(
            {"repo": str(repo), "task": task, "model": "gemini-3.6-flash-medium", "session_memory": {}},
            ctx,
        )

        prompt = captured["cmd"][captured["cmd"].index("-p") + 1]
        static = "CRITICAL SINGLE-FILE HTML DIRECTIVE" in prompt
        react = "CRITICAL REACT / NEXT.JS MODULAR SYNTHESIS DIRECTIVE" in prompt
        targeted = "CRITICAL TARGETED UPDATE DIRECTIVE" in prompt
        redesign = "CRITICAL LOCAL FOLDER REDESIGN DIRECTIVE" in prompt
        blueprint = "Reference Blueprint Template" in prompt
        status = "ok" if ctx.payload and ctx.payload.get("status") == "success" else f"NOT OK ({ctx.err or ctx.payload})"

        print(f"--- {label}")
        print(f"    task: {task}")
        print(f"    existing_project={existing_react_project} | status={status}")
        print(f"    SINGLE_FILE={static} | REACT={react} | TARGETED_UPDATE={targeted} | REDESIGN={redesign} | DESIGN_BLUEPRINT={blueprint}")
        print(f"    prompt_len={len(prompt)}")
        return {"static": static, "react": react, "targeted": targeted, "redesign": redesign, "blueprint": blueprint}


CV_TASK = (
    "Create an entirely new, single-file HTML portfolio based on my CV content. "
    "It must be a complete design within one index"
)

results = {}
results["cv_static_over_react_folder"] = run_case("CV single-file HTML in existing React folder", CV_TASK, True)
results["react_explicit"] = run_case("Explicit React request", "Build a React landing page with Vite for my startup", False)
results["static_negation"] = run_case("Single HTML with 'no react'", "Build a website using single html, no react, no framework", False)

print("\n==== ASSERTIONS ====")
ok = True


def check(cond, msg):
    global ok
    print(("  PASS  " if cond else "  FAIL  ") + msg)
    ok = ok and cond


r = results["cv_static_over_react_folder"]
check(r["static"] and not r["react"] and not r["targeted"], "CV task -> SINGLE-FILE HTML, not React, not targeted-update")
check(r["blueprint"], "CV task -> Hamza Taste design blueprint referenced")

r = results["react_explicit"]
check(r["react"] and not r["static"], "Explicit React task -> React directive")

r = results["static_negation"]
check(r["static"] and not r["react"], "'single html, no react' -> static, not React")

print("\nRESULT:", "ALL PASS" if ok else "FAILURES")
sys.exit(0 if ok else 1)
