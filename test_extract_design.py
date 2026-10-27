"""
test_extract_design.py — Quick Test Runner for ZEZO 2-File Design Extractor & Cache Store.

Usage:
  # 1. Interactive mode (select from references list):
  python test_extract_design.py

  # 2. Direct path mode:
  python test_extract_design.py "skills/website_build/references/3_portfolios/Hairline Grid Portfolio.html"

  # 3. Specify custom output directory:
  python test_extract_design.py "skills/website_build/references/1_landing_pages/saas.html" --out my_test_dir

Creator & Lead Architect: Hamza Bukhari
"""

import sys
import time
from pathlib import Path

# Add project root to path
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.design_resolver import generate_blueprint_and_template


def main():
    references_dir = _ROOT / "skills" / "website_build" / "references"
    all_refs = sorted(list(references_dir.glob("*/*.html")))

    # Check arguments
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out_arg = "test_output"
    if "--out" in sys.argv:
        idx = sys.argv.index("--out")
        if idx + 1 < len(sys.argv):
            out_arg = sys.argv[idx + 1]

    target_ref: Path | None = None

    if args:
        candidate = Path(args[0])
        if not candidate.is_absolute():
            candidate = (_ROOT / candidate).resolve()
        if candidate.exists() and candidate.is_file():
            target_ref = candidate
        else:
            print(f"❌ Error: File not found: {args[0]}")
            sys.exit(1)
    else:
        # Interactive selection
        if not all_refs:
            print("❌ No HTML reference files found in skills/website_build/references/")
            sys.exit(1)

        print("\n" + "=" * 65)
        print("🎨 ZEZO DESIGN EXTRACTOR TEST RUNNER")
        print("=" * 65)
        print("Select a reference HTML file to extract:\n")
        for i, ref in enumerate(all_refs, 1):
            category = ref.parent.name
            print(f"  [{i:2d}] [{category}] {ref.name}")

        print("\n" + "-" * 65)
        choice = input(f"Enter number (1-{len(all_refs)}) [Default: 1]: ").strip()
        if not choice:
            choice_idx = 0
        else:
            try:
                choice_idx = int(choice) - 1
                if not (0 <= choice_idx < len(all_refs)):
                    print("❌ Invalid selection.")
                    sys.exit(1)
            except ValueError:
                print("❌ Invalid number.")
                sys.exit(1)

        target_ref = all_refs[choice_idx]

    out_dir = _ROOT / out_arg
    out_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 65)
    print(f"[*] Processing: {target_ref.name}")
    print(f"[*] Output Dir: {out_dir}")
    print("=" * 65)

    t0 = time.perf_counter()
    design_md, master_template = generate_blueprint_and_template(target_ref, out_dir)
    dt = time.perf_counter() - t0

    md_size = design_md.stat().st_size
    mt_size = master_template.stat().st_size

    print("\n[+] EXTRACTION COMPLETE!")
    print(f"[+] Time Taken: {dt:.3f}s")
    print(f"[+] DESIGN.md:        {design_md.resolve()} ({md_size:,} bytes)")
    print(f"[+] master-template:  {master_template.resolve()} ({mt_size:,} bytes)")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
