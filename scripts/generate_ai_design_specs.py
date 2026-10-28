"""
scripts/generate_ai_design_specs.py — Batch Pre-warming utility for Reference DESIGN.md.

Executes design specification generation across all 20 active reference templates
using the active default code engine configured in ZEZO Frontend Settings, and caches
the results in skills/website_build/references/design_md/ and extracted_cache/.

Usage:
  python scripts/generate_ai_design_specs.py
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

# Set workspace root
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from core.code_engines import get_default_engine, resolve_binary
from core.design_extractor import extract_design_tokens
from core.ai_design_generator import generate_ai_design_md
from core.master_template_builder import build_master_template

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("zezo.prewarm")


def prewarm_all_references() -> None:
    engine_id = get_default_engine()
    bin_path = resolve_binary(engine_id)
    logger.info("Starting Reference Pre-warming with Engine: %s (%s)", engine_id, bin_path)

    ref_dir = REPO_ROOT / "skills" / "website_build" / "references"
    design_md_dir = ref_dir / "design_md"
    design_md_dir.mkdir(parents=True, exist_ok=True)
    cache_base = ref_dir / "extracted_cache"
    cache_base.mkdir(parents=True, exist_ok=True)

    templates = sorted(list(ref_dir.glob("*/*.html")))
    logger.info("Discovered %d reference templates across sequential folders.", len(templates))

    success_count = 0
    for idx, tmpl in enumerate(templates, 1):
        slug = tmpl.stem.lower().replace(" ", "-")
        logger.info("[%d/%d] Processing %s/%s (slug: %s)...", idx, len(templates), tmpl.parent.name, tmpl.name, slug)

        raw_html = tmpl.read_text(encoding="utf-8")
        tokens = extract_design_tokens(raw_html)

        # 1. Generate & Cache DESIGN.md
        target_md = design_md_dir / f"{slug}.md"
        cached_folder = cache_base / slug
        cached_folder.mkdir(parents=True, exist_ok=True)
        cached_md = cached_folder / "DESIGN.md"

        t0 = time.perf_counter()
        md_text = generate_ai_design_md(raw_html, tokens, name=slug, output_path=cached_md)
        target_md.write_text(md_text, encoding="utf-8")

        # 2. Generate & Cache master-template.html
        cached_mt = cached_folder / "master-template.html"
        mt_html = build_master_template(raw_html, tokens)
        cached_mt.write_text(mt_html, encoding="utf-8")

        dt = time.perf_counter() - t0
        logger.info(
            "  -> Completed in %.2fs: DESIGN.md=%.1f KB, master-template=%.1f KB",
            dt,
            len(md_text.encode("utf-8")) / 1024,
            len(mt_html.encode("utf-8")) / 1024,
        )
        success_count += 1

    logger.info("Successfully pre-warmed %d/%d reference templates!", success_count, len(templates))


if __name__ == "__main__":
    prewarm_all_references()
