from bs4 import BeautifulSoup
from pathlib import Path

html = Path("heyclicky_com_clone/raw_rendered.html").read_text(encoding="utf-8", errors="ignore")
soup = BeautifulSoup(html, "html.parser")

stage = soup.find("div", class_="stage")
for i, child in enumerate(stage.children):
    if child.name:
        classes = " ".join(child.get("class", [])) if child.get("class") else ""
        el_id = child.get("id", "")
        print(f"Child {i}: <{child.name}> id='{el_id}' class='{classes}' len_html={len(str(child))}")
