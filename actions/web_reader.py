"""
actions/web_reader.py — High-Performance Anti-Bot Web Scraper and Reader for Zezo.

Uses Scrapling (Fetcher & StealthyFetcher) when installed to bypass Cloudflare,
anti-bot protections, and modern JavaScript paywalls. When Scrapling is not
available, it falls back to requests + BeautifulSoup so the tool always works.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional
from urllib.parse import urlparse

logger = logging.getLogger("zezo.web_reader")

# Scrapling is an optional anti-bot backend. When it is not installed (it is not
# a declared requirement), the reader must still work via plain HTTP + bs4.
try:
    import scrapling  # noqa: F401
    _HAS_SCRAPLING = True
except Exception:
    _HAS_SCRAPLING = False

# Reason the last plain-HTTP attempt failed, surfaced to the model/log so a
# failed read explains itself instead of a bare "Unable to read".
_last_http_error: str = ""

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# Scrapling's browser fetch defaults to a 30s navigation timeout and waits for
# network-idle. Sites that keep long-poll/analytics sockets open (notably
# reddit.com) never settle, so every attempt burned ~30s and then retried
# (observed repeatedly in the log bus), making a multi-source research task take
# minutes. Fail fast instead: the outer requests + BeautifulSoup path still runs.
_STEALTH_KWARGS = {"timeout": 15000, "network_idle": False, "retries": 1}


def _requests_fallback(clean_url: str) -> Optional[str]:
    """Plain-HTTP fallback used when Scrapling is unavailable or blocked."""
    global _last_http_error
    try:
        import requests
    except Exception as e:
        _last_http_error = f"requests not installed ({e})"
        logger.warning(f"HTTP fallback unavailable for {clean_url}: {e}")
        return None
    try:
        print(f"[WebReader] Falling back to requests + BeautifulSoup for {clean_url}...")
        _last_http_error = ""
        resp = requests.get(
            clean_url,
            headers={"User-Agent": _UA, "Accept-Language": "en-US,en;q=0.9"},
            timeout=20,
        )
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or resp.encoding
        return resp.text
    except Exception as e:
        _last_http_error = f"{type(e).__name__}: {e}"
        logger.warning(f"requests fallback failed for {clean_url}: {e}")
        return None


def _html_to_readable(html: str, fallback_title: str) -> tuple[str, str]:
    """Convert raw HTML into (title, clean text) with no external converter."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(
        ["script", "style", "noscript", "template", "svg", "form",
         "nav", "footer", "header", "aside", "iframe"]
    ):
        tag.decompose()
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    root = soup.find("main") or soup.find("article") or soup.body or soup
    # Keep block boundaries so prose does not collapse into one line, while
    # joining inline tags (links, <sup> citations) with spaces, not breaks.
    for block in root.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li",
                                "blockquote", "pre", "tr", "dd", "dt"]):
        block.insert_after("\n")
    text = root.get_text(" ", strip=False) if hasattr(root, "get_text") else ""
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]*\n[ \t]*", "\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return (title or fallback_title), text


def extract_web_content(url: str, max_chars: int = 8000, stealth: bool = False) -> str:
    """
    Fetch a URL using Scrapling and return clean, readable Markdown text.
    Automatically handles anti-bot challenges, Cloudflare, and fallbacks.
    """
    clean_url = (url or "").strip()
    if not clean_url:
        return "Please provide a valid web URL to read."

    if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
        clean_url = "https://" + clean_url

    parsed = urlparse(clean_url)
    if not parsed.netloc:
        return f"Invalid URL structure: {url}"

    page = None

    # 1. Fetch via Scrapling when available (optional anti-bot backend)
    if _HAS_SCRAPLING:
        from scrapling import Fetcher, StealthyFetcher

        def _stealth_fetch():
            """One StealthyFetcher attempt. Never re-raised, so a timeout here
            cannot trigger a second browser attempt through an outer handler."""
            try:
                print(f"[WebReader] Fetching {clean_url} via Scrapling StealthyFetcher...")
                return StealthyFetcher.fetch(clean_url, **_STEALTH_KWARGS)
            except Exception as e:
                logger.warning(f"StealthyFetcher failed for {clean_url}: {e}")
                return None

        if stealth:
            page = _stealth_fetch()

        if page is None:
            try:
                print(f"[WebReader] Fetching {clean_url} via Scrapling Fetcher...")
                page = Fetcher.get(clean_url, timeout=20)
            except Exception as e:
                logger.warning(f"Fetcher failed for {clean_url}: {e}")
                page = None

            if page is not None and page.status in (403, 429, 503):
                print(f"[WebReader] Status {page.status}. Retrying via StealthyFetcher...")
                page = _stealth_fetch()
    else:
        logger.info("Scrapling not installed — using requests + BeautifulSoup fallback for %s", clean_url)

    # 2. Extract title and clean Markdown from Scrapling, else plain HTTP
    page_title = parsed.netloc
    md_content = ""

    if page is not None:
        try:
            title_el = page.find("title")
            page_title = title_el.text.strip() if title_el and title_el.text else parsed.netloc

            if hasattr(page, "markdown") and callable(page.markdown):
                try:
                    md_content = page.markdown()
                except Exception:
                    pass

            if not md_content:
                md_content = page.get_all_text() if hasattr(page, "get_all_text") else (page.text or "")
        except Exception as e:
            logger.warning(f"Scrapling parse failed for {clean_url}: {e}")

    if not md_content:
        html = _requests_fallback(clean_url)
        if html:
            try:
                page_title, md_content = _html_to_readable(html, parsed.netloc)
            except Exception as e:
                logger.warning(f"HTML parse failed for {clean_url}: {e}")

    if not md_content:
        detail = _last_http_error or "no readable content returned"
        return f"[WebReader Error] Unable to read {clean_url}: {detail}"

    # Clean excess whitespace
    md_content = re.sub(r"\n{3,}", "\n\n", md_content).strip()

    if not md_content:
        return f"Retrieved page from {clean_url}, but no readable text was found."

    if len(md_content) > max_chars:
        md_content = md_content[:max_chars] + f"\n\n... [Content truncated at {max_chars} characters]"

    return f"# {page_title}\nSource: {clean_url}\n\n{md_content}"


def web_reader_action(parameters: dict, player=None, speak=None) -> str:
    """Action handler called by core.action_loader."""
    url = parameters.get("url") or parameters.get("link") or ""
    max_chars = int(parameters.get("max_chars") or 8000)
    stealth = bool(parameters.get("stealth", False))

    result = extract_web_content(url=url, max_chars=max_chars, stealth=stealth)

    if player and hasattr(player, "show_content") and result:
        player.show_content("WEB READER (SCRAPLING)", result[:2000])

    return result


# ── Action Discovery TOOL Schema ─────────────────────────────────────────────
TOOL = {
    "name": "web_read_page",
    "description": (
        "Read and extract clean markdown text from any web page URL, blog post, article, or documentation. "
        "Uses Scrapling to bypass anti-bot and Cloudflare protections when available, "
        "with a built-in requests + BeautifulSoup fallback."
    ),
    "risk": "read_only",
    "enabled": True,
    "behavior": "NON_BLOCKING",
    "scheduling": "WHEN_IDLE",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "url": {
                "type": "STRING",
                "description": "The target website or webpage URL to scrape and read.",
            },
            "stealth": {
                "type": "BOOLEAN",
                "description": "Set to true if the website is heavily protected by Cloudflare Turnstile or captchas.",
            },
            "max_chars": {
                "type": "INTEGER",
                "description": "Maximum number of characters to return. Defaults to 8000.",
            },
        },
        "required": ["url"],
    },
    "handler": web_reader_action,
}
