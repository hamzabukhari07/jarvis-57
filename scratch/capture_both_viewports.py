import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from playwright.sync_api import sync_playwright
from actions.website_cloner import start_local_preview_server

clone_dir = Path(r"C:\Users\Hamza\Desktop\heyclicky_com_clone_1")
preview_url, port = start_local_preview_server(clone_dir)
print(f"Preview server running at: {preview_url}")

art_dir = Path(r"C:\Users\Hamza\.gemini\antigravity-ide\brain\14010a5b-0116-4107-9e41-b0ac653bfcab")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    
    # 1. Desktop Screenshot (1440px)
    ctx_desktop = browser.new_context(viewport={"width": 1440, "height": 900})
    page_d = ctx_desktop.new_page()
    page_d.goto(preview_url, wait_until="domcontentloaded")
    page_d.wait_for_timeout(800)
    desktop_png = art_dir / "option_b_desktop_1440.png"
    page_d.screenshot(path=str(desktop_png), full_page=True)
    print(f"Saved desktop screenshot to {desktop_png}")
    ctx_desktop.close()

    # 2. Mobile Screenshot (375px)
    ctx_mobile = browser.new_context(viewport={"width": 375, "height": 812})
    page_m = ctx_mobile.new_page()
    page_m.goto(preview_url, wait_until="domcontentloaded")
    page_m.wait_for_timeout(800)
    mobile_png = art_dir / "option_b_mobile_375.png"
    page_m.screenshot(path=str(mobile_png), full_page=True)
    print(f"Saved mobile screenshot to {mobile_png}")
    ctx_mobile.close()
    
    browser.close()
