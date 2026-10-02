import json
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    try:
        page.goto("https://heyclicky.com", wait_until="domcontentloaded", timeout=15000)
    except Exception as e:
        print("Goto warning:", e)
        
    page.wait_for_timeout(1000)
    
    # Scroll smoothly through whole page to hydrate everything
    for y in range(0, 5000, 400):
        page.evaluate(f"window.scrollTo(0, {y})")
        page.wait_for_timeout(100)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(300)
    
    sections = page.evaluate("""
        () => {
            const results = [];
            // Target direct top-level semantic sections
            const elements = document.querySelectorAll('.stage > section, .stage > header, .stage > footer, main > section, main > header, main > footer, body > section, body > header, body > footer');
            elements.forEach((el, i) => {
                const rect = el.getBoundingClientRect();
                const top = Math.round(rect.top + window.scrollY);
                const height = Math.round(rect.height);
                const tag = el.tagName.toLowerCase();
                const cls = el.className;
                const id = el.id;
                
                // Skip invisible or empty elements
                if (height < 30) return;
                
                results.push({
                    index: i,
                    tag: tag,
                    id: id,
                    classes: typeof cls === 'string' ? cls : '',
                    top: top,
                    height: height,
                    text_preview: (el.innerText || '').slice(0, 80).replace(/\\s+/g, ' ').trim(),
                    html_len: el.outerHTML.length
                });
            });
            return results;
        }
    """)
    
    print("Detected Top-Level Sections:")
    for s in sections:
        preview = s['text_preview'].encode('ascii', 'replace').decode('ascii')
        print(f"[{s['index']:02d}] <{s['tag']}> id='{s['id']}' class='{s['classes']}' top={s['top']} h={s['height']} html_len={s['html_len']}")
        print(f"     Preview: {preview}")
        
    browser.close()
