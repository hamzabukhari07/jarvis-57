import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from actions.reverse_engineer import TOOL, reverse_engineer_action
from core.teardown_engine import (
    TeardownEvidence,
    build_rea_scenario_spec,
    generate_deterministic_blueprint,
    synthesize_groq_blueprint,
    get_configured_scaffolding_engine,
    scaffold_with_selected_engine,
)


def test_reverse_engineer_tool_declaration():
    """Verify standard Rule 4 TOOL declaration."""
    assert TOOL["name"] == "reverse_engineer"
    assert TOOL["behavior"] == "NON_BLOCKING"
    assert callable(TOOL["handler"])
    params = TOOL["parameters"]["properties"]
    assert "url" in params
    assert "focus" in params


def test_rea_scenario_spec_structure():
    """Verify scenario spec conforms to REA's browserScenarioSchema."""
    spec = build_rea_scenario_spec("https://stripe.com")
    assert "browser" in spec
    assert spec["browser"]["mode"] == "launch"
    assert spec["browser"]["headless"] is True
    assert spec["start_url"]["url"] == "https://stripe.com"
    assert "environment" in spec
    assert spec["environment"]["viewport"]["width"] == 1440
    assert "capture" in spec
    assert "dom" in spec["capture"]["at_end"]
    assert "accessibility" in spec["capture"]["at_end"]
    assert spec["capture"]["network"]["request_body"] is True


def test_get_configured_scaffolding_engine():
    """Verify configured engine lookup reads fleet settings without hardcoding."""
    cfg = get_configured_scaffolding_engine()
    assert isinstance(cfg, dict)
    assert "engine" in cfg
    assert "model" in cfg
    # Should resolve to one of the supported engines
    assert cfg["engine"] in ("antigravity_run", "opencode_run", "kilo_run", "groq")


def test_deterministic_blueprint_generation():
    """Verify deterministic fallback produces complete Markdown blueprint."""
    evidence = TeardownEvidence(
        url="https://threejs.org",
        domain="threejs.org",
        timestamp="2026-10-23T12:00:00Z",
        title="Three.js – JavaScript 3D Library",
        frameworks=["Vite", "React"],
        graphics=["WebGL 2.0", "Three.js (Detected)"],
        animations=["GSAP / GreenSock"],
        styling=["Tailwind CSS"],
        key_scripts=["https://threejs.org/build/three.module.js"],
        detected_apis=[{"url": "https://threejs.org/api/models.json", "method": "GET"}],
        dom_metrics={"total_nodes": 850},
        shaders_detected=["StandardMaterialShader"],
    )
    blueprint = generate_deterministic_blueprint(evidence)
    assert "Architectural Teardown: threejs.org" in blueprint
    assert "threejs.org" in blueprint
    assert "WebGL 2.0" in blueprint
    assert "GSAP" in blueprint
    assert "Tailwind CSS" in blueprint


@pytest.mark.asyncio
async def test_groq_synthesis_fallback():
    """Verify Groq blueprint synthesis falls back cleanly to deterministic blueprint when API unavailable."""
    evidence = TeardownEvidence(
        url="https://example.com",
        domain="example.com",
        timestamp="2026-10-23T12:00:00Z",
        title="Example Domain",
        frameworks=["HTML5"],
        graphics=[],
        animations=[],
        styling=["Vanilla CSS"],
    )
    blueprint = await synthesize_groq_blueprint(evidence)
    assert isinstance(blueprint, str)
    assert len(blueprint) > 50
    assert "example.com" in blueprint


def test_reverse_engineer_action_dispatch():
    """Verify the reverse_engineer_action handler dispatches non-blocking execution cleanly."""
    res = reverse_engineer_action({"url": "https://testsite.com"})
    assert isinstance(res, str)
    assert "Official REA engine is capturing testsite.com" in res
    assert "Desktop workspace" in res
    assert "Task ID:" in res


def test_conversational_url_and_domain_extraction():
    """Verify conversational prompts extract clean domain and URL without directory naming pollution."""
    conversational_inputs = [
        "can you rebuild this just only frontend https://stripe.com",
        "Inspect the architecture of vercel.com and rebuild it",
        "apple.com/iphone teardown please",
    ]
    for user_input in conversational_inputs:
        res = reverse_engineer_action({"url": user_input})
        assert isinstance(res, str)
        assert "can you rebuild" not in res
        assert "Inspect the architecture" not in res


@pytest.mark.asyncio
async def test_scaffold_creates_high_fidelity_components(tmp_path):
    """Verify scaffold_with_selected_engine generates real components, styling, package.json and standalone index.html."""
    evidence = TeardownEvidence(
        url="https://stripe.com",
        domain="stripe.com",
        timestamp="2026-10-23T12:00:00Z",
        title="Stripe | Financial Infrastructure",
        frameworks=["Next.js", "React"],
        graphics=["WebGL 2.0"],
        animations=["GSAP"],
        styling=["Tailwind CSS"],
    )

    out_dir = tmp_path / "stripe.com_rebuild"
    blueprint_path = tmp_path / "blueprint.md"
    blueprint_path.write_text("# Blueprint", encoding="utf-8")

    engine_config = {"engine": "antigravity_run", "model": "gemini-3.7-flash-medium"}
    await scaffold_with_selected_engine(evidence, blueprint_path, out_dir, engine_config)

    assert (out_dir / "index.html").exists()
    assert (out_dir / "package.json").exists()
    assert (out_dir / "README.md").exists()
    assert (out_dir / "components" / "Navbar.tsx").exists()
    assert (out_dir / "components" / "Hero.tsx").exists()
    assert (out_dir / "components" / "Scene3D.tsx").exists()
    assert (out_dir / "styles" / "globals.css").exists()

    index_content = (out_dir / "index.html").read_text(encoding="utf-8")
    app_content = (out_dir / "src" / "App.tsx").read_text(encoding="utf-8")
    assert "stripe.com" in app_content
    assert "React 18 + Vite + Tailwind" in app_content
