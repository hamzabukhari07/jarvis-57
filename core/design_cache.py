"""
Design Cache Architecture (PHASE 4.2)
=====================================
Persistent, deterministic cache for extracted design tokens (DESIGN.md) and
lean interactive master templates (master-template.html).

Cache hit delivers artifacts in < 5ms without re-extraction.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import NamedTuple, Optional, Tuple

logger = logging.getLogger("zezo.design_cache")

_EXTRACTOR_VERSION = "v2"  # Bump this whenever design_extractor.py logic changes
EXTRACTOR_VERSION = _EXTRACTOR_VERSION

_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
_EXTRACTED_CACHE_DIR = _WORKSPACE_ROOT / "skills" / "website_build" / "references" / "extracted_cache"


class DirectHtmlReferenceResult(NamedTuple):
    source_name: str
    source_type: str
    raw_html: str
    full_raw_html: str
    source_path: Optional[Path]


def _sanitize_html_for_prompt(raw_html: str, max_chars: int = 50000) -> str:
    """Strip bulky base64 data URIs while preserving all CSS styles, animations, and layouts."""
    if not raw_html:
        return ""
    cleaned = re.sub(
        r"data:image/[^;]+;base64,[A-Za-z0-9+/=]{100,}",
        'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100%" height="100%" fill="%23222"/></svg>',
        raw_html,
    )
    cleaned = re.sub(r'd="[A-Za-z0-9\s,\.\-]{1000,}"', 'd="M0 0h24v24H0z"', cleaned)
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars] + "\n<!-- [Template content truncated for context budget] -->\n</body>\n</html>"
    return cleaned


def _load_direct_html_reference(
    html_file: Optional[Path | str],
) -> Optional[DirectHtmlReferenceResult]:
    """
    Returns DirectHtmlReferenceResult(source_name, source_type, raw_html, full_raw_html, source_path)
    Loads raw HTML directly with zero intermediate markdown extraction or MD files.
    """
    if not html_file:
        return None
    p = Path(html_file).resolve() if isinstance(html_file, (str, Path)) else None
    if p and p.exists() and p.is_file():
        try:
            full_raw_html = p.read_text(encoding="utf-8", errors="ignore")
            raw_html = _sanitize_html_for_prompt(full_raw_html)
            clean_stem = re.sub(r"[-_\s]+", "-", p.stem).title()
            return DirectHtmlReferenceResult(
                source_name=clean_stem,
                source_type="reference_raw_html",
                raw_html=raw_html,
                full_raw_html=full_raw_html,
                source_path=p,
            )
        except Exception as e:
            logger.warning("Failed reading raw html %s: %s", p, e)
    return None


load_direct_html_reference = _load_direct_html_reference


def get_or_create_reference_design_cache(
    reference_path: Path | str | None = None,
    reference_html_path: Path | str | None = None,
) -> Tuple[Path, Path]:
    """
    Returns (DESIGN.md path, master-template.html path). Cache hit < 5ms.
    Checks version file _extractor_version.txt == _EXTRACTOR_VERSION and cache freshness vs mtime.
    On MISS or STALE: extracts tokens with core.design_extractor, generates markdown with
    core.design_md_generator, and builds master template with core.master_template_builder.
    """
    target = reference_path if reference_path is not None else reference_html_path
    if not target:
        raise ValueError("reference_path must be provided")

    ref_path = Path(str(target).strip()).resolve()
    if not ref_path.exists() or not ref_path.is_file():
        raise FileNotFoundError(f"Reference HTML file not found at: {ref_path}")

    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ref_path.stem).strip("_").lower()
    cache_dir = _EXTRACTED_CACHE_DIR / slug
    version_file = cache_dir / "_extractor_version.txt"
    cached_md = cache_dir / "DESIGN.md"
    cached_mt = cache_dir / "master-template.html"

    ref_mtime = ref_path.stat().st_mtime
    version_ok = version_file.exists() and version_file.read_text(encoding="utf-8").strip() == _EXTRACTOR_VERSION
    files_ok = (
        cached_md.exists()
        and cached_md.stat().st_size > 0
        and cached_md.stat().st_mtime >= ref_mtime
        and cached_mt.exists()
        and cached_mt.stat().st_size > 0
        and cached_mt.stat().st_mtime >= ref_mtime
    )
    if version_ok and files_ok:
        logger.debug("Cache HIT: %s", cache_dir)
        return cached_md, cached_mt

    # Cache MISS or STALE
    logger.info(
        "Cache %s for '%s'. Re-extracting...",
        "STALE" if version_file.exists() else "MISS",
        ref_path.name,
    )
    cache_dir.mkdir(parents=True, exist_ok=True)
    raw_html = ref_path.read_text(encoding="utf-8", errors="ignore")

    from core.design_extractor import extract_design_tokens
    from core.design_md_generator import generate_design_md
    from core.master_template_builder import build_master_template

    tokens = extract_design_tokens(raw_html, ref_path.stem)
    md = generate_design_md(tokens, ref_path.stem)
    mt = build_master_template(raw_html, tokens, max_bytes=39900)

    cached_md.write_text(md, encoding="utf-8")
    cached_mt.write_text(mt, encoding="utf-8")
    version_file.write_text(_EXTRACTOR_VERSION, encoding="utf-8")
    return cached_md, cached_mt


def generate_blueprint_and_template(
    reference_html_path: Path | str,
    output_dir: Path | str,
) -> Tuple[Path, Path]:
    """
    Legacy name - external callers depend on it. Copies cache into output_dir.
    1. Reads reference HTML file or fetches from persistent cache (_EXTRACTED_CACHE_DIR).
    2. Provisions DESIGN.md and master-template.html into output_dir.
    3. Returns (dest_md, dest_mt).
    """
    ref_path = Path(str(reference_html_path).strip()).resolve()
    out_dir = Path(str(output_dir).rstrip()).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Retrieve from or store into permanent reference cache
    cached_md, cached_mt = get_or_create_reference_design_cache(ref_path)

    # Copy directly into output directory
    dest_md = out_dir / "DESIGN.md"
    dest_mt = out_dir / "master-template.html"

    dest_md.write_text(cached_md.read_text(encoding="utf-8"), encoding="utf-8")
    dest_mt.write_text(cached_mt.read_text(encoding="utf-8"), encoding="utf-8")

    md_size = dest_md.stat().st_size
    mt_size = dest_mt.stat().st_size
    logger.info(
        "Provisioned DESIGN.md (%d bytes) & master-template (%d bytes, < 40KB) at %s",
        md_size,
        mt_size,
        out_dir,
    )
    return dest_md, dest_mt


__all__ = [
    "_EXTRACTOR_VERSION",
    "EXTRACTOR_VERSION",
    "_EXTRACTED_CACHE_DIR",
    "DirectHtmlReferenceResult",
    "_sanitize_html_for_prompt",
    "_load_direct_html_reference",
    "load_direct_html_reference",
    "get_or_create_reference_design_cache",
    "generate_blueprint_and_template",
]
