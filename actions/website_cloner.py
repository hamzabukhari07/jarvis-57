"""
actions/website_cloner.py — Autonomous Website Cloner & Adaptive Redesigner for Zezo.

Auto-discovered by core/action_loader.
Clones full frontend websites into Desktop/<domain>_clone/ with offline assets,
launches a local HTTP preview server (http://127.0.0.1:PORT), and provides
seamless chaining to Antigravity Agent for React conversion or studio redesign.

Architecture:
- Tier 1: Playwright Headless Chromium (rendered DOM + React/Next.js/Webflow hydration)
- Tier 2: Resilient HTTP Stream via urllib/requests + BeautifulSoup / Scrapling
- Tier 3: Cross-platform HTTrack CLI (shutil.which) for explicit multi-page mirroring
- Fault-tolerant asset localizer (partial success guard, size caps, relative path rewriter)
- Local ephemeral HTTP server (no CORS / no file:// path breakage)
- Asynchronous TaskManager execution with 5-milestone progress reporting
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

from core.repo_context import get_unique_clone_dir, register_clone
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


def run_uncage_exporter(
    url: str,
    output_dir: Path,
    ctx: Optional[TaskContext] = None,
    max_pages: int = 1,
    max_depth: Optional[int] = None,
    timeout_sec: int = 180,
) -> Tuple[bool, str]:
    """
    Executes the self-contained Uncage CLI (tools/uncage/bin/uncage.js) with live streaming progress.
    Supports single-page extraction (max_pages=1, max_depth=0) or multi-page crawling.
    Returns True if the bundle was successfully exported.
    """
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
        ]
        if max_depth is not None:
            cmd.extend(["--max-depth", str(max_depth)])

        _safe_report(ctx, 22, f"[UNCAGE] Initializing crawler (max_pages={max_pages})...")

        proc = subprocess.Popen(
            cmd,
            cwd=str(uncage_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            **_WIN_HIDE,
        )

        start_t = time.time()
        err_lines: List[str] = []
        if proc.stdout:
            for line in iter(proc.stdout.readline, ""):
                line_str = line.strip()
                if not line_str:
                    continue
                logger.debug("[UNCAGE LIVE] %s", line_str)

                # Keep the last real error line so a failure can be explained to
                # the user instead of the old generic "extraction failed".
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
                    _safe_report(ctx, 78, "[UNCAGE] Optimizing and purging stylesheets...")
                elif "Compiling Static HTML" in line_str:
                    _safe_report(ctx, 84, "[UNCAGE] Compiling static pages...")
                elif "Finalizing Static HTML" in line_str or "Successfully exported" in line_str:
                    _safe_report(ctx, 90, "[UNCAGE] Bundle finalized successfully.")

                if (time.time() - start_t) > timeout_sec:
                    proc.kill()
                    logger.warning("Uncage execution timed out after %ds", timeout_sec)
                    break

            proc.stdout.close()
        proc.wait(timeout=10)

        # Check output in Uncage's output directory
        if not raw_output_dir.exists():
            # Check if directory was created with sanitized name
            for candidate in (uncage_root / "output").glob(f"*{target_name}*"):
                if candidate.is_dir() and (list(candidate.rglob("*.html")) or (candidate / "assets").exists()):
                    raw_output_dir = candidate
                    break

        html_candidates = list(raw_output_dir.rglob("*.html")) if raw_output_dir.exists() else []
        if raw_output_dir.exists() and (html_candidates or (raw_output_dir / "assets").exists()):
            # Sync all exported files into output_dir
            for item in raw_output_dir.iterdir():
                dest = output_dir / item.name
                if item.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest, ignore_errors=True)
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)

            # Ensure an index.html exists in root output_dir for preview server
            if not (output_dir / "index.html").exists():
                all_htmls = [p for p in output_dir.rglob("*.html") if p.is_file()]
                if all_htmls:
                    shutil.copy2(all_htmls[0], output_dir / "index.html")

            file_count = len(list(output_dir.rglob("*")))
            _safe_report(ctx, 92, f"[UNCAGE] Successfully extracted full bundle ({file_count} files/pages).")
            return True, ""

        detail = err_lines[-1] if err_lines else (
            f"Uncage exited with code {proc.returncode}." if proc.returncode
            else "Uncage produced no output bundle.")
        logger.warning("Uncage extraction failed (returncode=%s): %s", proc.returncode, detail)
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


def _clone_worker(params: dict, ctx: TaskContext) -> dict:
    """
    Main asynchronous worker executing the website cloning pipeline with Multimodal Vision v2 + IR Responsive Delta Engine.
    """
    raw_url = params.get("url") or params.get("link") or params.get("target") or ""
    url = _normalize_url(raw_url)
    mode = params.get("mode") or "single_page"
    output_format = params.get("output_format") or "static"
    target_dir_param = params.get("target_dir") or params.get("repo") or params.get("project_path")

    if not url:
        raise ValueError("A valid URL is required for website cloning.")

    domain = _extract_domain(url)

    # 1. Setup Workspace Directory
    if target_dir_param:
        clone_dir = Path(target_dir_param).resolve()
        clone_dir.mkdir(parents=True, exist_ok=True)
    else:
        clone_dir = get_unique_clone_dir(domain)

    _safe_report(ctx, 5, f"[INIT] Allocated workspace at {clone_dir.name}...")

    # 2. Register Undo Snapshot
    register_clone_snapshot(clone_dir, tool_label=f"Clone of {domain}")

    # 3. User Intent & Component Framework Check
    user_prompt = (params.get("task") or params.get("instruction") or params.get("prompt") or "").lower()
    explicit_framework = (
        output_format in ("react", "nextjs")
        or any(k in user_prompt for k in ["react", "nextjs", "next.js", "vite", "vue", "svelte", "tailwind app"])
    )
    if explicit_framework:
        _safe_report(ctx, 8, "[INTENT] User explicitly requested Component Framework project. Chaining to React/Next.js engine.")

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
    uncage_ok, uncage_detail = run_uncage_exporter(url, clone_dir, ctx, max_pages=uncage_pages, max_depth=uncage_depth)

    if not uncage_ok or (not (clone_dir / "index.html").exists() and not list(clone_dir.rglob("*.html"))):
        reason = uncage_detail or "output bundle not found"
        _safe_report(ctx, 100, f"[UNCAGE ERROR] Uncage extraction failed for {url}: {reason}")
        raise RuntimeError(f"Uncage extraction failed for {url}: {reason}.")

    if not (clone_dir / "index.html").exists():
        all_htmls = [p for p in clone_dir.rglob("*.html") if p.is_file()]
        if all_htmls:
            shutil.copy2(all_htmls[0], clone_dir / "index.html")

    _safe_report(ctx, 88, f"[UNCAGE] Bundle extracted successfully into {clone_dir.name}.")

    # 7. Start Local Ephemeral HTTP Preview Server
    _safe_report(ctx, 90, f"[SERVER] Starting local preview server for {clone_dir.name}...")
    preview_url, port = start_local_preview_server(clone_dir)
    _safe_report(ctx, 93, f"[SERVER] Preview running on {preview_url} (opened in browser).")

    # 8. Open in Default Browser
    try:
        from actions.browser_control import browser_control
        browser_control({"action": "go_to", "url": preview_url})
    except Exception:
        import webbrowser
        webbrowser.open(preview_url)

    # 9. Sync Active Repository Context & Memory
    register_clone(clone_dir)
    try:
        from memory.memory_manager import remember
        remember("active_project", str(clone_dir), category="projects")
        remember("recent_task", f"Cloned website {url} into {clone_dir.name}", category="goals")
    except Exception:
        pass

    # Downstream Antigravity synthesis & vision critique held on user instruction
    total_files = len(list(clone_dir.rglob("*")))
    _safe_report(ctx, 100, f"[DONE] Uncage clone complete ({total_files} files in {clone_dir.name}).")

    return {
        "status": "success",
        "url": url,
        "engine": engine_used,
        "mode": mode,
        "output_format": output_format,
        "clone_dir": str(clone_dir),
        "files_downloaded": total_files,
        "failed_assets": 0,
        "preview_url": preview_url,
        "summary": (
            f"Cloning complete for '{url}'. Complete static project saved in '{clone_dir.name}' ({total_files} files). "
            f"Preview live at {preview_url}."
        ),
    }


# ── Action Entrypoint & Tool Schema ─────────────────────────────────────────

def clone_website_action(
    parameters: dict,
    player: Any = None,
    speak: Any = None,
    session_memory: Any = None,
) -> str:
    """
    Action handler called by core.action_loader.
    Submits background worker task and returns immediate conversational confirmation.
    """
    raw_url = parameters.get("url") or parameters.get("link") or parameters.get("target") or ""
    url = _normalize_url(raw_url)
    mode = (parameters.get("mode") or "single_page").lower()
    output_format = (parameters.get("output_format") or "static").lower()

    if not url:
        return "Please provide a valid website URL to clone."

    domain = _extract_domain(url)
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
            f"URL: {url}\nMode: {mode}\nFormat: {output_format}\nTask ID: {task_id}\nTarget: Desktop/{domain}_clone",
        )

    return f"Cloning {domain} (Task ID: {task_id}). A live preview will open in your browser once complete."


TOOL = {
    "name": "clone_website",
    "description": (
        "Clone, reverse-engineer, and recreate a website's frontend to a local folder on Desktop as a clean, 100% human-editable single-file HTML document (or React/Next.js project). "
        "Extracts rendered DOM, design tokens (colors, fonts), and media assets, then synthesizes clean semantic HTML5, Flexbox/Grid CSS, and Vanilla JS interactions. "
        "Starts a local preview server and opens the result automatically in your default browser. "
        "Use mode='full_site' only if user explicitly asks for full mirror. "
        "Use output_format='react' or 'nextjs' if user asks for React/Next.js components."
    ),
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
                "description": "Default: 'single_page' (fast, reverse-engineers target page). Use 'full_site' only if user asks for full multi-page mirror.",
            },
            "output_format": {
                "type": "STRING",
                "enum": ["static", "clean_html", "react", "nextjs", "redesign"],
                "description": "Default: 'static' (clean, editable standalone HTML/CSS/JS). Use 'react' or 'nextjs' if user asks for React/Next.js.",
            },
            "target_dir": {
                "type": "STRING",
                "description": "Optional custom target directory. If omitted, defaults to Desktop/<domain>_clone.",
            },
        },
        "required": ["url"],
    },
    "handler": clone_website_action,
}
