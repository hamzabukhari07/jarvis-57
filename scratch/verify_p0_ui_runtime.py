"""P0 runtime verification through the REAL frontend code path.

Serves the actual frontend/ directory over HTTP + a real /ws endpoint that
emits N `log_entry` events (spaced 80 ms, like real backend logs). Playwright
opens the real index.html and a MutationObserver on #stream-box counts how
many nodes get added/removed while the log stream is appended.

Before fix (innerHTML +=): every new line destroys+recreates all existing
cards  -> added == N*(N+1)/2, removed > 0  -> visible blinking.
After  fix (insertAdjacentHTML): each line adds exactly 1 node, nothing is
destroyed -> added == N, removed == 0.

Run: python scratch/verify_p0_ui_runtime.py
Exit 0 = fixed behaviour observed on the production file.
"""
import asyncio
import sys
import threading
from pathlib import Path

from aiohttp import web
from playwright.sync_api import sync_playwright

N = 10
INTERVAL = 0.08
ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"


def build_app() -> web.Application:
    app = web.Application()

    async def index(_request):
        return web.FileResponse(FRONTEND / "index.html")

    async def start(request):
        request.app["start_event"].set()
        return web.Response(text="ok")

    async def ws_handler(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await request.app["start_event"].wait()
        state = request.app["state"]
        if not state["sent"]:
            state["sent"] = True
            for i in range(N):
                await ws.send_json({"type": "log_entry",
                                    "data": {"tag": "SYS", "message": f"line {i}"}})
                await asyncio.sleep(INTERVAL)
        # keep the socket open a moment so the last frame lands
        await asyncio.sleep(0.5)
        return ws

    app.router.add_get("/", index)
    app.router.add_get("/index.html", index)
    app.router.add_get("/start", start)
    app.router.add_get("/ws", ws_handler)
    app.router.add_static("/", path=str(FRONTEND), show_index=False)
    return app


class ServerThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        import socket
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        self.port = s.getsockname()[1]
        s.close()
        self._loop = None
        self._started = threading.Event()

    def run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        app = build_app()
        app["start_event"] = asyncio.Event()
        app["state"] = {"sent": False}
        runner = web.AppRunner(app)
        self._loop.run_until_complete(runner.setup())
        site = web.TCPSite(runner, "127.0.0.1", self.port)
        self._loop.run_until_complete(site.start())
        self._started.set()
        self._loop.run_forever()


def main() -> int:
    if not (FRONTEND / "index.html").exists():
        print("frontend/index.html not found")
        return 2

    server = ServerThread()
    server.start()
    if not server._started.wait(10):
        print("server failed to start")
        return 2
    url = f"http://127.0.0.1:{server.port}/"
    print(f"serving real frontend at {url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        # Block external CDNs so the run is fast/deterministic; the log
        # rendering path under test does not depend on them.
        def _route(route):
            u = route.request.url
            if u.startswith(("http://127.0.0.1", "http://localhost", "data:", "blob:")):
                route.continue_()
            else:
                route.abort()

        context.route("**/*", _route)
        page = context.new_page()
        page.on("console", lambda m: print("  [console]", m.type, m.text))
        page.on("pageerror", lambda e: print("  [pageerror]", e))

        # expect_websocket must wrap the action that triggers the connection.
        with page.expect_websocket(timeout=15000):
            page.goto(url, wait_until="domcontentloaded")

        # Install observer before any log frame is sent (server waits on /start).
        page.evaluate("""() => {
            window.__mut = { added: 0, removed: 0 };
            const isEl = n => n.nodeType === 1;
            const box = document.getElementById('stream-box');
            const obs = new MutationObserver(recs => {
                for (const r of recs) {
                    window.__mut.added += Array.from(r.addedNodes).filter(isEl).length;
                    window.__mut.removed += Array.from(r.removedNodes).filter(isEl).length;
                }
            });
            obs.observe(box, { childList: true });
        }""")

        page.evaluate("() => fetch('/start')")
        page.wait_for_timeout(int(N * INTERVAL * 1000) + 1200)

        result = page.evaluate("() => window.__mut")
        children = page.evaluate("() => document.getElementById('stream-box').children.length")
        first_text = page.evaluate(
            "() => { const c = document.getElementById('stream-box').children[0];"
            " return c ? c.textContent.trim().slice(0, 40) : ''; }"
        )
        _ = first_text
        browser.close()

    print(f"log lines emitted            : {N}")
    print(f"#stream-box nodes added      : {result['added']}   (expect {N})")
    print(f"#stream-box nodes removed    : {result['removed']}   (expect 0)")
    print(f"#stream-box final children   : {children}   (expect {N})")

    ok = result["added"] == N and result["removed"] == 0 and children == N
    print("RUNTIME VERIFY PASS (no node churn)" if ok else "RUNTIME VERIFY FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
