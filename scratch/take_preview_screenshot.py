import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from playwright.sync_api import sync_playwright
from actions.website_cloner import start_local_preview_server

clone_dir = Path(r"C:\Users\Hamza\Desktop\heyclicky_com_clone")
preview_url, port = start_local_preview_server(clone_dir)
print(f"Preview server running at: {preview_url}")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    
    page.goto(preview_url, wait_until="domcontentloaded")
    page.wait_for_timeout(1000)
    
    out_png = Path(r"C:\Users\Hamza\.gemini\antigravity-ide\brain\14010a5b-0116-4107-9e41-b0ac653bfcab\full_clone_verified.png")
    page.screenshot(path=str(out_png), full_page=True)
    print(f"Saved full page screenshot to {out_png}")
    browser.close()
