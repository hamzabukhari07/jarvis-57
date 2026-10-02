import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto("https://heyclicky.com", wait_until="networkidle")
    
    print("Initial #feat text:", len(page.inner_text("#feat")))
    
    # Scroll down gradually
    for y in range(0, 5000, 400):
        page.evaluate(f"window.scrollTo(0, {y})")
        time.sleep(0.15)
        
    time.sleep(1.0)
    print("After scrolling #feat text:", len(page.inner_text("#feat")))
    print("After scrolling #feat HTML len:", len(page.inner_html("#feat")))
    
    # Check all sections text
    for sec_id in ["menubar", "hero", "feat", "man-section", "fb", "pr", "faq", "footer"]:
        selector = f"#{sec_id}" if sec_id in ["feat", "pr"] else f".{sec_id}"
        el = page.query_selector(selector)
        if el:
            txt = el.inner_text().strip()[:60].replace("\n", " ")
            print(f"Found {selector}: len_text={len(el.inner_text())}, preview={repr(txt)}")
        else:
            print(f"NOT found: {selector}")
            
    browser.close()
