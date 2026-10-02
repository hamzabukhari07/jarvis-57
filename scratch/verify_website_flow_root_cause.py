"""Scratch: prove design_resolver explicit-match false positive + branch classification."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.design_resolver import (
    is_ui_task,
    is_redesign_or_explicit_request,
    resolve_design,
)

TASK = (
    "Create an entirely new, single-file HTML portfolio based on my CV content. "
    "It must be a complete design within one index"
)

# 1) Reproduce the resolver's explicit-match subroutine exactly as written
def is_explicit_match(stem_str):
    if stem_str.lower() in ("design-system", "design_system", "design system"):
        return False
    clean_stem = re.sub(r"[-_\s]+", " ", stem_str.lower())
    clean_stem = clean_stem.replace(".html", "").replace(".md", "").replace("design", "").strip()
    stem_tokens = [t for t in clean_stem.split() if t not in ("landing","page","the","a","an","and","component","system")]
    if not stem_tokens:
        stem_tokens = clean_stem.split()
    # exact code from design_resolver.py (post-fix):
    if stem_tokens and all(tok in task_words for tok in stem_tokens):
        return True
    if clean_stem and len(clean_stem) >= 3 and re.search(rf"\b{re.escape(clean_stem)}\b", task_clean):
        return True
    return False

task_clean = TASK.lower()
task_words = set(re.findall(r"[a-z0-9]+", task_clean))

print("TASK:", TASK)
print("task_words:", sorted(task_words))
print()
for stem in ["En-DESIGN", "saas-DESIGN", "Dub-Landing-Page-DESIGN", "Nexus-DESIGN"]:
    print(f"is_explicit_match({stem!r}) = {is_explicit_match(stem)}")
print()
print("'en' appears as substring in task:", "en" in task_clean)
print("'en' appears as whole word in task:", "en" in task_words)
print()
print("is_ui_task:", is_ui_task(TASK))
print("is_redesign_or_explicit_request:", is_redesign_or_explicit_request(TASK))
print("is_react_or_next:", any(k in task_clean for k in ("react","vite","nextjs","next.js","next 15","jsx","tsx")))
res = resolve_design(TASK)
print()
print("RESOLVED design:")
print("  source_name:", res.source_name)
print("  source_type:", res.source_type)
print("  is_active:", res.is_active())
print("  raw_html length:", len(res.raw_html))
print("  design_spec length:", len(res.design_spec))
