import re
from pathlib import Path

text = Path("core/ui_server.py").read_text(encoding="utf-8")
endpoints = re.findall(r'@app\.(?:get|post|put|delete)\(["\']([^"\']+)["\']', text)
for ep in sorted(endpoints):
    print(ep)

