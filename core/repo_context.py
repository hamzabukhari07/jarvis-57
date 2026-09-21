"""
core/repo_context.py

Resolves which repository/project directory a coding task should run in.

3-tier resolution (in order):
  1. Explicit path from tool parameters (highest trust, auto-created if needed)
  2. Last remembered repo (persisted in memory/repo_context.json)
  3. Current working directory, if it's a git repo

If none of the three resolve, returns (None, "none") so the calling
tool can ask the user rather than guessing.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

_STORE_KEY = "last_active_repo"
_STORE_PATH = Path(__file__).resolve().parent.parent / "memory" / "repo_context.json"


# ── store ────────────────────────────────────────────────────────

def _load() -> dict:
    try:
        if _STORE_PATH.exists():
            return json.loads(_STORE_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("repo_context: read failed: %s", e)
    return {}


def _save(data: dict) -> None:
    try:
        _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _STORE_PATH.write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )
    except Exception as e:
        logger.warning("repo_context: write failed: %s", e)


def remember_repo(path: str) -> None:
    """Persist a repo path as the last active one."""
    resolved_path = str(Path(path).resolve())
    data = _load()
    data[_STORE_KEY] = resolved_path
    _save(data)
    logger.info("repo_context: remembered %s", path)
    try:
        from memory.memory_manager import remember
        remember("active_project", resolved_path, category="projects")
    except Exception:
        pass



def get_last_repo() -> Optional[str]:
    return _load().get(_STORE_KEY)


# ── resolution ───────────────────────────────────────────────────

def _is_git_repo(p: Path) -> bool:
    return (p / ".git").exists()


def _expand(raw: str) -> Optional[Path]:
    """Turn a possibly-relative user-typed path into an absolute one with fuzzy matching."""
    import re
    if not raw:
        return None
    raw = raw.strip().strip("\"'")
    norm = raw.replace("\\", "/")

    # Check if absolute path (e.g. C:/... or /home/...)
    p = Path(raw).expanduser()
    if p.is_absolute() and p.exists():
        return p.resolve()

    parts = [part for part in norm.split("/") if part]
    if not parts:
        return None

    first = parts[0].lower()
    # Common user folder shorthands
    if first in ("desktop", "downloads", "documents", "projects", "dev"):
        base = Path.home() / parts[0].capitalize()
        sub = "/".join(parts[1:]) if len(parts) > 1 else ""
        if not sub:
            return base.resolve()

        direct = base / sub
        if direct.exists():
            return direct.resolve()

        # Fuzzy match subfolder under base
        target_norm = re.sub(r"[\s_\-]+", "", sub.lower())
        if base.exists():
            try:
                for child in base.iterdir():
                    child_norm = re.sub(r"[\s_\-]+", "", child.name.lower())
                    if target_norm == child_norm or target_norm in child_norm or child_norm in target_norm:
                        return child.resolve()
            except Exception:
                pass
        return direct.resolve()

    # Check under common roots if subfolder exists (exact or fuzzy)
    target_norm = re.sub(r"[\s_\-]+", "", raw.lower())
    for root in (
        Path.home() / "Desktop",
        Path.home() / "Documents",
        Path.home() / "Projects",
        Path.home() / "dev",
        Path.cwd(),
    ):
        if not root.exists():
            continue
        cand = root / raw
        if cand.exists():
            return cand.resolve()
        try:
            for child in root.iterdir():
                child_norm = re.sub(r"[\s_\-]+", "", child.name.lower())
                if target_norm and (target_norm == child_norm or target_norm in child_norm or child_norm in target_norm):
                    return child.resolve()
        except Exception:
            pass

    # If it's a simple name like "coding" or "my_project", target Desktop/name
    return (Path.home() / "Desktop" / raw).resolve()



def resolve(
    explicit: Optional[str] = None,
    require_git: bool = False,
) -> Tuple[Optional[Path], str]:
    """
    Returns (path, source).

    source ∈ {"explicit", "memory", "cwd", "none"}
    """
    # 1. explicit
    if explicit:
        p = _expand(explicit)
        if p:
            # Auto-create project folder if specified explicitly
            p.mkdir(parents=True, exist_ok=True)
            if require_git and not _is_git_repo(p):
                logger.info("repo_context: explicit %s is not a git repo", p)
            remember_repo(str(p))
            return p, "explicit"

    # 2. memory
    last = get_last_repo()
    if last:
        p = Path(last)
        if p.is_dir():
            return p, "memory"

    # 3. cwd (only if it's already a git repo or explicitly active)
    cwd = Path.cwd()
    if cwd.is_dir() and (not require_git or _is_git_repo(cwd)):
        return cwd, "cwd"

    return None, "none"
