import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

import time
from actions.website_cloner import _clone_worker

class DummyCtx:
    def report(self, pct, msg=""):
        print(f"[{pct:03d}%] {msg}")

print("=== STARTING FULL REVERSE-ENGINEERING CLONE TEST ===")
res = _clone_worker({"url": "https://heyclicky.com"}, DummyCtx())
print("\n=== CLONE WORKER RESULT ===")
for k, v in res.items():
    print(f"  {k}: {v}")

clone_dir = Path(res.get("clone_dir", ""))
if (clone_dir / "index.html").exists():
    html = (clone_dir / "index.html").read_text(encoding="utf-8", errors="ignore")
    print(f"\nGenerated index.html length: {len(html)} bytes")
    # Check for all key features
    checks = {
        "Header/Menubar": "menubar" in html or "heyclicky" in html,
        "Hero Section": "class=\"hero\"" in html or "class='hero'" in html or "Download for macOS" in html,
        "Features (All 3 Rows)": "fl studio" in html.lower() and ("claude code" in html.lower() or "sound design" in html.lower()),
        "Manifesto Notes": "man-section" in html or "the dream" in html.lower() or "small set of simple" in html.lower(),
        "Feedback Grid (Wall of Love)": "class=\"fb\"" in html or "class='fb'" in html or "they use it everyday" in html.lower(),
        "Pricing (3 Cards)": "$0" in html and "$20" in html and "$100" in html,
        "FAQ Accordion": "faq" in html or "frequently asked questions" in html.lower(),
        "Footer": "footer" in html or "product" in html.lower()
    }
    print("\nSection Presence Validation:")
    for name, passed in checks.items():
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
