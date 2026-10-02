from bs4 import BeautifulSoup
from pathlib import Path

html = Path("heyclicky_com_clone/raw_rendered.html").read_text(encoding="utf-8", errors="ignore")
soup = BeautifulSoup(html, "html.parser")

print("Body direct children:")
if soup.body:
    for c in soup.body.children:
        if c.name:
            print(f"<{c.name} id='{c.get('id', '')}' class='{c.get('class', [])}'>")

print("\n--- Major sections found ---")
for el in soup.find_all(True):
    classes = " ".join(el.get("class", [])) if el.get("class") else ""
    el_id = el.get("id", "")
    tag = el.name
    combo = (tag + " " + el_id + " " + classes).lower()
    if tag in ["header", "footer", "section", "main", "nav"] or any(k in combo for k in ["hero", "feat", "stage", "manifesto", "love", "feedback", "fb", "pricing", "faq", "pr"]):
        if len(el.find_parents()) <= 4:
            print(f"Tag: <{tag}> id='{el_id}' class='{classes}' text_len={len(el.get_text(strip=True))}")
