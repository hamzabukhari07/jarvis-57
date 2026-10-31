"""
actions/uncage_capture_handler.py — Standalone Pre-Flight Action Handler for Uncage Website Capture.

Creator & Lead Architect: Hamza Bukhari

Dynamically imported and invoked by actions/run_skill.py when a skill frontmatter
declares `pre_flight_action: "uncage_capture"`.
Captures target website assets into output_dir before the coding agent is dispatched.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("zezo.uncage_capture_handler")


def execute(url: Optional[str], output_dir: Path, params: Optional[dict[str, Any]] = None) -> bool:
    """Executes the pre-flight uncage website capture into output_dir.

    Args:
        url: Target website URL to clone.
        output_dir: Destination folder path.
        params: Optional user task or skill parameters.

    Returns:
        True if capture succeeded and assets exist on disk, False otherwise.
    """
    if not url:
        logger.warning("[uncage_capture_handler] No URL provided for pre-flight capture.")
        return False

    clean_url = url.strip()
    if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
        clean_url = "https://" + clean_url

    out_p = Path(output_dir).resolve()
    out_p.mkdir(parents=True, exist_ok=True)

    # If already cloned and verified, skip duplicate crawl
    if (out_p / "index.html").exists() and (out_p / "index.html").stat().st_size > 50:
        logger.info("[uncage_capture_handler] %s already contains valid index.html, skipping capture.", out_p)
        return True

    try:
        from actions.website_cloner import run_uncage_exporter

        task_ctx = (params or {}).get("task_ctx") if isinstance(params, dict) else None
        logger.info("[uncage_capture_handler] Starting pre-flight capture for %s -> %s", clean_url, out_p)
        ok, why = run_uncage_exporter(
            url=clean_url,
            output_dir=out_p,
            ctx=task_ctx,
            timeout_sec=120,
        )
        if ok and (out_p / "index.html").exists():
            logger.info("[uncage_capture_handler] Pre-flight capture succeeded for %s", clean_url)
            return True

        logger.warning("[uncage_capture_handler] Uncage export failed or index.html missing: %s", why)
        return False
    except Exception as exc:
        logger.error("[uncage_capture_handler] Pre-flight capture failed with exception: %s", exc)
        return False
