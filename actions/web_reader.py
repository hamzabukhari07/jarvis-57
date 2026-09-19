"""
actions/web_reader.py — High-Performance Anti-Bot Web Scraper and Reader for Zezo.

Powered by Scrapling (Fetcher & StealthyFetcher) with Markdown extraction.
Bypasses Cloudflare, anti-bot protections, and modern JavaScript paywalls.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional
from urllib.parse import urlparse

logger = logging.getLogger("zezo.web_reader")


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

    # 1. Fetch via StealthyFetcher if stealth requested, or Fetcher first
    if stealth:
        try:
            print(f"[WebReader] Fetching {clean_url} via Scrapling StealthyFetcher (Stealth mode)...")
            from scrapling import StealthyFetcher
            page = StealthyFetcher.fetch(clean_url, timeout=30000)
        except Exception as e:
            logger.warning(f"StealthyFetcher failed for {clean_url}: {e}")
    
    if page is None:
        try:
            print(f"[WebReader] Fetching {clean_url} via Scrapling Fetcher...")
            from scrapling import Fetcher
            page = Fetcher.get(clean_url, timeout=20)
            
            if page.status in (403, 429, 503):
                print(f"[WebReader] Status {page.status}. Retrying via StealthyFetcher...")
                from scrapling import StealthyFetcher
                page = StealthyFetcher.fetch(clean_url, timeout=30000)
        except Exception as e:
            logger.warning(f"Fetcher failed for {clean_url}: {e}, trying StealthyFetcher...")
            try:
                from scrapling import StealthyFetcher
                page = StealthyFetcher.fetch(clean_url, timeout=30000)
            except Exception as e2:
                return f"[WebReader Error] Unable to read {clean_url}: {e2}"

    if page is None:
        return f"[WebReader Error] Could not retrieve content from {clean_url}."

    # 2. Extract title and clean Markdown
    try:
        title_el = page.find("title")
        page_title = title_el.text.strip() if title_el and title_el.text else parsed.netloc

        md_content = ""
        if hasattr(page, "markdown") and callable(page.markdown):
            try:
                md_content = page.markdown()
            except Exception:
                pass

        if not md_content:
            md_content = page.get_all_text() if hasattr(page, "get_all_text") else (page.text or "")

        # Clean excess whitespace
        md_content = re.sub(r"\n{3,}", "\n\n", md_content).strip()

        if not md_content:
            return f"Retrieved page from {clean_url}, but no readable text was found."

        if len(md_content) > max_chars:
            md_content = md_content[:max_chars] + f"\n\n... [Content truncated at {max_chars} characters]"

        return f"# {page_title}\nSource: {clean_url}\n\n{md_content}"

    except Exception as e:
        return f"[WebReader Error] Failed to parse content from {clean_url}: {e}"


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
        "Powered by Scrapling to bypass anti-bot and Cloudflare protections without getting blocked."
    ),
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
