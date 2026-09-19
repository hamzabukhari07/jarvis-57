"""
core/skill_loader.py — Declarative Skills Discovery & Closed-Loop Learning Engine.

Inspired by QwenPaw (Skill vs Tool Architecture) and Hermes-Agent (Self-Learning Loop).
Provides:
  - Discovery and parsing of standard `SKILL.md` folders.
  - Zero-overhead token prompt index.
  - On-demand skill instruction reading.
  - Autonomous self-learning skill synthesizer (`save_learned_skill`).
"""

from __future__ import annotations

import os
import re
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
SKILLS_DIR = BASE_DIR / "skills"

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
_lock = threading.Lock()


@dataclass
class SkillRecord:
    name: str
    description: str
    instructions: str
    folder_path: Path
    author: str = "system"
    version: str = "1.0"
    tags: list[str] = field(default_factory=list)


def _parse_yaml_frontmatter(raw_yaml: str) -> dict[str, str]:
    """Lightweight, zero-dependency YAML frontmatter parser."""
    meta: dict[str, str] = {}
    for line in raw_yaml.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip().lower()] = v.strip().strip('"').strip("'")
    return meta


class SkillRegistry:
    def __init__(self, skills_dir: Path | None = None, logger: Optional[Callable[[str], None]] = None):
        self._dir = skills_dir or SKILLS_DIR
        self._logger = logger or (lambda m: print(f"[Skills] {m}"))
        self._skills: dict[str, SkillRecord] = {}
        self.reload()

    def reload(self) -> None:
        """Scan skills directory and parse all SKILL.md manifests."""
        with _lock:
            self._skills.clear()
            if not self._dir.exists():
                self._dir.mkdir(parents=True, exist_ok=True)
                return

            for item in self._dir.iterdir():
                if item.is_dir():
                    skill_file = item / "SKILL.md"
                    if skill_file.exists():
                        try:
                            content = skill_file.read_text(encoding="utf-8")
                            m = _FRONTMATTER_RE.match(content)
                            if m:
                                meta_block, body = m.group(1), m.group(2).strip()
                                meta = _parse_yaml_frontmatter(meta_block)
                                name = meta.get("name") or item.name
                                desc = meta.get("description") or f"Skill for {name}"
                                author = meta.get("author") or "system"
                                version = meta.get("version") or "1.0"
                            else:
                                name = item.name
                                desc = f"Skill for {item.name}"
                                body = content.strip()
                                author = "system"
                                version = "1.0"

                            self._skills[name] = SkillRecord(
                                name=name,
                                description=desc,
                                instructions=body,
                                folder_path=item,
                                author=author,
                                version=version,
                            )
                        except Exception as e:
                            self._logger(f"⚠️ Failed to parse {skill_file}: {e}")

    def list_skills(self) -> list[dict[str, str]]:
        """Return metadata list of all discovered skills."""
        with _lock:
            return [
                {
                    "name": s.name,
                    "description": s.description,
                    "author": s.author,
                    "version": s.version,
                }
                for s in self._skills.values()
            ]

    def read_skill(self, name: str) -> str:
        """Retrieve full markdown instructions for a specific skill."""
        with _lock:
            clean_name = (name or "").strip()
            # Direct match
            if clean_name in self._skills:
                s = self._skills[clean_name]
                return f"# SKILL: {s.name}\n**Description:** {s.description}\n\n{s.instructions}"
            
            # Fuzzy match
            for k, s in self._skills.items():
                if clean_name.lower() in k.lower() or k.lower() in clean_name.lower():
                    return f"# SKILL: {s.name}\n**Description:** {s.description}\n\n{s.instructions}"

            return f"Skill '{name}' not found. Available skills: {', '.join(self._skills.keys()) if self._skills else 'None'}"

    def save_learned_skill(self, name: str, description: str, instructions: str, author: str = "auto_learned") -> str:
        """
        Synthesize and persist a new skill from autonomous experience (Hermes-Style Closed Learning Loop).
        """
        clean_name = re.sub(r"[^a-zA-Z0-9_]", "_", (name or "").strip().lower()).strip("_")
        if not clean_name:
            return "Failed to save skill: Invalid skill name."

        skill_dir = self._dir / clean_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skill_dir / "SKILL.md"

        content = (
            f"---\n"
            f"name: {clean_name}\n"
            f"description: {description.strip()}\n"
            f"metadata:\n"
            f"  author: {author}\n"
            f"  version: '1.0'\n"
            f"---\n\n"
            f"# {clean_name.replace('_', ' ').title()}\n\n"
            f"{instructions.strip()}\n"
        )

        with _lock:
            try:
                skill_file.write_text(content, encoding="utf-8")
                self._skills[clean_name] = SkillRecord(
                    name=clean_name,
                    description=description.strip(),
                    instructions=instructions.strip(),
                    folder_path=skill_dir,
                    author=author,
                    version="1.0",
                )
                self._logger(f"[Skills] Learned new skill: '{clean_name}'")
                return f"Successfully learned and saved skill '{clean_name}'."
            except Exception as e:
                return f"Failed to save skill '{clean_name}': {e}"

    def format_prompt_block(self) -> str:
        """Format a lightweight skills index table to include in the system prompt."""
        with _lock:
            if not self._skills:
                return ""
            lines = [
                "[AVAILABLE SKILLS & WORKFLOWS — call read_skill(name) to fetch step-by-step instructions before executing]",
            ]
            for s in self._skills.values():
                lines.append(f"  - {s.name}: {s.description}")
            return "\n".join(lines) + "\n\n"


_global_registry: Optional[SkillRegistry] = None


def get_skill_registry() -> SkillRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = SkillRegistry()
    return _global_registry
