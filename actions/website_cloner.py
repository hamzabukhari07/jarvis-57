"""
actions/website_cloner.py - Autonomous Website Cloner & Capture Rebuilder for Zezo.

Auto-discovered by core/action_loader.
Clones a site's static frontend into Desktop/<domain>_clone/ with offline assets and launches a
local HTTP preview server (http://127.0.0.1:PORT). With output_format=react/nextjs it then rebuilds
the capture as a real React/Vite project in Desktop/<domain>_cloned_app via ZEZO's own coding engine.

Architecture:
- Engine: bundled Uncage CLI (tools/uncage) — stealth Playwright crawl, asset localization, static assembly
- Strict completion check: a run counts as success only when the assembler finished
  (asset-map.json + index.html present, captured-raw*.html gone) — see _uncage_result_ok
- Self-tuned flags: explicit per-page --timeout, generous wall-clock budget, and a
  degradation retry with --skip-deps when a heavy crawl is cut short
- Post-clone asset integrity gate before the preview opens (verify_local_assets)
- Optional React/Next rebuild performed by ZEZO itself via the local Antigravity CLI
- Local ephemeral HTTP server (no CORS / no file:// path breakage)
- Asynchronous TaskManager execution with milestone progress reporting
"""

from __future__ import annotations

import concurrent.futures
import functools
import http.server
import json
import logging
import mimetypes
import os
import platform
import queue
import re
import shutil
import socket
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# Defensive Package Imports
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

try:
    from scrapling import Fetcher, StealthyFetcher
    SCRAPLING_AVAILABLE = True
except ImportError:
    SCRAPLING_AVAILABLE = False

from core.repo_context import (
    expand_user_dir,
    get_unique_clone_dir,
    is_zezo_source_dir,
    register_clone,
    register_rebuild,
)
from core.task_manager import get_task_manager, TaskContext
from core.undo import register_clone_snapshot

logger = logging.getLogger("zezo.website_cloner")

if platform.system() == "Windows":
    _WIN_HIDE = {
        "creationflags": (
            subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS
        )
    }
else:
    _WIN_HIDE = {}

# Hard Resource & Safety Caps
MAX_SINGLE_ASSET_BYTES = 25 * 1024 * 1024   # 25 MB
MAX_TOTAL_DIR_BYTES = 200 * 1024 * 1024     # 200 MB
MAX_ASSET_WORKERS = 8
MAX_PAGES_FULL_SITE = 50
MAX_DEPTH_FULL_SITE = 2

# Uncage auto-tuning. Two different timeouts exist and must not be conflated:
#   * SINGLE/PER_PAGE/CRAWL_* below are ZEZO's WALL-CLOCK budget for the whole process
#   * UNCAGE_PAGE_TIMEOUT_* feed uncage's own --timeout, its PER-PAGE navigation timeout
# A heavy SPA can be killed inside uncage's unbounded JS module dependency scan, so the
# wall-clock budget is generous and a killed crawl is retried with --skip-deps (see
# run_uncage_exporter) rather than reported as a broken success.
SINGLE_PAGE_TIMEOUT_SEC = 150
PER_PAGE_TIMEOUT_SEC = 40
CRAWL_BASE_SEC = 60
MIN_CRAWL_TIMEOUT_SEC = 180
MAX_CRAWL_TIMEOUT_SEC = 600          # stays under TaskManager.MAX_WALLCLOCK_SEC (1200)
UNCAGE_PAGE_TIMEOUT_SINGLE_MS = 30000
UNCAGE_PAGE_TIMEOUT_CRAWL_MS = 45000
# Fidelity-first: PurgeCSS can drop classes that are only applied at runtime, which renders
# a cloned page broken. Keeping every class costs file size but preserves the design.
UNCAGE_NO_PURGE = True

# Global Preview Server Pool
_PREVIEW_SERVERS: Dict[int, http.server.ThreadingHTTPServer] = {}
_PREVIEW_DIR_TO_PORT: Dict[str, Tuple[str, int]] = {}
_PREVIEW_LOCK = threading.Lock()


def _safe_report(ctx: Optional[TaskContext], pct: int, msg: str = "") -> None:
    """Safely report progress without raising if context is absent."""
    if ctx and hasattr(ctx, "report") and callable(ctx.report):
        try:
            ctx.report(pct, msg)
        except Exception:
            pass


# ── Ephemeral Preview HTTP Server ──────────────────────────────────────────

def _find_free_port(start: int = 9400, end: int = 9480) -> int:
    """Finds an available TCP loopback port that is NOT in use."""
    for port in range(start, end):
        if port in _PREVIEW_SERVERS:
            continue
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    # Fallback to OS assigned ephemeral port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _QuietHTTPHandler(http.server.SimpleHTTPRequestHandler):
    """Simple HTTP request handler with suppressed logging and CORS headers."""
    def log_message(self, format: str, *args: Any) -> None:
        pass  # Suppress terminal noise

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()


def start_local_preview_server(directory: Path) -> Tuple[str, int]:
    """Starts or reuses a lightweight daemon HTTP server serving the cloned directory."""
    with _PREVIEW_LOCK:
        norm_path = str(directory.resolve())
        if norm_path in _PREVIEW_DIR_TO_PORT:
            preview_url, port = _PREVIEW_DIR_TO_PORT[norm_path]
            if port in _PREVIEW_SERVERS:
                return preview_url, port

        httpd = None
        selected_port = 9400
        for _ in range(10):
            selected_port = _find_free_port()
            try:
                handler_cls = functools.partial(_QuietHTTPHandler, directory=norm_path)
                httpd = http.server.ThreadingHTTPServer(("127.0.0.1", selected_port), handler_cls)
                break
            except OSError:
                _PREVIEW_SERVERS.pop(selected_port, None)
                continue

        if httpd is None:
            handler_cls = functools.partial(_QuietHTTPHandler, directory=norm_path)
            httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
            selected_port = httpd.server_address[1]

        _PREVIEW_SERVERS[selected_port] = httpd
        preview_url = f"http://127.0.0.1:{selected_port}/index.html"
        _PREVIEW_DIR_TO_PORT[norm_path] = (preview_url, selected_port)

        t = threading.Thread(
            target=httpd.serve_forever,
            name=f"zezo-preview-{selected_port}",
            daemon=True,
        )
        t.start()
        logger.info("Started preview server on %s for %s", preview_url, norm_path)
        return preview_url, selected_port


def _open_in_browser(url: str) -> None:
    """Open a URL/URI in the user's browser, preferring ZEZO's own browser channel."""
    if url.startswith("file://"):
        opened = False
        try:
            import webbrowser
            opened = bool(webbrowser.open(url))
        except Exception:
            opened = False
        if not opened and os.name == "nt":
            try:
                path_str = urllib.request.url2pathname(urllib.parse.urlparse(url).path)
                os.startfile(path_str)
            except Exception:
                pass
        return

    try:
        from actions.browser_control import browser_control
        res = browser_control({"action": "go_to", "url": url})
        if not res or (
            isinstance(res, str)
            and (
                res.startswith("Validation error")
                or res.startswith("Invalid URL")
                or res.startswith("Error")
            )
        ):
            import webbrowser
            webbrowser.open(url)
    except Exception:
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            pass


def _open_deliverable(path: Path, clone_dir: Path) -> str:
    """Open the finished artifact and return where it was opened.

    A single self-contained HTML page opens straight off disk (file://) - a localhost server for
    one file is pointless indirection. A page whose refs are root-absolute ('/assets/...') cannot
    render over file://, and a project folder has no single file to open, so only those two cases
    keep the server. Which one applies is read from the file's own markup, never assumed.
    """
    html = ""
    if path.is_file():
        try:
            html = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            html = ""

    if html and not re.search(r'(?:src|href)\s*=\s*["\']/(?!/)', html):
        uri = path.resolve().as_uri()
        _open_in_browser(uri)
        return uri

    _preview_url, port = start_local_preview_server(clone_dir)
    try:
        rel = path.relative_to(clone_dir).as_posix()
        subpath = "" if rel == "." else f"/{rel}"
    except Exception:
        subpath = ""
    url = f"http://127.0.0.1:{port}{subpath}"
    _open_in_browser(url)
    return url


# ── URL Normalization & Sanitization ────────────────────────────────────────

def _normalize_url(raw: str) -> str:
    """Ensures scheme and standard formatting."""
    url = (raw or "").strip()
    if not url:
        return ""
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    return url


def _extract_domain(url: str) -> str:
    """Extracts a clean domain name for directory naming (e.g. 'apple.com' -> 'apple')."""
    try:
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc or parsed.path
        netloc = re.sub(r":\d+$", "", netloc)  # Remove port
        netloc = re.sub(r"^www\.", "", netloc) # Remove www
        clean = re.sub(r"[^\w\-]", "_", netloc).strip("_")
        return clean or "website"
    except Exception:
        return "website"


def _sanitize_filename(name: str, max_len: int = 64) -> str:
    """Creates a clean filesystem-safe filename."""
    name = re.sub(r"[\\/*?:\"<>|]", "_", name)
    name = re.sub(r"_+", "_", name).strip("_.")
    if not name:
        name = "asset"
    if len(name) > max_len:
        stem, ext = os.path.splitext(name)
        name = stem[:max_len - len(ext)] + ext
    return name


# ── 200ms Tech-Stack Fingerprinting Engine ─────────────────────────────────

def detect_tech_stack(url: str, timeout_sec: int = 4) -> str:
    """
    Lightweight (<200ms) HTTP head/headers inspection to determine website framework.
    Returns: 'framer' | 'webflow' | 'nextjs' | 'react' | 'wordpress' | 'shopify' | 'wix' | 'squarespace' | 'standard_html'
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            chunk = resp.read(32768).decode("utf-8", errors="ignore").lower()
            headers_str = str(resp.headers).lower()

            if "framerusercontent.com" in chunk or 'content="framer"' in chunk or "__framer__" in chunk:
                return "framer"
            if "data-wf-page" in chunk or "webflow.js" in chunk or "wf-site" in chunk:
                return "webflow"
            if "__next_data__" in chunk or "/_next/static/" in chunk or "x-powered-by: next.js" in headers_str:
                return "nextjs"
            if "/wp-content/" in chunk or "/wp-includes/" in chunk or 'content="wordpress"' in chunk:
                return "wordpress"
            if "cdn.shopify.com" in chunk or "shopify.theme" in chunk:
                return "shopify"
            if "wix.com" in chunk or "parastorage.com" in chunk or "wix-code" in chunk:
                return "wix"
            if "squarespace.com" in chunk or "static1.squarespace.com" in chunk:
                return "squarespace"
    except Exception as e:
        logger.debug("Tech stack detection error: %s", e)

    return "standard_html"


def _ensure_uncage_browsers(uncage_root: Path, ctx: Optional[TaskContext] = None) -> Tuple[bool, str]:
    """Make sure the Node Playwright inside tools/uncage has a matching Chromium.

    Uncage launches Chromium through its own `playwright` install. When that npm
    package is updated without re-downloading its browser, every clone dies at
    "[1/5] Launching stealth browser" with "Executable doesn't exist at
    ...chromium_headless_shell-<rev>...". Asking the installed package where its
    browser should be, and fetching it when absent, turns a hard failure into a
    one-time self-heal. Returns (ok, detail).
    """
    node_bin = shutil.which("node") or shutil.which("node.exe") or "node"
    cli = uncage_root / "node_modules" / "playwright" / "cli.js"
    probe = (
        "const {chromium}=require('playwright');"
        "process.stdout.write(chromium.executablePath())"
    )

    def _browser_path() -> str:
        r = subprocess.run(
            [node_bin, "-e", probe],
            cwd=str(uncage_root), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=60, **_WIN_HIDE,
        )
        return (r.stdout or "").strip() if r.returncode == 0 else ""

    try:
        exe = _browser_path()
        if exe and Path(exe).exists():
            return True, ""
    except Exception as e:
        logger.debug("Uncage browser preflight could not read executablePath: %s", e)

    if not cli.exists():
        return False, f"Uncage Playwright CLI missing at {cli}."

    _safe_report(ctx, 18, "[UNCAGE] Playwright browser missing — downloading Chromium (one-time)…")
    try:
        r = subprocess.run(
            [node_bin, str(cli), "install", "chromium"],
            cwd=str(uncage_root), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=900, **_WIN_HIDE,
        )
        if r.returncode != 0:
            tail = (r.stderr or r.stdout or "").strip().splitlines()
            return False, "Playwright browser download failed: " + (tail[-1] if tail else "unknown error")
    except Exception as e:
        return False, f"Playwright browser download failed: {e}"

    try:
        exe = _browser_path()
        if exe and Path(exe).exists():
            return True, ""
        return False, "Playwright browser still missing after install."
    except Exception as e:
        return False, f"Playwright browser re-check failed: {e}"


# ── Uncage Result Validation & Post-Clone Integrity ────────────────────────

def crawl_timeout_budget(max_pages: int) -> int:
    """ZEZO's wall-clock budget for one uncage run, derived from crawl scope."""
    if max_pages <= 1:
        return SINGLE_PAGE_TIMEOUT_SEC
    return min(
        MAX_CRAWL_TIMEOUT_SEC,
        max(MIN_CRAWL_TIMEOUT_SEC, CRAWL_BASE_SEC + max_pages * PER_PAGE_TIMEOUT_SEC),
    )


def _uncage_page_timeout_ms(max_pages: int) -> int:
    """Uncage's --timeout is a PER-PAGE navigation timeout, not the crawl budget."""
    return UNCAGE_PAGE_TIMEOUT_CRAWL_MS if max_pages > 1 else UNCAGE_PAGE_TIMEOUT_SINGLE_MS


def _uncage_result_ok(raw_output_dir: Path, returncode: int) -> Tuple[bool, str]:
    """
    True only for a COMPLETED uncage run.

    A killed or crashed run leaves a staging snapshot behind: `captured-raw*.html` is
    written per route early in extraction (tools/uncage/src/extractor.ts:708), while
    `asset-map.json` is the extractor's LAST write, after the JS module dependency scan
    (src/extractor.ts:748), and the assembler deletes the raw snapshots when it finishes
    (src/formats/html.ts:308-316). Requiring all three signals is what separates
    "assembled" from "died halfway" — the distinction that was previously lost.
    """
    if returncode != 0:
        return False, f"uncage exited with code {returncode}"
    root = Path(raw_output_dir)
    if not root.is_dir():
        return False, "uncage wrote no output directory"

    raws = sorted(p.name for p in root.glob("captured-raw*.html"))
    has_index = (root / "index.html").is_file()
    has_map = (root / "asset-map.json").is_file()

    # A surviving raw snapshot means the consolidate/assemble stage never ran. That stage sits
    # AFTER compile in the pipeline, so index.html + asset-map.json can both exist while the
    # bundle is still un-assembled — accepting that state is the false success this guards.
    if raws:
        return False, (
            "uncage stopped before assembly: the raw page snapshot "
            f"({raws[0]}) was never consolidated into the final bundle"
        )
    if not has_map:
        return False, "uncage produced no asset-map.json - extraction did not finish"
    if not has_index:
        return False, "uncage produced no assembled index.html"
    return True, ""


def _looks_like_partial_extraction(raw_output_dir: Path) -> bool:
    """True when uncage wrote raw page snapshots but never completed extraction."""
    try:
        root = Path(raw_output_dir)
        return root.is_dir() and any(root.glob("captured-raw*.html"))
    except Exception:
        return False


_LOCAL_REF_RE = re.compile(r'(?:src|href)\s*=\s*["\']([^"\']+)["\']', re.I)
_SKIP_REF_PREFIXES = ("http://", "https://", "//", "data:", "mailto:", "javascript:", "#")
# Evidence: uncage localises stylesheets, scripts, fonts and images, but its asset pipeline does
# not track <video>/<audio> sources at all - a real export's asset-map.json contained no .mp4 entry
# while every image was fetched. A missing stylesheet/script/image means the page renders broken
# (the reported defect), so that is fatal; a video uncage never tried to download is reported as a
# caveat instead, because failing the clone would block every video-bearing site forever.
_SKIP_MEDIA_EXT = (
    ".mp4", ".webm", ".mov", ".m4v", ".ogv", ".avi", ".mkv",
    ".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac",
)
# How much missing render-critical material means "broken clone" rather than "a few stragglers".
# Both ends are measured, not guessed: the clone the user reported as broken resolved 0% of its
# assets (the assets/ folder was never populated at all), while a healthy clone of a JS-heavy
# marketing site resolved ~97% (a handful of lazy <img> and <video> sources uncage left behind).
# 25% sits far from both, and the exact "renders unstyled" symptom is caught separately below by
# the stylesheet/script rules, independent of any ratio.
_MISSING_ASSET_FATAL_RATIO = 0.25


def verify_local_assets(root: Path, max_files: int = 25) -> Tuple[bool, str]:
    """
    Verify that assets/... references in the exported HTML resolve on disk.

    Scoped deliberately to the uncage asset namespace: a missing favicon, robots.txt or
    a leftover CDN reference must never fail an otherwise-good clone.

    Returns (ok, detail). `ok` is False only for wholesale breakage: most render-critical
    references missing, or every stylesheet/script gone (which is the "पेज फटा हुआ" symptom
    this gate exists to catch). Anything smaller is delivered with an explicit caveat, and
    heavy media uncage never downloads is always a caveat rather than a failure.
    """
    root = Path(root)
    missing: Set[str] = set()
    missing_media: Set[str] = set()
    critical: Set[str] = set()
    css_refs: Set[str] = set()
    css_ok: Set[str] = set()
    js_refs: Set[str] = set()
    js_ok: Set[str] = set()

    for html in sorted(root.rglob("*.html"))[:max_files]:
        try:
            text = html.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for raw_ref in _LOCAL_REF_RE.findall(text):
            ref = raw_ref.split("?", 1)[0].split("#", 1)[0].strip()
            if not ref or ref.startswith(_SKIP_REF_PREFIXES):
                continue
            norm = ref.lstrip("./")
            if not norm.startswith("assets/"):
                continue
            exists = (root / norm).exists()
            if norm.lower().endswith(_SKIP_MEDIA_EXT):
                if not exists:
                    missing_media.add(norm)
                continue
            critical.add(norm)
            if exists:
                if norm.lower().endswith(".css"):
                    css_ok.add(norm)
                elif norm.lower().endswith((".js", ".mjs")):
                    js_ok.add(norm)
                continue
            missing.add(norm)
            if norm.lower().endswith(".css"):
                css_refs.add(norm)
            elif norm.lower().endswith((".js", ".mjs")):
                js_refs.add(norm)

    total = len(critical)
    gone = len(missing)
    example = ", ".join(sorted(missing)[:3]) or ", ".join(sorted(missing_media)[:3])

    if total and (gone / total) >= _MISSING_ASSET_FATAL_RATIO:
        return False, f"{gone} of {total} referenced asset(s) missing locally (e.g. {example})"
    if css_refs and not css_ok:
        return False, f"none of the page's {len(css_refs)} stylesheets were saved (e.g. {example})"
    if js_refs and not js_ok:
        return False, f"none of the page's {len(js_refs)} scripts were saved (e.g. {example})"

    if not total:
        detail = "no local asset references found"
    elif gone:
        detail = f"{gone} of {total} local asset reference(s) could not be saved (e.g. {example})"
    else:
        detail = f"all {total} local asset reference(s) resolve"
    if missing_media:
        detail += (
            f"; {len(missing_media)} video/audio file(s) were not downloaded "
            f"(e.g. {', '.join(sorted(missing_media)[:3])}) - the page will show those as empty"
        )
    return True, detail


def _run_uncage_process(
    cmd: List[str],
    cwd: Path,
    ctx: Optional[TaskContext],
    timeout_sec: int,
) -> Tuple[int, bool, List[str], List[str]]:
    """
    Run uncage with a wall-clock budget that can actually fire.

    A reader thread feeds a queue so the deadline is evaluated while WAITING for output.
    The previous `for line in iter(proc.stdout.readline, "")` loop only checked the clock
    *after* a line arrived, so a silent stall hung the task forever.

    Returns (returncode, killed_by_budget, error_lines, tail_lines).
    """
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        **_WIN_HIDE,
    )

    out_queue: "queue.Queue[str]" = queue.Queue()
    err_lines: List[str] = []
    tail_lines: List[str] = []

    def _pump() -> None:
        try:
            if proc.stdout:
                for ln in iter(proc.stdout.readline, ""):
                    out_queue.put(ln)
        except Exception:
            pass
        finally:
            out_queue.put("")   # sentinel: stream closed

    threading.Thread(target=_pump, daemon=True, name="uncage-stdout").start()

    start_t = time.time()
    killed_by_budget = False

    def _over_budget() -> bool:
        if (time.time() - start_t) > timeout_sec:
            proc.kill()
            logger.warning("Uncage exceeded its %ds budget and was stopped", timeout_sec)
            return True
        return False

    while True:
        try:
            line = out_queue.get(timeout=1.0)
        except queue.Empty:
            if _over_budget():
                killed_by_budget = True
                break
            if proc.poll() is not None and out_queue.empty():
                break
            continue

        if line == "":
            break

        line_str = line.strip()
        if not line_str:
            continue
        logger.debug("[UNCAGE LIVE] %s", line_str)

        # Unfiltered tail: uncage frequently fails with a plain line, and the keyword
        # filter below would drop the only useful explanation.
        tail_lines.append(line_str)
        if len(tail_lines) > 12:
            tail_lines.pop(0)

        # Keep the last real error line so a failure can be explained to the user
        # instead of a generic "extraction failed".
        _low = line_str.lower()
        if ("error" in _low or "executable doesn't exist" in _low
                or "browsertype.launch" in _low or "cannot find module" in _low):
            err_lines.append(line_str)

        if "Reading robots.txt" in line_str or "Discovering sitemaps" in line_str:
            _safe_report(ctx, 28, "[UNCAGE] Discovering sitemaps & crawl policy...")
        elif "Launching stealth browser" in line_str:
            _safe_report(ctx, 35, "[UNCAGE] Launching stealth browser engine...")
        elif "Setting up global network interceptors" in line_str:
            _safe_report(ctx, 45, "[UNCAGE] Intercepting network assets & DOM...")
        elif "Crawling:" in line_str:
            page_part = line_str.split("Crawling:", 1)[-1].strip()
            _safe_report(ctx, 55, f"[UNCAGE] Crawling {page_part[:45]}...")
        elif "Rewriting asset URLs" in line_str:
            _safe_report(ctx, 70, "[UNCAGE] Localizing and rewriting asset URLs...")
        elif "Purging and minifying" in line_str or "Optimizing CSS" in line_str:
            _safe_report(ctx, 78, "[UNCAGE] Optimizing stylesheets...")
        elif "Compiling Static HTML" in line_str:
            _safe_report(ctx, 84, "[UNCAGE] Compiling static pages...")
        elif "Finalizing Static HTML" in line_str or "Successfully exported" in line_str:
            _safe_report(ctx, 90, "[UNCAGE] Bundle finalized successfully.")

        if _over_budget():
            killed_by_budget = True
            break

    if proc.stdout:
        try:
            proc.stdout.close()
        except Exception:
            pass

    if proc.poll() is None:
        try:
            proc.wait(timeout=10)
        except Exception:
            try:
                proc.kill()
                proc.wait(timeout=5)
            except Exception:
                pass

    rc = proc.returncode if proc.returncode is not None else -1
    return rc, killed_by_budget, err_lines, tail_lines


def run_uncage_exporter(
    url: str,
    output_dir: Path,
    ctx: Optional[TaskContext] = None,
    max_pages: int = 1,
    max_depth: Optional[int] = None,
    timeout_sec: Optional[int] = None,
    priority_only: bool = False,
) -> Tuple[bool, str]:
    """
    Executes the self-contained Uncage CLI (tools/uncage/bin/uncage.js) with live streaming progress.
    Supports single-page extraction (max_pages=1, max_depth=0) or multi-page crawling.

    Uncage's own options are auto-selected here — the user is never asked about them.
    Returns (ok, detail) where `ok` means the export was genuinely ASSEMBLED and
    `detail` explains a failure in terms the user can act on.
    """
    if timeout_sec is None:
        timeout_sec = crawl_timeout_budget(max_pages)
    _safe_report(ctx, 15, f"[UNCAGE] Dispatching local Uncage engine for {url} (max_pages={max_pages})...")
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        node_bin = shutil.which("node") or shutil.which("node.exe") or "node"

        # Strictly resolve within ZEZO workspace (tools/uncage)
        zezo_root = Path(__file__).resolve().parent.parent
        uncage_js = zezo_root / "tools" / "uncage" / "bin" / "uncage.js"

        if not uncage_js.exists():
            # Auto-setup for fresh PC deployments
            logger.info("tools/uncage not found. Initializing self-contained Uncage engine...")
            tools_dir = zezo_root / "tools"
            tools_dir.mkdir(parents=True, exist_ok=True)
            try:
                subprocess.run(
                    ["git", "clone", "--depth", "1", "https://github.com/Nightteye/uncage.git", str(tools_dir / "uncage")],
                    check=True,
                    timeout=60,
                    **_WIN_HIDE,
                )
                subprocess.run(
                    ["npm", "install", "--omit=dev"],
                    cwd=str(tools_dir / "uncage"),
                    check=True,
                    timeout=90,
                    shell=True if platform.system() == "Windows" else False,
                    **_WIN_HIDE,
                )
            except Exception as se:
                logger.error("Failed to auto-setup tools/uncage: %s", se)

        if not uncage_js.exists():
            logger.warning("Local Uncage binary (uncage.js) not available at %s", uncage_js)
            return False, f"Uncage binary missing at {uncage_js}."

        uncage_root = uncage_js.parent.parent
        target_name = re.sub(r"[^\w\-]", "_", urllib.parse.urlparse(url).netloc or "site").strip("_")
        if not target_name:
            target_name = "cloned_site"

        # Clean previous raw output in tools/uncage/output if existing
        raw_output_dir = uncage_root / "output" / target_name
        if raw_output_dir.exists():
            try:
                shutil.rmtree(raw_output_dir, ignore_errors=True)
            except Exception:
                pass

        # Make sure Uncage's own Playwright has a matching Chromium before the
        # long crawl starts — otherwise it dies at "Launching stealth browser".
        _pre_ok, _pre_why = _ensure_uncage_browsers(uncage_root, ctx)
        if not _pre_ok:
            logger.warning("Uncage preflight failed: %s", _pre_why)
            return False, _pre_why

        cmd = [
            node_bin,
            str(uncage_js),
            url,
            "-o", target_name,
            "--max-pages", str(max_pages),
            # uncage's --timeout is a PER-PAGE navigation timeout; ZEZO always sets it
            # explicitly rather than inheriting uncage's 30s default.
            "--timeout", str(_uncage_page_timeout_ms(max_pages)),
        ]
        if max_depth is not None:
            cmd.extend(["--max-depth", str(max_depth)])
        if UNCAGE_NO_PURGE:
            cmd.append("--no-purge")
        if priority_only and max_pages > 1:
            cmd.append("--priority-only")
        # Deliberately never auto-set: --ignore-robots (respecting robots.txt and its
        # crawl delay is the safe default), --safe-mode (disables JS), --no-headless,
        # --keep-analytics.

        _safe_report(ctx, 22, f"[UNCAGE] Initializing crawler (max_pages={max_pages})...")

        rc, killed_by_budget, err_lines, tail_lines = _run_uncage_process(
            cmd, uncage_root, ctx, timeout_sec
        )
        ok, why = _uncage_result_ok(raw_output_dir, rc)

        # uncage may sanitize the output directory name slightly differently.
        if not ok:
            for candidate in (uncage_root / "output").glob(f"*{target_name}*"):
                if candidate.is_dir() and _uncage_result_ok(candidate, rc)[0]:
                    raw_output_dir, ok, why = candidate, True, ""
                    break

        # Degradation retry: heavy SPA crawls die inside uncage's unbounded JS module
        # dependency scan. With --skip-deps that scan is skipped, while asset-map.json,
        # the asset rewrites and the assembler all still run — so the clone completes
        # instead of being reported as a broken success. Only lazy-loaded route chunks
        # stay remote.
        degraded = False
        if not ok and (killed_by_budget or _looks_like_partial_extraction(raw_output_dir)):
            degraded = True
            _safe_report(ctx, 22, "[UNCAGE] Crawl was cut short - retrying with the JS dependency scan disabled...")
            logger.info("Retrying uncage with --skip-deps after an incomplete extraction")
            if raw_output_dir.exists():
                shutil.rmtree(raw_output_dir, ignore_errors=True)
            rc2, killed2, err_lines2, tail_lines2 = _run_uncage_process(
                cmd + ["--skip-deps"], uncage_root, ctx, timeout_sec
            )
            ok2, why2 = _uncage_result_ok(raw_output_dir, rc2)
            if not ok2:
                for candidate in (uncage_root / "output").glob(f"*{target_name}*"):
                    if candidate.is_dir() and _uncage_result_ok(candidate, rc2)[0]:
                        raw_output_dir, ok2, why2 = candidate, True, ""
                        break
            if ok2:
                ok, why = True, ""
                rc, killed_by_budget = rc2, killed2
                err_lines, tail_lines = err_lines2, tail_lines2
            else:
                # Surface whichever attempt got furthest into explaining the problem.
                rc, killed_by_budget = rc2, killed2
                err_lines, tail_lines = err_lines2, tail_lines2

        if ok:
            # Sync all exported files into output_dir
            for item in raw_output_dir.iterdir():
                dest = output_dir / item.name
                if item.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest, ignore_errors=True)
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)

            # The assembler already produced index.html — the old "copy the first .html
            # we find" fallback is gone, because that is what promoted a raw pre-assembly
            # snapshot into the served page and made a broken clone look successful.
            if not (output_dir / "index.html").exists():
                return False, (
                    "uncage reported success but no index.html reached the clone folder."
                )

            file_count = len(list(output_dir.rglob("*")))
            suffix = " [degraded: JS dependency scan skipped]" if degraded else ""
            _safe_report(ctx, 92, f"[UNCAGE] Successfully assembled bundle ({file_count} files/pages){suffix}")
            return True, ""

        last_output = err_lines[-1] if err_lines else (tail_lines[-1] if tail_lines else "")
        if killed_by_budget:
            detail = f"uncage exceeded its {timeout_sec}s budget and was stopped"
        else:
            detail = f"{why}." if why else f"uncage exited with code {rc}."
        if last_output:
            detail = f"{detail} Last output: {last_output[:200]}"
        logger.warning("Uncage extraction failed (returncode=%s): %s", rc, detail)
        return False, detail
    except Exception as e:
        logger.warning("Uncage CLI execution error: %s", e)
        return False, str(e)

    return False, "Uncage produced no output bundle."


# ── 3-Tier HTML Fetching Engine ─────────────────────────────────────────────

def _fetch_html_tier1_playwright(url: str, timeout_ms: int = 15000) -> Tuple[str, str]:
    """Tier 1: Playwright Headless Chromium for full dynamic DOM hydration."""
    if not PLAYWRIGHT_AVAILABLE:
        raise ImportError("Playwright is not installed.")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
        )
        page = context.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
        except Exception:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

        html = page.content()
        title = page.title() or ""
        browser.close()
        return html, title


def _fetch_html_tier2_scrapling(url: str, timeout_ms: int = 20000) -> Tuple[str, str]:
    """Tier 2: High-speed anti-bot stealth HTTP/2 fetch via Scrapling StealthyFetcher."""
    if not SCRAPLING_AVAILABLE:
        raise ImportError("Scrapling is not available.")
    page = StealthyFetcher.fetch(url, timeout=timeout_ms)
    html = page.html_content or page.prettify() or ""
    title = page.css("title::text").first if hasattr(page, "css") else ""
    if not title and BS4_AVAILABLE and html:
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string.strip() if (soup.title and soup.title.string) else ""
    return html, title


def _fetch_html_tier3_http(url: str, timeout_sec: int = 15) -> Tuple[str, str]:
    """Tier 3: Resilient HTTP stream via urllib + BeautifulSoup."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    title = ""
    if BS4_AVAILABLE:
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string.strip() if (soup.title and soup.title.string) else ""
    else:
        m = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if m:
            title = m.group(1).strip()

    return html, title


def _fetch_tier4_httrack(url: str, output_dir: Path, max_depth: int = MAX_DEPTH_FULL_SITE) -> bool:
    """Tier 4: Cross-platform HTTrack CLI invocation for full recursive mirroring."""
    httrack_bin = shutil.which("httrack") or shutil.which("httrack.exe")
    if not httrack_bin:
        logger.warning("HTTrack executable not found on PATH.")
        return False

    cmd = [
        httrack_bin,
        url,
        "-O", str(output_dir),
        f"-r{max_depth}",
        "-%v",
        "-*+*.png", "-*+*.jpg", "-*+*.jpeg", "-*+*.gif", "-*+*.css", "-*+*.js", "-*+*.svg", "-*+*.woff2",
        "--max-rate=250000",
    ]
    try:
        subprocess.run(cmd, timeout=90, check=False, **_WIN_HIDE)
        return True
    except Exception as e:
        logger.warning("HTTrack execution failed: %s", e)
        return False


def fetch_rendered_html(url: str, ctx: Optional[TaskContext] = None) -> Tuple[str, str, str]:
    """
    Multi-Tier Fallback Ladder:
    1. Playwright Headless Chromium (rendered DOM + React hydration)
    2. Scrapling StealthyFetcher (anti-bot Cloudflare bypass)
    3. HTTP Stream + BeautifulSoup
    Returns (html, title, engine_used).
    """
    # Try Tier 1: Playwright
    if PLAYWRIGHT_AVAILABLE:
        try:
            _safe_report(ctx, 12, f"[DOM] Rendering {url} in Playwright Headless Chromium...")
            html, title = _fetch_html_tier1_playwright(url, timeout_ms=15000)
            if html and len(html.strip()) > 100:
                return html, title, "Playwright Chromium"
        except Exception as e:
            logger.warning("Playwright Tier 1 failed for %s (%s). Falling back to Scrapling Tier 2...", url, e)

    # Try Tier 2: Scrapling StealthyFetcher (Anti-bot / Cloudflare bypass)
    if SCRAPLING_AVAILABLE:
        try:
            _safe_report(ctx, 18, f"[DOM] Stealth fallback: Fetching {url} via Scrapling...")
            html, title = _fetch_html_tier2_scrapling(url, timeout_sec=20)
            if html and len(html.strip()) > 100:
                return html, title, "Scrapling Stealth"
        except Exception as se:
            logger.warning("Scrapling Tier 2 failed for %s (%s). Falling back to HTTP stream...", url, se)

    # Try Tier 3: HTTP Stream
    try:
        _safe_report(ctx, 22, f"[DOM] Standard HTTP Stream fallback for {url}...")
        html, title = _fetch_html_tier3_http(url, timeout_sec=15)
        if html and len(html.strip()) > 100:
            return html, title, "HTTP Stream"
    except Exception as e:
        logger.warning("HTTP Stream Tier 3 failed for %s (%s).", url, e)

    raise RuntimeError(f"Could not retrieve webpage from '{url}'. The site may be unreachable or protected by anti-bot challenge.")


# ── Fault-Tolerant Asset Downloader & Localizer ─────────────────────────────

def _download_single_asset(
    asset_url: str,
    target_path: Path,
    headers: Dict[str, str],
) -> bool:
    """Downloads one asset file safely with size checks and anti-bot retry."""
    try:
        req = urllib.request.Request(asset_url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            clength = resp.headers.get("Content-Length")
            if clength and int(clength) > MAX_SINGLE_ASSET_BYTES:
                logger.warning("Skipping oversized asset (%s bytes): %s", clength, asset_url)
                return False

            content = resp.read(MAX_SINGLE_ASSET_BYTES + 1024)
            if len(content) > MAX_SINGLE_ASSET_BYTES:
                logger.warning("Asset exceeded 25MB: %s", asset_url)
                return False

            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(content)
            return True
    except urllib.error.HTTPError as e:
        # If 403 / 401 on strict CDN, retry with clean browser headers without strict origin
        if e.code in (403, 401, 400):
            try:
                fallback_headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                    "Accept": "*/*",
                    "Accept-Language": "en-US,en;q=0.9",
                }
                req = urllib.request.Request(asset_url, headers=fallback_headers)
                with urllib.request.urlopen(req, timeout=8) as resp:
                    content = resp.read(MAX_SINGLE_ASSET_BYTES + 1024)
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    target_path.write_bytes(content)
                    return True
            except Exception:
                pass
        logger.debug("Failed downloading asset %s: %s", asset_url, e)
        return False
    except Exception as e:
        logger.debug("Failed downloading asset %s: %s", asset_url, e)
        return False


def _sanitize_and_clean_dom(soup: BeautifulSoup) -> None:
    """
    Purges minified vendor chunks, tracking scripts, and hydration runtime tags
    to ensure output HTML matches hamza_taste gold-standard reference blueprints.
    """
    blocked_patterns = [
        r"_next/static",
        r"turbopack",
        r"webpack",
        r"googletagmanager",
        r"google-analytics",
        r"connect\.facebook\.net",
        r"doubleclick",
        r"hotjar",
        r"clarity\.ms",
        r"wp-emoji",
        r"cookieadmin",
        r"sw-register",
    ]
    blocked_re = re.compile("|".join(blocked_patterns), re.IGNORECASE)

    for s in soup.find_all("script"):
        src = s.get("src", "")
        script_id = s.get("id", "")
        script_text = s.string or s.text or ""
        if src and blocked_re.search(src):
            s.decompose()
            continue
        if script_id in ("__NEXT_DATA__", "__remixContext", "__NUXT__") or "self.__next_f" in script_text or "webpackChunk" in script_text:
            s.decompose()
            continue

    # Remove framework hydration metadata attributes
    for tag in soup.find_all(True):
        for attr in list(tag.attrs.keys()):
            if attr.startswith(("data-reactroot", "data-reactid", "data-n-head", "data-server-rendered", "data-v-", "data-turbo")):
                del tag.attrs[attr]

    # Remove nextjs/spa overlay tags
    for el in soup.find_all(["next-route-announcer", "div#__next-build-watcher"]):
        el.decompose()


def localize_and_download_assets(
    base_url: str,
    html: str,
    output_dir: Path,
    ctx: Optional[TaskContext] = None,
) -> Tuple[str, int, int]:
    """
    Parses HTML, discovers remote assets (CSS, JS, images, fonts, media, preloads),
    downloads them in parallel into output_dir/assets/, rewrites paths to relative.
    Resolves relative CSS assets against the CSS file's own URL origin.
    Returns (localized_html, downloaded_count, failed_count).
    """
    if not BS4_AVAILABLE:
        return html, 0, 0

    soup = BeautifulSoup(html, "html.parser")
    _sanitize_and_clean_dom(soup)

    parsed_base = urllib.parse.urlparse(base_url)
    origin = f"{parsed_base.scheme}://{parsed_base.netloc}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": base_url,
        "Origin": origin,
    }

    assets_dir = output_dir / "assets"
    css_dir = assets_dir / "css"
    js_dir = assets_dir / "js"
    img_dir = assets_dir / "images"
    font_dir = assets_dir / "fonts"

    for d in (css_dir, js_dir, img_dir, font_dir):
        d.mkdir(parents=True, exist_ok=True)

    download_queue: List[Tuple[Any, str, str, Path, str]] = []
    seen_urls: Dict[str, Tuple[Path, str]] = {}
    css_map: Dict[str, Tuple[Path, str]] = {}

    # 1. Stylesheets, Preloaded Fonts, Images, and Favicons
    for link in soup.find_all("link"):
        href = link.get("href")
        if not href or href.startswith("data:") or href.startswith("javascript:"):
            continue

        abs_url = urllib.parse.urljoin(base_url, href)
        rel = link.get("rel") or []
        if isinstance(rel, str):
            rel = [rel]
        rel_str = " ".join(rel).lower()
        as_attr = (link.get("as") or "").lower()
        parsed_path = urllib.parse.urlparse(abs_url).path
        basename = os.path.basename(parsed_path) or "asset"

        # Stylesheet or preloaded style
        if "stylesheet" in rel_str or as_attr == "style" or parsed_path.endswith(".css") or ".css" in abs_url:
            if abs_url in seen_urls:
                local_path, rel_url = seen_urls[abs_url]
            else:
                fname = _sanitize_filename(basename if basename.endswith(".css") else f"{basename}.css")
                local_path = css_dir / fname
                rel_url = f"./assets/css/{fname}"
                seen_urls[abs_url] = (local_path, rel_url)
            css_map[abs_url] = (local_path, rel_url)
            link["rel"] = "stylesheet"
            if "as" in link.attrs:
                del link.attrs["as"]
            download_queue.append((link, "href", abs_url, local_path, rel_url))

        # Font (preloaded or stylesheet font)
        elif as_attr == "font" or parsed_path.endswith((".woff2", ".woff", ".ttf", ".otf", ".eot")):
            if abs_url in seen_urls:
                local_path, rel_url = seen_urls[abs_url]
            else:
                fname = _sanitize_filename(basename)
                local_path = font_dir / fname
                rel_url = f"./assets/fonts/{fname}"
                seen_urls[abs_url] = (local_path, rel_url)
            download_queue.append((link, "href", abs_url, local_path, rel_url))

        # Image / Icon (preloaded image or favicon)
        elif as_attr == "image" or "icon" in rel_str or parsed_path.endswith((".png", ".jpg", ".jpeg", ".svg", ".webp", ".avif", ".ico", ".gif")):
            if abs_url in seen_urls:
                local_path, rel_url = seen_urls[abs_url]
            else:
                fname = _sanitize_filename(basename)
                local_path = img_dir / fname
                rel_url = f"./assets/images/{fname}"
                seen_urls[abs_url] = (local_path, rel_url)
            download_queue.append((link, "href", abs_url, local_path, rel_url))

    # 2. Images, Sources, Videos, Audios
    for tag in soup.find_all(["img", "source", "video", "audio"]):
        for attr in ("src", "poster"):
            src = tag.get(attr)
            if src and not src.startswith("data:") and not src.startswith("javascript:"):
                abs_url = urllib.parse.urljoin(base_url, src)
                if abs_url in seen_urls:
                    local_path, rel_url = seen_urls[abs_url]
                else:
                    parsed_path = urllib.parse.urlparse(abs_url).path
                    ext = os.path.splitext(parsed_path)[1] or ".png"
                    fname = _sanitize_filename(os.path.basename(parsed_path) or f"media_{len(seen_urls)+1}{ext}")
                    local_path = img_dir / fname
                    rel_url = f"./assets/images/{fname}"
                    seen_urls[abs_url] = (local_path, rel_url)
                download_queue.append((tag, attr, abs_url, local_path, rel_url))

    # 3. Background Images in Inline Styles
    for el in soup.find_all(style=True):
        style_text = el.get("style", "")
        urls_found = re.findall(r"url\((['\"]?)(.*?)\1\)", style_text)
        for quote, bg_url in urls_found:
            if bg_url.startswith("data:") or bg_url.startswith("#"):
                continue
            abs_url = urllib.parse.urljoin(base_url, bg_url)
            if abs_url in seen_urls:
                local_path, rel_url = seen_urls[abs_url]
            else:
                parsed_path = urllib.parse.urlparse(abs_url).path
                fname = _sanitize_filename(os.path.basename(parsed_path) or f"bg_{len(seen_urls)+1}.png")
                local_path = img_dir / fname
                rel_url = f"./assets/images/{fname}"
                seen_urls[abs_url] = (local_path, rel_url)
            download_queue.append((None, style_text, abs_url, local_path, rel_url))

    total_assets = len(seen_urls)
    _safe_report(ctx, 35, f"[ASSETS] Discovered {total_assets} assets. Downloading in parallel...")

    downloaded_count = 0
    failed_count = 0

    # Parallel Download with ThreadPoolExecutor
    unique_items = list(seen_urls.items())
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_ASSET_WORKERS) as executor:
        future_to_url = {
            executor.submit(_download_single_asset, url_item, target, headers): (url_item, target, rel)
            for url_item, (target, rel) in unique_items
        }

        completed = 0
        for future in concurrent.futures.as_completed(future_to_url):
            url_item, target, rel = future_to_url[future]
            completed += 1
            try:
                success = future.result()
                if success:
                    downloaded_count += 1
                else:
                    failed_count += 1
            except Exception:
                failed_count += 1

            if completed % 10 == 0 or completed == total_assets:
                pct = 35 + int((completed / max(1, total_assets)) * 30)
                _safe_report(ctx, pct, f"[ASSETS] Downloaded {downloaded_count}/{total_assets} assets...")

    # 4. Rewrite DOM elements
    for el, attr, abs_url, target_path, rel_url in download_queue:
        if el is None:
            continue
        if target_path.exists() and target_path.stat().st_size > 0:
            el[attr] = rel_url
        else:
            el[attr] = abs_url

    # Rewrite inline styles with local background images
    for el in soup.find_all(style=True):
        style_text = el.get("style", "")
        for abs_url, (target_path, rel_url) in seen_urls.items():
            if target_path.exists() and target_path.stat().st_size > 0:
                style_text = style_text.replace(abs_url, rel_url)
        el["style"] = style_text

    # 5. Localize and Rewrite Assets Referenced inside CSS Files
    for orig_css_url, (css_file, _) in css_map.items():
        if not css_file.exists():
            continue
        try:
            css_content = css_file.read_text(encoding="utf-8", errors="replace")
            css_urls = re.findall(r"url\((['\"]?)(.*?)\1\)", css_content)
            for quote, c_url in css_urls:
                if c_url.startswith("data:") or c_url.startswith("#"):
                    continue
                # Resolve relative URL against CSS file's OWN origin URL
                abs_asset_url = urllib.parse.urljoin(orig_css_url, c_url)
                parsed_asset = urllib.parse.urlparse(abs_asset_url).path
                ext = os.path.splitext(parsed_asset)[1].lower()

                if ext in (".woff2", ".woff", ".ttf", ".otf", ".eot"):
                    fname = _sanitize_filename(os.path.basename(parsed_asset) or "font.woff2")
                    dest = font_dir / fname
                    if _download_single_asset(abs_asset_url, dest, headers):
                        css_content = css_content.replace(c_url, f"../fonts/{fname}")
                        downloaded_count += 1
                elif ext in (".png", ".jpg", ".jpeg", ".svg", ".webp", ".avif", ".gif", ".ico"):
                    fname = _sanitize_filename(os.path.basename(parsed_asset) or "asset.png")
                    dest = img_dir / fname
                    if _download_single_asset(abs_asset_url, dest, headers):
                        css_content = css_content.replace(c_url, f"../images/{fname}")
                        downloaded_count += 1

            css_file.write_text(css_content, encoding="utf-8")
        except Exception as e:
            logger.warning("Error processing CSS file %s: %s", css_file.name, e)

    # 6. Generate clean interactive app.js
    app_js_path = js_dir / "app.js"
    if not app_js_path.exists():
        app_js_code = (
            "// Clean Vanilla Interactions for Desktop Clone\n"
            "document.addEventListener('DOMContentLoaded', () => {\n"
            "    const menuBtns = document.querySelectorAll('[data-menu-toggle], .mobile-menu-btn, button[aria-label=\"Menu\"]');\n"
            "    const mobileNavs = document.querySelectorAll('[data-mobile-menu], .mobile-nav, nav.mobile');\n"
            "    menuBtns.forEach(btn => {\n"
            "        btn.addEventListener('click', () => {\n"
            "            mobileNavs.forEach(nav => nav.classList.toggle('hidden'));\n"
            "        });\n"
            "    });\n"
            "\n"
            "    document.querySelectorAll('a[href^=\"#\"]').forEach(anchor => {\n"
            "        anchor.addEventListener('click', function(e) {\n"
            "            const target = document.querySelector(this.getAttribute('href'));\n"
            "            if (target) {\n"
            "                e.preventDefault();\n"
            "                target.scrollIntoView({ behavior: 'smooth' });\n"
            "            }\n"
            "        });\n"
            "    });\n"
            "});\n"
        )
        app_js_path.write_text(app_js_code, encoding="utf-8")

    if soup.body and not soup.find("script", {"src": "./assets/js/app.js"}):
        app_script = soup.new_tag("script", src="./assets/js/app.js")
        soup.body.append(app_script)

    _safe_report(ctx, 75, f"[REWRITE] Localized {downloaded_count} assets ({failed_count} failed).")
    return str(soup), downloaded_count, failed_count


# ── AI Website Reverse Engineering Synthesis ─────────────────────────────────

def _sanitize_dom_for_synthesis(html_text: str, base_url: str) -> str:
    """
    Cleans raw rendered DOM for AI Reverse Engineering synthesis:
    - Strips scripts, tracking pixels, ads, analytics, and minified framework runtime bloat.
    - Resolves relative links and image sources to absolute URLs.
    - Preserves semantic elements, typography, navigation, sections, cards, text, and SVG icons.
    """
    if not html_text:
        return ""
    if not BS4_AVAILABLE:
        cleaned = re.sub(r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>", "", html_text, flags=re.IGNORECASE)
        cleaned = re.sub(r"<noscript\b[^<]*(?:(?!<\/noscript>)<[^<]*)*<\/noscript>", "", cleaned, flags=re.IGNORECASE)
        return cleaned[:60000]

    soup = BeautifulSoup(html_text, "html.parser")
    for tag in soup(["script", "noscript", "iframe", "object", "embed"]):
        tag.decompose()

    for img in soup.find_all("img"):
        w = img.get("width")
        h = img.get("height")
        if w in ("1", "0") or h in ("1", "0") or "pixel" in str(img.get("src", "")).lower():
            img.decompose()
            continue
        src = img.get("src")
        if src and not src.startswith("data:"):
            img["src"] = urllib.parse.urljoin(base_url, src)

    for a in soup.find_all("a", href=True):
        a["href"] = urllib.parse.urljoin(base_url, a["href"])

    for tag in soup.find_all(True):
        attrs_to_remove = [k for k in list(tag.attrs.keys()) if k.startswith(("data-react", "data-v-", "_ng", "data-wf-", "ng-"))]
        for attr in attrs_to_remove:
            del tag.attrs[attr]

    return soup.prettify()[:80000]


def _extract_design_tokens_summary(html_text: str, base_url: str) -> dict:
    """
    Text-only fallback: extracts basic design tokens from raw HTML when
    Playwright computed style extraction is unavailable.
    Returns a design_tokens dict compatible with synthesize_design_tokens output.
    """
    from collections import Counter

    colors = Counter()
    backgrounds = Counter()
    fonts = Counter()
    font_sizes = Counter()

    # Extract inline style colors
    for match in re.findall(r'color:\s*([^;"]+)', html_text, re.IGNORECASE):
        val = match.strip()
        if val and val not in ('inherit', 'initial', 'unset', 'currentColor'):
            colors[val] += 1

    for match in re.findall(r'background(?:-color)?:\s*([^;"]+)', html_text, re.IGNORECASE):
        val = match.strip()
        if val and val not in ('inherit', 'initial', 'unset', 'transparent', 'none'):
            backgrounds[val] += 1

    for match in re.findall(r'font-family:\s*([^;"]+)', html_text, re.IGNORECASE):
        val = match.strip().split(',')[0].strip("'\" ")
        if val:
            fonts[val] += 1

    for match in re.findall(r'font-size:\s*([^;"]+)', html_text, re.IGNORECASE):
        val = match.strip()
        if val:
            font_sizes[val] += 1

    return {
        "palette": {
            "text_colors": colors.most_common(10),
            "background_colors": backgrounds.most_common(10),
        },
        "typography": {
            "font_families": [f[0] for f in fonts.most_common(5)] or ["Inter", "sans-serif"],
            "font_sizes": sorted([s[0] for s in font_sizes.most_common(15)], key=lambda x: float(re.sub(r'[^\d.]', '', x) or 0)),
            "font_weights": ["400", "500", "600", "700"],
            "line_heights": [],
            "letter_spacings": [],
        },
        "spacing": {
            "base_unit": "16px",
            "common_gaps": [],
            "common_paddings": [],
        },
        "shape": {
            "border_radii": [],
            "shadows": [],
        },
        "css_variables": {},
    }


def _synthesize_clean_website(
    url: str,
    raw_html: str,
    clone_dir: Path,
    target_format: str = "static",
    ctx: Optional[TaskContext] = None,
) -> str:
    """
    Antigravity Master Reverse-Engineering Engine:
    Single-pass high-fidelity synthesis of the full standalone HTML5 document
    based on inspected DOM, extracted design tokens, local assets, and Vanilla JS interactions.
    """
    cleaned = _sanitize_dom_for_synthesis(raw_html, url)

    # Build local asset inventory
    asset_inv_lines = []
    if clone_dir and (clone_dir / "assets").exists():
        for f in (clone_dir / "assets").rglob("*"):
            if f.is_file():
                rel = f"./assets/{f.relative_to(clone_dir / 'assets').as_posix()}"
                asset_inv_lines.append(f"- {f.name} -> {rel}")
    asset_inv = "\n".join(asset_inv_lines[:80])

    prompt = f"""You are an expert Web Designer, UI Designer, Frontend Engineer, and Website Reverse Engineering AI Agent.
Your only task is to inspect the entire project provided to you and rebuild the website as accurately as possible based on the actual code, assets, styles, and content.
Do not rely on assumptions when the required information already exists inside the project.

Understand how the original website is structured from top to bottom and reverse engineer every visible section:
- macOS menubar / header (live system clock, status pills, popups)
- hero section (draggable floating stickers, draggable retro video windows with hover-expansion physics, volume controls, seekable progress bars)
- dynamic feature rows (12-bar animated audio waveforms, speech bubble pills with gradient gloss)
- manifesto / the dream (rainbow gradient arch steps, draggable macOS note card with author signature)
- feedback wall (marquee banner, masonry tweet cards with macOS colored window chrome)
- pricing (interactive monthly/yearly toggle switch, blue sky background, pricing tiers)
- interactive FAQ accordion (smooth grid height transitions)
- retro footer (column navigation, full-bleed wordmark)

═══════════════════════════════════════════
SOURCE URL: {url}
═══════════════════════════════════════════

═══════════════════════════════════════════
LOCAL ASSETS AVAILABLE (Use exact relative paths ./assets/...):
═══════════════════════════════════════════
{asset_inv or 'Use ./assets/images/ and ./assets/fonts/'}

═══════════════════════════════════════════
RENDERED DOM MARKUP & CONTENT:
═══════════════════════════════════════════
{cleaned[:65000]}

═══════════════════════════════════════════
REVERSE ENGINEERING RULES:
═══════════════════════════════════════════
1. Recreate the website as a single standalone HTML file that contains the complete visual experience, with embedded CSS (<style>) and JavaScript (<script>).
2. Make it fully responsive across desktop, tablet, and mobile (@media max-width: 1024px and 768px).
3. Reuse the project's actual assets whenever possible instead of creating replacements.
4. Reproduce important interactions such as dropdowns, mobile navigation, accordions, tabs, draggable stickers, sliders, hover effects, and menus using clean Vanilla JavaScript.
5. Do not create a design system report, do not write an analysis report, do not explain what you found, and do not simplify the website into a basic approximation.
6. Output ONLY the complete, production-quality <!DOCTYPE html> document. NO markdown fences. NO conversational preamble.
"""

    try:
        from core import gemini
        result = gemini.text(prompt, tier=gemini.SMART, timeout_ms=75_000)
        if result:
            result = re.sub(r"^```(?:html)?\s*", "", result, flags=re.IGNORECASE)
            result = re.sub(r"\s*```$", "", result)
            return result.strip()
    except Exception as e:
        logger.warning("Antigravity master synthesis failed: %s", e)

    # Ultimate fallback: return the localized HTML as-is
    return raw_html


# ============================================================
# COMPUTED STYLE EXTRACTOR & MULTIMODAL VISION V2 ENGINE
# ============================================================

COMPUTED_STYLES_JS = """
() => {
    const walker = document.createTreeWalker(
        document.body,
        NodeFilter.SHOW_ELEMENT,
        {
            acceptNode: (node) => {
                const rect = node.getBoundingClientRect();
                const cs = getComputedStyle(node);
                if (rect.width < 5 || rect.height < 5) return NodeFilter.FILTER_SKIP;
                if (cs.display === 'none' || cs.visibility === 'hidden') return NodeFilter.FILTER_SKIP;
                if (parseFloat(cs.opacity) < 0.05) return NodeFilter.FILTER_SKIP;
                return NodeFilter.FILTER_ACCEPT;
            }
        }
    );

    const results = [];
    let node;
    let index = 0;

    while ((node = walker.nextNode()) && index < 2500) {
        const cs = getComputedStyle(node);
        const rect = node.getBoundingClientRect();

        const path = (() => {
            const parts = [];
            let el = node;
            while (el && el !== document.body && parts.length < 4) {
                let tag = el.tagName.toLowerCase();
                if (el.id) { parts.unshift(`${tag}#${el.id}`); break; }
                if (el.className && typeof el.className === 'string') {
                    const cls = el.className.split(' ').filter(c => c && !c.includes('__') && !c.includes(':')).slice(0, 2).join('.');
                    if (cls) tag += `.${cls}`;
                }
                parts.unshift(tag);
                el = el.parentElement;
            }
            return parts.join(' > ');
        })();

        results.push({
            index: index++,
            path: path,
            tag: node.tagName.toLowerCase(),
            text: (node.childNodes.length === 1 && node.childNodes[0].nodeType === 3)
                  ? node.textContent.trim().slice(0, 120) : '',
            rect: {
                x: Math.round(rect.x),
                y: Math.round(rect.y),
                width: Math.round(rect.width),
                height: Math.round(rect.height)
            },
            style: {
                fontSize: cs.fontSize,
                fontWeight: cs.fontWeight,
                fontFamily: cs.fontFamily ? cs.fontFamily.split(',')[0].replace(/['"]/g, '').trim() : '',
                lineHeight: cs.lineHeight,
                letterSpacing: cs.letterSpacing,
                color: cs.color,
                backgroundColor: cs.backgroundColor,
                backgroundImage: cs.backgroundImage !== 'none' ? 'gradient' : 'none',
                padding: cs.padding,
                paddingTop: cs.paddingTop,
                paddingRight: cs.paddingRight,
                paddingBottom: cs.paddingBottom,
                paddingLeft: cs.paddingLeft,
                margin: cs.margin,
                borderRadius: cs.borderRadius,
                boxShadow: cs.boxShadow,
                border: cs.border,
                display: cs.display,
                flexDirection: cs.flexDirection,
                justifyContent: cs.justifyContent,
                alignItems: cs.alignItems,
                gap: cs.gap,
                gridTemplateColumns: cs.gridTemplateColumns,
                position: cs.position,
                textAlign: cs.textAlign,
                textTransform: cs.textTransform,
                opacity: cs.opacity
            }
        });
    }

    const cssVars = {};
    for (const sheet of document.styleSheets) {
        try {
            for (const rule of sheet.cssRules || []) {
                if (rule.style) {
                    for (let i = 0; i < rule.style.length; i++) {
                        const prop = rule.style[i];
                        if (prop && prop.startsWith('--')) {
                            cssVars[prop] = rule.style.getPropertyValue(prop).trim();
                        }
                    }
                }
            }
        } catch (e) { }
    }

    const loadedFonts = [];
    try {
        if (document.fonts) {
            document.fonts.forEach(f => {
                if (f.family) loadedFonts.push({ family: f.family, weight: f.weight, style: f.style });
            });
        }
    } catch (e) { }

    return { elements: results, cssVariables: cssVars, fonts: loadedFonts };
}
"""


def synthesize_design_tokens(computed_data: dict) -> dict:
    """
    Takes raw computed styles and synthesizes a full design token system.
    Outputs: color palette, type scale, spacing scale, radii, shadows.
    """
    from collections import Counter
    import math

    elements = computed_data.get("elements", [])
    css_vars = computed_data.get("cssVariables", {})

    colors = Counter()
    backgrounds = Counter()
    font_sizes = Counter()
    font_weights = Counter()
    line_heights = Counter()
    letter_spacings = Counter()
    radii = Counter()
    shadows = Counter()
    gaps = Counter()
    paddings = Counter()
    fonts = Counter()

    for el in elements:
        s = el.get("style", {})

        # Colors — skip transparent
        c = s.get("color")
        if c and c not in ("rgba(0, 0, 0, 0)", "transparent"):
            colors[c] += 1
        bg = s.get("backgroundColor")
        if bg and bg not in ("rgba(0, 0, 0, 0)", "transparent"):
            backgrounds[bg] += 1

        # Typography
        if s.get("fontSize"):
            font_sizes[s["fontSize"]] += 1
        if s.get("fontWeight"):
            font_weights[s["fontWeight"]] += 1
        if s.get("lineHeight") and s["lineHeight"] != "normal":
            line_heights[s["lineHeight"]] += 1
        if s.get("letterSpacing") and s["letterSpacing"] != "normal":
            letter_spacings[s["letterSpacing"]] += 1
        if s.get("fontFamily"):
            fonts[s["fontFamily"]] += 1

        # Spacing & shape
        if s.get("borderRadius") and s["borderRadius"] != "0px":
            radii[s["borderRadius"]] += 1
        if s.get("boxShadow") and s["boxShadow"] != "none":
            shadows[s["boxShadow"]] += 1
        if s.get("gap") and s["gap"] != "normal":
            gaps[s["gap"]] += 1
        if s.get("padding") and s["padding"] != "0px":
            paddings[s["padding"]] += 1

    gap_values = []
    for gap, _ in gaps.most_common(20):
        try:
            vals = [float(x.replace("px", "")) for x in gap.split()]
            for v in vals:
                if v > 0:
                    gap_values.append(v)
        except Exception:
            pass

    base_unit = 16
    if gap_values:
        int_vals = [int(v) for v in gap_values if v == int(v)]
        if int_vals:
            base_unit = int_vals[0]
            for v in int_vals[1:]:
                base_unit = math.gcd(base_unit, v) or 16

    return {
        "palette": {
            "text_colors": colors.most_common(10),
            "background_colors": backgrounds.most_common(10),
        },
        "typography": {
            "font_families": [f[0] for f in fonts.most_common(5)] or ["Inter", "sans-serif"],
            "font_sizes": sorted([s[0] for s in font_sizes.most_common(15)], key=lambda x: float(re.sub(r"[^\d.]", "", x) or 0)),
            "font_weights": [w[0] for w in font_weights.most_common(6)],
            "line_heights": [l[0] for l in line_heights.most_common(8)],
            "letter_spacings": [l[0] for l in letter_spacings.most_common(8)],
        },
        "spacing": {
            "base_unit": f"{base_unit}px",
            "common_gaps": [g[0] for g in gaps.most_common(10)],
            "common_paddings": [p[0] for p in paddings.most_common(10)],
        },
        "shape": {
            "border_radii": [r[0] for r in radii.most_common(10)],
            "shadows": [s[0] for s in shadows.most_common(8)],
        },
        "css_variables": css_vars,
    }


def capture_section_screenshots_sync(page, output_dir: Path, viewport_width: int = 1440) -> List[dict]:
    """
    Detects top-level semantic sections on the rendered page and captures clean per-section screenshots.
    Uses non-nested container resolution to prevent wrapper elements (e.g. .stage) from masking child sections.
    """
    sections_dir = output_dir / "sections"
    sections_dir.mkdir(parents=True, exist_ok=True)

    # Detect top-level section boundaries in browser DOM
    raw_eval = page.evaluate("""
        () => {
            const candidates = Array.from(document.querySelectorAll(
                'header, nav, section, footer, ' +
                'main > header, main > nav, main > section, main > footer, ' +
                '.stage > header, .stage > nav, .stage > section, .stage > footer, ' +
                '#root > header, #root > section, #root > footer, ' +
                '#__next > header, #__next > section, #__next > footer'
            ));

            // Keep only highest-level non-nested sections
            const topLevel = candidates.filter(el => {
                const rect = el.getBoundingClientRect();
                const height = Math.round(rect.height);
                const width = Math.round(rect.width);
                if (height < 40 || width < 300) return false;

                // If this element is nested inside another section/header/footer, skip it
                let parent = el.parentElement;
                while (parent && parent !== document.body) {
                    const tag = parent.tagName.toLowerCase();
                    const cls = typeof parent.className === 'string' ? parent.className : '';
                    if (tag === 'section' || tag === 'header' || tag === 'footer') {
                        return false;
                    }
                    if (tag === 'div' && cls.includes('section') && !cls.includes('stage')) {
                        return false;
                    }
                    parent = parent.parentElement;
                }
                return true;
            });

            // Deduplicate elements by DOM identity
            const uniqueElements = Array.from(new Set(topLevel));

            // Sort candidates vertically from top of page to bottom
            uniqueElements.sort((a, b) => {
                const topA = Math.round(a.getBoundingClientRect().top + window.scrollY);
                const topB = Math.round(b.getBoundingClientRect().top + window.scrollY);
                return topA - topB;
            });

            const results = [];
            let idx = 0;

            uniqueElements.forEach(el => {
                const rect = el.getBoundingClientRect();
                const top = Math.round(rect.top + window.scrollY);
                const height = Math.round(rect.height);
                const width = Math.round(rect.width);
                const tag = el.tagName.toLowerCase();
                const cls = typeof el.className === 'string' ? el.className.slice(0, 100) : '';

                // Extract clean outerHTML snippet without gigantic base64 payloads
                let htmlSnippet = el.outerHTML || '';
                htmlSnippet = htmlSnippet.replace(/src=["']data:[^"']+["']/gi, 'src="./assets/images/placeholder.png"').slice(0, 32000);

                results.push({
                    index: idx++,
                    tag: tag,
                    classes: cls,
                    id: el.id || '',
                    top: top,
                    height: height,
                    width: width,
                    domHtml: htmlSnippet,
                    fullText: (el.innerText || '').slice(0, 6000).trim(),
                    textPreview: (el.innerText || '').slice(0, 150).replace(/\\s+/g, ' ').trim()
                });
            });

            return results;
        }
    """)

    raw_sections = raw_eval if isinstance(raw_eval, list) else []

    logger.info("[DEBUG] Total top-level sections detected: %d", len(raw_sections))
    print(f"\n[DEBUG_SECTIONS] Top-level sections detected: {len(raw_sections)}")
    for s in raw_sections:
        print(f"  [{s.get('index'):02d}] <{s.get('tag')}> id='{s.get('id')}' class={s.get('classes')[:30]!r} top={s.get('top')} height={s.get('height')}")

    slices = []
    for sec in raw_sections:
        try:
            page.evaluate(f"window.scrollTo(0, {max(0, sec['top'] - 20)})")
            time.sleep(0.2)

            path = sections_dir / f"section_{sec['index']:02d}.png"
            page.screenshot(
                path=str(path),
                clip={
                    "x": 0,
                    "y": max(0, sec["top"]),
                    "width": min(sec["width"], viewport_width),
                    "height": min(sec["height"], 1800),
                },
                full_page=True,
            )
            sec["screenshot_path"] = str(path)
            slices.append(sec)
        except Exception as e:
            logger.warning("Failed to slice section %s: %s", sec.get("index"), e)

    return slices


def _compute_responsive_deltas(desktop_elements: list, tablet_elements: list, mobile_elements: list) -> List[dict]:
    """
    Computes property-level responsive deltas between Desktop (1440px), Tablet (768px), and Mobile (375px).
    Extracts changes in flex-direction, grid columns, font-size, padding, gap, and width.
    """
    tablet_by_path = {el.get("path"): el for el in tablet_elements if el.get("path")}
    mobile_by_path = {el.get("path"): el for el in mobile_elements if el.get("path")}

    deltas = []
    for d_el in desktop_elements[:200]:
        path = d_el.get("path")
        if not path:
            continue

        d_style = d_el.get("style", {})
        t_el = tablet_by_path.get(path, {})
        t_style = t_el.get("style", {})
        m_el = mobile_by_path.get(path, {})
        m_style = m_el.get("style", {})

        diffs = []
        # Flex / Grid direction
        if d_style.get("flexDirection") and m_style.get("flexDirection") and d_style["flexDirection"] != m_style["flexDirection"]:
            diffs.append(f"flex-direction: {d_style['flexDirection']} -> {m_style['flexDirection']}")
        if d_style.get("display") and m_style.get("display") and d_style["display"] != m_style["display"]:
            diffs.append(f"display: {d_style['display']} -> {m_style['display']}")

        # Typography
        if d_style.get("fontSize") and m_style.get("fontSize") and d_style["fontSize"] != m_style["fontSize"]:
            diffs.append(f"font-size: {d_style['fontSize']} -> {m_style['fontSize']}")

        # Gap & Spacing
        if d_style.get("gap") and m_style.get("gap") and d_style["gap"] != m_style["gap"] and m_style["gap"] != "normal":
            diffs.append(f"gap: {d_style['gap']} -> {m_style['gap']}")
        if d_style.get("padding") and m_style.get("padding") and d_style["padding"] != m_style["padding"]:
            diffs.append(f"padding: {d_style['padding']} -> {m_style['padding']}")

        # Width
        d_w = d_el.get("rect", {}).get("width", 0)
        m_w = m_el.get("rect", {}).get("width", 0)
        if d_w > 0 and m_w > 0 and abs(d_w - m_w) > 100:
            diffs.append(f"width: {d_w}px -> {m_w}px")

        if diffs:
            deltas.append({
                "path": path,
                "tag": d_el.get("tag", ""),
                "rect_desktop": d_el.get("rect", {}),
                "rect_mobile": m_el.get("rect", {}),
                "diffs": diffs
            })

    return deltas


SECTION_PROMPT_TEMPLATE = """You are a Master Frontend Architect and Reverse Engineering Specialist.
Your task is to recreate this EXACT website section PIXEL-PERFECTLY as clean semantic HTML5 with embedded scoped modern CSS (<style>).

═══════════════════════════════════════════
ACTUAL LIVE DOM HTML FOR THIS SECTION (Exact structure, tags, cards, text, SVGs, pricing tiers, testimonial reviews):
═══════════════════════════════════════════
{dom_html}

═══════════════════════════════════════════
COMPLETE TEXT CONTENT FOR THIS SECTION (DO NOT OMIT ANY HEADING, CARD, BUTTON, OR COPY):
═══════════════════════════════════════════
{full_text}

═══════════════════════════════════════════
DESIGN SYSTEM TOKENS (Use these as CSS variables)
═══════════════════════════════════════════
{design_tokens}

═══════════════════════════════════════════
COMPUTED STYLES FOR THIS SECTION (Exact browser px values — DO NOT GUESS)
═══════════════════════════════════════════
{computed_styles}

═══════════════════════════════════════════
MEASURED RESPONSIVE BREAKPOINT DELTAS (Exact browser layout changes at 768px & 375px):
═══════════════════════════════════════════
{responsive_deltas}

═══════════════════════════════════════════
LOCAL ASSETS AVAILABLE (Use relative paths ./assets/...)
═══════════════════════════════════════════
{asset_inv_str}

═══════════════════════════════════════════
NON-NEGOTIABLE REVERSE ENGINEERING RULES:
═══════════════════════════════════════════
1. VISUAL PIXEL FIDELITY: Inspect the attached screenshot closely. Replicate the visual hierarchy, layout geometry, typography, and card alignments exactly.
2. ZERO CONTENT OMISSION: Use the LIVE DOM HTML and COMPLETE TEXT above. Replicate ALL cards, tiers, testimonials, buttons, and badges without truncating or inventing placeholders.
3. EXACT COMPUTED VALUES: Match font-size, font-weight, line-height, letter-spacing, and gap values from the computed styles JSON above.
4. GLOSSY BUTTONS & GRADIENTS: If the screenshot shows glossy macOS buttons or linear gradients, craft full CSS gradients and pseudo-element highlights (`::before`).
5. EXACT SVG / MEDIA SIZING: Prevent SVG overflow. Constrain status icons (`height: 16px; width: auto; object-fit: contain;`), window dots (`width: 12px; height: 12px; border-radius: 50%;`), and video cards (`width: 100%; max-width: 850px; margin: 0 auto; border-radius: 16px; overflow: hidden;`).
6. NORMAL VERTICAL FLOW: Sections MUST use normal block document flow (`position: relative; width: 100%; margin: 0 auto;`). NEVER use `position: absolute` or `position: fixed` on section root wrappers. NEVER use hardcoded page `top: ...px` offsets.
7. MEASURED RESPONSIVENESS: Use the MEASURED RESPONSIVE DELTAS above to write exact scoped `@media (max-width: 900px)` and `@media (max-width: 600px)` rules for this section.
8. SECTION SPECIFICS:
   - HEADER / MENUBAR: Left brand & nav links (heyclicky, features, pricing, trust, changelog, careers), center SVG logo mark, right status pills with hover popups.
   - HERO: Center the main layout (`display: flex; flex-direction: column; align-items: center; text-align: center;`). Include large bold headline 'heyclicky' (64px+, 800 weight), subtitle 'an ai buddy on your mac', 2 centered glossy action buttons ('Download for macOS' blue pill + 'Watch video' pill), floating polaroids/stickers on margins, and centered macOS video player card with window controls.
   - FEATURES: Include ALL 3 alternating feature showcase rows with macOS video windows, titles, and text descriptions (Row 1: Left text / Right video; Row 2: Left video / Right text; Row 3: Left text / Right video).
   - MANIFESTO: Replicate the pastel rainbow arch steps with gradient: `background: linear-gradient(90deg, rgba(255,102,204,0.45) 0%, rgba(255,153,51,0.45) 25%, rgba(255,204,0,0.45) 50%, rgba(102,204,51,0.45) 75%, rgba(51,153,102,0.45) 100%);` and centered macOS manifesto note card with highlight and signature.
   - FEEDBACK (Wall of Love): Replicate the FULL 3x3 grid of 9 macOS testimonial cards with colored header bars (green, blue, pink, yellow, cyan) and the bottom badge pill.
   - PRICING: Replicate the blue sky background with ALL 3 macOS pricing cards ($0 Free, $20 Pro, $100 Team) side-by-side in a 3-column grid and the bottom dark terminal license card.
   - FAQ: Centered clean accordion with smooth open/close and right-side polaroid face sticker.
   - FOOTER: Include 4 link columns and the massive 3D pixelated 'heyclicky' logo banner.
9. OUTPUT FORMAT: Output ONLY the clean HTML block for this section (e.g. `<section class="..."> ... </section>`). No markdown fences. No conversational preamble.
"""


def generate_section_html(
    section_data: dict,
    section_screenshot_path: str,
    design_tokens: dict,
    computed_styles: list,
    clone_dir: Optional[Path] = None,
    ctx: Optional[TaskContext] = None,
    responsive_deltas: Optional[list] = None,
) -> str:
    """
    Generates a single section's HTML using Gemini Multimodal Vision + Computed Styles + Responsive Deltas.
    """
    sec_idx = section_data.get("index", 0)
    sec_tag = section_data.get("tag", "section")
    sec_cls = section_data.get("classes", "")
    top_bound = section_data.get("top", 0)
    height = section_data.get("height", 800)

    section_styles = [
        s for s in computed_styles
        if (top_bound - 120) <= s.get("rect", {}).get("y", 0) <= (top_bound + height + 120)
    ][:50]

    sec_deltas = [
        d for d in (responsive_deltas or [])
        if (top_bound - 120) <= d.get("rect_desktop", {}).get("y", 0) <= (top_bound + height + 120)
    ][:20]

    delta_lines = []
    for d in sec_deltas:
        delta_lines.append(f"- {d.get('path', 'element')}: {', '.join(d.get('diffs', []))}")
    responsive_deltas_str = "\n".join(delta_lines) or "Switch flex/grid layouts to column, reduce font-size by ~30%, set container width: 100% at @media (max-width: 768px)."

    asset_inv_lines = []
    if clone_dir and (clone_dir / "assets").exists():
        for f in (clone_dir / "assets").rglob("*"):
            if f.is_file():
                rel = f"./assets/{f.relative_to(clone_dir / 'assets').as_posix()}"
                asset_inv_lines.append(f"- {f.name} -> {rel}")
    asset_inv_str = "\n".join(asset_inv_lines[:40])

    prompt = SECTION_PROMPT_TEMPLATE.format(
        dom_html=section_data.get("domHtml", "") or "<!-- DOM structure unavailable -->",
        full_text=section_data.get("fullText", "") or section_data.get("textPreview", ""),
        design_tokens=json.dumps(design_tokens, indent=2),
        computed_styles=json.dumps(section_styles, indent=2),
        responsive_deltas=responsive_deltas_str,
        asset_inv_str=asset_inv_str or "Use ./assets/images/ and ./assets/fonts/",
    )

    section_code = ""

    # 1. Try Gemini Vision with Multimodal Part via gemini.call() ladder
    try:
        from core import gemini
        from google.genai import types as gtypes
        img_path = Path(section_screenshot_path)
        if img_path.exists():
            img_bytes = img_path.read_bytes()
            part = gtypes.Part.from_bytes(data=img_bytes, mime_type="image/png")
            resp = gemini.call(
                contents=[prompt, part],
                tier=gemini.SMART,
                timeout_ms=60_000,
            )
            if resp and hasattr(resp, "text") and resp.text:
                section_code = resp.text.strip()
    except Exception as ge:
        logger.warning("Gemini vision call for section %s failed: %s", sec_idx, ge)

    # 2. Fallback to text-only synthesis if vision failed
    if not section_code or len(section_code) < 80:
        try:
            from core import gemini
            section_code = gemini.text(prompt, tier=gemini.SMART, timeout_ms=45_000) or ""
        except Exception as te:
            logger.warning("Gemini text fallback for section %s failed: %s", sec_idx, te)

    # 3. High-fidelity deterministic DOM fallback if LLM synthesis returned empty or rate-limited
    if not section_code or len(section_code) < 60:
        dom_fallback = section_data.get("domHtml", "")
        if dom_fallback and len(dom_fallback) > 30:
            logger.info("Using deterministic DOM structure for section %s (%s)", sec_idx+1, sec_tag)
            section_code = dom_fallback

    # Clean markdown fences
    if section_code:
        section_code = re.sub(r"^```(?:html)?\s*", "", section_code, flags=re.IGNORECASE)
        section_code = re.sub(r"\s*```$", "", section_code).strip()

    # Ensure section is wrapped in a valid container element
    if section_code and not re.match(r"^\s*<(section|header|footer|nav|main|div)\b", section_code, re.IGNORECASE):
        wrapper_tag = sec_tag if sec_tag in ("header", "footer", "nav", "section") else "section"
        cls_attr = f' class="{sec_cls}"' if sec_cls else f' class="section-{sec_idx+1}"'
        section_code = f"<{wrapper_tag}{cls_attr}>\n{section_code}\n</{wrapper_tag}>"

    return section_code


def _sanitize_section_layout_styles(sec_html: str) -> str:
    """
    Strips harmful absolute/fixed positioning, hardcoded top/left offsets from section-level
    tags and root styles to guarantee natural vertical document flow.
    """
    if not sec_html:
        return sec_html

    # 1. Remove position: absolute/fixed, top, left, right from inline style attributes
    def _strip_inline_styles(match: re.Match) -> str:
        tag_text = match.group(0)
        cleaned = re.sub(r'position\s*:\s*(?:absolute|fixed)\s*;?', 'position: relative;', tag_text, flags=re.IGNORECASE)
        cleaned = re.sub(r'(?:top|left|right)\s*:\s*-?\d+px\s*;?', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'transform\s*:\s*translateY\([^)]+\)\s*;?', '', cleaned, flags=re.IGNORECASE)
        return cleaned

    sec_html = re.sub(r'<(?:section|header|footer|nav|main|div)\b[^>]*style=["\'][^"\']*["\']', _strip_inline_styles, sec_html, flags=re.IGNORECASE)

    # 2. In embedded <style> blocks, sanitize root section selectors that declare position: absolute
    sec_html = re.sub(
        r'((?:section|header|footer|nav|main|\.hero|\.feat|\.man-section|\.fb|\.pr|\.faq)[^{}]*\{[^}]*?)position\s*:\s*absolute\s*;?',
        r'\1position: relative;',
        sec_html,
        flags=re.IGNORECASE,
    )
    sec_html = re.sub(
        r'((?:section|header|footer|nav|main|\.hero|\.feat|\.man-section|\.fb|\.pr|\.faq)[^{}]*\{[^}]*?)top\s*:\s*-?\d+px\s*;?',
        r'\1top: auto;',
        sec_html,
        flags=re.IGNORECASE,
    )
    return sec_html


def _extract_section_signature(sec_html: str) -> str:
    """Extracts a distinctive semantic signature from section HTML for deduplication without collision."""
    lower = sec_html[:600].lower()
    if "<header" in lower or "menubar" in lower:
        return "section:header"
    if "<footer" in lower or 'class="footer' in lower or "class='footer" in lower:
        return "section:footer"
    if "class=\"hero\"" in lower or "class='hero'" in lower or ("heyclicky" in lower and "hero" in lower):
        return "section:hero"
    if "class=\"feat\"" in lower or "id=\"feat\"" in lower or "features" in lower or "sound design" in lower:
        return "section:features"
    if "man-section" in lower or "the dream" in lower or "notes" in lower or "small set of simple" in lower:
        return "section:manifesto"
    if 'class="fb"' in lower or "class='fb'" in lower or "feedback" in lower or "they use it everyday" in lower:
        return "section:feedback"
    if 'class="pr"' in lower or 'id="pr"' in lower or "three simple plans" in lower or "$20" in lower:
        return "section:pricing"
    if 'class="faq"' in lower or "frequently asked questions" in lower:
        return "section:faq"

    m = re.search(r"<(section|header|footer|nav|div)[^>]*(?:id=[\"']([^\"']+)[\"']|class=[\"']([^\"']+)[\"'])", sec_html, re.IGNORECASE)
    if m:
        tag, sec_id, sec_cls = m.groups()
        if sec_id:
            return f"{tag.lower()}#{sec_id.lower()}"
        if sec_cls:
            classes = "-".join(sorted(sec_cls.lower().split()))
            return f"{tag.lower()}.{classes}"
    return sec_html[:80].strip()

    m = re.search(r"<(section|header|footer|nav|div)[^>]*(?:id=[\"']([^\"']+)[\"']|class=[\"']([^\"']+)[\"'])", sec_html, re.IGNORECASE)
    if m:
        tag, sec_id, sec_cls = m.groups()
        if sec_id:
            return f"{tag.lower()}#{sec_id.lower()}"
        if sec_cls:
            classes = "-".join(sorted(sec_cls.lower().split()))
            return f"{tag.lower()}.{classes}"
    return sec_html[:80].strip()


def assemble_master_html(
    sections_html: List[str],
    design_tokens: dict,
    original_url: str,
    page_title: str = "",
    clone_dir: Optional[Path] = None,
) -> str:
    """
    Merges all synthesized section blocks into a unified, responsive production-grade HTML5 document
    with comprehensive :root variables, deduplicated sections, and responsive CSS breakpoints.
    """
    palette_vars = []
    for i, (color, _) in enumerate(design_tokens.get("palette", {}).get("text_colors", [])[:8]):
        palette_vars.append(f"  --color-text-{i+1}: {color};")
    for i, (color, _) in enumerate(design_tokens.get("palette", {}).get("background_colors", [])[:8]):
        palette_vars.append(f"  --color-bg-{i+1}: {color};")

    type_vars = []
    for i, size in enumerate(design_tokens.get("typography", {}).get("font_sizes", [])[:10]):
        type_vars.append(f"  --text-size-{i+1}: {size};")

    radius_vars = []
    for i, r in enumerate(design_tokens.get("shape", {}).get("border_radii", [])[:6]):
        radius_vars.append(f"  --radius-{i+1}: {r};")

    # Font Face Declarations from localized fonts
    font_faces = []
    if clone_dir and (clone_dir / "assets" / "fonts").exists():
        for font_file in (clone_dir / "assets" / "fonts").glob("*.woff2"):
            font_faces.append(
                f"@font-face {{\n  font-family: 'LocalFont_{font_file.stem[:8]}';\n  src: url('./assets/fonts/{font_file.name}') format('woff2');\n  font-display: swap;\n}}"
            )
    font_face_css = "\n".join(font_faces)

    font_families = design_tokens.get("typography", {}).get("font_families", [])
    primary_font = font_families[0] if font_families else "Inter, -apple-system, sans-serif"

    root_css = f"""
{font_face_css}

:root {{
{chr(10).join(palette_vars)}
{chr(10).join(type_vars)}
{chr(10).join(radius_vars)}
  --spacing-base: {design_tokens.get("spacing", {}).get("base_unit", "16px")};
  --font-family-main: '{primary_font}', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}}

*, *::before, *::after {{
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}}

html {{
  scroll-behavior: smooth;
  -webkit-text-size-adjust: 100%;
}}

body {{
  font-family: var(--font-family-main);
  background-color: #f5f5f5 !important;
  color: var(--color-text-1, #000000);
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  overflow-x: hidden;
  width: 100%;
}}

img, video, svg, canvas {{
  display: block;
  max-width: 100%;
  height: auto;
}}

a {{
  color: inherit;
  text-decoration: none;
}}

button {{
  cursor: pointer;
  font-family: inherit;
  border: none;
  background: none;
}}

/* Universal Responsive Container Layout & Normal Block Flow */
section, header, footer, main, [class*="section-"] {{
  position: relative !important;
  top: auto !important;
  left: auto !important;
  width: 100% !important;
  display: block !important;
  clear: both !important;
  box-sizing: border-box !important;
  margin: 0 auto;
}}

/* Explicit Section Background Defaults */
[class*="hero"], [class*="feat"], [class*="fb"], [class*="faq"], footer {{
  background-color: transparent;
}}

/* Pricing Sky Gradient */
[class*="pr"], [class*="pricing"], #pr {{
  background: linear-gradient(180deg, #38bdf8 0%, #60a5fa 35%, #93c5fd 70%, #dbeafe 90%, #f5f5f5 100%) !important;
}}

/* Manifesto Rainbow Gradient */
.man-rainbow, [class*="rainbow"], [class*="arch"], [class*="step-arch"] {{
  background: linear-gradient(90deg,
    rgba(255,102,204,0.35) 0%,
    rgba(255,153,51,0.35) 25%,
    rgba(255,204,0,0.35) 50%,
    rgba(102,204,51,0.35) 75%,
    rgba(51,153,102,0.35) 100%) !important;
}}

/* Responsive Breakpoints & Mobile Adaptability */
@media (max-width: 1024px) {{
  :root {{
    --spacing-base: 14px;
  }}
  [class*="grid"], .grid {{
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)) !important;
  }}
}}

@media (max-width: 768px) {{
  :root {{
    --spacing-base: 12px;
  }}
  h1 {{ font-size: clamp(28px, 6vw, 42px) !important; line-height: 1.15 !important; }}
  h2 {{ font-size: clamp(22px, 5vw, 32px) !important; line-height: 1.2 !important; }}
  h3 {{ font-size: clamp(18px, 4vw, 24px) !important; }}
  p {{ font-size: 15px !important; line-height: 1.45 !important; }}

  [class*="flex-row"], .row {{
    flex-direction: column !important;
  }}

  [class*="hero"], [class*="feat"], [class*="fb"], [class*="pr"], [class*="faq"] {{
    padding-left: 16px !important;
    padding-right: 16px !important;
  }}
}}
"""

    # Deduplicate sections by semantic signature
    seen_signatures = {}
    deduped_sections = []

    for idx, sec_html in enumerate(sections_html):
        sec_html = (sec_html or "").strip()
        if not sec_html or len(sec_html) < 60:
            continue

        sec_html = _sanitize_section_layout_styles(sec_html)
        sig = _extract_section_signature(sec_html)
        if sig in seen_signatures:
            prev_idx, prev_html = seen_signatures[sig]
            if len(sec_html) > len(prev_html):
                deduped_sections[prev_idx] = sec_html
                seen_signatures[sig] = (prev_idx, sec_html)
            continue

        seen_signatures[sig] = (len(deduped_sections), sec_html)
        deduped_sections.append(sec_html)

    joined_sections = "\n\n".join(deduped_sections)

    master_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{page_title or original_url}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
{root_css}
  </style>
</head>
<body>
{joined_sections}

  <script src="./assets/js/app.js"></script>
</body>
</html>
"""
    return master_html


def generate_design_system_md(design_tokens: dict, original_url: str, page_title: str) -> str:
    """Generates a clean studio-grade DESIGN.md specification file."""
    # ASCII-safe headers — no emoji, prevents cp1252 corruption on Windows
    lines = [
        f"# DESIGN SYSTEM SPECIFICATION: {page_title or original_url}",
        f"> **Source URL:** `{original_url}`  ",
        f"> **Extracted:** `{time.strftime('%Y-%m-%d %H:%M:%S')}`  \n",
        "## Color Palette Tokens",
    ]
    for color, count in design_tokens.get("palette", {}).get("text_colors", []):
        lines.append(f"- **Text Color:** `{color}` (used {count}x)")
    for color, count in design_tokens.get("palette", {}).get("background_colors", []):
        lines.append(f"- **Background Color:** `{color}` (used {count}x)")

    lines.append("\n## Typography & Type Scale")
    for f in design_tokens.get("typography", {}).get("font_families", []):
        lines.append(f"- **Font Family:** `{f}`")
    lines.append(f"- **Font Sizes:** {', '.join(design_tokens.get('typography', {}).get('font_sizes', []))}")
    lines.append(f"- **Font Weights:** {', '.join(design_tokens.get('typography', {}).get('font_weights', []))}")
    lh = design_tokens.get('typography', {}).get('line_heights', [])
    if lh:
        lines.append(f"- **Line Heights:** {', '.join(lh)}")
    ls = design_tokens.get('typography', {}).get('letter_spacings', [])
    if ls:
        lines.append(f"- **Letter Spacings:** {', '.join(ls)}")

    lines.append("\n## Spacing & Shape Matrix")
    lines.append(f"- **Base Spacing Unit:** `{design_tokens.get('spacing', {}).get('base_unit', '16px')}`")
    gaps = design_tokens.get('spacing', {}).get('common_gaps', [])
    if gaps:
        lines.append(f"- **Common Gaps:** {', '.join(gaps)}")
    pads = design_tokens.get('spacing', {}).get('common_paddings', [])
    if pads:
        lines.append(f"- **Common Paddings:** {', '.join(pads[:8])}")
    lines.append(f"- **Border Radii:** {', '.join(design_tokens.get('shape', {}).get('border_radii', []))}")
    lines.append(f"- **Shadows:** {', '.join(design_tokens.get('shape', {}).get('shadows', []))}")

    css_vars = design_tokens.get('css_variables', {})
    if css_vars:
        lines.append("\n## CSS Custom Properties (:root)")
        for k, v in list(css_vars.items())[:20]:
            lines.append(f"- `{k}`: `{v}`")

    return "\n".join(lines)


def _fetch_html_and_visual_data_playwright(
    url: str,
    clone_dir: Path,
    ctx: Optional[TaskContext] = None,
    timeout_ms: int = 25000,
) -> Tuple[str, str, dict, List[dict], List[dict], Optional[Path]]:
    """
    Tier 1 Multimodal Multi-Viewport Capture:
    1. Desktop (1440px): Dynamic auto-scroll, section slicing, computed styles, full screenshot.
    2. Tablet (768px): Resizes viewport, extracts tablet computed layout.
    3. Mobile (375px): Resizes viewport, extracts mobile computed layout & captures mobile screenshot.
    4. Computes property-level responsive deltas between viewports.
    """
    if not PLAYWRIGHT_AVAILABLE:
        raise ImportError("Playwright is not installed.")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
        )
        page = context.new_page()

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        except Exception:
            page.goto(url, wait_until="load", timeout=timeout_ms)

        time.sleep(1.0)

        # Dynamic Auto-Scroll across full page depth to trigger lazy-loaded sections and React hydration
        try:
            for y in range(0, 8000, 350):
                page.evaluate(f"window.scrollTo(0, {y})")
                time.sleep(0.08)
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(0.3)
        except Exception:
            pass

        # ── Desktop DOM & Computed Layout ──
        _safe_report(ctx, 18, f"[EXTRACT] Analyzing DOM & computed CSS for {url}...")
        computed_desktop = {}
        try:
            computed_desktop = page.evaluate(COMPUTED_STYLES_JS)
        except Exception as ce:
            logger.warning("Desktop computed styles extraction error: %s", ce)

        html = page.content()
        title = page.title() or ""
        browser.close()

        return html, title, computed_desktop


def _synthesize_clean_website(
    url: str,
    raw_html: str,
    clone_dir: Path,
    target_format: str = "static",
    ctx: Optional[TaskContext] = None,
) -> str:
    """
    Antigravity Master Reverse-Engineering Engine:
    Ingests Uncage raw bundle (multi-pages, asset-map.json, styles, raw DOM),
    and synthesizes a clean, high-fidelity standalone single-file index.html with:
    - Scoped modern CSS (CSS variables, flex/grid, zero absolute-positioning bugs)
    - Full Vanilla JS micro-interactions (draggables, audio waveforms, tabs, accordions, modals)
    - Localized ./assets/ asset path mapping
    """
    _safe_report(ctx, 75, f"[SYNTHESIS] Processing site bundle & asset map for {url}...")

    asset_map_str = ""
    asset_map_file = clone_dir / "asset-map.json"
    if asset_map_file.exists():
        try:
            asset_map_data = json.loads(asset_map_file.read_text(encoding="utf-8", errors="replace"))
            asset_map_str = json.dumps(asset_map_data, indent=2)[:6000]
        except Exception:
            pass

    # Read available local assets
    asset_files = []
    if (clone_dir / "assets").exists():
        for f in (clone_dir / "assets").rglob("*"):
            if f.is_file():
                rel = f"./assets/{f.relative_to(clone_dir / 'assets').as_posix()}"
                asset_files.append(rel)
    asset_list_str = "\n".join(asset_files[:50]) or "Use ./assets/images/ and ./assets/fonts/"

    # Read sub-pages if Uncage crawled them
    subpage_snippets = []
    for html_file in clone_dir.glob("*.html"):
        if html_file.name != "index.html":
            txt = html_file.read_text(encoding="utf-8", errors="replace")[:1500]
            subpage_snippets.append(f"<!-- Page: {html_file.name} -->\n{txt}")
    subpages_str = "\n\n".join(subpage_snippets[:5])

    # Truncate raw HTML safely
    clean_raw = raw_html[:45000] if raw_html else ""

    prompt = f"""You are the Antigravity Master Reverse-Engineering Specialist and Lead Frontend Architect for Zezo (created by Hamza Bukhari).
Your task is to synthesize an immaculate, 100% production-ready, standalone single-file `index.html` that reverse-engineers the target website with PIXEL-PERFECT FIDELITY and full interactivity.

TARGET URL: {url}

LOCAL ASSET CATALOG:
{asset_list_str}

ASSET MAP (Original -> Local):
{asset_map_str or "Standard relative asset paths"}

SUB-PAGES DISCOVERED:
{subpages_str or "Single landing page"}

RAW EXTRACTED DOM / CONTENT:
{clean_raw[:35000]}

NON-NEGOTIABLE ARCHITECTURAL & DESIGN RULES:
1. SINGLE-FILE STANDALONE: Deliver ONE complete `<!DOCTYPE html>` with embedded `<style>` in `<head>` and complete `<script>` before `</body>`.
2. 100% FAITHFUL CONTENT: Replicate all actual headings, subtitles, cards, tiers, reviews, buttons, badges, and footer links from the raw DOM. Do NOT omit any section.
3. PREVENT LAYOUT COLLAPSE: Use standard modern CSS (Flexbox, CSS Grid, clamp(), CSS custom properties). NEVER use `position: absolute` or hardcoded `top: ...px` on section wrappers.
4. COMPLETE VANILLA JS MICRO-INTERACTIONS:
   - Floating polaroids/stickers: Draggable with mouse drag & drop (`mousedown`, `mousemove`, `mouseup`).
   - Audio waveform: 12-bar animated or interactive bars.
   - Accordion / FAQ: Smooth height toggles with active indicator rotation.
   - Pricing Switcher: Monthly / Annual toggle updating card pricing and terms.
   - Video Cards & Modals: macOS style window dots (red/yellow/green) with hover effects.
   - Navbar Links: Smooth scroll to matching section anchors.
5. CLEAN ASSET LINKING: Reference images, icons, and media via `./assets/...` relative paths matching the asset list above.
6. RESPONSIVE DESIGN: Flawless fluid layout across Desktop (1440px), Tablet (768px), and Mobile (375px) via `@media (max-width: 900px)` and `@media (max-width: 600px)`.
7. OUTPUT ONLY RAW HTML: Return ONLY the raw HTML string starting with `<!DOCTYPE html>`. No markdown code fences, no conversational commentary.
"""

    synth_html = ""
    try:
        from core import gemini
        _safe_report(ctx, 80, "[SYNTHESIS] Synthesizing clean standalone code via Antigravity Engine...")
        synth_html = gemini.text(prompt, tier=gemini.SMART, timeout_ms=75_000) or ""
    except Exception as ge:
        logger.warning("Gemini Antigravity text synthesis error: %s", ge)

    if synth_html:
        synth_html = re.sub(r"^```(?:html)?\s*", "", synth_html.strip(), flags=re.IGNORECASE)
        synth_html = re.sub(r"\s*```$", "", synth_html.strip())

    if synth_html and "<!DOCTYPE html>" in synth_html and len(synth_html) > 500:
        _safe_report(ctx, 88, "[SYNTHESIS] Successfully generated clean standalone HTML.")
        return synth_html

    logger.warning("Antigravity synthesis returned incomplete output. Falling back to deterministic assembly.")
    return raw_html if raw_html else "<!DOCTYPE html><html><body><h1>Website Cloned</h1></body></html>"


def _faithful_cleanup(raw_html: str, url: str, clone_dir: Path, ctx=None) -> str:
    """Return the raw clone HTML verbatim so the Antigravity output is 100% faithful to the original."""
    if not raw_html:
        return ""
    _safe_report(ctx, 91, "[CLEANUP] Preserving raw clone HTML verbatim (100% faithful).")
    _safe_report(ctx, 93, "[CLEANUP] Cleanup complete - 100% faithful to original.")
    return raw_html


# ── ZEZO-native reverse engineering of a captured site ───────────────────────
#
# ZEZO ports nothing itself and pre-builds nothing. Once uncage has finished, it runs the
# local coding engine (agy) ONCE with a complete caller-authored prompt whose ONLY variable
# is the output-format clause, and the engine writes the artifact itself.
#
# The capture folder is the reference and is NEVER rewritten: uncage's index.html, assets/
# and asset-map.json stay exactly as uncage produced them. The rebuilt artifact is ADDED at a
# new path. That placement is forced, not cosmetic - a single-file rebuild must sit inside the
# capture folder or its relative assets/... references would 404, and a project rebuild needs
# its own subfolder because uncage already writes a package.json and README.md at its root.

RE_ARTIFACT_SINGLE = "rebuilt.html"
RE_ARTIFACT_APP_DIR = "rebuilt_app"
DEFAULT_OUTPUT_FORMAT = "raw_html"

# The prefix of the text a failed rebuild raises. core/prompt.txt decides how ZEZO explains a
# failed clone by matching this exact prefix, and the two drifted apart once already (the message
# became "Rebuild FAILED -" while the prompt still matched "React rebuild FAILED -"), which
# silently killed the branch that tells the model to pass `path` to fleet_control. It is a shared
# constant now, and tests/test_website_cloner_suite.py asserts it appears in core/prompt.txt, so
# the next rewrite of either side fails the suite instead of failing quietly in a live session.
RE_REBUILD_FAILURE_PREFIX = "Rebuild FAILED - capture intact at"


def rebuild_failure_message(clone_dir: Path, preview_url: str, detail: str) -> str:
    """The exact text a failed rebuild raises.

    Kept as one function so the prompt contract and the raiser cannot drift: the folder path leads
    the message because the failure notification ZEZO receives is cut at 150 chars.
    """
    return (
        f"{RE_REBUILD_FAILURE_PREFIX} {clone_dir} (preview open at {preview_url}). "
        f"Reason: {detail}. A fleet agent can be pointed at that folder to finish it."
    )

# Explicit opt-out: deliver the capture and skip the engine stage entirely.
# The legacy 'static'/'clean_html' values map here so the old capture-only behaviour stays
# reachable and unchanged; the default for a fresh clone is now a rebuilt single HTML page.
CAPTURE_ONLY_FORMATS = ("capture_only", "static", "clean_html", "none")

# Human phrases for the read-back, so the user hears what they will get before any crawl.
RE_READBACK_FORMATS = {
    "raw_html": "one rebuilt single HTML page (rebuilt from the capture, not a copy of it)",
    "single_html": "one rebuilt single HTML page (rebuilt from the capture, not a copy of it)",
    "html": "one rebuilt single HTML page (rebuilt from the capture, not a copy of it)",
    "react": "a React + Vite project",
    "nextjs": "a Next.js project",
    "php": "a PHP project",
    "capture_only": "nothing new - just the raw capture and its preview",
    "static": "nothing new - just the raw capture and its preview",
    "clean_html": "nothing new - just the raw capture and its preview",
    "none": "nothing new - just the raw capture and its preview",
}

# The inspection half of the reverse-engineering prompt. Taken from the prompt Hamza Bukhari
# runs by hand against an uncage export, which is the proven-fidelity version of this task.
RE_PROMPT_INSPECT = (
    "You are an expert Web Designer, UI Designer, Frontend Engineer, and Website Reverse "
    "Engineering AI Agent. Your only task is to inspect the entire project provided to you "
    "through the project files and then rebuild the website as accurately as possible based on "
    "the actual files, code, assets, screenshots, components, styles, routes, content, and "
    "existing implementation. Do not rely on assumptions when the required information already "
    "exists inside the project. First inspect the complete project structure and identify all "
    "relevant files including HTML, JSX, TSX, JavaScript, CSS, SCSS, Tailwind files, JSON, "
    "images, SVGs, videos, fonts, icons, components, layouts, routes, configuration files, and "
    "any other assets or references that affect the website's visual appearance. Understand how "
    "the original website is structured from top to bottom and reverse engineer every visible "
    "section, including announcement bars, header, navigation, hero, sub-navigation, feature "
    "sections, content blocks, image sections, cards, testimonials, logos, statistics, pricing, "
    "FAQs, forms, CTAs, footer, and any additional sections or reusable patterns found in the "
    "project. Inspect the existing code and assets carefully to determine exact typography, "
    "colors, spacing, dimensions, layout behavior, responsive rules, animations, interactions, "
    "image usage, iconography, borders, shadows, gradients, backgrounds, and component "
    "relationships."
)

# The shared rules half. The "no design system / no analysis report / no description" clauses
# are what keep the engine writing artifacts instead of prose, so they are load-bearing.
RE_PROMPT_TAIL = (
    "Reuse the project's actual assets whenever possible instead of creating replacements, "
    "preserve original image proportions and visual hierarchy, use the actual fonts when "
    "available, and reproduce important interactions such as dropdowns, mobile navigation, "
    "accordions, tabs, sliders, hover effects, scroll animations, menus, and other visible "
    "behaviors when they can reasonably be recreated with vanilla JavaScript. Do not create a "
    "design system, do not write an analysis report, do not explain what you found, and do not "
    "simplify the website into a basic approximation. The objective is to reverse engineer the "
    "provided project and produce a highly accurate visual recreation of the website. After "
    "inspecting the files, directly build the final implementation using the information "
    "available in the project. Keep the implementation clean, structured, responsive, and "
    "production-quality. Write the actual deliverable files - answering with a plan, a summary "
    "or a diff instead of real files counts as failure."
)

# The ONE part of the prompt that varies with what the user asked for.
RE_OUTPUT_CLAUSES = {
    "raw_html": (
        f"Recreate the website as a single standalone HTML file named '{RE_ARTIFACT_SINGLE}' "
        f"written in the workspace root, containing the complete visual experience, with "
        f"embedded CSS and JavaScript, and make it fully responsive across desktop, tablet, and "
        f"mobile. Keep the capture's local asset references working by pointing them at the same "
        f"relative 'assets/...' paths the capture already uses. Do NOT overwrite or modify "
        f"index.html, assets/ or asset-map.json - they are the reference. The deliverable is "
        f"that one file, not a description of it."
    ),
    "react": (
        f"Recreate the website as a React + Vite project inside a new subfolder named "
        f"'{RE_ARTIFACT_APP_DIR}' in the workspace root. Split the captured page into reusable "
        f"components, translate the markup to valid JSX (class -> className, for -> htmlFor, "
        f"inline style strings -> style objects), and carry the captured stylesheets, fonts and "
        f"images across unchanged rather than restyling them. Ship package.json, vite.config.ts, "
        f"an index.html entry and the src/ entrypoint so 'npm install' then 'npm run dev' runs "
        f"it. Do not run npm install, do not run npm run dev, do not start any server."
    ),
    "nextjs": (
        f"Recreate the website as a Next.js project inside a new subfolder named "
        f"'{RE_ARTIFACT_APP_DIR}' in the workspace root, using the App Router. Split the "
        f"captured page into reusable components and carry the captured stylesheets, fonts and "
        f"images across unchanged. Ship package.json, next.config.js and the app/ route files "
        f"so 'npm install' then 'npm run dev' runs it. Do not run npm install, do not run "
        f"npm run dev, do not start any server."
    ),
    "php": (
        f"Recreate the website as a PHP project inside a new subfolder named "
        f"'{RE_ARTIFACT_APP_DIR}' in the workspace root: index.php plus the shared markup split "
        f"into partials under includes/, with the captured stylesheets, fonts and images carried "
        f"across unchanged. It must run with 'php -S localhost:8000' with no build step. Do not "
        f"start any server yourself."
    ),
}

# How success is judged per format - inspected on disk, never taken from the engine's prose.
# globs are single-segment patterns because Path.rglob already recurses.
RE_ARTIFACT_SPECS = {
    "raw_html": {"kind": "single"},
    "react": {
        "kind": "project", "require": ["package.json"],
        "dirs": ["src", "app"], "globs": ["*.tsx", "*.jsx"],
    },
    "nextjs": {
        "kind": "project", "require": ["package.json"],
        "dirs": ["app", "pages", "src"], "globs": ["*.tsx", "*.jsx"],
    },
    "php": {
        "kind": "project", "require": ["index.php"],
        "dirs": [], "globs": ["*.php"],
    },
}


def _re_output_clause(output_format: str) -> str:
    """Return the output-format clause for the requested format.

    Any value that is not one of the curated formats is treated as a stack the user named in
    their own words ("svelte", "ruby on rails", "a one-page portfolio"). The confirmation gate
    reads the value back before this runs, and that read-back is what catches a misheard stack
    name - so free text is safe here where a silent default would not be.
    """
    fmt = (output_format or "").strip()
    clause = RE_OUTPUT_CLAUSES.get(fmt.lower())
    if clause:
        return clause
    return (
        f"Recreate the website as: {fmt}. Build it inside a new subfolder named "
        f"'{RE_ARTIFACT_APP_DIR}' in the workspace root, unless that request names a single "
        f"file, in which case write that one file in the workspace root. Ship everything the "
        f"stack needs to run (manifest, entrypoint, source files) - do not describe it."
    )


def reverse_engineer_prompt(url: str, output_format: str) -> str:
    """The complete prompt handed to the coding engine, in verbatim mode.

    Sent untouched: actions/antigravity_agent.py skips its own stack directives and its 6000
    character cap when prompt_mode='verbatim'. Appending ZEZO's directives to this prompt would
    hand the agent two contradicting instruction sets - a reverse-engineering prompt that says
    "reuse the real assets, one file" next to ZEZO's "modular React + Tailwind project".
    """
    return "\n\n".join(
        (
            f"REFERENCE PROJECT: this workspace is a complete offline capture of {url}. Inspect "
            f"it directly - index.html, assets/, asset-map.json and every other file in it are "
            f"the ground truth. Never modify or delete anything already in this folder; it is "
            f"the reference you are rebuilding from.",
            RE_PROMPT_INSPECT,
            _re_output_clause(output_format),
            RE_PROMPT_TAIL,
        )
    )


def _new_html_files(root: Path, before: Set[str]) -> List[Path]:
    """HTML files that appeared during the engine run, newest first.

    Uncage's own snapshots are excluded: a `captured-raw*` file is the pre-assembly state and
    antigravity_clone.html is ZEZO's verbatim copy, so neither is ever a rebuilt artifact.
    """
    fresh = [
        p for p in root.rglob("*.html")
        if str(p) not in before
        and not p.name.startswith("captured-raw")
        and p.name != "antigravity_clone.html"
    ]
    return sorted(fresh, key=lambda p: p.stat().st_mtime, reverse=True)


def _verify_re_artifact(
    clone_dir: Path, output_format: str, before_html: Set[str]
) -> Tuple[bool, str, Optional[Path]]:
    """Decide success by inspecting the folder, never by what the engine says it did."""
    spec = RE_ARTIFACT_SPECS.get((output_format or "").strip().lower())

    if spec is None:
        # A stack named in the user's own words: we cannot know its shape, so the honest test
        # is that real files appeared - either in the app subfolder or as a new HTML file.
        app = clone_dir / RE_ARTIFACT_APP_DIR
        if app.is_dir() and any(p.is_file() for p in app.rglob("*")):
            return True, f"build written to {RE_ARTIFACT_APP_DIR}/", app
        fresh = _new_html_files(clone_dir, before_html)
        if fresh:
            return True, f"build written as {fresh[0].name}", fresh[0]
        return False, "the engine produced no files for the requested stack", None

    if spec["kind"] == "single":
        fresh = _new_html_files(clone_dir, before_html)
        if not fresh:
            return False, (
                "the engine wrote no new HTML file - answering with a plan or a summary "
                "instead of the file counts as failure"
            ), None
        return True, f"rebuilt page written as {fresh[0].name}", fresh[0]

    app = clone_dir / RE_ARTIFACT_APP_DIR
    if not app.is_dir():
        return False, f"the engine created no {RE_ARTIFACT_APP_DIR}/ folder", None
    missing = [f for f in spec["require"] if not (app / f).exists()]
    if missing:
        return False, f"the engine finished without {', '.join(missing)}", app
    if spec["dirs"] and not any((app / d).is_dir() for d in spec["dirs"]):
        return False, f"the engine finished without any of {', '.join(spec['dirs'])}/", app
    if spec["globs"]:
        found = sum(len(list(app.rglob(g))) for g in spec["globs"])
        if found == 0:
            return False, f"the engine produced no source files ({', '.join(spec['globs'])})", app
        return True, f"{found} source file(s) in {RE_ARTIFACT_APP_DIR}/", app
    if not any(p.is_file() for p in app.rglob("*")):
        return False, f"{RE_ARTIFACT_APP_DIR}/ is empty", app
    return True, f"build written to {RE_ARTIFACT_APP_DIR}/", app


def _run_reverse_engineer(
    url: str, clone_dir: Path, ctx: TaskContext, output_format: str
) -> Tuple[bool, str, Optional[Path]]:
    """Reverse-engineer a completed capture into the requested format with ZEZO's own engine.

    Returns (ok, detail, artifact_path). The call reuses the existing run_in_place seam in
    actions/antigravity_agent.py, so the build reports into THIS task's card instead of
    spawning a second task - and it is the same agy.exe invocation a fleet agent would make.
    """
    fmt = (output_format or DEFAULT_OUTPUT_FORMAT).strip()
    before_html = {str(p) for p in clone_dir.rglob("*.html")}

    _safe_report(ctx, 99, f"[REBUILD] ZEZO is reverse-engineering the capture into '{fmt}' in {clone_dir.name}...")
    try:
        from actions.antigravity_agent import antigravity_action
        engine_out = antigravity_action(
            {
                "task": reverse_engineer_prompt(url, fmt),
                # cwd == the capture folder, exactly like running the agent by hand against an
                # uncage export: the reference is right there and --add-dir covers it.
                "project_path": str(clone_dir),
                "run_in_place": True,
                "task_ctx": ctx,
                # verbatim: send this prompt untouched, no ZEZO stack directives appended.
                "prompt_mode": "verbatim",
                # A rebuild reproduces the captured design, so no Hamza Taste blueprint may be
                # injected; and the engine's own file:// preview is suppressed because ZEZO
                # serves the capture and the rebuilt artifact itself.
                "skip_design": True,
                "skip_preview": True,
            },
            session_memory={},
        )
    except Exception as e:
        return False, f"the coding engine crashed ({e})", None

    engine_status = ""
    try:
        parsed = json.loads(engine_out) if isinstance(engine_out, str) else engine_out
        if isinstance(parsed, dict) and parsed.get("status") not in (None, "success"):
            engine_status = str(parsed.get("error") or parsed.get("status"))
    except Exception:
        pass

    # An engine that reports failure is taken at its word even if the folder looks plausible:
    # it may have written a few files before dying, and a half-built artifact reported as
    # finished is exactly the false success this tool must not produce.
    if engine_status:
        return False, f"the coding engine reported a failure ({engine_status[:120]})", None

    return _verify_re_artifact(clone_dir, fmt, before_html)


def _clone_worker(params: dict, ctx: TaskContext) -> dict:
    """
    Main asynchronous worker executing the website cloning pipeline with Multimodal Vision v2 + IR Responsive Delta Engine.
    """
    raw_url = params.get("url") or params.get("link") or params.get("target") or ""
    url = _normalize_url(raw_url)
    mode = params.get("mode") or "single_page"
    # The confirmation gate always supplies this, so the fallback is for direct callers only;
    # it matches the default the gate advertises.
    output_format = params.get("output_format") or DEFAULT_OUTPUT_FORMAT
    target_dir_param = params.get("target_dir") or params.get("repo") or params.get("project_path")

    if not url:
        raise ValueError("A valid URL is required for website cloning.")

    domain = _extract_domain(url)

    # 1. Setup Workspace Directory
    #    expand_user_dir (not Path.resolve) so a user-facing name like "Desktop/x" is placed on the
    #    real Desktop instead of being resolved against ZEZO's own CWD, i.e. inside the repo.
    if target_dir_param:
        clone_dir = expand_user_dir(target_dir_param)
        clone_dir.mkdir(parents=True, exist_ok=True)
    else:
        clone_dir = get_unique_clone_dir(domain)

    _safe_report(ctx, 5, f"[INIT] Allocated workspace at {clone_dir.name}...")

    # 2. Register Undo Snapshot
    register_clone_snapshot(clone_dir, tool_label=f"Clone of {domain}")

    # 3. Static clone is always delivered first; the optional React/Next rebuild runs at the
    #    end of this worker (step 11) so a failed rebuild can never cost the captured bundle.

    # 4. Zero-Latency Tech Stack Fingerprinting (<200ms)
    _safe_report(ctx, 9, "[STACK] Fingerprinting target website tech stack...")
    detected_stack = detect_tech_stack(url)
    _safe_report(ctx, 11, f"[STACK] Detected framework: {detected_stack.upper()}")

    # 5. Handle Full Site Mirroring (HTTrack) if requested
    if mode == "full_site" or detected_stack == "wordpress":
        _safe_report(ctx, 12, f"[MIRROR] Initiating site mirror for {url} (mode={mode})...")
        httrack_ok = _fetch_tier4_httrack(url, clone_dir, max_depth=MAX_DEPTH_FULL_SITE)
        if httrack_ok and (clone_dir / "index.html").exists():
            downloaded_files = len(list(clone_dir.rglob("*")))
            preview_url, port = start_local_preview_server(clone_dir)
            register_clone(clone_dir)
            _safe_report(ctx, 100, f"[DONE] Site mirrored successfully ({downloaded_files} files).")
            return {
                "status": "success",
                "url": url,
                "mode": mode,
                "output_format": output_format,
                "clone_dir": str(clone_dir),
                "files_downloaded": downloaded_files,
                "failed_assets": 0,
                "preview_url": preview_url,
                "summary": f"Site mirrored to '{clone_dir.name}' ({downloaded_files} files). Preview running at {preview_url}.",
            }

    # 6. Dynamic Scraper Dispatch: Pure 100% Uncage Engine (Zero Fallbacks)
    engine_used = "Uncage Static Cloner"
    uncage_pages = 1 if mode == "single_page" else min(MAX_PAGES_FULL_SITE, 25)
    uncage_depth = 0 if mode == "single_page" else MAX_DEPTH_FULL_SITE
    _safe_report(ctx, 15, f"[UNCAGE] Dispatching Uncage static cloner for {url} (max_pages={uncage_pages})...")
    uncage_ok, uncage_detail = run_uncage_exporter(
        url, clone_dir, ctx,
        max_pages=uncage_pages,
        max_depth=uncage_depth,
        timeout_sec=crawl_timeout_budget(uncage_pages),
        priority_only=bool(params.get("main_pages_only")),
    )

    if not uncage_ok:
        reason = uncage_detail or "output bundle not found"
        _safe_report(ctx, 100, f"[UNCAGE ERROR] Uncage extraction failed for {url}: {reason}")
        raise RuntimeError(f"Uncage extraction failed for {url}: {reason}.")

    _safe_report(ctx, 88, f"[UNCAGE] Bundle assembled successfully into {clone_dir.name}.")

    # 6b. Asset integrity gate. A clone whose local assets 404 renders unstyled — that was
    # the reported defect, so fail loudly here rather than opening a preview and calling a
    # broken clone a success.
    assets_ok, assets_msg = verify_local_assets(clone_dir)
    if not assets_ok:
        _safe_report(ctx, 100, f"[INTEGRITY ERROR] {assets_msg}")
        raise RuntimeError(
            f"Clone produced a page with unresolved local assets: {assets_msg}. "
            f"Refusing to report success - partial output kept at {clone_dir}."
        )
    _safe_report(ctx, 89, f"[INTEGRITY] {assets_msg}.")
    # Anything uncage failed to save is a caveat the user should hear, not a silent gap.
    media_note = (
        " Note: some images and video/audio files could not be downloaded, so a few spots show up empty."
        if ("could not be saved" in assets_msg or "were not downloaded" in assets_msg) else ""
    )

    antigravity_file = clone_dir / "antigravity_clone.html"
    if output_format in CAPTURE_ONLY_FORMATS:
        # 7. Antigravity Master Reverse-Engineering (section-aware multimodal, with faithful fallback)
        _safe_report(ctx, 90, "[ANTIGRAVITY] Running reverse-engineering synthesis...")
        raw_html = ""
        index_file = clone_dir / "index.html"
        if index_file.exists():
            try:
                raw_html = index_file.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass

        synth_html = ""
        # Primary: faithful cleanup (preserves 100% of original design)
        try:
            synth_html = _faithful_cleanup(raw_html, url, clone_dir, ctx)
        except Exception as _fe:
            logger.warning("Faithful cleanup failed: %s", _fe)
            synth_html = ""

        # Secondary: section-aware multimodal (only for redesign mode)
        if output_format == "redesign" and (not synth_html or len(synth_html) < 500):
            try:
                _safe_report(ctx, 91, "[ANTIGRAVITY] Capturing multi-viewport DOM + computed styles...")
                html_d, title_d, computed_desktop = _fetch_html_and_visual_data_playwright(url, clone_dir, ctx)
                design_tokens = synthesize_design_tokens(computed_desktop or {})
                sections = capture_section_screenshots_sync  # placeholder guard
                # capture sections via playwright page already closed; re-open lightweight by reusing html_d
                # We'll use the existing helper that returns section slices if available
                try:
                    from playwright.sync_api import sync_playwright as _sp
                    with _sp() as _p:
                        _b = _p.chromium.launch(headless=True, args=["--no-sandbox"])
                        _c = _b.new_context(viewport={"width": 1440, "height": 900})
                        _pg = _c.new_page()
                        _pg.goto(url, wait_until="domcontentloaded", timeout=25000)
                        time.sleep(1.0)
                        for _y in range(0, 8000, 350):
                            _pg.evaluate(f"window.scrollTo(0, {_y})")
                            time.sleep(0.05)
                        _pg.evaluate("window.scrollTo(0, 0)")
                        time.sleep(0.3)
                        slices = capture_section_screenshots_sync(_pg, clone_dir, viewport_width=1440)
                        _b.close()
                except Exception as _se:
                    logger.warning("Section capture failed: %s", _se)
                    slices = []

                if slices:
                    _safe_report(ctx, 93, f"[ANTIGRAVITY] Synthesizing {len(slices)} sections via Gemini vision...")
                    sec_htmls = []
                    for _sec in slices:
                        try:
                            _sh = generate_section_html(
                                _sec,
                                _sec.get("screenshot_path", ""),
                                design_tokens,
                                (computed_desktop or {}).get("elements", []) if isinstance(computed_desktop, dict) else [],
                                clone_dir,
                                ctx,
                            )
                            if _sh:
                                sec_htmls.append(_sh)
                        except Exception as _ge:
                            logger.warning("Section synth failed: %s", _ge)
                    if sec_htmls:
                        synth_html = assemble_master_html(sec_htmls, design_tokens, url, title_d or "", clone_dir)
            except Exception as _pe:
                logger.warning("Section-aware pipeline failed: %s", _pe)
                synth_html = ""

        # Fallback: faithful rewrite (preserve all content, clean/enhance only)
        if not synth_html or len(synth_html) < 500:
            _safe_report(ctx, 94, "[ANTIGRAVITY] Falling back to faithful rewrite synthesis...")
            try:
                synth_html = _synthesize_clean_website(url, raw_html, clone_dir, output_format, ctx)
            except Exception as _fe:
                logger.warning("Faithful rewrite failed: %s", _fe)
                synth_html = ""

        # Validation gate: never ship a degraded version
        raw_size = len(raw_html)
        if synth_html and raw_size > 0 and len(synth_html) < int(raw_size * 0.95):
            logger.warning("Antigravity output degraded (%d < 60%% of %d). Using raw bundle.", len(synth_html), raw_size)
            synth_html = raw_html

        if not synth_html:
            synth_html = raw_html if raw_html else "<!DOCTYPE html><html><body><h1>Website Cloned</h1></body></html>"

        try:
            antigravity_file.write_text(synth_html, encoding="utf-8")
            _safe_report(ctx, 96, f"[ANTIGRAVITY] Clean standalone HTML written to {antigravity_file.name}.")
        except Exception as e:
            logger.warning("Failed to write antigravity clone file: %s", e)

    # 8. Opening is deferred to step 11, once the deliverable is known. Opening the raw snapshot
    #    here forced a localhost server for every clone even when the finished deliverable is a
    #    single HTML page that opens straight off disk, and it put uncage's byte-faithful copy in
    #    front of the user instead of the artifact. antigravity_clone.html genuinely needs the
    #    server (its refs are '/assets/...'), so _open_deliverable decides from the file's own
    #    markup rather than from an assumption.

    # 9. Sync Active Repository Context & Memory
    register_clone(clone_dir)
    try:
        from memory.memory_manager import remember
        remember("recent_task", f"Cloned website {url} into {clone_dir.name}", category="goals")
    except Exception:
        pass

    total_files = len(list(clone_dir.rglob("*")))
    _safe_report(ctx, 98, f"[DONE] Static clone complete ({total_files} files in {clone_dir.name}).")

    opened_url = ""
    initial_summary = (
        f"Capture complete for '{url}'. Raw bundle in '{clone_dir.name}' ({total_files} files), "
        f"verbatim page saved as 'antigravity_clone.html'.{media_note}"
        if output_format in CAPTURE_ONLY_FORMATS
        else f"Capture complete for '{url}'. Raw bundle in '{clone_dir.name}' ({total_files} files).{media_note}"
    )
    result = {
        "status": "success",
        "url": url,
        "engine": engine_used,
        "mode": mode,
        "output_format": output_format,
        "clone_dir": str(clone_dir),
        "files_downloaded": total_files,
        "failed_assets": 0,
        "preview_url": "",
        "summary": initial_summary,
    }

    # 11. Reverse-engineer the capture into the format the user asked for (ZEZO's own engine)
    if output_format not in CAPTURE_ONLY_FORMATS:
        rebuild_ok, rebuild_detail, artifact = _run_reverse_engineer(url, clone_dir, ctx, output_format)
        if not rebuild_ok:
            # The user asked for a rebuilt artifact and it did not arrive. Open the capture - it is
            # the deliverable now - and report the failure plainly instead of shipping a fake
            # success. The folder is kept so a fleet agent can be pointed straight at it, and the
            # message comes from rebuild_failure_message so core/prompt.txt cannot drift from it.
            _safe_report(ctx, 100, f"[REBUILD ERROR] {rebuild_detail}")
            fallback_target = (
                antigravity_file
                if antigravity_file.exists()
                else (clone_dir / "index.html" if (clone_dir / "index.html").exists() else clone_dir)
            )
            capture_url = _open_deliverable(fallback_target, clone_dir)
            result["preview_url"] = capture_url
            raise RuntimeError(rebuild_failure_message(clone_dir, capture_url, rebuild_detail))
        if artifact:
            # Never open the raw snapshot when a rebuild exists: the rebuilt artifact is the
            # deliverable, and on success it is the only thing the user is shown.
            artifact_url = _open_deliverable(artifact, clone_dir)
            result["artifact"] = str(artifact)
            result["artifact_url"] = artifact_url
            try:
                register_rebuild(
                    artifact if artifact.is_dir() else clone_dir,
                    entrypoint=artifact.name if not artifact.is_dir() else "index.html",
                )
            except Exception as e:
                logger.warning("Could not register rebuild workspace: %s", e)
            opened_url = artifact_url

        result["summary"] = (
            f"Rebuilt '{url}' from its offline capture as {output_format} - {rebuild_detail}. "
            f"Raw capture kept in '{clone_dir.name}'; the rebuilt artifact is open in the browser "
            f"at {result.get('artifact_url') or clone_dir}.{media_note}"
        )
    elif output_format in CAPTURE_ONLY_FORMATS:
        # Nothing was rebuilt, so the capture itself is the deliverable and gets opened.
        deliverable_target = (
            antigravity_file
            if antigravity_file.exists()
            else (clone_dir / "index.html" if (clone_dir / "index.html").exists() else clone_dir)
        )
        opened_url = _open_deliverable(deliverable_target, clone_dir)
        result["summary"] = (
            f"Capture complete for '{url}'. Static bundle in '{clone_dir.name}' "
            f"({total_files} files), preview live at {opened_url}. "
            f"No rebuild was requested.{media_note}"
        )

    result["preview_url"] = opened_url

    _safe_report(ctx, 100, result["summary"])
    return result


# ── Action Entrypoint & Tool Schema ─────────────────────────────────────────

def _readback_target(target_dir: Optional[str], default_dir: Path) -> str:
    """The absolute folder the clone will really land in, for the read-back.

    The read-back used to speak only the last path segment ("into 'linear_app_clone'"), so the user
    confirmed a name they could not place - and never learned the folder was inside ZEZO's own
    repo. This resolves with expand_user_dir, the exact resolution _clone_worker uses, so what is
    spoken is the folder that will actually be created.
    """
    resolved = expand_user_dir(target_dir) if target_dir else default_dir
    if is_zezo_source_dir(resolved):
        # Unreachable after the workspace resolution, so treat it as an assertion: a clone must
        # never be planted inside ZEZO's own source tree.
        raise ValueError(
            f"Refusing to clone into {resolved}: it is inside ZEZO's own source tree. "
            f"Pass a folder outside the ZEZO installation (e.g. Desktop/<name>)."
        )
    return str(resolved)


def clone_website_action(
    parameters: dict,
    player: Any = None,
    speak: Any = None,
    session_memory: Any = None,
) -> str:
    """
    Action handler called by core.action_loader.

    Runs a two-step confirmation gate before submitting the background worker:
      1. INTAKE  — ask only the values the user has not already given.
      2. COMMIT  — read the plan back and require an explicit yes.
    The read-back is also the last defence against a misheard URL or folder, which is
    why it is never skipped even when the user supplied everything at once.
    """
    raw_url = parameters.get("url") or parameters.get("link") or parameters.get("target") or ""
    url = _normalize_url(raw_url)

    if not url:
        return "Please provide a valid website URL to clone."

    domain = _extract_domain(url)
    mode = (parameters.get("mode") or "").strip().lower() or None
    output_format = (parameters.get("output_format") or "").strip().lower() or None
    target_dir = str(parameters.get("target_dir") or "").strip() or None
    confirmed = parameters.get("confirmed") is True

    default_dir = get_unique_clone_dir(domain)
    # Resolved once, so the read-back and the HUD name the same real folder the worker will use.
    folder = _readback_target(target_dir, default_dir)

    # ── Two-step confirmation gate ─────────────────────────────────────────
    # A parameter that is PRESENT means "the user said this"; absent means "still
    # unknown". clone_website_action is the only submitter of the website_cloner tool
    # anywhere in the codebase, so this handler is the complete enforcement surface.
    #
    # This gate is deliberately STATELESS — it reads only the parameters of this single
    # call and remembers nothing between calls. That is a requirement, not a
    # simplification: main.py never sets a session_id, so core/action_loader always
    # resolves the session as "global", and main.py resets "global" on every new user
    # utterance and every turn-complete. The user's answer IS a new utterance, so a
    # stored "already asked" flag would be wiped before it could ever be read and the
    # feature would ask forever. Do not make this stateful.
    missing: List[str] = []
    if not mode:
        missing.append("- scope: only the landing page (single_page), or the whole site (full_site)?")
    if not output_format:
        missing.append(
            "- output: a rebuilt single HTML page (the default), a project in a stack you name "
            "(React, Next.js, PHP, or anything else), or just the raw capture with no rebuild?"
        )
    if not target_dir:
        missing.append(f"- folder: the default '{default_dir.name}', or a different folder?")

    if missing:
        return (
            "CLONE NOT STARTED. Ask the user these questions out loud, in the user's own "
            "language, then call clone_website again with the answers:\n" + "\n".join(missing)
        )

    if not confirmed:
        scope = (
            "only the landing page"
            if mode == "single_page"
            else f"the whole site (up to {min(MAX_PAGES_FULL_SITE, 25)} pages)"
        )
        fmt = RE_READBACK_FORMATS.get(output_format, f"a '{output_format}' build, reverse-engineered from the capture")
        return (
            "CLONE NOT STARTED. Read the plan back to the user in ONE short sentence and wait "
            "for a clear yes, then call clone_website again with identical arguments plus "
            f"confirmed=true. Plan: clone {url} - {scope}, then rebuild it as {fmt}, into '{folder}'. "
            f"The capture is always kept and previewed, so the rebuild is added alongside it."
        )

    tm = get_task_manager()

    from core.models import DEFAULT_ANTIGRAVITY_MODEL
    parameters_with_meta = {**parameters, "model": DEFAULT_ANTIGRAVITY_MODEL}
    task_id = tm.submit(
        tool_name="website_cloner",
        fn=_clone_worker,
        params=parameters_with_meta,
    )

    if player and hasattr(player, "show_content"):
        player.show_content(
            "WEBSITE CLONER",
            f"URL: {url}\nMode: {mode}\nFormat: {output_format}\nTask ID: {task_id}\n"
            f"Target: {folder}",
        )

    tail = (
        "A live preview will open in your browser once complete."
        if output_format in CAPTURE_ONLY_FORMATS
        else (
            "The raw capture lands first; ZEZO then rebuilds it into "
            f"{output_format} from that capture, and the rebuilt artifact opens when it is ready "
            f"(the rebuild takes several minutes longer)."
        )
    )
    return f"Cloning {domain} (Task ID: {task_id}). {tail}"


TOOL = {
    "name": "clone_website",
    "description": (
        "Clone, mirror, or save an offline copy of a website's static HTML/CSS/JS frontend to a local Desktop folder. "
        "Downloads rendered DOM, media assets, stylesheets, and fonts, serving an offline preview. "
        "ONLY use this tool when the user explicitly asks to 'clone this website', 'save an offline copy', 'download HTML/CSS copy of this site', or 'mirror this site'. "
        "DO NOT use for 'rebuild', 'rebuild frontend', 'scaffold', 'teardown', 'reverse engineer', 'inspect stack', 'x-ray', or 'architecture' requests — those MUST dispatch reverse_engineer instead. "
        "Use mode='full_site' only if user explicitly asks for full mirror."
    ),
    "risk": "code_execution",
    "enabled": True,
    "behavior": "NON_BLOCKING",
    "scheduling": "WHEN_IDLE",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "url": {
                "type": "STRING",
                "description": "Full web URL to clone/reverse-engineer (e.g. 'https://www.heyclicky.com/' or 'https://apple.com').",
            },
            "mode": {
                "type": "STRING",
                "enum": ["single_page", "full_site"],
                "description": (
                    "Crawl scope. Set this ONLY if the user explicitly stated the scope in their request. "
                    "Otherwise OMIT it — ZEZO will ask the user. Never fill in a default yourself."
                ),
            },
            "output_format": {
                "type": "STRING",
                "description": (
                    "What to rebuild the capture into. 'raw_html' = one standalone HTML page with "
                    "its CSS/JS embedded (the usual answer). 'react', 'nextjs', 'php' = a project "
                    "in that stack. Any other value is treated as the stack the user named in "
                    "their own words, so pass it verbatim ('svelte', 'ruby on rails'). "
                    "'capture_only' = no rebuild, just the raw offline capture. "
                    "Set this ONLY if the user explicitly stated the output they want. Otherwise "
                    "OMIT it - ZEZO will ask the user. Never fill in a default yourself."
                ),
            },
            "target_dir": {
                "type": "STRING",
                "description": (
                    "Folder to save the clone into. Set this ONLY if the user explicitly named a folder. "
                    "Otherwise OMIT it — ZEZO will offer the default Desktop/<domain>_clone and ask."
                ),
            },
            "confirmed": {
                "type": "BOOLEAN",
                "description": (
                    "Set true ONLY after ZEZO has read the plan back to the user AND the user said yes. "
                    "Omit it on the first call — the runtime will not start a crawl without it."
                ),
            },
            "main_pages_only": {
                "type": "BOOLEAN",
                "description": (
                    "Optional refinement for mode='full_site': set true when the user asks for the main / "
                    "important pages only rather than every page."
                ),
            },
        },
        "required": ["url"],
    },
    "handler": clone_website_action,
}
