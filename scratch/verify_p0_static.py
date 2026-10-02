"""Layer-1 static verification for the P0 log-flicker fix.

- extracts every inline <script> from frontend/index.html and runs `node --check`
- asserts no `innerHTML +=` remains (the churn operator)
- asserts the 5 append sites use insertAdjacentHTML('beforeend', ...)

Run: python scratch/verify_p0_static.py   (exit 0 = pass)
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "frontend" / "index.html"

EXPECTED_APPEND_SITES = 5


def main() -> int:
    html = INDEX.read_text(encoding="utf-8")
    ok = True

    # 1. no churn operator left
    churn = re.findall(r"innerHTML\s*\+=", html)
    print(f"1) innerHTML += occurrences          : {len(churn)} (expect 0)")
    ok &= len(churn) == 0

    # 2. append sites use insertAdjacentHTML
    appends = re.findall(r"insertAdjacentHTML\('beforeend',", html)
    print(f"2) insertAdjacentHTML append sites   : {len(appends)} (expect {EXPECTED_APPEND_SITES})")
    ok &= len(appends) == EXPECTED_APPEND_SITES

    # 3. syntax-check every inline script with node --check
    script_re = re.compile(r"<script(?![^>]*\bsrc=)([^>]*)>(.*?)</script>", re.DOTALL | re.IGNORECASE)
    scripts = script_re.findall(html)
    print(f"3) inline scripts found              : {len(scripts)}")
    for i, (attrs, body) in enumerate(scripts):
        is_module = 'type="module"' in attrs
        suffix = ".mjs" if is_module else ".js"
        with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False,
                                         encoding="utf-8") as f:
            f.write(body)
            tmp = f.name
        proc = subprocess.run(["node", "--check", tmp],
                              capture_output=True, text=True)
        status = "OK" if proc.returncode == 0 else "SYNTAX ERROR"
        print(f"   script[{i}] {'module' if is_module else 'classic'}: {status}")
        if proc.returncode != 0:
            print(proc.stderr.strip())
            ok = False
        Path(tmp).unlink(missing_ok=True)

    print("LAYER-1 PASS" if ok else "LAYER-1 FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
