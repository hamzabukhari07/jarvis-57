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
_ZEZO_ROOT = Path(__file__).resolve().parent.parent


def is_zezo_source_dir(p: Path | str) -> bool:
    """True if p is the Zezo assistant's own codebase/installation folder, which must NEVER be used as a target user repo."""
    try:
        cand = Path(p).resolve()
        if cand == _ZEZO_ROOT or _ZEZO_ROOT in cand.parents:
            return True
        # Also check signature files of Zezo repo
        if (cand / "main.py").exists() and (cand / "actions").is_dir() and (cand / "core").is_dir():
            return True
    except Exception:
        pass
    return False


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
    """Persist a repo path as the last active one (never Zezo installation directory)."""
    if not path or is_zezo_source_dir(path):
        logger.debug("repo_context: ignoring request to remember Zezo root or empty path: %s", path)
        return
    resolved_path = str(Path(path).resolve())
    data = _load()
    data[_STORE_KEY] = resolved_path
    _save(data)
    logger.info("repo_context: remembered %s", resolved_path)
    try:
        from memory.memory_manager import remember
        remember("active_project", resolved_path, category="projects")
    except Exception:
        pass



def forget_repo(path: Optional[str] = None) -> None:
    """Clear or reset the remembered repo path."""
    data = _load()
    if not path or data.get(_STORE_KEY) == str(Path(path).resolve()):
        data.pop(_STORE_KEY, None)
        _save(data)
        logger.info("repo_context: cleared remembered repo")
        try:
            from memory.memory_manager import forget
            forget("active_project", category="projects")
        except Exception:
            pass


def get_last_repo() -> Optional[str]:
    repo = _load().get(_STORE_KEY)
    if repo and is_zezo_source_dir(repo):
        return None
    return repo


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
        if not root.exists() or is_zezo_source_dir(root):
            continue
        cand = root / raw
        if cand.exists() and not is_zezo_source_dir(cand):
            return cand.resolve()
        try:
            for child in root.iterdir():
                child_norm = re.sub(r"[\s_\-]+", "", child.name.lower())
                if target_norm and (target_norm == child_norm or target_norm in child_norm or child_norm in target_norm):
                    if not is_zezo_source_dir(child):
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

    source ∈ {"explicit", "memory", "cwd", "default", "none"}
    """
    # 1. explicit
    if explicit:
        p = _expand(explicit)
        if p and not is_zezo_source_dir(p):
            # Auto-create project folder if specified explicitly
            p.mkdir(parents=True, exist_ok=True)
            if require_git and not _is_git_repo(p):
                logger.info("repo_context: explicit %s is not a git repo", p)
            remember_repo(str(p))
            return p, "explicit"

    # 2. memory
    last = get_last_repo()
    if last and not is_zezo_source_dir(last):
        p = Path(last)
        if p.is_dir():
            return p, "memory"

    # 3. cwd (only if it's already a git repo and NOT Zezo source)
    cwd = Path.cwd()
    if cwd.is_dir() and not is_zezo_source_dir(cwd) and (not require_git or _is_git_repo(cwd)):
        return cwd, "cwd"

    # 4. Clean user project default fallback (Desktop/website)
    fallback = (Path.home() / "Desktop" / "website").resolve()
    fallback.mkdir(parents=True, exist_ok=True)
    remember_repo(str(fallback))
    return fallback, "default"


def get_unique_clone_dir(domain_or_name: str) -> Path:
    """Generate a collision-safe Desktop/<domain>_clone directory path (e.g. apple_clone, apple_clone_1)."""
    import re
    clean_name = re.sub(r"[^\w\-]", "_", (domain_or_name or "website").strip().lower())
    clean_name = re.sub(r"_+", "_", clean_name).strip("_") or "website"
    base_name = f"{clean_name}_clone"

    desktop = Path.home() / "Desktop"
    desktop.mkdir(parents=True, exist_ok=True)

    target = desktop / base_name
    if not target.exists():
        return target.resolve()

    counter = 1
    while True:
        cand = desktop / f"{base_name}_{counter}"
        if not cand.exists():
            return cand.resolve()
        counter += 1


def register_clone(clone_path: str | Path) -> Path:
    """Register and persist a newly cloned website directory as the active workspace."""
    p = Path(clone_path).resolve()
    p.mkdir(parents=True, exist_ok=True)
    remember_repo(str(p))
    logger.info("repo_context: registered cloned workspace at %s", p)
    return p

