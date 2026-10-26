import os
import shutil
import re
from pathlib import Path

ROOT = Path(r"D:\anitgravity\zezo work\jarvis-57")

def update_file(path: Path, replacements: list[tuple[str, str]]):
    if not path.exists():
        print(f"File not found: {path}")
        return
    content = path.read_text(encoding="utf-8")
    original = content
    for target, rep in replacements:
        if target in content:
            content = content.replace(target, rep)
        else:
            print(f"Warning: target not found in {path.name}: {target[:50]}...")
    if content != original:
        path.write_text(content, encoding="utf-8")
        print(f"Updated {path.name}")
    else:
        print(f"No changes in {path.name}")

# 1. actions/design_extractor.py
design_extractor = ROOT / "actions" / "design_extractor.py"
de_content = design_extractor.read_text(encoding="utf-8")
de_content = re.sub(
    r'def _get_ui_dirs\(\) -> tuple\[Path, Path, Path\]:.*?(?=def _norm_stem)',
    '''def _get_ui_dirs() -> tuple[Path, Path, Path]:
    ws = _get_workspace_root()
    ref_ui = ws / "skills" / "website_build" / "references"
    if not ref_ui.exists() and (ws / "References" / "UI").exists():
        ref_ui = ws / "References" / "UI"
        
    html_dir = ref_ui
    md_dir = ref_ui / "design_md"
    md_dir.mkdir(parents=True, exist_ok=True)
    return ref_ui, html_dir, md_dir


''',
    de_content,
    flags=re.DOTALL
)

# update recursive search in _find_reference_file
old_search = '''    # 2. Search in html/
    if html_dir.exists():
        for p in html_dir.iterdir():
            if p.is_file() and p.suffix.lower() in (".html", ".htm"):
                if norm_q == _norm_stem(p.name) or norm_q in _norm_stem(p.name):
                    matched_html = p
                    break'''

new_search = '''    # 2. Search across references (recursively scanning all html files)
    if ref_ui.exists():
        for p in ref_ui.rglob("*.html"):
            if p.is_file():
                if norm_q == _norm_stem(p.name) or norm_q in _norm_stem(p.name):
                    matched_html = p
                    break'''

if old_search in de_content:
    de_content = de_content.replace(old_search, new_search)

design_extractor.write_text(de_content, encoding="utf-8")
print("Updated actions/design_extractor.py")

# 2. core/design_resolver.py
update_file(
    ROOT / "core" / "design_resolver.py",
    [
        (
            'p_ht = ws / "skills" / "hamza_taste" / "references" / "html" / Path(ref_path).name\n    if p_ht.exists() and p_ht.is_file() and p_ht.stat().st_size > 0:\n        return p_ht',
            'wb_dir = ws / "skills" / "website_build" / "references"\n    if wb_dir.exists():\n        for p in wb_dir.rglob(Path(ref_path).name):\n            if p.is_file() and p.stat().st_size > 0:\n                return p'
        ),
        (
            'fallback_ref = ws / "skills" / "hamza_taste" / "references"',
            'fallback_ref = ws / "References" / "new Designs"'
        ),
        (
            'ws / "skills" / "hamza_taste" / "SKILL.md",',
            '# ws / "skills" / "hamza_taste" / "SKILL.md",'
        ),
        (
            'ws / "skills" / "hamza_taste" / "references" / "catalog.json",',
            '# ws / "skills" / "hamza_taste" / "references" / "catalog.json",'
        )
    ]
)

# 3. tests/test_design_system_suite.py
update_file(
    ROOT / "tests" / "test_design_system_suite.py",
    [
        (
            'fake_session = {"active_design_path": "skills/hamza_taste/references/design md/Aura-Frame-DESIGN.md"}',
            'fake_session = {"active_design_path": "skills/website_build/references/5_components/aura frame.html"}'
        )
    ]
)

# 4. tests/test_extractor_suite.py
update_file(
    ROOT / "tests" / "test_extractor_suite.py",
    [
        (
            'html_dir = _PROJECT_ROOT / "skills" / "hamza_taste" / "references" / "html"\nmd_dir = _PROJECT_ROOT / "skills" / "hamza_taste" / "references" / "design md"',
            'html_dir = _PROJECT_ROOT / "skills" / "website_build" / "references" / "1_landing_pages"\nmd_dir = _PROJECT_ROOT / "skills" / "website_build" / "references" / "design_md"\nmd_dir.mkdir(parents=True, exist_ok=True)'
        ),
        (
            'matches = list(html_dir.glob(f"*{keyword}*.html"))',
            'matches = list((_PROJECT_ROOT / "skills" / "website_build" / "references").rglob(f"*{keyword}*.html"))'
        )
    ]
)

# 5. tests/test_phase4_agent_capability_registry_suite.py
test_phase4 = ROOT / "tests" / "test_phase4_agent_capability_registry_suite.py"
t4_content = test_phase4.read_text(encoding="utf-8")
t4_content = t4_content.replace('fleet_manager.get_agent("ALI")', 'fleet_manager.get_agent("VERVE")')
t4_content = t4_content.replace('"hamza_taste" in agent.allowed_skills', '"website_build" in agent.allowed_skills')
t4_content = t4_content.replace('"antigravity_run" in agent.allowed_tools', 'agent.engine == "antigravity"')
t4_content = t4_content.replace('ali_entry = next((a for a in state if a["id"] == "ALI"), None)', 'ali_entry = next((a for a in state if a["id"] == "VERVE"), None)')
t4_content = t4_content.replace('"antigravity_run" in ali_entry["allowed_tools"]', 'ali_entry.get("engine") == "antigravity"')
t4_content = t4_content.replace('agent_id="ALI"', 'agent_id="VERVE"')
t4_content = t4_content.replace('"antigravity_run" in ali_names', '"browser_control" in ali_names')
t4_content = t4_content.replace('assert res["agent_name"] == "Ali"', 'assert res["agent_name"] == "Verve"')
test_phase4.write_text(t4_content, encoding="utf-8")
print("Updated tests/test_phase4_agent_capability_registry_suite.py")

# 6. skills/antigravity_agent/SKILL.md
update_file(
    ROOT / "skills" / "antigravity_agent" / "SKILL.md",
    [
        (
            "skills/hamza_taste/references/html",
            "skills/website_build/references/"
        )
    ]
)

# 7. frontend/src/components/office/AutonomousOfficeScreen.tsx
update_file(
    ROOT / "frontend" / "src" / "components" / "office" / "AutonomousOfficeScreen.tsx",
    [
        (
            "{ id: 'hamza_taste', name: 'hamza_taste', desc: 'Studio UI aesthetic, anti-slop rules & design presets' }",
            "{ id: 'website_build', name: 'website_build', desc: 'Studio UI aesthetic, anti-slop rules & design presets' }"
        ),
        (
            "'hamza_taste'",
            "'website_build'"
        )
    ]
)

# 8. frontend/src/components/settings/SkillsSettingsTab.tsx
update_file(
    ROOT / "frontend" / "src" / "components" / "settings" / "SkillsSettingsTab.tsx",
    [
        (
            "id: 'hamza_taste',\n  name: 'Hamza Taste (Studio UI)',\n  type: 'skill',\n  category: 'design',",
            "id: 'website_build',\n  name: 'Website Build (Studio UI)',\n  type: 'skill',\n  category: 'ui',"
        ),
        (
            "['hamza_taste', 'antigravity_agent', 'make_plan'",
            "['website_build', 'antigravity_agent', 'make_plan'"
        )
    ]
)

# 9. Delete skills/hamza_taste directory permanently
hamza_taste_dir = ROOT / "skills" / "hamza_taste"
if hamza_taste_dir.exists():
    shutil.rmtree(hamza_taste_dir)
    print(f"DELETED DIRECTORY: {hamza_taste_dir}")
else:
    print(f"Directory already removed: {hamza_taste_dir}")

print("Clean operation completed successfully.")
