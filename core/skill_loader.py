"""
core/skill_loader.py — Declarative Skills Discovery & Dynamic Trigger Index Engine.

Inspired by QwenPaw (Skill vs Tool Architecture) and Hermes-Agent (Self-Learning Loop).
Provides:
  - Multi-tier discovery and parsing of standard `SKILL.md` packages.
  - Category / Domain namespace support (UI/UX, Coding, Research, Diagnostics).
  - Dynamic Trigger-Indexed intent matching and context budgeting.
  - Hot-reloading, Drag & Drop skill importer, and persistent skill status.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import sys
import threading
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
SKILLS_DIR = BASE_DIR / "skills"
SKILLS_CONFIG_FILE = BASE_DIR / "config" / "skills_state.json"

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
_lock = threading.RLock()


@dataclass
class SkillRecord:
    name: str
    description: str
    instructions: str
    folder_path: Path
    domain: str = "general"
    author: str = "system"
    version: str = "1.0"
    tags: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    auto_activate: bool = True
    pinned: bool = False
    disabled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "domain": self.domain,
            "author": self.author,
            "version": self.version,
            "tags": self.tags,
            "triggers": self.triggers,
            "auto_activate": self.auto_activate,
            "pinned": self.pinned,
            "disabled": self.disabled,
            "folder": str(self.folder_path),
        }


def _parse_yaml_frontmatter(raw_yaml: str) -> dict[str, Any]:
    """Lightweight, robust zero-dependency YAML frontmatter parser."""
    meta: dict[str, Any] = {}
    current_key: Optional[str] = None
    for raw_line in raw_yaml.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        
        # Array item in multi-line list (- item)
        if line.startswith("- ") and current_key:
            val = line[2:].strip().strip('"').strip("'")
            if isinstance(meta.get(current_key), list):
                meta[current_key].append(val)
            else:
                meta[current_key] = [val]
            continue

        if ":" in line:
            k, v = line.split(":", 1)
            k = k.strip().lower()
            v = v.strip()
            current_key = k

            if v.startswith("[") and v.endswith("]"):
                # Inline JSON-like array: ["a", "b", "c"]
                items = [item.strip().strip('"').strip("'") for item in v[1:-1].split(",") if item.strip()]
                meta[k] = items
            elif v.lower() in ("true", "yes", "on"):
                meta[k] = True
            elif v.lower() in ("false", "no", "off"):
                meta[k] = False
            elif v:
                meta[k] = v.strip('"').strip("'")
            else:
                meta[k] = []
    return meta


def _infer_domain_from_name_and_tags(name: str, tags: list[str], folder: Path) -> str:
    combined = (name + " " + " ".join(tags) + " " + folder.name).lower()
    if any(k in combined for k in ("ui", "design", "frontend", "taste", "css", "theme", "preset", "aesthetic", "style")):
        return "ui"
    if any(k in combined for k in ("code", "opencode", "kilo", "antigravity", "git", "deploy", "fastapi", "dev", "refactor")):
        return "coding"
    if any(k in combined for k in ("research", "social", "scrape", "scraper", "youtube", "reddit", "web", "pipeline")):
        return "research"
    if any(k in combined for k in ("system", "diagnostic", "hardware", "bench", "monitor", "telemetry")):
        return "system"
    return "general"


def _generate_default_triggers(name: str, domain: str, tags: list[str]) -> list[str]:
    triggers = set(t.lower() for t in tags if len(t) > 2)
    clean_name = name.replace("_", " ").replace("-", " ").lower()
    triggers.add(clean_name)
    if domain == "ui":
        triggers.update(["landing page", "hero section", "frontend", "ui design", "component", "styling", "anti slop"])
    elif domain == "coding":
        triggers.update(["coding", "build app", "full stack", "refactor", "git commit", "deploy", "synthesize"])
    elif domain == "research":
        triggers.update(["research", "scrape", "social media", "analyze trends", "deep search"])
    elif domain == "system":
        triggers.update(["diagnostics", "hardware check", "system telemetry", "telemetry"])
    return sorted(triggers)


class SkillRegistry:
    def __init__(self, skills_dir: Path | None = None, logger_fn: Optional[Callable[[str], None]] = None):
        self._dir = skills_dir or SKILLS_DIR
        self._logger = logger_fn or (lambda m: print(f"[Skills] {m}"))
        self._skills: dict[str, SkillRecord] = {}
        self._state: dict[str, dict[str, Any]] = self._load_state()
        self.reload()

    def _load_state(self) -> dict[str, dict[str, Any]]:
        try:
            if SKILLS_CONFIG_FILE.exists():
                return json.loads(SKILLS_CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def _save_state(self) -> None:
        try:
            SKILLS_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            state = {
                name: {
                    "pinned": s.pinned,
                    "disabled": s.disabled,
                    "auto_activate": s.auto_activate,
                }
                for name, s in self._skills.items()
            }
            SKILLS_CONFIG_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
        except Exception as e:
            logger.debug("Failed to save skills state: %s", e)

    def reload(self) -> None:
        """Scan skills directory recursively for all SKILL.md packages."""
        with _lock:
            self._skills.clear()
            if not self._dir.exists():
                self._dir.mkdir(parents=True, exist_ok=True)
                return

            # Discover all SKILL.md files (top-level and domain categorized)
            for skill_file in self._dir.rglob("SKILL.md"):
                item_folder = skill_file.parent
                try:
                    content = skill_file.read_text(encoding="utf-8")
                    m = _FRONTMATTER_RE.match(content)
                    if m:
                        meta_block, body = m.group(1), m.group(2).strip()
                        meta = _parse_yaml_frontmatter(meta_block)
                        name = str(meta.get("name") or item_folder.name).strip()
                        desc = str(meta.get("description") or f"Skill for {name}").strip()
                        author = str(meta.get("author") or "system").strip()
                        version = str(meta.get("version") or "1.0").strip()
                        tags = meta.get("tags") if isinstance(meta.get("tags"), list) else []
                        triggers = meta.get("triggers") if isinstance(meta.get("triggers"), list) else []
                        domain = str(meta.get("domain") or "").strip()
                    else:
                        name = item_folder.name
                        desc = f"Skill for {item_folder.name}"
                        body = content.strip()
                        author = "system"
                        version = "1.0"
                        tags = []
                        triggers = []
                        domain = ""

                    if not domain:
                        domain = _infer_domain_from_name_and_tags(name, tags, item_folder)

                    if not triggers:
                        triggers = _generate_default_triggers(name, domain, tags)

                    # Apply saved user preferences
                    saved = self._state.get(name, {})
                    pinned = saved.get("pinned", False)
                    disabled = saved.get("disabled", False)
                    auto_activate = saved.get("auto_activate", True)

                    self._skills[name] = SkillRecord(
                        name=name,
                        description=desc,
                        instructions=body,
                        folder_path=item_folder,
                        domain=domain,
                        author=author,
                        version=version,
                        tags=tags,
                        triggers=triggers,
                        auto_activate=auto_activate,
                        pinned=pinned,
                        disabled=disabled,
                    )
                except Exception as e:
                    self._logger(f"⚠️ Failed to parse {skill_file}: {e}")

            self._logger(f"Discovered {len(self._skills)} declarative skills across {len(self.list_domains())} domains.")

    def list_domains(self) -> list[str]:
        """Return list of all unique domains."""
        with _lock:
            domains = set(s.domain.upper() for s in self._skills.values())
            return sorted(domains or ["GENERAL"])

    def list_skills(self, domain: Optional[str] = None) -> list[dict[str, Any]]:
        """Return metadata list of all discovered skills, optionally filtered by domain."""
        with _lock:
            skills = list(self._skills.values())
            if domain and domain.upper() != "ALL":
                skills = [s for s in skills if s.domain.upper() == domain.upper()]
            return [s.to_dict() for s in skills]

    def read_skill(self, name: str) -> str:
        """Retrieve full markdown instructions for a specific skill."""
        with _lock:
            clean_name = (name or "").strip()
            if clean_name in self._skills:
                s = self._skills[clean_name]
                return f"# SKILL: {s.name} ({s.domain.upper()})\n**Description:** {s.description}\n\n{s.instructions}"
            
            for k, s in self._skills.items():
                if clean_name.lower() in k.lower() or k.lower() in clean_name.lower():
                    return f"# SKILL: {s.name} ({s.domain.upper()})\n**Description:** {s.description}\n\n{s.instructions}"

            return f"Skill '{name}' not found. Available: {', '.join(self._skills.keys()) if self._skills else 'None'}"

    def match_skills(self, query: str, max_matches: int = 3) -> list[SkillRecord]:
        """
        Match user task query against skill triggers and tags.
        Returns prioritized active skills for prompt context injection.
        """
        with _lock:
            q = (query or "").lower().strip()
            if not q:
                return [s for s in self._skills.values() if s.pinned and not s.disabled]

            matched: list[tuple[int, SkillRecord]] = []
            for s in self._skills.values():
                if s.disabled:
                    continue
                if s.pinned:
                    matched.append((100, s))
                    continue
                if not s.auto_activate:
                    continue

                score = 0
                # Exact trigger match
                for trig in s.triggers:
                    trig_l = trig.lower()
                    if trig_l in q:
                        score += 30 + len(trig_l)
                
                # Tag / Keyword match
                for tag in s.tags:
                    if tag.lower() in q:
                        score += 15

                # Name match
                if s.name.replace("_", " ") in q:
                    score += 40

                if score > 0:
                    matched.append((score, s))

            matched.sort(key=lambda x: x[0], reverse=True)
            return [item[1] for item in matched[:max_matches]]

    def format_prompt_block(self) -> str:
        """
        Format discovered skills summary for system prompt injection.
        Lists available skills with their name, domain, and description,
        plus full instructions for any pinned skills.
        """
        with _lock:
            active_skills = [s for s in self._skills.values() if not s.disabled]
            if not active_skills:
                return ""

            lines = ["[AVAILABLE SKILLS & WORKFLOWS]"]
            lines.append("Use read_skill(skill_name) before performing specialized workflows:")
            for s in active_skills:
                lines.append(f"• {s.name} ({s.domain.upper()}): {s.description}")

            pinned = [s for s in active_skills if s.pinned]
            if pinned:
                lines.append("\n[PINNED SKILL GUIDELINES]")
                for s in pinned:
                    lines.append(f"### SKILL [{s.domain.upper()}]: {s.name}\n{s.instructions}\n")

            return "\n".join(lines) + "\n"

    def get_active_skill_prompt(self, task_text: str, max_tokens_budget: int = 1200) -> str:
        """
        Builds a compact, budgeted active skill instruction block to inject into the LLM context.
        """
        matched = self.match_skills(task_text, max_matches=3)
        if not matched:
            return ""

        blocks = ["[ACTIVE DOMAIN SKILLS & GUIDELINES INJECTED FOR THIS TASK]"]
        total_chars = 0
        char_limit = max_tokens_budget * 4

        for s in matched:
            # Compact formatted instructions
            header = f"### SKILL [{s.domain.upper()}]: {s.name} (v{s.version})\n{s.description}\n"
            body = s.instructions.strip()
            # Trim large skills if exceeding budget
            if len(body) > 1800:
                body = body[:1750] + "\n...(truncated for context budget)"
            section = f"{header}\n{body}\n"
            if total_chars + len(section) > char_limit:
                break
            blocks.append(section)
            total_chars += len(section)

        return "\n".join(blocks) + "\n\n"

    def set_skill_mode(self, name: str, pinned: bool = False, disabled: bool = False, auto_activate: bool = True) -> bool:
        """Update toggle mode for a skill and persist state."""
        with _lock:
            if name not in self._skills:
                return False
            s = self._skills[name]
            s.pinned = pinned
            s.disabled = disabled
            s.auto_activate = auto_activate
            self._save_state()
            return True

    def install_skill(self, source_path_or_zip: str | Path, target_domain: str = "") -> tuple[bool, str]:
        """
        Install a new skill from a local folder or .zip archive.
        Safely unpacks, validates SKILL.md, and reloads registry.
        """
        with _lock:
            src = Path(source_path_or_zip).resolve()
            if not src.exists():
                return False, f"Source path '{src}' does not exist."

            dest_parent = self._dir / target_domain.lower() if target_domain else self._dir

            try:
                if src.is_file() and src.suffix.lower() == ".zip":
                    with zipfile.ZipFile(src, "r") as z:
                        # Find folder containing SKILL.md in archive
                        skill_entries = [e for e in z.namelist() if e.endswith("SKILL.md")]
                        if not skill_entries:
                            return False, "Archive does not contain a valid SKILL.md file."
                        top_folder = Path(skill_entries[0]).parent
                        extract_name = top_folder.name if str(top_folder) != "." else src.stem
                        dest_dir = dest_parent / extract_name
                        dest_dir.mkdir(parents=True, exist_ok=True)
                        z.extractall(dest_dir)
                elif src.is_dir():
                    if not (src / "SKILL.md").exists():
                        return False, "Directory does not contain a SKILL.md file."
                    dest_dir = dest_parent / src.name
                    if dest_dir.exists():
                        shutil.rmtree(dest_dir)
                    shutil.copytree(src, dest_dir)
                else:
                    return False, "Provided file is neither a directory nor a .zip skill archive."

                self.reload()
                return True, f"Skill successfully installed to {dest_dir.name}."
            except Exception as e:
                return False, f"Failed to install skill: {e}"

    def save_learned_skill(
        self,
        name: str,
        description: str,
        instructions: str,
        domain: str = "",
        author: str = "system",
        triggers: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> tuple[bool, str]:
        """
        Autonomously synthesize or update a procedural skill package on disk with valid YAML frontmatter.
        """
        with _lock:
            try:
                clean_name = re.sub(r"[^\w\-]", "_", name.strip().lower())
                if not clean_name:
                    return False, "Skill name cannot be empty."

                skill_tags = tags or []
                inferred_domain = domain.lower() if domain else _infer_domain_from_name_and_tags(clean_name, skill_tags, Path(clean_name))

                target_dir = self._dir / clean_name
                target_dir.mkdir(parents=True, exist_ok=True)
                skill_md = target_dir / "SKILL.md"

                skill_trigs = triggers or _generate_default_triggers(clean_name, inferred_domain, skill_tags)

                trig_yaml = "\n".join(f"  - {t}" for t in skill_trigs)
                tag_yaml = "\n".join(f"  - {t}" for t in skill_tags) if skill_tags else f"  - {inferred_domain}"

                content = f"""---
name: {clean_name}
description: {description.strip()}
domain: {inferred_domain}
author: {author}
version: 1.0
triggers:
{trig_yaml}
tags:
{tag_yaml}
---

{instructions.strip()}
"""
                skill_md.write_text(content, encoding="utf-8")
                self.reload()
                return True, f"Skill '{clean_name}' successfully saved."
            except Exception as e:
                return False, f"Failed to save skill: {e}"

    def delete_skill(self, name: str) -> tuple[bool, str]:
        """Safely delete a skill directory."""
        with _lock:
            if name not in self._skills:
                return False, f"Skill '{name}' not found."
            s = self._skills[name]
            try:
                if s.folder_path.exists():
                    shutil.rmtree(s.folder_path)
                del self._skills[name]
                if name in self._state:
                    del self._state[name]
                self._save_state()
                return True, f"Skill '{name}' deleted successfully."
            except Exception as e:
                return False, f"Failed to delete skill '{name}': {e}"


_global_registry: Optional[SkillRegistry] = None


def get_skill_registry() -> SkillRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = SkillRegistry()
    return _global_registry
