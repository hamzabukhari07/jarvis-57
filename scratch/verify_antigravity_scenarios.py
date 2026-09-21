"""
scratch/verify_antigravity_scenarios.py — End-to-end verification of diverse scenarios for Antigravity & Design Resolver.
"""

import os
import sys
from pathlib import Path

# Add project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.design_resolver import resolve_design, is_redesign_or_explicit_request, format_design_prompt

def run():
    print("=" * 60)
    print("VERIFYING SCENARIOS FOR DESIGN RESOLVER & ANTIGRAVITY")
    print("=" * 60)

    # Scenario 1: Generic Real Estate Landing Page
    p1 = "Create a modern, clean real estate landing page with 7 sections, header and footer"
    d1 = resolve_design(p1)
    print(f"\n[Scenario 1 - Real Estate generic]:\n  Prompt: '{p1}'\n  -> Resolved: {d1.source_name} ({d1.source_type})")
    assert "dub" in d1.source_name.lower(), f"Expected Dub reference for real estate, got {d1.source_name}"

    # Scenario 2: Redesign existing project with explicit reference (Saas-DESIGN)
    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        (tmp_path / "index.html").write_text("<html><head><style>:root { --bg: #fff; }</style></head><body><h1>Old Real Estate</h1></body></html>", encoding="utf-8")
        (tmp_path / "style.css").write_text("body { background: #fff; }", encoding="utf-8")

        p2 = "Change the design of the real estate landing page. Using the 'Saas-DESIGN.md' reference, completely update the color theme, typography, and styling."
        d2 = resolve_design(p2, repo_path=tmp_path)
        print(f"\n[Scenario 2 - Redesign existing with Saas reference]:\n  Prompt: '{p2}'\n  -> Resolved: {d2.source_name} ({d2.source_type})")
        assert "saas" in d2.source_name.lower(), f"Expected Saas reference, got {d2.source_name}"
        assert d2.source_type != "project_existing", "Redesign must override project_existing!"
        assert is_redesign_or_explicit_request(p2) is True, "Expected redesign intent detected"

    # Scenario 3: Creative Agency Showcase
    p3 = "Build a dynamic portfolio showcase for a branding design agency"
    d3 = resolve_design(p3)
    print(f"\n[Scenario 3 - Creative Agency]:\n  Prompt: '{p3}'\n  -> Resolved: {d3.source_name} ({d3.source_type})")
    assert "crazy" in d3.source_name.lower(), f"Expected Crazy UI for agency, got {d3.source_name}"

    # Scenario 4: AI Assistant Landing Page
    p4 = "Build a landing page for autonomous AI agents and bots"
    d4 = resolve_design(p4)
    print(f"\n[Scenario 4 - AI Agent]:\n  Prompt: '{p4}'\n  -> Resolved: {d4.source_name} ({d4.source_type})")
    assert "autonomus" in d4.source_name.lower(), f"Expected Autonomus for AI, got {d4.source_name}"

    # Scenario 5: Developer Platform
    p5 = "Create a developer API cloud platform landing page"
    d5 = resolve_design(p5)
    print(f"\n[Scenario 5 - Developer API Platform]:\n  Prompt: '{p5}'\n  -> Resolved: {d5.source_name} ({d5.source_type})")
    assert any(k in d5.source_name.lower() for k in ("saas", "nexus", "ecosystem")), f"Expected SaaS/Nexus/Ecosystem, got {d5.source_name}"

    # Scenario 6: Luxury Showcase
    p6 = "Build an elegant dark mode landing page for luxury watches and jewelry"
    d6 = resolve_design(p6)
    print(f"\n[Scenario 6 - Luxury Watch]:\n  Prompt: '{p6}'\n  -> Resolved: {d6.source_name} ({d6.source_type})")
    assert "aura" in d6.source_name.lower(), f"Expected Aura Frame for luxury, got {d6.source_name}"

    print("\n" + "=" * 60)
    print("ALL SCENARIOS VERIFIED SUCCESSFULLY WITH 100% ACCURACY!")
    print("=" * 60)

if __name__ == "__main__":
    run()
