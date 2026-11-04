"""
tests/test_path_jail.py - Verification suite for core/path_jail.py.

Tests defense-in-depth Windows path containment:
  1. Traversal attacks (../../)
  2. NTFS Junction escapes
  3. Symlink escapes
  4. Case variation / case-insensitivity
  5. Null-byte injection
  6. New file in valid existing directory
  7. New file escaping via junctioned parent
  8. Read confidentiality of sensitive system files
  9. Invalid / non-existent workspace root
 10. is_safe_path() predicate helper
"""

import os
import platform
import subprocess
import tempfile
from pathlib import Path

import pytest
from core.path_jail import SecurityAccessDenied, is_safe_path, secure_resolve_path


@pytest.fixture
def workspace_env():
    """
    Creates an isolated temporary directory tree with:
      - workspace/
      - workspace/sub/
      - workspace/sub/doc.txt
      - outside/
      - outside/secret.txt
    """
    with tempfile.TemporaryDirectory() as td:
        # Resolve realpath of temp dir to normalize 8.3 short names on Windows
        td_real = Path(os.path.realpath(td))
        ws = td_real / "workspace"
        ws.mkdir()
        sub = ws / "sub"
        sub.mkdir()
        doc = sub / "doc.txt"
        doc.write_text("safe content", encoding="utf-8")

        outside = td_real / "outside"
        outside.mkdir()
        secret = outside / "secret.txt"
        secret.write_text("sensitive data", encoding="utf-8")

        yield {
            "root": td_real,
            "workspace": ws,
            "sub": sub,
            "doc": doc,
            "outside": outside,
            "secret": secret,
        }


def test_valid_file_within_workspace(workspace_env):
    """Test 1: Valid relative and absolute paths within workspace resolve correctly."""
    ws = workspace_env["workspace"]
    doc = workspace_env["doc"]

    # Relative path
    resolved_rel = secure_resolve_path("sub/doc.txt", ws)
    assert resolved_rel.exists()
    assert resolved_rel == doc

    # Absolute path
    resolved_abs = secure_resolve_path(str(doc), ws)
    assert resolved_abs == doc


def test_directory_traversal_blocked(workspace_env):
    """Test 2: Directory traversal (../../) is strictly blocked."""
    ws = workspace_env["workspace"]

    with pytest.raises(SecurityAccessDenied, match="escapes workspace"):
        secure_resolve_path("../../outside/secret.txt", ws)

    with pytest.raises(SecurityAccessDenied, match="escapes workspace"):
        secure_resolve_path("sub/../../outside/secret.txt", ws)


def test_ntfs_junction_escape_blocked(workspace_env):
    """Test 3: An NTFS junction pointing outside the workspace raises SecurityAccessDenied."""
    if platform.system() != "Windows":
        pytest.skip("NTFS junction test is Windows-specific")

    ws = workspace_env["workspace"]
    outside = workspace_env["outside"]
    junc_link = ws / "junc_link"

    # Create junction inside workspace pointing outside
    cmd = ["cmd", "/c", "mklink", "/J", str(junc_link), str(outside)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        pytest.skip(f"mklink /J failed (permissions or filesystem): {res.stderr}")

    target_through_junc = junc_link / "secret.txt"
    assert target_through_junc.exists()

    # Accessing secret.txt through junction must be caught and blocked
    with pytest.raises(SecurityAccessDenied, match="escapes workspace"):
        secure_resolve_path(str(target_through_junc), ws)


def test_symlink_escape_blocked(workspace_env):
    """Test 4: A file symlink pointing outside the workspace raises SecurityAccessDenied."""
    ws = workspace_env["workspace"]
    secret = workspace_env["secret"]
    link = ws / "sym_secret.txt"

    try:
        os.symlink(str(secret), str(link))
    except (OSError, NotImplementedError) as e:
        pytest.skip(f"Symlinks not permitted in this environment: {e}")

    assert link.exists()

    with pytest.raises(SecurityAccessDenied, match="escapes workspace"):
        secure_resolve_path(str(link), ws)


def test_case_variation_handling(workspace_env):
    """Test 5: Windows case-insensitivity does not produce false positives or escapes."""
    ws = workspace_env["workspace"]
    doc = workspace_env["doc"]

    # Target path with altered casing
    varied_target = str(doc).upper()
    resolved = secure_resolve_path(varied_target, ws)
    assert os.path.normcase(str(resolved)) == os.path.normcase(str(doc))


def test_null_byte_rejection(workspace_env):
    """Test 6: Embedded null bytes in path raise ValueError."""
    ws = workspace_env["workspace"]
    with pytest.raises(ValueError, match="null byte"):
        secure_resolve_path("sub/doc.txt\x00.exe", ws)


def test_new_file_creation_in_valid_directory(workspace_env):
    """Test 7: New file creation path is permitted if parent exists within workspace."""
    ws = workspace_env["workspace"]
    new_file_path = ws / "sub" / "new_report.txt"

    assert not new_file_path.exists()
    resolved = secure_resolve_path("sub/new_report.txt", ws, allow_nonexistent=True)
    assert os.path.normcase(str(resolved)) == os.path.normcase(str(new_file_path))


def test_new_file_creation_escaping_via_junction_blocked(workspace_env):
    """Test 8: New file creation targeting a junctioned directory escaping workspace is blocked."""
    if platform.system() != "Windows":
        pytest.skip("NTFS junction test is Windows-specific")

    ws = workspace_env["workspace"]
    outside = workspace_env["outside"]
    junc_dir = ws / "escaped_folder"

    cmd = ["cmd", "/c", "mklink", "/J", str(junc_dir), str(outside)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        pytest.skip(f"mklink /J failed: {res.stderr}")

    new_file_in_junc = junc_dir / "dropped_payload.txt"
    with pytest.raises(SecurityAccessDenied, match="escapes workspace"):
        secure_resolve_path(str(new_file_in_junc), ws, allow_nonexistent=True)


def test_read_confidentiality_system_files(workspace_env):
    """Test 9: Attempting to read Windows system or user files raises SecurityAccessDenied."""
    ws = workspace_env["workspace"]

    windows_files = [
        r"C:\Windows\System32\drivers\etc\hosts",
        r"C:\Windows\notepad.exe",
    ]
    for win_file in windows_files:
        if os.path.exists(win_file):
            with pytest.raises(SecurityAccessDenied, match="escapes workspace"):
                secure_resolve_path(win_file, ws)


def test_invalid_workspace_root(workspace_env):
    """Test 10: Non-existent or non-directory workspace root raises SecurityAccessDenied."""
    doc = workspace_env["doc"]
    with pytest.raises(SecurityAccessDenied, match="Invalid workspace root"):
        secure_resolve_path("doc.txt", r"C:\NonExistent\Fake\Dir_12345")

    with pytest.raises(SecurityAccessDenied, match="not a directory"):
        secure_resolve_path("doc.txt", str(doc))


def test_is_safe_path_predicate(workspace_env):
    """Test 11: is_safe_path convenience predicate returns boolean accurately."""
    ws = workspace_env["workspace"]
    doc = workspace_env["doc"]
    secret = workspace_env["secret"]

    assert is_safe_path(str(doc), ws) is True
    assert is_safe_path("sub/doc.txt", ws) is True
    assert is_safe_path(str(secret), ws) is False
    assert is_safe_path("../../secret.txt", ws) is False
    assert is_safe_path("sub/doc.txt\x00.exe", ws) is False

