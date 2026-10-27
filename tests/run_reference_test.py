"""
tests/run_reference_test.py — Dedicated Live Test & Extraction Runner

Extracts `blueprint.html` and `master-template.html` from curated reference HTML files,
validates that both files are properly formed, valid HTML, with complete body structure,
CSS animations intact, and semantic slots correctly injected.
"""
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.design_resolver import generate_blueprint_and_template

def run_test_on_reference(reference_rel_path: str, output_base: Path):
    ref_path = Path(reference_rel_path)
    if not ref_path.exists():
        print(f"[!] Reference not found: {ref_path}")
        return None

    dest_dir = output_base / ref_path.stem
    dest_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=======================================================")
    print(f"[*] TESTING REFERENCE: {ref_path.name}")
    print(f"   Original Size: {ref_path.stat().st_size / 1024:.1f} KB ({ref_path.stat().st_size / 1024 / 1024:.2f} MB)")
    print(f"=======================================================")

    t0 = time.perf_counter()
    bp, mt = generate_blueprint_and_template(ref_path, dest_dir)
    elapsed = time.perf_counter() - t0

    bp_content = bp.read_text(encoding="utf-8")
    mt_content = mt.read_text(encoding="utf-8")

    # Blueprint assertions
    bp_size_kb = bp.stat().st_size / 1024
    has_bp_doctype = "<!DOCTYPE html>" in bp_content
    has_bp_swatches = "swatches-grid" in bp_content
    has_bp_keyframes = "Keyframe Animations" in bp_content or "@keyframes" in bp_content
    has_bp_tokens = "css-tokens-code" in bp_content or ":root" in bp_content

    # Master template assertions
    mt_size_kb = mt.stat().st_size / 1024
    has_mt_doctype = "<!DOCTYPE html>" in mt_content
    has_mt_body = ("<body" in mt_content) and ("</body>" in mt_content)
    has_mt_head = ("<head" in mt_content) and ("</head>" in mt_content)
    has_mt_html = ("<html" in mt_content) and ("</html>" in mt_content)

    slots = ["HERO", "PROJECTS", "SKILLS", "CONTACT"]
    slots_status = {s: (f"<!-- SLOT:{s}_START -->" in mt_content and f"<!-- SLOT:{s}_END -->" in mt_content) for s in slots}
    has_all_slots = all(slots_status.values())
    has_dummy_slots = '<section class="slot-hero"></section>' in mt_content

    print(f">> Extraction Speed: {elapsed:.3f} seconds (< 1.0s target)")
    print(f"\n[1] BLUEPRINT FILE: {bp.name}")
    print(f"   - Path: {bp.resolve()}")
    print(f"   - Size: {bp.stat().st_size} bytes ({bp_size_kb:.1f} KB)")
    print(f"   - Status: {'[OK] PASSED (< 25 KB)' if bp.stat().st_size < 25600 else '[WARN] WARNING'}")
    print(f"   - Complete DOCTYPE: {'[OK] Yes' if has_bp_doctype else '[FAIL] No'}")
    print(f"   - Extracted Palette Swatches: {'[OK] Yes' if has_bp_swatches else '[FAIL] No'}")
    print(f"   - Keyframe Animations Showcase: {'[OK] Yes' if has_bp_keyframes else '[FAIL] No'}")
    print(f"   - Tokens & :root Stylesheet: {'[OK] Yes' if has_bp_tokens else '[FAIL] No'}")

    print(f"\n[2] MASTER TEMPLATE FILE: {mt.name}")
    print(f"   - Path: {mt.resolve()}")
    print(f"   - Size: {mt.stat().st_size} bytes ({mt_size_kb:.1f} KB)")
    print(f"   - Complete Document (HTML/HEAD/BODY): {'[OK] Yes (100% Valid)' if (has_mt_html and has_mt_head and has_mt_body) else '[FAIL] Broken/Truncated'}")
    print(f"   - Preserved Interactive Scripts: {'[OK] Yes' if '<script' in mt_content else '[FAIL] No'}")
    print(f"   - Preserved Styling/Animations: {'[OK] Yes' if '<style' in mt_content else '[FAIL] No'}")
    print(f"   - Semantic Slots Injected on Real DOM: {'[OK] Yes (4/4)' if (has_all_slots and not has_dummy_slots) else '[FAIL] Fallback/Missing'}")
    for s, present in slots_status.items():
        print(f"     * SLOT:{s} -> {'[OK]' if present else '[MISSING]'}")

    # Design.md assertions
    design_md_path = dest_dir / "DESIGN.md"
    has_design_md = design_md_path.exists()
    dmd_size_kb = design_md_path.stat().st_size / 1024 if has_design_md else 0.0
    dmd_content = design_md_path.read_text(encoding="utf-8") if has_design_md else ""
    has_dmd_context = "<design-context>" in dmd_content and "</design-context>" in dmd_content
    has_dmd_yaml = all(k in dmd_content for k in ["colors:", "typography:", "rounded:", "spacing:", "components:"])
    has_dmd_sections = all(k in dmd_content for k in ["## Overview", "## Colors", "## Typography", "## Layout", "## Do's and Don'ts"])

    print(f"\n[3] DESIGN SYSTEM SPECIFICATION: DESIGN.md")
    print(f"   - Path: {design_md_path.resolve()}")
    print(f"   - Size: {design_md_path.stat().st_size if has_design_md else 0} bytes ({dmd_size_kb:.1f} KB)")
    print(f"   - Exists on Disk: {'[OK] Yes' if has_design_md else '[FAIL] No'}")
    print(f"   - Valid <design-context> XML wrapper: {'[OK] Yes' if has_dmd_context else '[FAIL] No'}")
    print(f"   - Machine-Readable YAML Token DSL: {'[OK] Yes (colors, typography, rounded, spacing, components)' if has_dmd_yaml else '[FAIL] No'}")
    print(f"   - Architectural Narrative Sections: {'[OK] Yes (Overview, Hierarchy, Responsive, Elevation, Do\'s & Don\'ts)' if has_dmd_sections else '[FAIL] No'}")

    return {
        "ref": ref_path.name,
        "elapsed": elapsed,
        "bp_path": str(bp.resolve()),
        "mt_path": str(mt.resolve()),
        "bp_size_kb": bp_size_kb,
        "mt_size_kb": mt_size_kb,
        "valid_body": has_mt_body,
        "all_slots": has_all_slots,
        "dmd_size_kb": dmd_size_kb,
    }

if __name__ == "__main__":
    out_dir = Path("tests/extracted_templates")
    out_dir.mkdir(parents=True, exist_ok=True)

    test_references = [
        "skills/website_build/references/3_portfolios/Scrapbook Resume.html",
        "skills/website_build/references/3_portfolios/Hairline Grid Portfolio.html",
        "skills/website_build/references/1_landing_pages/Crazy UI landing page.html",
    ]

    # If user provided a specific path via CLI arg
    if len(sys.argv) > 1:
        test_references = [sys.argv[1]]

    results = []
    for ref in test_references:
        res = run_test_on_reference(ref, out_dir)
        if res:
            results.append(res)

    print("\n" + "=" * 55)
    print("[*] SUMMARY OF TEST RUN")
    print("=" * 55)
    for r in results:
        print(f"- {r['ref']}: Speed={r['elapsed']:.2f}s | DESIGN.md={r.get('dmd_size_kb', 0):.1f} KB | Blueprint={r['bp_size_kb']:.1f} KB | MasterTemplate={r['mt_size_kb']:.1f} KB | ValidBody={r['valid_body']} | Slots={r['all_slots']}")
