"""
core/path_jail.py - Defense-in-Depth Path Security Jail for ZEZO Custom Agents.

Enforces workspace boundary containment for custom agent file operations,
protecting against path traversal, symlink spoofing, NTFS junction escapes,
and 8.3 short-name bypasses on Windows.

Author: Hamza Bukhari
"""

import os
from pathlib import Path


class SecurityAccessDenied(PermissionError):
    """Raised when a file operation targets a path outside the authorized workspace jail."""
    pass


def secure_resolve_path(
    target_path: str | Path,
    workspace_root: str | Path,
    allow_nonexistent: bool = False,
) -> Path:
    """
    Defense-in-depth Windows path resolution enforcing strict workspace containment.

    Protections provided:
      1. Workspace validation: Workspace root must exist and canonicalize cleanly.
      2. Reparse point resolution: Resolves all symlinks, NTFS junctions, and mount points
         to their canonical target on disk using os.path.realpath().
      3. NTFS case normalization: Uses os.path.normcase() to prevent casing bypasses.
      4. Containment-first validation: Verifies boundary containment BEFORE checking file
         existence to prevent external file-existence oracle leakage.
      5. Strict boundary containment: Verifies that the resolved canonical target path
         is equal to or a subpath of the canonical workspace root.
      6. Non-existent file safety (writes): Canonicalizes nearest existing ancestor directory
         to ensure file creation cannot occur through a junctioned parent.

    Documented Limitations (Residual Risks):
      - TOCTOU: A race condition exists between path resolution and actual file open()
        if another process modifies junctions concurrently. Userspace Python cannot
        eliminate this without OS-level sandboxing (Windows AppContainer / Linux seccomp).
      - Process Authority: Agents executing within the main Python process inherit the
        process security token. Architectural isolation via ToolExecutor and PathJail
        is enforced at the application layer.

    Args:
        target_path: The file or directory path requested by the agent/tool.
        workspace_root: The authorized workspace directory root.
        allow_nonexistent: Set True when validating paths for new file creation.

    Returns:
        Path: The canonical, verified absolute Path object guaranteed to reside within workspace_root.

    Raises:
        SecurityAccessDenied: If target_path or its parent escapes the workspace boundary.
        FileNotFoundError: If allow_nonexistent=False and the target file does not exist.
        ValueError: If target_path contains embedded null bytes.
    """
    if target_path is None:
        raise SecurityAccessDenied("Target path cannot be None.")

    target_str = str(target_path)
    if "\x00" in target_str:
        raise ValueError("Embedded null byte detected in path.")

    if not target_str.strip():
        raise SecurityAccessDenied("Target path cannot be empty.")

    # 1. Canonicalize workspace root (must exist and be an accessible directory)
    try:
        ws_real_str = os.path.realpath(str(workspace_root))
        ws_real = Path(ws_real_str).resolve(strict=True)
        if not ws_real.is_dir():
            raise SecurityAccessDenied(f"Workspace root is not a directory: {ws_real}")
    except Exception as e:
        if isinstance(e, SecurityAccessDenied):
            raise
        raise SecurityAccessDenied(f"Invalid workspace root '{workspace_root}': {e}")

    # 2. Convert target to absolute path relative to workspace root if relative
    raw_target = Path(target_str)
    if not raw_target.is_absolute():
        raw_target = ws_real / raw_target

    # 3. Canonicalize target by fully resolving symlinks, junctions, and traversals
    target_real_str = os.path.realpath(str(raw_target))
    target_real = Path(target_real_str)

    # 4. Containment check FIRST: prevents path escape AND prevents external file oracle leak
    ws_norm = os.path.normcase(str(ws_real))
    target_norm = os.path.normcase(str(target_real))

    if not (target_norm == ws_norm or target_norm.startswith(ws_norm + os.sep)):
        raise SecurityAccessDenied(
            f"Access Denied: Path escapes workspace boundary!\n"
            f"  Target (resolved):   {target_real}\n"
            f"  Workspace jail root: {ws_real}"
        )

    # 5. Check existence within the verified contained workspace
    if not target_real.exists():
        if not allow_nonexistent:
            raise FileNotFoundError(f"Path does not exist: {target_real}")

        # For non-existent files (e.g. file creation): find and verify nearest existing ancestor
        curr = raw_target.parent
        parts_below = [raw_target.name]
        while not curr.exists() and curr != curr.parent:
            parts_below.append(curr.name)
            curr = curr.parent

        if not curr.exists():
            raise SecurityAccessDenied(f"Ancestor directory does not exist: {raw_target}")

        curr_real = Path(os.path.realpath(str(curr)))
        curr_norm = os.path.normcase(str(curr_real))

        # Check ancestor containment
        if not (curr_norm == ws_norm or curr_norm.startswith(ws_norm + os.sep)):
            raise SecurityAccessDenied(
                f"Parent directory escapes workspace jail:\n"
                f"  Target: {raw_target}\n"
                f"  Resolved Ancestor: {curr_real}\n"
                f"  Workspace Root: {ws_real}"
            )

        # Reconstruct canonical path below the verified existing ancestor
        target_real = curr_real
        for part in reversed(parts_below):
            target_real = target_real / part

    return target_real


def is_safe_path(
    target_path: str | Path,
    workspace_root: str | Path,
    allow_nonexistent: bool = False,
) -> bool:
    """
    Convenience predicate that returns True if the target path is contained within workspace_root.
    """
    try:
        secure_resolve_path(target_path, workspace_root, allow_nonexistent=allow_nonexistent)
        return True
    except (SecurityAccessDenied, FileNotFoundError, ValueError):
        return False
