---
name: git_workflow
description: Professional Git workflow for staging, meaningful commit messages, branch management, and diff reviews.
metadata:
  author: Zezo / FatihMakes
  version: '1.0'
---

# Git Workflow & Source Control Protocol

Use this skill when the user asks to commit code, inspect git status, create branches, or review changes in a repository.

## Execution Steps:
1. **Inspect Working Tree Status:**
   - Execute `git status -s` to see modified, untracked, and staged files.
2. **Review Diffs Carefully:**
   - Execute `git diff` or `git diff --staged` before finalizing any commit.
   - Verify that no `.env`, API keys, or temporary binary files are staged.
3. **Draft Semantic Commit Messages:**
   - Follow Conventional Commits format (`feat: ...`, `fix: ...`, `refactor: ...`, `docs: ...`).
   - Keep subject line under 72 characters.
4. **Summary Feedback:**
   - Report exactly which files were modified and the resulting commit hash to the user.
