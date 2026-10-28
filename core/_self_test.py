"""core/_self_test.py - Self-test suite for the ZEZO design extraction & template pipeline.

Executes all 9 regression, correctness, and performance tests defined in PHASE 5 of
prompt to fix.md:
1. Scrapbook regression (canvas, accents, components, no Vercel artifacts)
2. Vercel-like source / SaaS (components, no phantom semantic colors)
3. Base64 preservation (clean stripping preserving surrounding HTML)
4. Media query parsing (@media rules preserved in css extraction)
5. HSL wrap (_hsl_to_hex wrap-around logic)
6. Foreground (_best_foreground contrast)
7. Master template size (< 40000 bytes or ValueError on huge inputs)
8. Determinism (identical output for identical input)
9. Cache versioning (re-extraction on version mismatch)

Runnable directly via:
    python -m core._self_test
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path


def test_1_scrapbook_regression() -> None:
    """1. Scrapbook regression: canvas, accents, components, no Vercel artifacts."""
    from core.design_extractor import extract_design_tokens
    from core.design_md_generator import generate_design_md

    scrapbook = """<html><head><style>
:root { --paper: #f3eee2; --ink: #2b2b2b; --tape: #f0d531; --accent: #e05a47; }
body { background: var(--paper); color: var(--ink); }
.polaroid { background:#fff; border-radius:4px; padding:12px; }
.tape { background: var(--tape); }
.notepaper { background:#faf6ea; border-radius:2px; padding:16px; }
</style></head><body>
<div class="polaroid"><div class="tape"></div></div>
<div class="notepaper">Note</div>
</body></html>"""

    tokens = extract_design_tokens(scrapbook, "Scrapbook")
    assert tokens.colors.canvas == "#f3eee2", f"Expected canvas #f3eee2, got {tokens.colors.canvas}"
    assert tokens.colors.primary_accent in ("#e05a47", "#f0d531"), (
        f"Unexpected primary_accent: {tokens.colors.primary_accent}"
    )
    component_names = {c.name for c in tokens.components}
    assert "polaroid" in component_names, f"'polaroid' missing from components: {component_names}"
    assert "notepaper" in component_names, f"'notepaper' missing from components: {component_names}"

    md = generate_design_md(tokens, "Scrapbook")
    assert "nav-bar" not in md, "nav-bar should not be in Scrapbook md"
    assert "pricing-card" not in md, "pricing-card should not be in Scrapbook md"
    assert "#7928ca" not in md, "#7928ca should not be in Scrapbook md"
    assert "#ff0080" not in md, "#ff0080 should not be in Scrapbook md"
    assert "#f9cb28" not in md, "#f9cb28 should not be in Scrapbook md"


def test_2_saas_tokens_and_markdown() -> None:
    """2. Vercel-like source (SaaS): components, no phantom semantic colors."""
    from core.design_extractor import extract_design_tokens
    from core.design_md_generator import generate_design_md

    saas = """<html><head><style>
:root { --background: #000; --foreground: #fff; --accent: #0070f3; }
body { background: var(--background); color: var(--foreground); }
.nav-bar { height: 64px; }
.btn-primary { background: #0070f3; color: #fff; }
.pricing-card { border: 1px solid #333; padding: 32px; }
</style></head><body><nav class="nav-bar"></nav><button class="btn-primary">Go</button><div class="pricing-card"></div></body></html>"""

    tokens = extract_design_tokens(saas, "SaaS")
    md = generate_design_md(tokens, "SaaS")
    assert "nav-bar" in md, "'nav-bar' should be in SaaS md"
    assert "pricing-card" in md, "'pricing-card' should be in SaaS md"
    assert "success:" not in md, "'success:' should not be in md (no semantic success in source)"
    assert "error:" not in md, "'error:' should not be in md (no semantic error in source)"
    assert "warning:" not in md, "'warning:' should not be in md (no semantic warning in source)"


def test_3_base64_preservation() -> None:
    """3. Base64 preservation: <img src="data:image/png;base64,..."><p>after</p> -> <p>after</p> survives."""
    from core.design_extractor import strip_base64_images

    html_input = '<img src="data:image/png;base64,iVBORw0KGgo=\nAAAA=="><p>after</p>'
    cleaned = strip_base64_images(html_input)
    assert "<p>after</p>" in cleaned, f"'<p>after</p>' must survive after strip_base64_images: {cleaned}"
    assert "iVBORw0KGgo" not in cleaned, "Base64 payload was not stripped"


def test_4_media_query_parsing() -> None:
    """4. Media query parsing: @media (max-width:600px){.foo{color:red}} -> (.foo, {color: red})."""
    import core.design_extractor as de

    css = "@media (max-width:600px){.foo{color:red}}"
    if hasattr(de, "_extract_css_rules"):
        try:
            rules = de._extract_css_rules(css, {})
        except TypeError:
            rules = de._extract_css_rules(css)
    elif hasattr(de, "_parse_css_blocks"):
        rules = de._parse_css_blocks(css)
    else:
        raise AttributeError("Neither _extract_css_rules nor _parse_css_blocks found in core.design_extractor")

    matched = False
    if isinstance(rules, list):
        for item in rules:
            if isinstance(item, tuple) and len(item) == 2:
                sel, props = item
                if sel.strip() == ".foo":
                    if isinstance(props, dict) and props.get("color") == "red":
                        matched = True
                        break
                    elif isinstance(props, str) and "color" in props and "red" in props:
                        matched = True
                        break
    elif isinstance(rules, dict):
        if ".foo" in rules and rules[".foo"].get("color") == "red":
            matched = True

    assert matched, f"Expected selector '.foo' with color: red in extracted css rules, got: {rules}"


def test_5_hsl_wrap() -> None:
    """5. HSL wrap: _hsl_to_hex(-30, 100, 50) == _hsl_to_hex(330, 100, 50)."""
    from core.design_extractor import _hsl_to_hex

    assert _hsl_to_hex(-30, 100, 50) == _hsl_to_hex(330, 100, 50), (
        f"HSL wrap failed: {_hsl_to_hex(-30, 100, 50)} != {_hsl_to_hex(330, 100, 50)}"
    )


def test_6_foreground() -> None:
    """6. Foreground: _best_foreground("#f0d531") == "#000000" and _best_foreground("#09090b") == "#ffffff"."""
    from core.design_extractor import _best_foreground

    assert _best_foreground("#f0d531") == "#000000", (
        f"Expected #000000 for #f0d531, got {_best_foreground('#f0d531')}"
    )
    assert _best_foreground("#09090b") == "#ffffff", (
        f"Expected #ffffff for #09090b, got {_best_foreground('#09090b')}"
    )


def test_7_master_template_size() -> None:
    """7. Master template size: synthetic 500 KB HTML -> < 40000 bytes OR ValueError raised."""
    from core.design_extractor import extract_design_tokens
    from core.master_template_builder import build_master_template

    chunk = '<div class="card"><p class="desc">Synthetic card content with bloat</p><span>Item</span></div>'
    repeat_count = (500 * 1024) // len(chunk) + 10
    body_content = chunk * repeat_count
    html = f"""<!DOCTYPE html>
<html>
<head>
<title>Synthetic 500KB</title>
<style>
:root {{ --bg: #fff; --fg: #000; }}
body {{ background: var(--bg); color: var(--fg); }}
.card {{ padding: 16px; border-radius: 8px; }}
</style>
</head>
<body>
{body_content}
</body>
</html>"""

    tokens = extract_design_tokens(html, "SyntheticHuge")
    try:
        template = build_master_template(html, tokens, max_bytes=40000)
        size = len(template.encode("utf-8"))
        assert size < 40000, f"Template size {size} exceeds 40000 bytes! Never return oversized file."
    except ValueError:
        # Expected alternative: raising ValueError when input cannot be reduced below budget
        pass


def test_8_determinism() -> None:
    """8. Determinism: generate_design_md(extract_design_tokens(H, "X"), "X") == generate_design_md(extract_design_tokens(H, "X"), "X")."""
    from core.design_extractor import extract_design_tokens
    from core.design_md_generator import generate_design_md

    sample_html = """<!DOCTYPE html>
<html>
<head>
<style>
:root { --canvas: #fafafa; --ink: #111111; --brand: #ff5500; }
body { background: var(--canvas); color: var(--ink); }
.card { border-radius: 8px; padding: 24px; background: #fff; }
.btn { background: var(--brand); color: #fff; border-radius: 4px; padding: 8px 16px; }
</style>
</head>
<body>
<div class="card"><button class="btn">Click</button></div>
</body>
</html>"""

    run1 = generate_design_md(extract_design_tokens(sample_html, "DetTest"), "DetTest")
    run2 = generate_design_md(extract_design_tokens(sample_html, "DetTest"), "DetTest")
    assert run1 == run2, "generate_design_md output must be 100% deterministic"


def test_9_cache_versioning() -> None:
    """9. Cache versioning: write a v1 cache, bump _EXTRACTOR_VERSION to v2, verify it re-extracts."""
    import core.design_cache as dc
    from core.design_cache import get_or_create_reference_design_cache

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        ref_file = temp_path / "test_ref.html"
        ref_file.write_text(
            "<html><head><style>:root{--bg:#112233;}body{background:var(--bg);}</style></head>"
            "<body><div class='nav-bar'>Nav</div><div class='btn'>Action</div></body></html>",
            encoding="utf-8",
        )

        orig_cache_dir = getattr(dc, "_EXTRACTED_CACHE_DIR", None)
        dc._EXTRACTED_CACHE_DIR = temp_path / "cache_store"
        try:
            # 1. Initial extraction creates cache with current version
            md_path1, mt_path1 = get_or_create_reference_design_cache(ref_file)
            assert md_path1.exists() and mt_path1.exists(), "Cache files not created on initial run"

            slug = re.sub(r"[^a-zA-Z0-9]+", "_", ref_file.stem).strip("_").lower()
            version_file = dc._EXTRACTED_CACHE_DIR / slug / "_extractor_version.txt"
            assert version_file.exists(), "_extractor_version.txt not created"

            # 2. Simulate older cache with version 'v1' and stale content
            version_file.write_text("v1", encoding="utf-8")
            stale_marker = "# STALE DESIGN MD V1"
            md_path1.write_text(stale_marker, encoding="utf-8")
            assert md_path1.read_text(encoding="utf-8") == stale_marker

            # 3. Call get_or_create_reference_design_cache again; should detect version mismatch and re-extract
            md_path2, mt_path2 = get_or_create_reference_design_cache(ref_file)
            new_content = md_path2.read_text(encoding="utf-8")
            assert new_content != stale_marker, (
                "Cache was not re-extracted when version mismatch ('v1') occurred"
            )
            assert version_file.read_text().strip() == dc._EXTRACTOR_VERSION, (
                f"Version file was not updated to {dc._EXTRACTOR_VERSION}"
            )
        finally:
            if orig_cache_dir is not None:
                dc._EXTRACTED_CACHE_DIR = orig_cache_dir


TESTS = [
    ("1. Scrapbook regression", test_1_scrapbook_regression),
    ("2. Vercel-like source (SaaS)", test_2_saas_tokens_and_markdown),
    ("3. Base64 preservation", test_3_base64_preservation),
    ("4. Media query parsing", test_4_media_query_parsing),
    ("5. HSL wrap", test_5_hsl_wrap),
    ("6. Foreground", test_6_foreground),
    ("7. Master template size", test_7_master_template_size),
    ("8. Determinism", test_8_determinism),
    ("9. Cache versioning", test_9_cache_versioning),
]


def run_all() -> bool:
    print("=" * 60)
    print("ZEZO Design Extraction & Template Pipeline — Self-Test Suite")
    print("=" * 60)

    passed = 0
    failed = 0

    for name, test_fn in TESTS:
        sys.stdout.write(f"Running {name}... ")
        sys.stdout.flush()
        try:
            test_fn()
            print("PASSED")
            passed += 1
        except Exception as e:
            print(f"FAILED: {e}")
            failed += 1

    print("-" * 60)
    print(f"Results: {passed}/{len(TESTS)} passed ({failed} failed)")

    if failed == 0:
        print("All 9 self-tests PASSED successfully.")
        return True
    else:
        print(f"Self-test run failed with {failed} failure(s).")
        return False


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
