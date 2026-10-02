"""P1 verification — the real frontend no longer blends the avatar GIF.

- static: `mix-blend-mode` is gone from frontend/index.html
- runtime: serving the real index.html, the computed `mix-blend-mode` of
  #vortex-gif is `normal`, the GIF actually decoded (naturalWidth > 0), and the
  page produced no JS errors.

Run: python scratch/verify_p1_applied.py   (exit 0 = pass)
"""
import re
import socket
import sys
import threading
import functools
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
INDEX = FRONTEND / "index.html"


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def main() -> int:
    html = INDEX.read_text(encoding="utf-8")
    ok = True

    css_no_comments = re.sub(r"/\*.*?\*/", "", html, flags=re.DOTALL)
    static_blend = len(re.findall(r"mix-blend-mode\s*:", css_no_comments))
    print(f"1) static `mix-blend-mode` occurrences : {static_blend} (expect 0)")
    ok &= static_blend == 0

    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(FRONTEND))
    httpd = ThreadingHTTPServer(("127.0.0.1", _free_port()), handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()

        def _route(route):
            u = route.request.url
            if u.startswith(("http://127.0.0.1", "http://localhost", "data:", "blob:")):
                route.continue_()
            else:
                route.abort()

        context.route("**/*", _route)
        page = context.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"http://127.0.0.1:{port}/index.html", wait_until="domcontentloaded")
        page.wait_for_timeout(1500)

        info = page.evaluate("""() => {
            const gif = document.getElementById('vortex-gif');
            return {
                blend: gif ? getComputedStyle(gif).mixBlendMode : '(missing)',
                naturalWidth: gif ? gif.naturalWidth : -1,
                visible: gif ? gif.getBoundingClientRect().width > 0 : false,
            };
        }""")
        browser.close()

    httpd.shutdown()

    print(f"2) #vortex-gif computed mix-blend-mode : {info['blend']} (expect normal)")
    print(f"3) #vortex-gif decoded naturalWidth    : {info['naturalWidth']} (expect 600)")
    print(f"4) #vortex-gif has layout width        : {info['visible']}")
    print(f"5) page JS errors                      : {len(errors)} {errors}")

    ok &= info["blend"] == "normal"
    ok &= info["naturalWidth"] == 600
    ok &= info["visible"] is True
    ok &= len(errors) == 0

    print("P1 VERIFY PASS" if ok else "P1 VERIFY FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
