from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto("https://heyclicky.com", wait_until="domcontentloaded", timeout=15000)
    page.wait_for_timeout(500)
    
    # Scroll smoothly through whole page to hydrate everything
    for y in range(0, 8000, 400):
        page.evaluate(f"window.scrollTo(0, {y})")
        page.wait_for_timeout(80)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(300)
    
    sections = page.evaluate("""
        () => {
            // 1. Collect all candidate semantic containers
            const candidates = Array.from(document.querySelectorAll('header, nav, section, footer, main > div > section, .stage > section, .stage > header, .stage > footer'));
            
            // 2. Keep only highest-level non-nested sections
            const topLevel = candidates.filter(el => {
                const rect = el.getBoundingClientRect();
                const height = Math.round(rect.height);
                const width = Math.round(rect.width);
                if (height < 40 || width < 300) return false;
                
                // If this element is inside another candidate that is not body/main/stage, skip it
                let parent = el.parentElement;
                while (parent && parent !== document.body) {
                    const tag = parent.tagName.toLowerCase();
                    const cls = parent.className || '';
                    if (tag === 'section' || tag === 'header' || tag === 'footer' || (tag === 'div' && cls.includes('section') && !cls.includes('stage'))) {
                        return false; // nested inside another section
                    }
                    parent = parent.parentElement;
                }
                return true;
            });
            
            // 3. Sort vertically
            topLevel.sort((a, b) => {
                const topA = Math.round(a.getBoundingClientRect().top + window.scrollY);
                const topB = Math.round(b.getBoundingClientRect().top + window.scrollY);
                return topA - topB;
            });
            
            return topLevel.map((el, i) => {
                const rect = el.getBoundingClientRect();
                const top = Math.round(rect.top + window.scrollY);
                const height = Math.round(rect.height);
                return {
                    index: i,
                    tag: el.tagName.toLowerCase(),
                    id: el.id || '',
                    classes: typeof el.className === 'string' ? el.className.slice(0, 60) : '',
                    top: top,
                    height: height,
                    html_len: el.outerHTML.length,
                    text_preview: (el.innerText || '').slice(0, 60).replace(/\\s+/g, ' ').trim()
                };
            });
        }
    """)
    
    print(f"Universal Detector found {len(sections)} sections:")
    for s in sections:
        preview = s['text_preview'].encode('ascii', 'replace').decode('ascii')
        print(f"[{s['index']:02d}] <{s['tag']}> id='{s['id']}' class='{s['classes']}' top={s['top']} h={s['height']} html_len={s['html_len']}")
        print(f"     Preview: {preview}")
        
    browser.close()
