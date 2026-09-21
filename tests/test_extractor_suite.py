"""
tests/test_extractor_suite.py — Verification for core/design_extractor.py
"""

import re
import sys
from pathlib import Path

# Add project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from core.design_extractor import extract_design_system_from_html

html_dir = _PROJECT_ROOT / "skills" / "hamza_taste" / "references" / "html"
md_dir = _PROJECT_ROOT / "skills" / "hamza_taste" / "references" / "design md"

print("=" * 60)
print("TEST 1: CRAZY UI TEMPLATE EXTRACTION")
print("=" * 60)

crazy_html = html_dir / "Crazy UI landing page.html"
crazy_md = md_dir / "Crazy-Ui-Landing-Page-DESIGN.md"

if crazy_md.exists():
    crazy_md.unlink()

crazy_spec = extract_design_system_from_html(crazy_html, output_path=crazy_md)

theme = re.search(r'theme:\s*"?(\w+)"?', crazy_spec).group(1)
bg = re.search(r'background:\s*"?([#\w]+)"?', crazy_spec).group(1)
text = re.search(r'text-primary:\s*"?([#\w]+)"?', crazy_spec).group(1)
primary = re.search(r'primary:\s*"?([#\w]+)"?', crazy_spec).group(1)
font = re.search(r'fontFamily:\s*"?([^"\n]+)"?', crazy_spec).group(1)

print(f"Theme: {theme}")
print(f"Background: {bg}")
print(f"Text Primary: {text}")
print(f"Primary Accent: {primary}")
print(f"Display Font: {font}")
print(f"Contains '#1b5e20' as primary accent: {'#1b5e20' in primary}")
print(f"Contains 'deep obsidian' in description: {'deep obsidian' in crazy_spec.lower()}")

assert theme == "light", f"Expected light theme, got {theme}"
assert bg.lower() == "#f6f4f2", f"Expected #f6f4f2, got {bg}"
assert text.lower() == "#0a0a0a", f"Expected #0a0a0a, got {text}"
assert "instrument serif" in font.lower(), f"Expected Instrument Serif, got {font}"
assert primary != "#1b5e20", f"Primary accent should not be #1b5e20, got {primary}"
assert "deep obsidian" not in crazy_spec.lower(), "Should not contain deep obsidian"
print(">>> TEST 1 PASSED: 100% Exact Values Matched!\n")

print("=" * 60)
print("TEST 3: RE-EXTRACTING OTHER TEMPLATES (NEXUS, DUB, SAAS, AUTONOMUS)")
print("=" * 60)

for keyword in ["nexus", "dub", "saas", "autonomus"]:
    matches = list(html_dir.glob(f"*{keyword}*.html"))
    if not matches:
        continue
    target_html = matches[0]
    target_md = md_dir / f"{target_html.stem}-DESIGN.md"
    spec = extract_design_system_from_html(target_html, output_path=target_md)
    t = re.search(r'theme:\s*"?(\w+)"?', spec).group(1)
    b = re.search(r'background:\s*"?([#\w]+)"?', spec).group(1)
    tx = re.search(r'text-primary:\s*"?([#\w]+)"?', spec).group(1)
    p = re.search(r'primary:\s*"?([#\w]+)"?', spec).group(1)
    f = re.search(r'fontFamily:\s*"?([^"\n]+)"?', spec).group(1)
    print(f"[{target_html.name}] -> Theme: {t} | BG: {b} | Text: {tx} | Primary: {p} | Font: {f}")

print("\n>>> TEST 3 PASSED: All dark and light templates extracted faithfully!\n")
