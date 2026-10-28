import pytest
from core.master_template_builder import (
    build_master_template,
    inject_semantic_slots,
    generate_master_template_html,
)


def test_semantic_slot_injection():
    html = """<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
  <header class="navbar"><h1>Logo</h1></header>
  <main class="content"><p>Hello world</p></main>
  <footer class="site-footer"><p>Copyright</p></footer>
</body>
</html>"""
    res = inject_semantic_slots(html)
    assert "<!-- SLOT: HEADER -->" in res
    assert "<!-- SLOT: MAIN -->" in res
    assert "<!-- SLOT: FOOTER -->" in res
    assert "<!-- SLOT: MODAL -->" in res


def test_reduction_stages():
    # Construct an HTML with comments, large SVG, repetitive cards, scripts, and whitespace
    large_svg = '<svg viewBox="0 0 100 100">' + ('<path d="M0 0h10v10H0z"/>' * 20) + '</svg>'
    cards = "".join(f'<div class="card">Card {i}</div>' for i in range(10))
    raw = f"""<!DOCTYPE html>
<html>
<head>
  <style>
    /* CSS Comment to strip */
    body {{
      color: #333;
      background: #fff;
    }}
  </style>
</head>
<body>
  <!-- HTML Comment to strip -->
  <header>
    {large_svg}
  </header>
  <main>
    <div class="cards grid">
      {cards}
    </div>
  </main>
  <script>
    var bloat = "lots of hydration code here " * 500;
  </script>
  <footer>
    <p>Done</p>
  </footer>
</body>
</html>"""

    # Set budget small enough that cards are condensed (e.g. 700 bytes)
    res = build_master_template(raw, max_bytes=700)
    assert "<!-- HTML Comment to strip -->" not in res
    assert "/* CSS Comment to strip */" not in res
    assert "<!-- SLOT: HEADER -->" in res
    assert "<!-- SLOT: MAIN -->" in res
    assert "<!-- SLOT: FOOTER -->" in res
    assert "<!-- SLOT: MODAL -->" in res
    # First 2 cards should be kept, card 3+ decomposed
    assert "Card 0" in res
    assert "Card 1" in res
    assert "Card 5" not in res
    assert len(res.encode("utf-8")) <= 700


def test_budget_exceeded_raises_valueerror():
    huge_html = "<div>" + ("A" * 50000) + "</div>"
    with pytest.raises(ValueError) as excinfo:
        build_master_template(huge_html, max_bytes=1000)
    assert "master-template exceeds 1000 bytes after all reduction stages" in str(excinfo.value)
    assert "Input too complex" in str(excinfo.value)


def test_drop_scripts_stage():
    script_bloat = "<script>" + ("x = 1;" * 1000) + "</script>"
    html = f"""<!DOCTYPE html><html><body><header>H</header><main>M</main>{script_bloat}<footer>F</footer></body></html>"""
    # Without script it's ~200 bytes, with script it's > 6000 bytes
    res = build_master_template(html, max_bytes=500)
    assert "<script" not in res
    assert len(res.encode("utf-8")) <= 500


def test_empty_and_idempotency():
    assert build_master_template("") == ""
    assert build_master_template("   ") == "" or len(build_master_template("   ")) < 100

    html = "<div><header>H</header><main>M</main><footer>F</footer></div>"
    first = build_master_template(html, max_bytes=1000)
    second = build_master_template(first, max_bytes=1000)
    # Should be idempotent - slot comments not duplicated
    assert first.count("<!-- SLOT: HEADER -->") == 1
    assert second.count("<!-- SLOT: HEADER -->") == 1


def test_base64_stripping():
    base64_img = 'data:image/png;base64,' + ('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==' * 20)
    html = f"""<!DOCTYPE html><html><body><header><img src="{base64_img}"></header><main>Content</main><footer>F</footer></body></html>"""
    res = build_master_template(html, max_bytes=2000)
    assert "data:image/png;base64" not in res
    assert "data:image/svg+xml" in res  # SVG placeholder used


def test_alias_compatibility():
    html = "<header>A</header><main>B</main><footer>C</footer>"
    res = generate_master_template_html(html, max_bytes=5000)
    assert "<!-- SLOT: HEADER -->" in res

