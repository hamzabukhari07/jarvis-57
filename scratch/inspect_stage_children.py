import sys
from bs4 import BeautifulSoup
from pathlib import Path

html = Path("heyclicky_com_clone/raw_rendered.html").read_text(encoding="utf-8", errors="ignore")
soup = BeautifulSoup(html, "html.parser")

stage = soup.find("div", class_="stage")
if stage:
    print(f"Found div.stage with children:")
    for i, child in enumerate(stage.children):
        if child.name:
            classes = " ".join(child.get("class", [])) if child.get("class") else ""
            el_id = child.get("id", "")
            txt = child.get_text(strip=True)[:80].encode("ascii", "replace").decode("ascii")
            print(f"  [{i}] <{child.name}> id='{el_id}' class='{classes}' text_preview={repr(txt)}")
else:
    print("div.stage not found")
