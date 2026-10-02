"""Scratch (Layer 2 runtime): exercise the new deep multi-platform research compiler."""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from actions.agent_reach import fetch_multi_platform_search

OUT = "desktop/ZEZO_DEEP_TEST.md"
report, subtasks = fetch_multi_platform_search("production-ready AI vibe coding", output_file=OUT)

target = Path.home() / "Desktop" / "ZEZO_DEEP_TEST.md"
text = target.read_text(encoding="utf-8")
print("REPORT WRITTEN:", target)
print("bytes:", len(text), "| lines:", text.count("\n") + 1)
print("sections:", [l for l in text.splitlines() if l.startswith("## ")])
print("resource subheadings (###):", sum(1 for l in text.splitlines() if l.startswith("### ")))
print("has hardcoded Rust/Go matrix:", "| Factor | Rust | Go |" in text)
print()
print("----- first 40 lines -----")
print("\n".join(text.splitlines()[:40]))
