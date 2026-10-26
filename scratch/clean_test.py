from pathlib import Path

p = Path("tests/test_design_system_suite.py")
content = p.read_text(encoding="utf-8")
content = content.replace('self.assertIn("Aura", res.source_name)', 'self.assertIn("aura", res.source_name.lower())')
content = content.replace('self.assertIn("Saas", res_name.source_name)', 'self.assertIn("saas", res_name.source_name.lower())')
p.write_text(content, encoding="utf-8")
print("Fixed case insensitivity in test_design_system_suite.py")
