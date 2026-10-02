"""P1 evidence — is `mix-blend-mode: screen` on the avatar GIF a visual no-op?

The avatar GIF sits on a pure-black backdrop (#avatar-frame / #avatar-frame
.frame-inner { background:#000 !important }). For `screen`, blending any pixel
`s` over black `b=0` gives `1-(1-s)(1-0) = s`. So the blend cannot change a
single pixel there — it only forces a per-frame backdrop read inside a
`backdrop-filter` ancestor (the QtWebEngine compositor flicker hazard).

This test renders the GIF's real first frame twice, over the real nesting
(backdrop-filter parent, #000 background), once with `mix-blend-mode: screen`
and once with `normal`, screenshots both and asserts the pixels are identical.

Run: python scratch/verify_p1_blend.py   (exit 0 = blend is a confirmed no-op)
"""
import base64
import io
import sys
from pathlib import Path

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
GIF = ROOT / "frontend" / "download.gif"
SIZE = 200


def gif_first_frame_data_url() -> str:
    im = Image.open(GIF)
    im.seek(0)
    frame = im.convert("RGBA").resize((SIZE, SIZE))
    buf = io.BytesIO()
    frame.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


HTML = """
<!doctype html><html><head><style>
  html, body { margin:0; background:#000; }
  .frame-inner { position:relative; width:%(size)dpx; height:%(size)dpx;
                 background:#000 !important; backdrop-filter: blur(12px); }
  .vortex-gif { width:%(size)dpx; height:%(size)dpx; display:block; }
  #blend  .vortex-gif { mix-blend-mode: screen; }
  #normal .vortex-gif { mix-blend-mode: normal; }
</style></head><body>
  <div class="frame-inner" id="blend"><img class="vortex-gif" src="%(src)s"></div>
  <div class="frame-inner" id="normal"><img class="vortex-gif" src="%(src)s"></div>
</body></html>
"""


def main() -> int:
    if not GIF.exists():
        print("GIF not found")
        return 2
    data_url = gif_first_frame_data_url()
    html = HTML % {"size": SIZE, "src": data_url}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 500, "height": 500})
        page.set_content(html)

        styles = page.evaluate("""() => {
            const fi = document.getElementById('blend');
            const gif = fi.querySelector('.vortex-gif');
            return {
                frameBg: getComputedStyle(fi).backgroundColor,
                backdrop: getComputedStyle(fi).backdropFilter,
                blend: getComputedStyle(gif).mixBlendMode,
            };
        }""")

        el_blend = page.locator("#blend")
        el_normal = page.locator("#normal")
        shot_blend = el_blend.screenshot()
        shot_normal = el_normal.screenshot()
        browser.close()

    a = Image.open(io.BytesIO(shot_blend)).convert("RGB")
    b = Image.open(io.BytesIO(shot_normal)).convert("RGB")
    diff = ImageChops.difference(a, b)
    bbox = diff.getbbox()

    print(f"frame-inner background : {styles['frameBg']}  (expect rgb(0, 0, 0))")
    print(f"frame-inner backdrop   : {styles['backdrop']}")
    print(f"img mix-blend-mode     : {styles['blend']}  (expect screen)")
    print(f"pixel diff (blend vs normal): {bbox}  (expect None = identical)")

    ok = (
        styles["frameBg"] == "rgb(0, 0, 0)"
        and styles["backdrop"] not in (None, "", "none")
        and bbox is None
        and a.size == b.size
    )
    print("BLEND IS A VISUAL NO-OP OVER BLACK — safe to remove"
          if ok else "MISMATCH — blend changes pixels, do NOT remove blindly")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
