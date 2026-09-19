"""
actions/agent_reach.py — Deep Social & Multi-Platform Intelligence for Zezo.

Integrates Agent-Reach capabilities for multi-platform extraction:
- YouTube transcripts & video summaries (via youtube-transcript-api & yt-dlp)
- Reddit discussions, posts & top comments
- GitHub repositories, documentation & structure
- Twitter / X thread extraction
"""

from __future__ import annotations

import json
import logging
import re
import urllib.request
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger("zezo.agent_reach")


def _extract_youtube_id(url_or_id: str) -> Optional[str]:
    """Extract 11-character YouTube video ID from various URL formats."""
    raw = (url_or_id or "").strip()
    if len(raw) == 11 and re.match(r"^[a-zA-Z0-9_-]{11}$", raw):
        return raw

    patterns = [
        r"(?:v=|\/v\/|youtu\.be\/|\/embed\/|\/shorts\/)([a-zA-Z0-9_-]{11})",
        r"^([a-zA-Z0-9_-]{11})$",
    ]
    for pattern in patterns:
        m = re.search(pattern, raw)
        if m:
            return m.group(1)
    return None


def fetch_youtube_transcript(video_url_or_id: str, max_chars: int = 8000) -> str:
    """Fetch video transcript and metadata for a YouTube video."""
    video_id = _extract_youtube_id(video_url_or_id)
    if not video_id:
        return f"Could not identify a valid YouTube video ID from '{video_url_or_id}'."

    meta_title = f"YouTube Video [{video_id}]"
    transcript_text = ""

    # 1. Fetch transcript via youtube_transcript_api (direct or auto-generated)
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        
        ytt = YouTubeTranscriptApi()
        snippets = None

        # Try direct fetch first
        try:
            snippets = ytt.fetch(video_id)
        except Exception:
            pass

        # Try list of transcripts (including auto-generated in any language)
        if snippets is None:
            try:
                t_list = ytt.list(video_id)
                for t in t_list:
                    try:
                        snippets = t.fetch()
                        if snippets:
                            break
                    except Exception:
                        continue
            except Exception:
                pass

        if snippets is not None:
            lines = []
            for item in snippets:
                if hasattr(item, "text"):
                    text = (item.text or "").strip()
                    start = int(item.start or 0)
                elif isinstance(item, dict):
                    text = str(item.get("text", "")).strip()
                    start = int(item.get("start", 0))
                else:
                    text = str(item).strip()
                    start = 0

                mins, secs = divmod(start, 60)
                timestamp = f"[{mins:02d}:{secs:02d}]"
                if text:
                    lines.append(f"{timestamp} {text}")
            transcript_text = "\n".join(lines)
    except Exception as e:
        logger.warning(f"youtube_transcript_api failed: {e}")

    # 2. Extract metadata & description via yt-dlp
    try:
        import yt_dlp
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            if info:
                title = info.get("title", meta_title)
                channel = info.get("uploader") or info.get("channel", "Unknown")
                views = info.get("view_count", "N/A")
                duration = info.get("duration", 0)
                mins, secs = divmod(duration, 60)
                description = (info.get("description") or "")[:600]

                header = (
                    f"# {title}\n"
                    f"**Channel:** {channel} | **Duration:** {mins}:{secs:02d} | **Views:** {views}\n"
                    f"**URL:** https://www.youtube.com/watch?v={video_id}\n\n"
                    f"**Description Summary:**\n{description}\n\n"
                    f"## Video Transcript / Captions:\n"
                )
                if transcript_text:
                    full_result = header + transcript_text
                else:
                    full_result = header + "(Transcript not available for this video. Overview and description shown above.)"

                if len(full_result) > max_chars:
                    return full_result[:max_chars] + f"\n\n... [Transcript truncated at {max_chars} chars]"
                return full_result
    except Exception as e:
        logger.warning(f"yt-dlp info extraction failed: {e}")

    if transcript_text:
        return f"# YouTube Video Transcript ({video_id})\nURL: https://www.youtube.com/watch?v={video_id}\n\n{transcript_text[:max_chars]}"
    
    return f"Unable to fetch transcript or details for YouTube video: {video_url_or_id}"


def fetch_reddit_discussion(url: str, max_comments: int = 10) -> str:
    """Fetch a Reddit post and top comments directly via public JSON endpoint."""
    clean_url = url.strip()
    if not clean_url.endswith(".json"):
        clean_url = clean_url.rstrip("/") + ".json"

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ZezoAgent/2.0"}
    req = urllib.request.Request(clean_url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        post_data = data[0]["data"]["children"][0]["data"]
        title = post_data.get("title", "Reddit Post")
        subreddit = post_data.get("subreddit_name_prefixed", "")
        author = post_data.get("author", "[deleted]")
        score = post_data.get("score", 0)
        selftext = post_data.get("selftext", "")

        out = [
            f"# {title}",
            f"**Subreddit:** {subreddit} | **Author:** u/{author} | **Score:** {score} upvotes\n",
            "## Post Content:",
            selftext if selftext else "(No body text / Link post)",
            "\n## Top Discussion Comments:",
        ]

        comments_data = data[1]["data"]["children"]
        count = 0
        for c in comments_data:
            c_info = c.get("data", {})
            body = c_info.get("body", "").strip()
            c_author = c_info.get("author", "[deleted]")
            c_score = c_info.get("score", 0)
            if body and body != "[deleted]":
                count += 1
                out.append(f"- **u/{c_author}** ({c_score} pts):\n  {body}\n")
                if count >= max_comments:
                    break

        return "\n".join(out)
    except Exception as e:
        # Fallback to Scrapling reader
        from actions.web_reader import extract_web_content
        return extract_web_content(url)


def fetch_github_repository(repo_url_or_path: str) -> str:
    """Extract repository README, metadata, and file structure for a GitHub repository."""
    raw = repo_url_or_path.strip()
    match = re.search(r"github\.com[/:]([a-zA-Z0-9_\-\.]+)/([a-zA-Z0-9_\-\.]+)", raw)
    if match:
        owner, repo = match.group(1), match.group(2).replace(".git", "")
    else:
        parts = [p for p in raw.split("/") if p]
        if len(parts) >= 2:
            owner, repo = parts[-2], parts[-1]
        else:
            return f"Invalid GitHub repo reference: {repo_url_or_path}"

    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    readme_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/README.md"
    readme_alt = f"https://raw.githubusercontent.com/{owner}/{repo}/master/README.md"

    headers = {"User-Agent": "Zezo-Agent-Reach/2.0"}

    # Fetch repo metadata
    meta_str = ""
    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            info = json.loads(resp.read().decode("utf-8"))
            meta_str = (
                f"# GitHub: {info.get('full_name', f'{owner}/{repo}')}\n"
                f"**Stars:** [Stars: {info.get('stargazers_count', 0)}] | **Forks:** [Forks: {info.get('forks_count', 0)}] | "
                f"**Language:** {info.get('language', 'N/A')}\n"
                f"**Description:** {info.get('description', '')}\n"
                f"**URL:** https://github.com/{owner}/{repo}\n\n"
            )
    except Exception:
        meta_str = f"# GitHub: {owner}/{repo}\nURL: https://github.com/{owner}/{repo}\n\n"

    # Fetch README
    readme_content = ""
    for r_url in [readme_url, readme_alt]:
        try:
            req = urllib.request.Request(r_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                readme_content = resp.read().decode("utf-8", errors="replace")
                if readme_content:
                    break
        except Exception:
            continue

    if not readme_content:
        # Fallback to Scrapling
        from actions.web_reader import extract_web_content
        return extract_web_content(f"https://github.com/{owner}/{repo}")

    return meta_str + "## README:\n\n" + readme_content[:8000]


def agent_reach_action(parameters: dict, player=None, speak=None) -> str:
    """Action handler called by core.action_loader."""
    platform = (parameters.get("platform") or "auto").lower()
    target = parameters.get("target") or parameters.get("url") or parameters.get("query") or ""

    if not target:
        return "Please provide a target URL, video link, Reddit thread, or GitHub repository."

    # Auto detect platform if not specified
    low_target = target.lower()
    if platform == "auto":
        if "youtube.com" in low_target or "youtu.be" in low_target:
            platform = "youtube"
        elif "reddit.com" in low_target:
            platform = "reddit"
        elif "github.com" in low_target:
            platform = "github"
        elif "twitter.com" in low_target or "x.com" in low_target:
            platform = "twitter"
        else:
            platform = "web"

    if platform == "youtube":
        result = fetch_youtube_transcript(target)
    elif platform == "reddit":
        result = fetch_reddit_discussion(target)
    elif platform == "github":
        result = fetch_github_repository(target)
    else:
        if not target.startswith("http://") and not target.startswith("https://") and (" " in target or "." not in target):
            from actions.web_search import web_search
            return web_search({"query": target, "mode": "research"}, player=player)
        from actions.web_reader import extract_web_content
        result = extract_web_content(target)

    if player and hasattr(player, "show_content") and result:
        player.show_content(f"AGENT REACH — {platform.upper()}", result[:2000])

    return result


# ── Action Discovery TOOL Schema ─────────────────────────────────────────────
TOOL = {
    "name": "agent_reach",
    "description": (
        "Extract deep content, video transcripts, social discussions, and repository intelligence across platforms. "
        "Supports YouTube (full timestamps & transcript), Reddit (posts & top comments), GitHub (README & structure), and deep web articles."
    ),
    "behavior": "NON_BLOCKING",
    "scheduling": "WHEN_IDLE",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "target": {
                "type": "STRING",
                "description": "The URL, video ID, Reddit thread, or GitHub repository to extract.",
            },
            "platform": {
                "type": "STRING",
                "enum": ["auto", "youtube", "reddit", "github", "web"],
                "description": "Platform to extract from. Defaults to 'auto' based on the URL.",
            },
        },
        "required": ["target"],
    },
    "handler": agent_reach_action,
}
