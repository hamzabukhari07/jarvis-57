"""
core/url_prefetch.py — High-speed pre-flight extraction module for live URLs.

Creator & Lead Architect: Hamza Bukhari
Project: ZEZO (Autonomous Desktop AI Operating System v2)

Fetches DOM, stylesheets, and CSS tokens from a target URL with sub-second
concurrency and robust fallbacks.
"""

from __future__ import annotations

import concurrent.futures
import json
import logging
from pathlib import Path
import re
from typing import Any, Optional
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger("zezo.url_prefetch")

# Check scrapling availability
try:
    from scrapling import Fetcher, StealthyFetcher
    _HAS_SCRAPLING = True
except ImportError:
    try:
        from scrapling import Fetcher
        StealthyFetcher = None
        _HAS_SCRAPLING = True
    except ImportError:
        Fetcher = None
        StealthyFetcher = None
        _HAS_SCRAPLING = False


def _fetch_url_text(url: str, timeout: float = 3.0) -> str:
    """Fetch text content from a URL using Scrapling Fetcher with urllib fallback."""
    if _HAS_SCRAPLING and Fetcher is not None:
        try:
            res = Fetcher.get(url, timeout=timeout)
            if hasattr(res, "body") and res.body:
                return res.body.decode("utf-8", errors="replace")
            if hasattr(res, "html_content") and res.html_content:
                return str(res.html_content)
            if hasattr(res, "text") and res.text:
                return str(res.text)
        except Exception as exc:
            logger.debug("[url_prefetch] Scrapling Fetcher error for %s: %s", url, exc)

    # Fallback to urllib.request
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/css,*/*;q=0.8",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
            return raw.decode("utf-8", errors="replace")
    except Exception as exc:
        logger.debug("[url_prefetch] urllib fallback error for %s: %s", url, exc)
        return ""


def _extract_css_urls(html: str, base_url: str) -> list[str]:
    """Parse <link rel='stylesheet'> hrefs and resolve them to absolute URLs."""
    urls: list[str] = []
    link_tags = re.findall(r'<link\b[^>]*>', html, flags=re.IGNORECASE)
    for tag in link_tags:
        rel_match = re.search(r'rel=["\']?([a-zA-Z0-9_\-\s]+)["\']?', tag, flags=re.IGNORECASE)
        if rel_match and "stylesheet" in rel_match.group(1).lower():
            href_match = re.search(r'href=["\']?([^"\'\s>]+)["\']?', tag, flags=re.IGNORECASE)
            if href_match:
                raw_href = href_match.group(1).strip("\"'")
                if raw_href and not raw_href.startswith("data:") and not raw_href.startswith("#"):
                    full_url = urllib.parse.urljoin(base_url, raw_href)
                    if full_url not in urls:
                        urls.append(full_url)
    return urls


def _extract_inline_styles(html: str) -> list[str]:
    """Extract content of inline <style> blocks from HTML."""
    return [
        m.strip()
        for m in re.findall(r'<style\b[^>]*>(.*?)</style>', html, flags=re.DOTALL | re.IGNORECASE)
        if m.strip()
    ]


def _extract_css_tokens(css_text: str) -> dict[str, str]:
    """Extract CSS variables / tokens defined inside :root { ... } blocks."""
    tokens: dict[str, str] = {}
    if not css_text:
        return tokens

    root_blocks = re.findall(r':root[^{]*\{([^}]+)\}', css_text, flags=re.DOTALL | re.IGNORECASE)
    for block in root_blocks:
        clean_block = re.sub(r'/\*.*?\*/', '', block, flags=re.DOTALL)
        for m in re.finditer(r'(--[a-zA-Z0-9_\-]+)\s*:\s*([^;]+?)(?:;|\n|$)', clean_block):
            prop = m.group(1).strip()
            val = m.group(2).strip()
            if prop and val:
                tokens[prop] = val

    return tokens


def prefetch_url_assets(url: str, target_dir: Path, ctx: Optional[Any] = None) -> dict[str, str]:
    """Pre-fetch DOM, stylesheets, and CSS tokens from a live URL into target_dir.

    Args:
        url: The website URL to inspect.
        target_dir: Directory where prefetched assets will be saved.
        ctx: Optional TaskContext or object with a .report(progress, message) method.

    Returns:
        Dictionary containing paths to prefetched assets:
        {"dom": str, "css": str, "tokens": str}
    """
    target_path = Path(target_dir)
    target_path.mkdir(parents=True, exist_ok=True)

    dom_file = target_path / "site_dom.html"
    css_file = target_path / "site_styles.css"
    tokens_file = target_path / "site_tokens.json"

    try:
        # 1. Fetch HTML DOM
        html_dom = _fetch_url_text(url, timeout=3.0)
        if not html_dom:
            html_dom = f"<!-- Failed to fetch live DOM for {url} -->\n<!DOCTYPE html><html><head></head><body></body></html>"
        dom_file.write_text(html_dom, encoding="utf-8", errors="replace")

        # 2. Extract and fetch stylesheets (limit to 5 primary CSS files)
        css_links = _extract_css_urls(html_dom, url)[:5]
        css_parts: list[str] = []

        if css_links:
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(5, len(css_links))) as executor:
                future_map = {executor.submit(_fetch_url_text, link, 2.0): link for link in css_links}
                try:
                    for future in concurrent.futures.as_completed(future_map, timeout=2.5):
                        link_url = future_map[future]
                        try:
                            content = future.result()
                            if content and content.strip():
                                css_parts.append(f"/* Source: {link_url} */\n{content.strip()}")
                        except Exception as e:
                            logger.debug("[url_prefetch] Failed to read CSS future for %s: %s", link_url, e)
                except concurrent.futures.TimeoutError:
                    logger.debug("[url_prefetch] Stylesheet batch fetch timed out; proceeding with partial CSS")

        # Extract inline styles
        inline_styles = _extract_inline_styles(html_dom)
        for idx, inline in enumerate(inline_styles, 1):
            css_parts.append(f"/* Inline style block #{idx} */\n{inline}")

        combined_css = "\n\n".join(css_parts) if css_parts else "/* No styles found */\n"
        css_file.write_text(combined_css, encoding="utf-8", errors="replace")

        # 3. Extract CSS variables / tokens from :root { ... }
        tokens = _extract_css_tokens(combined_css)
        tokens_file.write_text(json.dumps(tokens, indent=2), encoding="utf-8")

        # 4. Report progress
        if ctx and hasattr(ctx, "report"):
            ctx.report(10, f"Pre-fetched site DOM and styles via Scrapling ({target_path.name})...")

    except Exception as exc:
        logger.warning("[url_prefetch] Pre-fetch encountered an error for %s: %s", url, exc)
        if not dom_file.exists():
            dom_file.write_text(f"<!-- Fallback DOM: {exc} -->\n<html><body></body></html>", encoding="utf-8")
        if not css_file.exists():
            css_file.write_text("/* Fallback empty styles */\n", encoding="utf-8")
        if not tokens_file.exists():
            tokens_file.write_text("{}", encoding="utf-8")

    return {
        "dom": str(dom_file),
        "css": str(css_file),
        "tokens": str(tokens_file),
    }
