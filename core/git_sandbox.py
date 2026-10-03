from __future__ import annotations

import logging
import os
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

_WIN_HIDE = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


@dataclass
class WorktreeResult:
    success: bool
    worktree_path: Optional[Path] = None
    branch_name: str = ""
    error: Optional[str] = None


class GitWorktreeSandbox:
    """Zero data-loss git worktree sandboxing with 4-gate safe teardown."""

    def __init__(self, repo_root: Optional[Path] = None):
        self.repo_root = (repo_root or Path.cwd()).resolve()
        self.worktree_base = self.repo_root / ".agent_worktrees"
        self._merge_lock = threading.Lock()

    def _run_git(self, args: list[str], cwd: Optional[Path] = None) -> Tuple[int, str, str]:
        cmd = ["git"] + args
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(cwd or self.repo_root),
                capture_output=True,
                text=True,
                creationflags=_WIN_HIDE,
                timeout=30.0,
            )
            return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
        except Exception as e:
            return 1, "", str(e)

    def create_worktree(self, task_id: str, base_branch: str = "main") -> WorktreeResult:
        """Create an isolated worktree on a dynamic branch."""
        clean_id = task_id.replace("/", "_").replace("\\", "_")
        branch_name = f"agent/{clean_id}"
        target_dir = self.worktree_base / clean_id

        self.worktree_base.mkdir(parents=True, exist_ok=True)

        if target_dir.exists():
            return WorktreeResult(success=True, worktree_path=target_dir, branch_name=branch_name)

        # Create branch and worktree
        code, out, err = self._run_git(["worktree", "add", "-b", branch_name, str(target_dir), base_branch])
        if code != 0:
            # Fallback: worktree without new branch if branch exists
            code2, out2, err2 = self._run_git(["worktree", "add", str(target_dir), branch_name])
            if code2 != 0:
                return WorktreeResult(success=False, error=f"Failed to create worktree: {err or err2}")

        return WorktreeResult(success=True, worktree_path=target_dir, branch_name=branch_name)

    def merge_worktree(self, task_id: str, target_branch: str = "main") -> Tuple[bool, str]:
        """Safely merge worktree branch into target branch using centralized merge lock."""
        clean_id = task_id.replace("/", "_").replace("\\", "_")
        branch_name = f"agent/{clean_id}"
        worktree_dir = self.worktree_base / clean_id

        with self._merge_lock:
            # Ensure worktree changes are committed on the branch
            if worktree_dir.exists():
                self._run_git(["add", "-A"], cwd=worktree_dir)
                self._run_git(["commit", "-m", f"Automated commit for task {task_id}"], cwd=worktree_dir)

            code, out, err = self._run_git(["merge", branch_name, "--no-ff", "-m", f"Merge agent task {task_id}"])
            if code != 0:
                conflict_branch = f"conflict/task_{clean_id}_{int(time.time())}"
                self._run_git(["branch", conflict_branch, branch_name])
                self._run_git(["merge", "--abort"])
                return False, f"Merge conflict on {target_branch}. Preserved in branch '{conflict_branch}'."

            return True, f"Successfully merged {branch_name} into {target_branch}."

    def safe_teardown(self, task_id: str) -> str:
        """4-Gate Safe Teardown Protocol."""
        clean_id = task_id.replace("/", "_").replace("\\", "_")
        target_dir = self.worktree_base / clean_id

        if not target_dir.exists():
            return f"Worktree for {task_id} does not exist."

        # Gate 1: Check uncommitted changes and quarantine
        code, out, _ = self._run_git(["status", "--porcelain"], cwd=target_dir)
        if out:
            ts = int(time.time())
            quarantine_branch = f"quarantine/task_{clean_id}_{ts}"
            self._run_git(["checkout", "-b", quarantine_branch], cwd=target_dir)
            self._run_git(["add", "-A"], cwd=target_dir)
            self._run_git(["commit", "-m", f"Quarantine uncommitted state for {task_id}"], cwd=target_dir)
            logger.info(f"[GitSandbox] Quarantined uncommitted work to {quarantine_branch}")

        # Gate 2: Unlock worktree
        self._run_git(["worktree", "unlock", str(target_dir)])

        # Gate 3: Prune & remove via git
        self._run_git(["worktree", "remove", "--force", str(target_dir)])
        time.sleep(0.3)

        # Gate 4: Handle lingering locked directory
        if target_dir.exists():
            try:
                shutil.rmtree(target_dir, ignore_errors=True)
            except Exception:
                pass

        if target_dir.exists():
            return f"Teardown: Worktree marked ORPHAN_PRESERVED at {target_dir} (locked by OS)."

        return f"Worktree for {task_id} safely disassembled."


git_sandbox = GitWorktreeSandbox()
