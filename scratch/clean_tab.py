from pathlib import Path

p = Path("frontend/src/components/settings/SkillsSettingsTab.tsx")
content = p.read_text(encoding="utf-8")
content = content.replace("id: 'hamza_taste'", "id: 'website_build'")
content = content.replace("name: 'Hamza Taste (Studio UI)'", "name: 'Website Build (Studio UI)'")
p.write_text(content, encoding="utf-8")
print("Successfully updated SkillsSettingsTab.tsx")
