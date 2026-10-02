from pathlib import Path
from bs4 import BeautifulSoup

html = Path(r"C:\Users\Hamza\Desktop\heyclicky_com_clone\index.html").read_text(encoding="utf-8", errors="ignore")
soup = BeautifulSoup(html, "html.parser")

pr = soup.find(id="pr") or soup.find(class_=lambda c: c and "pr" in c)
if pr:
    print(pr.get_text())
