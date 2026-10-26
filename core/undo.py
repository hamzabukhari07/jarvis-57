"""
core/undo.py — one shared undo stack for every action that changes state.

WHY THIS EXISTS
    A voice assistant misunderstands. When it does, "sorry" is not a remedy —
    the file is already in another folder and the brightness is already at 10%.
    Before this module the only recovery was to fix it by hand.

    The alternative — asking "are you sure?" before everything — is worse. Every
    confirmation is a round trip to the model and back, and an assistant that
    checks with you before turning the volume down is one you stop talking to.

    So: act immediately, remember how to reverse it, and let the user say
    "undo". Confirmation is then reserved for the handful of actions that
    genuinely cannot be reversed (see core/confirm.py).

HOW AN ACTION OPTS IN
    Actions do not have to know anything about this file's internals. They
    capture the "before" state and hand back a zero-argument callable:

        from core.undo import push_undo
        old = volume_get()
        volume_set(new)
        push_undo(f"volume → {new}%", lambda: volume_set(old))

    Only the action itself can know that the reverse of "move A to B" is "move
    B to A", which is why this cannot be fully centralised. What IS central is
    the stack, the ordering, the thread safety and the tool the model calls.

COST
    Pushing is a list append behind a lock: microseconds. Nothing in here runs
    until the user actually asks to undo something. This module cannot make the
    assistant slower.
"""

from __future__ import annotations

import os
import shutil
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

# How many reversible operations we keep. Ten is roughly "this conversation":
# far enough back to catch a mistake you noticed a few commands later, short
# enough that a closure holding a file's old contents cannot pile up in RAM.
MAX_DEPTH = 10


@dataclass
class _Entry:
    label:         str                              # human sentence, spoken back to the user
    undo:          Callable[[], str | dict]         # returns a short result string or dict
    at:            float = field(default_factory=time.monotonic)
    is_greenfield: bool = False
    created_files: list[str] = field(default_factory=list)
    repo_path:     str = ""
    tool:          str = ""

    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key)


class UndoResult(int):
    """Integer count of changed files that also supports dict-like access for backward compatibility."""
    def __new__(cls, count: int, **kwargs: Any):
        inst = super().__new__(cls, count)
        inst._meta = kwargs
        return inst

    def get(self, key: str, default: Any = None) -> Any:
        return self._meta.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self._meta[key]

    def __contains__(self, key: str) -> bool:
        return key in self._meta


_stack: list[Any] = []
_lock = threading.Lock()


def push_undo(
    label: str,
    undo_fn: Callable[[], str | dict],
    *,
    is_greenfield: bool = False,
    created_files: list[str] | None = None,
    repo_path: str = "",
    tool: str = "",
) -> None:
    """Record that `label` just happened and `undo_fn()` reverses it.

    Called from action handlers, which run in executor threads — hence the
    lock. Never raises: a broken undo registration must not take down the
    action that actually succeeded."""
    if not callable(undo_fn):
        return
    try:
        with _lock:
            _stack.append(_Entry(
                label=str(label)[:120],
                undo=undo_fn,
                is_greenfield=is_greenfield,
                created_files=created_files or [],
                repo_path=repo_path,
                tool=tool,
            ))
            # Drop the oldest rather than refusing the newest: the recent past
            # is what people ask to undo.
            while len(_stack) > MAX_DEPTH:
                _stack.pop(0)
    except Exception as e:                                  # pragma: no cover
        print(f"[Undo] push failed: {e}")


def can_undo() -> bool:
    with _lock:
        return bool(_stack)


def peek() -> str:
    """Label of the operation that `undo_last()` would reverse, or ''."""
    with _lock:
        if not _stack:
            return ""
        top = _stack[-1]
        return getattr(top, "label", "") or (top.get("label", "") if isinstance(top, dict) else "")


def history() -> list[str]:
    """Most recent first — used by the UI panel and the `undo` tool's list mode."""
    with _lock:
        return [
            getattr(e, "label", "") or (e.get("label", "") if isinstance(e, dict) else "")
            for e in reversed(_stack)
        ]


def undo_last() -> str:
    """Reverse the most recent reversible operation.

    The entry is popped *before* running so a failing undo cannot be retried
    forever against a world that has already moved on (the file the user is
    trying to restore may have been deleted by something else since)."""
    with _lock:
        entry = _stack.pop() if _stack else None

    if entry is None:
        return ("There is nothing to undo. I only track things I changed myself — "
                "files I moved or wrote, and settings I adjusted.")

    # Greenfield project creation rollback
    is_gf = bool(getattr(entry, "is_greenfield", False) or (isinstance(entry, dict) and entry.get("is_greenfield", False)))
    if is_gf:
        repo_str = getattr(entry, "repo_path", "") or (entry.get("repo_path", "") if isinstance(entry, dict) else "")
        root = Path(repo_str).resolve()
        created_files = getattr(entry, "created_files", []) or (entry.get("created_files", []) if isinstance(entry, dict) else [])
        reverted_count = 0
        for rel in created_files:
            try:
                target = root / rel
                if target.exists() and target.is_file():
                    target.unlink()
                    reverted_count += 1
            except Exception as e:
                print(f"[Undo] Could not remove created greenfield file {rel}: {e}")

        pruned = _prune_empty_dirs(root)
        prune_msg = " and pruned directory" if pruned else ""
        label = getattr(entry, "label", "") or (entry.get("label", "") if isinstance(entry, dict) else f"Greenfield project in {root.name}")
        return f"Undone: {label}. Removed {reverted_count} files{prune_msg}."

    try:
        undo_fn = getattr(entry, "undo", None) or (entry.get("undo") if isinstance(entry, dict) else None)
        detail = undo_fn() if callable(undo_fn) else ""
    except Exception as e:
        label = getattr(entry, "label", "") or (entry.get("label", "") if isinstance(entry, dict) else "")
        return f"Could not undo '{label}': {e}"

    label = getattr(entry, "label", "") or (entry.get("label", "") if isinstance(entry, dict) else "")
    return f"Undone: {label}." + (f" {detail}" if detail else "")


def apply_undo() -> dict[str, Any]:
    """Pop and execute the most recent undo operation.

    Returns a confirmation dictionary describing the result.
    If the popped entry has is_greenfield=True:
      - Cleanly removes the created files.
      - If the root directory was created by the tool and is now empty, prunes the directory.
      - Returns clear confirmation dict."""
    with _lock:
        entry = _stack.pop() if _stack else None

    if entry is None:
        return {
            "status": "empty",
            "message": "There is nothing to undo.",
        }

    is_gf = bool(getattr(entry, "is_greenfield", False) or (isinstance(entry, dict) and entry.get("is_greenfield", False)))
    if is_gf:
        repo_str = getattr(entry, "repo_path", "") or (entry.get("repo_path", "") if isinstance(entry, dict) else "")
        root = Path(repo_str).resolve()
        created_files = getattr(entry, "created_files", []) or (entry.get("created_files", []) if isinstance(entry, dict) else [])
        reverted_count = 0
        for rel in created_files:
            try:
                target = root / rel
                if target.exists() and target.is_file():
                    target.unlink()
                    reverted_count += 1
            except Exception as e:
                print(f"[Undo] Could not remove created greenfield file {rel}: {e}")

        pruned_root = _prune_empty_dirs(root)
        label = getattr(entry, "label", "") or (entry.get("label", "") if isinstance(entry, dict) else f"Greenfield project in {root.name}")

        return {
            "status": "success",
            "is_greenfield": True,
            "label": label,
            "reverted_files": reverted_count,
            "created_files": created_files,
            "repo_path": str(root),
            "root_pruned": pruned_root,
            "message": f"Successfully reverted greenfield project: removed {reverted_count} files" + (" and pruned directory." if pruned_root else "."),
        }

    try:
        undo_fn = getattr(entry, "undo", None) or (entry.get("undo") if isinstance(entry, dict) else None)
        detail = undo_fn() if callable(undo_fn) else ""
        label = getattr(entry, "label", "") or (entry.get("label", "") if isinstance(entry, dict) else "")
        return {
            "status": "success",
            "is_greenfield": False,
            "label": label,
            "detail": detail if isinstance(detail, str) else str(detail),
            "message": f"Undone: {label}." + (f" {detail}" if detail else ""),
        }
    except Exception as e:
        label = getattr(entry, "label", "") or (entry.get("label", "") if isinstance(entry, dict) else "")
        return {
            "status": "error",
            "is_greenfield": False,
            "label": label,
            "error": str(e),
            "message": f"Could not undo '{label}': {e}",
        }


def clear() -> None:
    """Forget the stack. Called when the app shuts down so closures holding old
    file contents do not outlive the session."""
    with _lock:
        _stack.clear()


# ── Repo Level Undo for Coding Agents (OpenCode / Kilo / Antigravity) ─────────

IGNORED_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__",
    ".next", "dist", "build", ".pytest_cache", ".idea", ".vscode",
    "target", "vendor", ".antigravity"
}
MAX_FILE_SIZE = 2_000_000  # 2MB per file snapshot


def _prune_empty_dirs(root: Path) -> bool:
    """Removes empty subdirectories inside root, and root itself if empty.
    Returns True if root itself was pruned, False otherwise."""
    if not root.exists() or not root.is_dir():
        return False
    try:
        # Walk bottom-up to delete leaf empty directories first
        for dirpath, dirnames, filenames in os.walk(root, topdown=False):
            p = Path(dirpath)
            if p.resolve() != root.resolve():
                try:
                    if not any(p.iterdir()):
                        p.rmdir()
                except Exception:
                    pass
        if root.exists() and not any(root.iterdir()):
            root.rmdir()
            return True
    except Exception as e:
        print(f"[Undo] _prune_empty_dirs error on {root}: {e}")
    return False


def capture_repo_snapshot(repo_path: str | Path) -> dict[str, bytes]:
    """Snapshots all relative file paths and their byte contents in a repository."""
    root = Path(repo_path).resolve()
    if not root.exists() or not root.is_dir():
        return {}

    snapshot: dict[str, bytes] = {}
    total_bytes = 0
    max_total_bytes = 25_000_000  # 25MB total cap

    try:
        for p in root.rglob("*"):
            if p.is_dir():
                continue
            try:
                rel_parts = p.relative_to(root).parts
                if any(part in IGNORED_DIRS or part.startswith(".git") for part in rel_parts):
                    continue
                if p.is_file() and p.stat().st_size <= MAX_FILE_SIZE:
                    content = p.read_bytes()
                    if total_bytes + len(content) > max_total_bytes:
                        break
                    rel_str = str(p.relative_to(root).as_posix())
                    snapshot[rel_str] = content
                    total_bytes += len(content)
            except Exception:
                continue
    except Exception as e:
        print(f"[Undo] capture_repo_snapshot error: {e}")

    return snapshot


def register_repo_undo(repo_path: str | Path, snapshot: dict[str, bytes], tool_label: str = "Coding agent") -> int:
    """Compares current repo state with snapshot and registers an undo callback if files changed.
    Returns the number of changed files detected."""
    root = Path(repo_path).resolve()
    if not root.exists() or not root.is_dir():
        return 0

    current_snapshot = capture_repo_snapshot(root)

    # Greenfield website / project build: initial snapshot was empty ({})
    if not snapshot:
        created_files = list(current_snapshot.keys())
        if not created_files:
            return 0

        def _undo_greenfield() -> str:
            reverted_count = 0
            for rel in created_files:
                try:
                    target = root / rel
                    if target.exists() and target.is_file():
                        target.unlink()
                        reverted_count += 1
                except Exception as e:
                    print(f"[Undo] Could not remove created greenfield file {rel}: {e}")

            pruned = _prune_empty_dirs(root)
            prune_msg = " and pruned directory" if pruned else ""
            return f"Removed {reverted_count} files{prune_msg}."

        label = f"{tool_label} created {root.name}"
        push_undo(
            label=label,
            undo_fn=_undo_greenfield,
            is_greenfield=True,
            created_files=created_files,
            repo_path=str(root),
            tool=tool_label,
        )
        return UndoResult(
            len(created_files),
            is_greenfield=True,
            created_files=created_files,
            repo_path=str(root),
            tool=tool_label,
        )

    created = [rel for rel in current_snapshot if rel not in snapshot]
    deleted = [rel for rel in snapshot if rel not in current_snapshot]
    modified = [rel for rel in current_snapshot if rel in snapshot and current_snapshot[rel] != snapshot[rel]]

    total_changed = len(created) + len(deleted) + len(modified)
    if total_changed == 0:
        return 0

    def _undo_repo() -> str:
        reverted_count = 0
        for rel in created:
            try:
                target = root / rel
                if target.exists():
                    target.unlink()
                    reverted_count += 1
            except Exception as e:
                print(f"[Undo] Could not remove created file {rel}: {e}")

        for rel in deleted:
            try:
                target = root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(snapshot[rel])
                reverted_count += 1
            except Exception as e:
                print(f"[Undo] Could not restore deleted file {rel}: {e}")

        for rel in modified:
            try:
                target = root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(snapshot[rel])
                reverted_count += 1
            except Exception as e:
                print(f"[Undo] Could not restore modified file {rel}: {e}")

        return f"Reverted {reverted_count} files."

    label = f"{tool_label} changes in {root.name}"
    push_undo(
        label=label,
        undo_fn=_undo_repo,
        is_greenfield=False,
        created_files=created,
        repo_path=str(root),
        tool=tool_label,
    )
    return UndoResult(
        total_changed,
        is_greenfield=False,
        created_files=created,
        repo_path=str(root),
        tool=tool_label,
    )


def register_clone_snapshot(clone_dir: str | Path, tool_label: str = "Website clone") -> None:
    """Register an undo handler for newly cloned website directories."""
    root = Path(clone_dir).resolve()

    def _undo_clone() -> str:
        if root.exists() and root.is_dir():
            try:
                shutil.rmtree(root)
                return f"Removed cloned directory {root.name}."
            except Exception as e:
                return f"Could not remove {root.name}: {e}"
        return f"{root.name} already removed."

    label = f"{tool_label} in {root.name}"
    push_undo(label, _undo_clone)
