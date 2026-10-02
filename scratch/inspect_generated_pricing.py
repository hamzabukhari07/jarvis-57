from pathlib import Path
from bs4 import BeautifulSoup

html = Path(r"C:\Users\Hamza\Desktop\heyclicky_com_clone\index.html").read_text(encoding="utf-8", errors="ignore")
soup = BeautifulSoup(html, "html.parser")

pr = soup.find(class_=lambda c: c and "pr" in c)
if pr:
    print("Found pricing section!")
    print(pr.get_text()[:300])
    cards = pr.find_all(class_=lambda c: c and any(k in c for k in ["card", "tier", "plan", "col", "mac"]))
    print(f"Cards found: {len(cards)}")
    for i, c in enumerate(cards[:5]):
        print(f"  Card {i}: {c.get_text()[:80]}")
else:
    print("Pricing section not found in index.html")
