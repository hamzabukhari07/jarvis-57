"""
actions/design_extractor.py — Extract & Cache Studio Design System from HTML/CSS References

Extracts design tokens, colors, typography, radii, spacing cadence, and component
recipes from an HTML reference file into a standardized DESIGN.md specification
ready for coding agents (OpenCode / Kilo / Antigravity).

Features:
- Smart timestamp-aware caching in References/UI/design md/ (0ms instant recall)
- Dynamic reference discovery across References/UI/html/ and References/UI/design md/
- Automatic re-extraction when source HTML is modified
- Custom destination support (e.g. Desktop, active repo workspace)
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Optional

from core.design_extractor import extract_design_system_from_html
from core.repo_context import resolve


def _get_workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _get_ui_dirs() -> tuple[Path, Path, Path]:
    ws = _get_workspace_root()
    ref_ui = ws / "skills" / "hamza_taste" / "references"
    if not ref_ui.exists() and (ws / "References" / "UI").exists():
        ref_ui = ws / "References" / "UI"
        
    html_dir = ref_ui / "html"
    
    # Check for 'design md' with space, or fallback to 'design_md'
    md_dir = ref_ui / "design md"
    if not md_dir.exists() and (ref_ui / "design_md").exists():
        md_dir = ref_ui / "design_md"
    
    html_dir.mkdir(parents=True, exist_ok=True)
    md_dir.mkdir(parents=True, exist_ok=True)
    return ref_ui, html_dir, md_dir


def _norm_stem(name: str) -> str:
    """Normalize a name for fuzzy matching (remove dashes, underscores, spaces, design suffix)."""
    clean = re.sub(r"[-_\s]+", "", name.lower())
    clean = clean.removesuffix(".html").removesuffix(".htm").removesuffix(".md").removesuffix("design")
    return clean


def _find_reference_file(query: str) -> tuple[Optional[Path], Optional[Path]]:
    """
    Search References/UI for matching design files.
    Returns: (html_file, md_file)
    """
    _, html_dir, md_dir = _get_ui_dirs()
    norm_q = _norm_stem(query)
    if not norm_q:
        return None, None

    matched_html: Optional[Path] = None
    matched_md: Optional[Path] = None

    # 1. Search in design md/
    if md_dir.exists():
        for p in md_dir.iterdir():
            if p.is_file() and p.suffix.lower() == ".md":
                if norm_q == _norm_stem(p.name) or norm_q in _norm_stem(p.name):
                    matched_md = p
                    break

    # 2. Search in html/
    if html_dir.exists():
        for p in html_dir.iterdir():
            if p.is_file() and p.suffix.lower() in (".html", ".htm"):
                if norm_q == _norm_stem(p.name) or norm_q in _norm_stem(p.name):
                    matched_html = p
                    break

    # 3. If matched HTML, check if corresponding MD exists in md_dir even if not named exactly identical
    if matched_html and not matched_md and md_dir.exists():
        h_norm = _norm_stem(matched_html.name)
        for p in md_dir.iterdir():
            if p.is_file() and p.suffix.lower() == ".md" and _norm_stem(p.name) == h_norm:
                matched_md = p
                break

    return matched_html, matched_md


def _resolve_path(raw: str) -> Path:
    raw = str(raw or "").strip().strip('"').strip("'")
    if not raw:
        return Path.cwd()

    shortcuts: dict[str, Path] = {
        "desktop": Path.home() / "Desktop",
        "downloads": Path.home() / "Downloads",
        "documents": Path.home() / "Documents",
        "pictures": Path.home() / "Pictures",
        "home": Path.home(),
    }
    
    lower = raw.lower().replace("\\", "/")
    if lower in shortcuts:
        return shortcuts[lower]

    head, sep, rest = lower.partition("/")
    if sep and head in shortcuts:
        rest_orig = raw.replace("\\", "/").partition("/")[2].strip("/")
        return shortcuts[head] / rest_orig if rest_orig else shortcuts[head]

    p = Path(raw).expanduser()
    if p.is_absolute():
        return p

    # If it's a relative path starting with common folder names
    parts = [part.lower() for part in p.parts]
    for key in ("desktop", "downloads", "documents", "pictures"):
        if key in parts:
            idx = parts.index(key)
            subpath = Path(*p.parts[idx:])
            remapped = Path.home() / subpath
            return remapped

    return Path.cwd() / p


def list_available_designs() -> str:
    """List all available HTML templates and extracted DESIGN.md specifications."""
    _, html_dir, md_dir = _get_ui_dirs()
    
    html_files = sorted([f.name for f in html_dir.glob("*.html")]) if html_dir.exists() else []
    md_files = sorted([f.name for f in md_dir.glob("*.md")]) if md_dir.exists() else []

    lines = ["📁 [DESIGN SYSTEM REPOSITORY — References/UI/]:"]
    if md_files:
        lines.append("\n✨ Cached Design Specifications (design md/):")
        for m in md_files:
            lines.append(f"  • {m}")
    else:
        lines.append("\n✨ Cached Design Specifications: None yet")

    if html_files:
        lines.append("\n🌐 Raw HTML References (html/):")
        for h in html_files:
            lines.append(f"  • {h}")
    else:
        lines.append("\n🌐 Raw HTML References: None")

    return "\n".join(lines)


def extract_design_action(parameters: dict, player=None, speak=None, session_memory=None) -> str:
    """
    Extracts or retrieves cached design tokens from References/UI or a specified path.
    """
    action = (parameters.get("action") or "").strip().lower()
    if action == "list":
        return list_available_designs()

    target_file = (parameters.get("file_path") or parameters.get("path") or "").strip()
    force = bool(parameters.get("force", False))
    
    # Check session memory if file_path is omitted
    if not target_file and session_memory and isinstance(session_memory, dict):
        target_file = session_memory.get("last_loaded_file", "") or session_memory.get("active_file", "")

    _, html_dir, md_dir = _get_ui_dirs()

    matched_html: Optional[Path] = None
    matched_md: Optional[Path] = None

    # Handle Live Web URLs (e.g. https://qwenpaw.agentscope.io/)
    if target_file and target_file.lower().startswith(("http://", "https://")):
        import urllib.request
        from urllib.parse import urlparse

        parsed = urlparse(target_file)
        netloc = parsed.netloc or "website"
        domain_name = netloc.replace("www.", "").split(".")[0].replace("-", " ").replace("_", " ").title()
        if not domain_name:
            domain_name = "Webpage"

        # Determine output path
        dest = parameters.get("output_path")
        if dest:
            target_out_p = _resolve_path(dest)
            if target_out_p.is_dir() or (not target_out_p.suffix and not str(target_out_p).endswith(".md")):
                target_out_p = target_out_p / f"{domain_name.replace(' ', '-')}-DESIGN.md"
        else:
            target_out_p = md_dir / f"{domain_name.replace(' ', '-')}-DESIGN.md"

        try:
            req = urllib.request.Request(
                target_file,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    )
                },
            )
            with urllib.request.urlopen(req, timeout=12) as response:
                raw_html = response.read().decode("utf-8", errors="replace")

            target_out_p.parent.mkdir(parents=True, exist_ok=True)
            md_text = extract_design_system_from_html(
                raw_html,
                output_path=target_out_p,
                component_name=f"{domain_name} Web Design",
            )

            if session_memory and isinstance(session_memory, dict):
                session_memory["active_design_path"] = str(target_out_p)

            if player and hasattr(player, "show_content"):
                player.show_content(
                    f"DESIGN SYSTEM EXTRACTED — {netloc}",
                    f"Extracted live design system from {target_file}\nSaved to: {target_out_p}\n\n" + md_text[:800] + "...",
                )

            return (
                f"Design system successfully extracted from '{target_file}' and saved to {target_out_p.name} "
                f"at {target_out_p.as_posix()}. "
                "Coding agents (Antigravity/OpenCode) can now build matching interfaces with these tokens."
            )
        except Exception as e:
            return f"Failed to extract design system from URL '{target_file}': {e}"

    if target_file:
        # Check direct path first
        direct_p = _resolve_path(target_file)
        if not direct_p.exists():
            direct_p = Path(target_file)

        if direct_p.exists():
            if direct_p.suffix.lower() in (".html", ".htm"):
                matched_html = direct_p
                # Check if matching MD exists in md_dir
                h_norm = _norm_stem(matched_html.name)
                for p in md_dir.iterdir():
                    if p.is_file() and p.suffix.lower() == ".md" and _norm_stem(p.name) == h_norm:
                        matched_md = p
                        break
            elif direct_p.suffix.lower() == ".md":
                matched_md = direct_p
        else:
            # Try fuzzy search in References/UI
            matched_html, matched_md = _find_reference_file(target_file)

    if not matched_html and not matched_md:
        if not target_file:
            avail = list_available_designs()
            return f"Please provide a design name, local file path, or website URL.\n\n{avail}"
        return f"Could not find any design reference matching '{target_file}' in References/UI/."


    # Determine custom destination if requested
    dest = parameters.get("output_path")
    custom_out_p: Optional[Path] = None
    if dest:
        custom_out_p = _resolve_path(dest)
        if custom_out_p.is_dir() or (not custom_out_p.suffix and not str(custom_out_p).endswith(".md")):
            stem = (matched_html or matched_md).stem
            clean_stem = re.sub(r"[-_\s]+", "-", stem).title().removesuffix("-Design").removesuffix("-DESIGN")
            custom_out_p = custom_out_p / f"{clean_stem}-DESIGN.md"

    # CASE 1: MD exists and is fresh (Cache Hit)
    if matched_md and matched_md.exists() and not force:
        html_is_newer = False
        if matched_html and matched_html.exists():
            try:
                html_is_newer = matched_html.stat().st_mtime > matched_md.stat().st_mtime
            except Exception:
                html_is_newer = False

        if not html_is_newer:
            # Valid Cache Hit!
            try:
                md_text = matched_md.read_text(encoding="utf-8")
                active_path = matched_md

                if custom_out_p:
                    custom_out_p.parent.mkdir(parents=True, exist_ok=True)
                    custom_out_p.write_text(md_text, encoding="utf-8")
                    active_path = custom_out_p

                if session_memory and isinstance(session_memory, dict):
                    session_memory["active_design_path"] = str(active_path)

                if player and hasattr(player, "show_content"):
                    player.show_content(
                        f"DESIGN SYSTEM (CACHED) — {matched_md.name}",
                        f"Using cached specification from:\n{active_path}\n\n" + md_text[:800] + "...",
                    )

                dest_msg = f" Exported to {active_path.name}." if custom_out_p else ""
                return (
                    f"Design system specification for '{matched_md.stem}' is already up to date in References/UI/design md/. "
                    f"Loaded instantly (0ms).{dest_msg} Coding agents can build matching interfaces with these tokens."
                )
            except Exception as e:
                # If read failed, fall through to re-extraction
                pass

    # CASE 2: Re-extraction needed or first-time extraction
    if not matched_html or not matched_html.exists():
        if matched_md and matched_md.exists():
            # Only MD exists, read it
            md_text = matched_md.read_text(encoding="utf-8")
            if session_memory and isinstance(session_memory, dict):
                session_memory["active_design_path"] = str(matched_md)
            return f"Loaded design specification from {matched_md.name}."
        return f"HTML source file missing for extraction: {target_file}"

    # Default output path is in References/UI/design md/
    clean_stem = re.sub(r"[-_\s]+", "-", matched_html.stem).title()
    default_md_name = f"{clean_stem}-DESIGN.md"
    target_md_path = md_dir / default_md_name

    try:
        md_text = extract_design_system_from_html(matched_html, output_path=target_md_path)
        active_path = target_md_path

        # If custom path requested (e.g. Desktop), copy there as well
        if custom_out_p:
            custom_out_p.parent.mkdir(parents=True, exist_ok=True)
            custom_out_p.write_text(md_text, encoding="utf-8")
            active_path = custom_out_p

        # Store in session memory
        if session_memory and isinstance(session_memory, dict):
            session_memory["active_design_path"] = str(active_path)

        if player and hasattr(player, "show_content"):
            player.show_content(
                f"DESIGN SYSTEM EXTRACTED — {matched_html.name}",
                f"Generated specification saved to:\n{target_md_path}\n\n" + md_text[:800] + "...",
            )

        custom_note = f" and copied to {custom_out_p}" if custom_out_p else ""
        return (
            f"Design system successfully extracted from {matched_html.name} and saved to {target_md_path.name}{custom_note}. "
            "Coding agents can now build matching interfaces with these tokens."
        )
    except Exception as e:
        return f"Failed to extract design system from {matched_html.name}: {e}"


TOOL = {
    "name": "extract_design_system",
    "description": (
        "Extract or load a studio design system (colors, typography, glass elevation, component recipes, "
        "and anti-slop rules) from live website URLs (e.g. 'https://...'), local HTML templates, or cached specifications in References/UI/. "
        "Features smart 0ms caching: uses existing DESIGN.md from References/UI/design md/ if fresh, "
        "or extracts live from URL/HTML if new or modified. Set action='list' to view all available designs."
    ),
    "behavior": "BLOCKING",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "file_path": {
                "type": "STRING",
                "description": "Website URL (e.g. 'https://qwenpaw.agentscope.io/'), design name ('nexus', 'dub', 'aura frame'), or local path to HTML/MD file.",
            },
            "output_path": {
                "type": "STRING",
                "description": "Optional custom destination path (e.g. 'Desktop/DESIGN.md', 'active_repo/DESIGN.md'). Default is References/UI/design md/.",
            },
            "action": {
                "type": "STRING",
                "description": "Optional action. Use 'list' to view all available design references.",
            },
            "force": {
                "type": "BOOLEAN",
                "description": "Set to true to force re-extraction even if a cached DESIGN.md already exists.",
            },
        },
        "required": [],
    },

    "handler": extract_design_action,
}

