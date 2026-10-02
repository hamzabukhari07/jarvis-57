"""Scratch: sweep realistic website-creation requests through the design resolver."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core.design_resolver import resolve_design

TASKS = [
    "Build a modern landing page",
    "Create a portfolio website",
    "Build a SaaS landing page",
    "Create a website for my content agency",
    "Build a modern website for a restaurant",
    "Create an entirely new, single-file HTML portfolio based on my CV content",
    "Design a clean personal portfolio",
    "Build a website",
    "Create a gym website",
    "Build a responsive agency site",
]

print(f"{'TASK':<62} {'RESOLVED':<40} RAW_HTML")
print("-" * 120)
for t in TASKS:
    r = resolve_design(t)
    flag = "" if r.raw_html else "  <-- NO HTML BLUEPRINT"
    print(f"{t[:60]:<62} {r.source_name[:38]:<40} {len(r.raw_html):>7}{flag}")
