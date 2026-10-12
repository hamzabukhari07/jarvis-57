"""
memory/vault_engine.py — Local Markdown Memory Vault & Knowledge Graph Engine for ZEZO.

Provides:
  - Local-first human-readable Markdown vault directory (memory/vault/*.md).
  - Bi-directional [[wikilink]] extraction & graph topology calculation.
  - Automatic migration from legacy long_term.json & SQLite facts into .md notes.
  - Full CRUD operations (get_graph, get_note, save_note, create_note, delete_note).
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
VAULT_DIR = BASE_DIR / "memory" / "vault"
LEGACY_MEMORY_JSON = BASE_DIR / "memory" / "long_term.json"

_vault_lock = threading.Lock()

# Wikilink pattern: [[Target Note]] or [[Target Note|Custom Label]]
WIKILINK_PATTERN = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")

CATEGORY_COLORS = {
    "profile": "#a855f7",       # Purple
    "project": "#38bdf8",       # Cyan
    "preference": "#fb923c",    # Orange
    "relationship": "#facc15",  # Yellow
    "knowledge": "#34d399",     # Emerald
    "general": "#94a3b8",      # Slate
}

DEFAULT_CATEGORIES = ["profile", "project", "preference", "relationship", "knowledge"]


class VaultEngine:
    """Manages the local Markdown vault and compiles the interactive knowledge graph."""

    def __init__(self, vault_dir: Optional[Path] = None):
        self.vault_dir = vault_dir or VAULT_DIR
        self._ensure_vault_initialized()

    def _ensure_vault_initialized(self) -> None:
        """Create vault directory and bootstrap default files or migrate legacy data."""
        with _vault_lock:
            self.vault_dir.mkdir(parents=True, exist_ok=True)
            self._migrate_legacy_data_if_needed()

    def _migrate_legacy_data_if_needed(self) -> None:
        """Seed initial Markdown files if the vault is brand new."""
        marker = self.vault_dir / ".initialized"
        if marker.exists():
            return

        user_profile_file = self.vault_dir / "user_profile.md"
        if user_profile_file.exists():
            try:
                marker.touch()
            except Exception:
                pass
            return

        try:
            marker.touch()
        except Exception:
            pass

        legacy_data = {}
        if LEGACY_MEMORY_JSON.exists():
            try:
                legacy_data = json.loads(LEGACY_MEMORY_JSON.read_text(encoding="utf-8"))
            except Exception:
                legacy_data = {}

        # 1. user_profile.md
        user_content = [
            "---",
            "id: user_profile",
            "title: Hamza Bukhari",
            "category: profile",
            f"updated: {datetime.now().strftime('%Y-%m-%d')}",
            "tags: [creator, architect, user]",
            "---",
            "",
            "# Hamza Bukhari",
            "",
            "Creator and Lead Architect of [[ZEZO OS]].",
            "Primary development workspace in Windows with full autonomy pipelines.",
            "",
            "## Related Links",
            "- Projects: [[ZEZO OS]]",
            "- Specialists: [[Autonomous Specialist Fleet]]",
            "- Preferences: [[System Preferences]]",
        ]
        user_profile_file.write_text("\n".join(user_content), encoding="utf-8")

        # 2. projects.md
        active_proj = ""
        if isinstance(legacy_data.get("projects"), dict):
            active_proj = legacy_data["projects"].get("active_project", {}).get("value", "")
        
        project_content = [
            "---",
            "id: zezo_os",
            "title: ZEZO OS",
            "category: project",
            f"updated: {datetime.now().strftime('%Y-%m-%d')}",
            "tags: [ai, agent_os, python, react]",
            "---",
            "",
            "# ZEZO OS (Autonomous Desktop AI Operating System)",
            "",
            "Modular Monolith Agent Operating System created by [[Hamza Bukhari]].",
            f"Primary local repository: `{active_proj or str(BASE_DIR)}`.",
            "",
            "## Architectural Invariants",
            "- Bidirectional Google Gemini Live audio streaming via WebSockets.",
            "- React 19 Full-Screen Workstation with ReUI design system.",
            "- Local-First Markdown Brain Vault with [[Obsidian Knowledge Graph]].",
            "- Multi-agent autonomous specialist fleet.",
        ]
        (self.vault_dir / "projects.md").write_text("\n".join(project_content), encoding="utf-8")

        # 3. preferences.md
        humor_note = ""
        if isinstance(legacy_data.get("notes"), dict):
            humor_note = legacy_data["notes"].get("humor_preference", {}).get("value", "liked subtle tech jokes")

        pref_content = [
            "---",
            "id: preferences",
            "title: System Preferences",
            "category: preference",
            f"updated: {datetime.now().strftime('%Y-%m-%d')}",
            "tags: [preferences, taste, ui]",
            "---",
            "",
            "# System Preferences",
            "",
            "- **Humor:** " + (humor_note or "Appreciates sharp, tech-informed wit.") + "",
            "- **Code Standards:** Anti-slop hygiene, cyclomatic complexity < 15, dictionary dispatch.",
            "- **Voice:** Authentic Google Gemini Live 24kHz voice output.",
            "- **UI Aesthetic:** Claude Terracotta / Neo-Mint Obsidian with Full-Screen Settings.",
            "",
            "Connected to [[Hamza Bukhari]] and [[ZEZO OS]].",
        ]
        (self.vault_dir / "preferences.md").write_text("\n".join(pref_content), encoding="utf-8")

        # 4. relationships.md
        fleet_note = [
            "---",
            "id: specialist_fleet",
            "title: Autonomous Specialist Fleet",
            "category: relationship",
            f"updated: {datetime.now().strftime('%Y-%m-%d')}",
            "tags: [fleet, agents, ai]",
            "---",
            "",
            "# Autonomous Specialist Fleet",
            "",
            "Autonomous multi-agent fleet executing specialist tasks under [[ZEZO OS]] and [[Hamza Bukhari]].",
        ]
        (self.vault_dir / "relationships.md").write_text("\n".join(fleet_note), encoding="utf-8")

        # 5. knowledge_facts.md
        knowledge_content = [
            "---",
            "id: obsidian_graph",
            "title: Obsidian Knowledge Graph",
            "category: knowledge",
            f"updated: {datetime.now().strftime('%Y-%m-%d')}",
            "tags: [graph, memory, d3]",
            "---",
            "",
            "# Obsidian Knowledge Graph",
            "",
            "Visual node-network memory browser built for [[ZEZO OS]].",
            "Powered by HTML5 2D Canvas and D3 force physics simulation.",
            "Allows [[Hamza Bukhari]] to visually explore, inspect, and edit all long-term memories in real time.",
        ]
        (self.vault_dir / "knowledge_facts.md").write_text("\n".join(knowledge_content), encoding="utf-8")

        # Synthesize real conversation memories from SQLite turns
        self.sync_real_conversations_from_db()

    def sync_real_conversations_from_db(self, limit_sessions: int = 25) -> int:
        """
        Dynamically inspect real conversation turns from zezo_brain.db
        and synthesize them into structured Markdown knowledge nodes with [[wikilinks]].
        """
        db_file = BASE_DIR / "memory" / "zezo_brain.db"
        if not db_file.exists():
            return 0

        created_count = 0
        try:
            import sqlite3
            with sqlite3.connect(str(db_file), timeout=5.0) as conn:
                cursor = conn.cursor()
                
                # Fetch distinct sessions with their date and sample turns
                cursor.execute("""
                    SELECT session_id, MIN(timestamp) as start_time, COUNT(*) as turn_count
                    FROM turns
                    GROUP BY session_id
                    HAVING COUNT(*) >= 2
                    ORDER BY id DESC
                    LIMIT ?
                """, (limit_sessions,))
                sessions = cursor.fetchall()

                for sess_id, start_time, turn_count in sessions:
                    # Clean identifier
                    slug = f"conv_{sess_id.replace('sess_', '')}"
                    target_file = self.vault_dir / f"{slug}.md"
                    if target_file.exists():
                        continue

                    # Fetch user and assistant messages for this session
                    cursor.execute("""
                        SELECT role, content, tool_name, timestamp
                        FROM turns
                        WHERE session_id = ?
                        ORDER BY id ASC
                        LIMIT 12
                    """, (sess_id,))
                    turns = cursor.fetchall()
                    if not turns:
                        continue

                    # Extract primary user directive to form a meaningful title
                    primary_topic = ""
                    highlights = []
                    tools_used = set()

                    for role, content, tool_name, _ in turns:
                        if tool_name:
                            tools_used.add(tool_name)
                        if role == "user" and not primary_topic and content:
                            clean_q = re.sub(r"[^a-zA-Z0-9\s\-_]", "", content).strip()
                            if len(clean_q) > 4:
                                words = clean_q.split()[:6]
                                primary_topic = " ".join(words).title()
                        if content and len(content.strip()) > 5:
                            short_c = content.strip().replace("\n", " ")[:140]
                            highlights.append(f"- **{role.capitalize()}:** {short_c}")

                    if not primary_topic:
                        primary_topic = f"Session {sess_id.replace('sess_', '')[:8]}"

                    # Auto-detect wikilinks to connect this conversation to other nodes
                    detected_links = ["[[ZEZO OS]]", "[[Hamza Bukhari]]"]
                    combined_text = " ".join([t[1] for t in turns if t[1]]).lower()

                    if any(w in combined_text for w in ("react", "ui", "frontend", "css", "settings", "theme", "modal", "dialog")):
                        detected_links.append("[[System Preferences]]")
                    if any(w in combined_text for w in ("fleet", "agent", "specialist", "verve", "flux", "michael", "nexus", "dwight")):
                        detected_links.append("[[Autonomous Specialist Fleet]]")
                    if any(w in combined_text for w in ("graph", "obsidian", "canvas", "d3", "memory")):
                        detected_links.append("[[Obsidian Knowledge Graph]]")

                    date_str = str(start_time)[:10] if start_time else datetime.now().strftime("%Y-%m-%d")

                    node_content = [
                        "---",
                        f"id: {slug}",
                        f"title: {primary_topic}",
                        "category: knowledge",
                        f"updated: {date_str}",
                        f"tags: [conversation, {len(turns)}_turns]",
                        "---",
                        "",
                        f"# {primary_topic}",
                        "",
                        f"Live interaction recorded on **{start_time or date_str}** ({turn_count} total turns).",
                        "",
                        "## Conversation Excerpts",
                        *highlights[:6],
                        "",
                        "## Connected Context",
                        "- Related Nodes: " + ", ".join(list(dict.fromkeys(detected_links))),
                    ]

                    if tools_used:
                        node_content.append(f"- Autonomous Tools Dispatched: {', '.join(sorted(tools_used))}")

                    target_file.write_text("\n".join(node_content), encoding="utf-8")
                    created_count += 1

        except Exception as e:
            print(f"[VaultEngine] Error syncing conversations from db: {e}")

        return created_count

    def _parse_frontmatter(self, text: str) -> tuple[Dict[str, Any], str]:
        """Extract yaml-style frontmatter headers from markdown content."""
        meta: Dict[str, Any] = {}
        body = text
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                header = parts[1]
                body = parts[2].lstrip()
                for line in header.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        k = k.strip().lower()
                        v = v.strip()
                        if v.startswith("[") and v.endswith("]"):
                            # parse simple tag array
                            items = [t.strip().strip("'\"") for t in v[1:-1].split(",") if t.strip()]
                            meta[k] = items
                        else:
                            meta[k] = v.strip("'\"")
        return meta, body

    def get_all_notes(self) -> List[Dict[str, Any]]:
        """List all markdown notes with metadata and excerpt."""
        with _vault_lock:
            notes = []
            for file_path in sorted(self.vault_dir.glob("*.md")):
                try:
                    raw_text = file_path.read_text(encoding="utf-8")
                    meta, body = self._parse_frontmatter(raw_text)
                    file_stem = file_path.stem
                    title = meta.get("title") or file_stem.replace("_", " ").title()
                    category = meta.get("category", "knowledge").lower()
                    
                    # Create excerpt (first non-heading, non-empty line)
                    snippet = ""
                    for line in body.splitlines():
                        trimmed = line.strip()
                        if trimmed and not trimmed.startswith("#") and not trimmed.startswith("---"):
                            snippet = trimmed[:180]
                            break

                    notes.append({
                        "id": meta.get("id") or file_stem,
                        "file": file_path.name,
                        "title": title,
                        "category": category,
                        "tags": meta.get("tags", []),
                        "updated": meta.get("updated", file_path.stat().st_mtime),
                        "snippet": snippet or "Markdown memory note",
                        "size": len(raw_text),
                    })
                except Exception as e:
                    print(f"[VaultEngine] Warning parsing {file_path.name}: {e}")
            return notes

    def get_note_content(self, file_name_or_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full markdown content and parsed links for a note."""
        target_name = file_name_or_id.strip()
        if not target_name.endswith(".md"):
            target_name += ".md"

        target_file = self.vault_dir / target_name
        if not target_file.exists():
            # Try searching by ID in frontmatter
            for f in self.vault_dir.glob("*.md"):
                try:
                    text = f.read_text(encoding="utf-8")
                    meta, body = self._parse_frontmatter(text)
                    if meta.get("id") == file_name_or_id:
                        target_file = f
                        break
                except Exception:
                    continue

        if not target_file.exists():
            return None

        with _vault_lock:
            raw_text = target_file.read_text(encoding="utf-8")
            meta, body = self._parse_frontmatter(raw_text)
            links = [match.group(1).strip() for match in WIKILINK_PATTERN.finditer(body)]
            
            return {
                "id": meta.get("id") or target_file.stem,
                "file": target_file.name,
                "title": meta.get("title") or target_file.stem.replace("_", " ").title(),
                "category": meta.get("category", "knowledge").lower(),
                "tags": meta.get("tags", []),
                "updated": meta.get("updated", ""),
                "content": raw_text,
                "body": body,
                "outbound_links": links,
            }

    def save_note(self, file_name: str, content: str) -> Dict[str, Any]:
        """Save or update a markdown note."""
        with _vault_lock:
            safe_name = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", file_name.strip())
            if not safe_name.endswith(".md"):
                safe_name += ".md"

            target_path = self.vault_dir / safe_name
            target_path.write_text(content, encoding="utf-8")
            return {"status": "success", "file": safe_name}

    def create_note(self, title: str, category: str, content: str, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create a brand new memory note with proper frontmatter."""
        with _vault_lock:
            clean_title = title.strip() or "Untitled Memory"
            slug = re.sub(r"[^a-zA-Z0-9_]", "_", clean_title.lower()).strip("_")
            file_name = f"{slug}.md"
            target_path = self.vault_dir / file_name

            tag_list = tags or ["memory"]
            header = [
                "---",
                f"id: {slug}",
                f"title: {clean_title}",
                f"category: {category.lower()}",
                f"updated: {datetime.now().strftime('%Y-%m-%d')}",
                f"tags: [{', '.join(tag_list)}]",
                "---",
                "",
                f"# {clean_title}",
                "",
                content.strip() or "New memory node created in ZEZO Brain.",
            ]
            full_text = "\n".join(header)
            target_path.write_text(full_text, encoding="utf-8")
            return {"status": "success", "file": file_name, "id": slug, "title": clean_title}

    def delete_note(self, file_name: str) -> Dict[str, Any]:
        """Delete a memory note file."""
        with _vault_lock:
            safe_name = file_name.strip()
            if not safe_name.endswith(".md"):
                safe_name += ".md"
            target_path = self.vault_dir / safe_name
            if target_path.exists():
                target_path.unlink()
                return {"status": "success", "deleted": safe_name}
            return {"status": "error", "message": "File not found"}

    def get_graph(self) -> Dict[str, Any]:
        """
        Compile full node-and-edge graph topology for Obsidian-style canvas.
        Nodes represent individual notes, edges represent [[wikilinks]] between them.
        """
        # Dynamically ingest any new conversation turns recorded in SQLite
        try:
            self.sync_real_conversations_from_db(limit_sessions=35)
        except Exception:
            pass

        notes = self.get_all_notes()
        title_to_node_id: Dict[str, str] = {}
        nodes: List[Dict[str, Any]] = []
        node_id_set = set()

        # 1. Build nodes list
        for n in notes:
            node_id = n["id"]
            title_to_node_id[n["title"].lower()] = node_id
            title_to_node_id[n["file"].lower()] = node_id
            title_to_node_id[n["file"].replace(".md", "").lower()] = node_id

            color = CATEGORY_COLORS.get(n["category"], CATEGORY_COLORS["knowledge"])
            nodes.append({
                "id": node_id,
                "label": n["title"],
                "category": n["category"],
                "file": n["file"],
                "snippet": n["snippet"],
                "color": color,
                "size": max(14, min(36, 12 + (n["size"] // 80))),
                "tags": n.get("tags", []),
            })
            node_id_set.add(node_id)

        # 2. Build edges list from wikilinks
        links: List[Dict[str, Any]] = []
        edge_keys = set()

        for n in notes:
            note_detail = self.get_note_content(n["file"])
            if not note_detail:
                continue

            source_id = n["id"]
            for link_target in note_detail.get("outbound_links", []):
                target_norm = link_target.strip().lower()
                target_id = title_to_node_id.get(target_norm)

                # If target is not yet an existing note, create an implicit node
                if not target_id:
                    clean_id = re.sub(r"[^a-zA-Z0-9_]", "_", target_norm).strip("_")
                    if clean_id not in node_id_set:
                        nodes.append({
                            "id": clean_id,
                            "label": link_target,
                            "category": "knowledge",
                            "file": "",
                            "snippet": f"Mentioned in {n['title']}",
                            "color": "#64748b",
                            "size": 12,
                            "tags": ["unwritten"],
                        })
                        node_id_set.add(clean_id)
                        title_to_node_id[target_norm] = clean_id
                    target_id = clean_id

                edge_key = f"{source_id}->{target_id}"
                if edge_key not in edge_keys and source_id != target_id:
                    edge_keys.add(edge_key)
                    links.append({
                        "source": source_id,
                        "target": target_id,
                        "value": 1,
                    })

        return {
            "status": "success",
            "nodes": nodes,
            "links": links,
            "stats": {
                "total_notes": len(notes),
                "total_links": len(links),
                "categories": list(CATEGORY_COLORS.keys()),
            },
        }

    def wipe_all_vault_memory(self, preserve_profile: bool = False) -> Dict[str, Any]:
        """Atomically delete all synthesized conversation notes and reset knowledge vault."""
        with _vault_lock:
            deleted_conv_count = 0
            if self.vault_dir.exists():
                for p in list(self.vault_dir.glob("*.md")):
                    if p.name.startswith("conv_"):
                        try:
                            p.unlink()
                            deleted_conv_count += 1
                        except Exception as e:
                            print(f"[VaultEngine] Error deleting {p.name}: {e}")
                    elif not preserve_profile:
                        try:
                            p.unlink()
                        except Exception as e:
                            print(f"[VaultEngine] Error deleting {p.name}: {e}")

            # Only re-seed baseline templates if explicitly requested
            if preserve_profile:
                self._migrate_legacy_data_if_needed()

            remaining = len(list(self.vault_dir.glob("*.md"))) if self.vault_dir.exists() else 0
            return {
                "status": "success",
                "deleted_conv_files": deleted_conv_count,
                "remaining_notes": remaining,
            }


# Global engine singleton
vault_engine = VaultEngine()


def wipe_all_vault_memory(preserve_profile: bool = True) -> Dict[str, Any]:
    return vault_engine.wipe_all_vault_memory(preserve_profile=preserve_profile)

