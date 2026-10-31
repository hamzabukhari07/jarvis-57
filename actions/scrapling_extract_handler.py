"""
actions/scrapling_extract_handler.py — Standalone Pre-Flight Action Handler for Scrapling DOM & Token Extraction.

Creator & Lead Architect: Hamza Bukhari

Dynamically imported and invoked by actions/run_skill.py when a skill frontmatter
declares `pre_flight_action: "scrapling_extract"`.
Extracts target website DOM snapshot, stylesheet, and token JSON before the coding agent is dispatched.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("zezo.scrapling_extract_handler")


def execute(url: Optional[str], output_dir: Path, params: Optional[dict[str, Any]] = None) -> bool:
    """Executes pre-flight Scrapling extraction into output_dir.

    Args:
        url: Target website URL.
        output_dir: Destination folder path.
        params: Optional task/skill parameters.

    Returns:
        True if extraction completed or files exist, False otherwise.
    """
    if not url:
        logger.warning("[scrapling_extract_handler] No URL provided for pre-flight extraction.")
        return False

    out_p = Path(output_dir).resolve()
    out_p.mkdir(parents=True, exist_ok=True)

    if (out_p / "site_dom.html").exists():
        logger.info("[scrapling_extract_handler] %s already contains site_dom.html, skipping.", out_p)
        return True

    try:
        from core.url_prefetch import prefetch_url_assets

        logger.info("[scrapling_extract_handler] Prefetching DOM & CSS tokens for %s -> %s", url, out_p)
        prefetch_url_assets(url, out_p)
        return True
    except Exception as exc:
        logger.error("[scrapling_extract_handler] Pre-flight extraction error: %s", exc)
        return False
