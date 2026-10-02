from bs4 import BeautifulSoup
from pathlib import Path

html = Path("heyclicky_com_clone/raw_rendered.html").read_text(encoding="utf-8", errors="ignore")
soup = BeautifulSoup(html, "html.parser")

feat = soup.find(id="feat")
print("Content of #feat:")
print(feat.prettify() if feat else "Not found")

print("\nWhere are the features rows?")
for el in soup.find_all(class_=lambda c: c and any(k in str(c) for k in ["feat", "showcase", "clicky-fl", "finally do the thing"])):
    print(f"<{el.name} class='{el.get('class')}'> text={el.get_text()[:40]}")
