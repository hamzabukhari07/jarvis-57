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
import threading
from pathlib import Path
import urllib.request
import urllib.parse
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


def _transcribe_video_audio(url: str, max_duration_sec: int = 0, include_timestamps: bool = True) -> Optional[str]:
    """Download audio from video URL (YouTube, Instagram reel, TikTok, Shorts) and transcribe with faster-whisper/whisper."""
    import os
    import tempfile
    try:
        import yt_dlp
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_template = os.path.join(tmp_dir, "audio.%(ext)s")
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "format": "bestaudio/best",
                "outtmpl": out_template,
                "extractor_args": {"youtube": {"player_client": ["android", "ios", "tv_embedded", "mweb"]}},
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "128",
                }],
                "socket_timeout": 15,
            }
            if max_duration_sec and max_duration_sec > 0:
                ydl_opts["postprocessor_args"] = ["-t", str(max_duration_sec)]

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            files = [os.path.join(tmp_dir, f) for f in os.listdir(tmp_dir) if f.endswith((".mp3", ".m4a", ".webm", ".opus", ".wav"))]
            if not files:
                return None

            audio_path = files[0]
            try:
                from faster_whisper import WhisperModel
                threads = min(6, os.cpu_count() or 4)
                model = WhisperModel("base", device="cpu", compute_type="int8", cpu_threads=threads)
                segments, info = model.transcribe(audio_path, beam_size=1, vad_filter=True)
                if include_timestamps:
                    transcribed_lines = []
                    for s in segments:
                        txt = s.text.strip()
                        if txt:
                            mins, secs = divmod(int(s.start), 60)
                            transcribed_lines.append(f"[{mins:02d}:{secs:02d}] {txt}")
                    if transcribed_lines:
                        return "\n".join(transcribed_lines)
                else:
                    transcribed_lines = [s.text.strip() for s in segments if s.text.strip()]
                    if transcribed_lines:
                        return " ".join(transcribed_lines)
            except Exception as fe:
                logger.debug(f"faster-whisper transcription fallback: {fe}")
                try:
                    import whisper
                    model = whisper.load_model("base")
                    res = model.transcribe(audio_path)
                    return (res.get("text") or "").strip()
                except Exception:
                    pass
    except Exception as e:
        logger.debug(f"Video audio transcription failed for {url}: {e}")
    return None


def fetch_youtube_transcript(video_url_or_id: str, max_chars: int = 150000, allow_audio_fallback: bool = True) -> str:
    """Fetch video transcript and metadata for a YouTube video, with oEmbed and multi-fallback resilience.

    Set `allow_audio_fallback=False` for batch/report use: the audio download +
    local Whisper path is minutes-per-video and must never run for a multi-source
    report (metadata + description is enough there).
    """
    video_id = _extract_youtube_id(video_url_or_id)
    if not video_id:
        return f"Could not identify a valid YouTube video ID from '{video_url_or_id}'."

    title = f"YouTube Video [{video_id}]"
    channel = "YouTube Creator"
    channel_url = ""
    description = ""
    transcript_text = ""

    # 1. Fetch guaranteed metadata via YouTube oEmbed API (Never blocked by bot verification or 429)
    try:
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        req = urllib.request.Request(oembed_url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            oedata = json.loads(resp.read().decode("utf-8"))
            title = oedata.get("title") or title
            channel = oedata.get("author_name") or channel
            channel_url = oedata.get("author_url") or ""
    except Exception as e:
        logger.debug(f"YouTube oEmbed fetch error: {e}")

    # 2. Fetch transcript via youtube_transcript_api (if available)
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        snippets = None
        try:
            snippets = YouTubeTranscriptApi.get_transcript(video_id)
        except Exception:
            try:
                t_list = YouTubeTranscriptApi.list_transcripts(video_id)
                for t in t_list:
                    try:
                        snippets = t.fetch()
                        if snippets:
                            break
                    except Exception:
                        continue
            except Exception:
                pass

        if snippets:
            lines = []
            for item in snippets:
                text = (item.get("text") if isinstance(item, dict) else getattr(item, "text", "")).strip()
                start = int(item.get("start") if isinstance(item, dict) else getattr(item, "start", 0))
                mins, secs = divmod(start, 60)
                timestamp = f"[{mins:02d}:{secs:02d}]"
                if text:
                    lines.append(f"{timestamp} {text}")
            transcript_text = "\n".join(lines)
    except Exception as e:
        logger.warning(f"youtube_transcript_api failed: {e}")

    # 3. Fetch metadata & description via yt-dlp
    try:
        import yt_dlp
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": True,
            "no_warnings": True,
            "extractor_args": {"youtube": {"player_client": ["android", "ios", "tv_embedded", "mweb"]}},
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            if info:
                title = info.get("title") or title
                channel = info.get("uploader") or info.get("channel") or channel
                description = (info.get("description") or "")[:1200]
    except Exception as e:
        logger.warning(f"yt-dlp info extraction failed: {e}")

    # 4. If transcript is empty (due to 429 / bot restriction), fallback to full audio download + faster-whisper
    if not transcript_text and allow_audio_fallback:
        try:
            logger.info(f"youtube_transcript_api unavailable for {video_id}, transcribing spoken audio via local Whisper...")
            whisper_text = _transcribe_video_audio(f"https://www.youtube.com/watch?v={video_id}", max_duration_sec=0, include_timestamps=True)
            if whisper_text:
                transcript_text = whisper_text
        except Exception as we:
            logger.debug(f"YouTube audio transcription fallback failed: {we}")

    # 5. If description is still missing and transcript is empty, search web for video context
    if not description and not transcript_text:
        try:
            from actions.web_search import web_search
            search_context = web_search({"query": f'"{title}" site:youtube.com', "mode": "search"})
            if search_context and len(search_context) > 40:
                lines = [l for l in search_context.split("\n") if len(l.strip()) > 20 and not l.startswith("http")]
                if lines:
                    description = "\n".join(lines[:3])
        except Exception:
            pass

    # Build comprehensive structured markdown response
    header = [
        f"# {title}",
        f"**Channel:** [{channel}]({channel_url if channel_url else 'https://www.youtube.com/watch?v=' + video_id})",
        f"**URL:** https://www.youtube.com/watch?v={video_id}\n",
    ]
    if description:
        header.append(f"## Video Description / Summary:\n{description}\n")

    if transcript_text:
        header.append(f"## Video Transcript / Captions:\n{transcript_text}")
    else:
        header.append(f"*(Full captions unavailable due to YouTube platform bot restriction. Video title, channel, and overview details shown above.)*")

    full_result = "\n".join(header)
    if len(full_result) > max_chars:
        return full_result[:max_chars] + f"\n\n... [Truncated at {max_chars} chars]"
    return full_result


def fetch_youtube_trending(region: str = "US", max_results: int = 8) -> List[Dict[str, Any]]:
    """Fetch trending videos via yt-dlp."""
    import yt_dlp
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": True,
        "playlistend": max_results,
    }
    entries = []
    url = f"https://www.youtube.com/feed/trending?gl={region.upper()}"
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            entries = info.get("entries", []) if info else []
    except Exception:
        entries = []

    if not entries:
        search_query = f"ytsearch{max_results}:trending videos {region.upper()}"
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                entries = info.get("entries", []) if info else []
        except Exception:
            entries = []

    return [
        {
            "rank": i + 1,
            "title": e.get("title", "Unknown"),
            "channel": e.get("uploader") or e.get("channel", "Unknown"),
            "url": e.get("url") or f"https://www.youtube.com/watch?v={e.get('id', '')}",
        }
        for i, e in enumerate(entries)
    ]


def fetch_youtube_search(query: str, max_results: int = 5) -> str:
    """Perform YouTube search via yt-dlp and return structured markdown results."""
    clean_q = query.strip()
    import yt_dlp

    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": True,
        "playlistend": max_results,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch{max_results}:{clean_q}", download=False)
            entries = info.get("entries", []) if info else []
            if entries:
                lines = [
                    f"# YouTube Search Results for: '{clean_q}'",
                    f"Showing top {len(entries)} videos:\n",
                ]
                for i, e in enumerate(entries):
                    t = e.get("title", "Unknown")
                    u = e.get("url") or f"https://www.youtube.com/watch?v={e.get('id', '')}"
                    ch = e.get("uploader") or e.get("channel", "Unknown")
                    views = e.get("view_count", "N/A")
                    if isinstance(views, int):
                        views = f"{views:,}"
                    lines.append(f"{i+1}. **[{t}]({u})** — Channel: {ch} | Views: {views}")
                return "\n".join(lines)
    except Exception as e:
        logger.warning(f"fetch_youtube_search failed for {clean_q}: {e}")

    return f"No YouTube search results found for: {query}"



def _is_direct_reddit_url(target: str) -> bool:
    """Check if a string is a valid direct Reddit post/thread URL rather than a search query."""
    raw = (target or "").strip().lower()
    if not raw or " " in raw or "site:" in raw or "subreddit:" in raw:
        return False
    return (
        raw.startswith(("http://", "https://")) and any(d in raw for d in ("reddit.com/r/", "reddit.com/user/", "reddit.com/comments/", "redd.it/"))
    ) or (
        raw.startswith(("reddit.com/r/", "www.reddit.com/r/", "redd.it/"))
    )


def fetch_reddit_discussion(url: str, max_comments: int = 10) -> str:
    """Fetch a Reddit post and top comments directly via public JSON endpoint or search."""
    clean_url = (url or "").strip()
    if not _is_direct_reddit_url(clean_url):
        from actions.web_search import web_search
        clean_q = re.sub(r'\bsite:reddit\.com\b', '', clean_url, flags=re.IGNORECASE).strip()
        return web_search({"query": f"site:reddit.com {clean_q}", "mode": "research"})

    if not clean_url.startswith(("http://", "https://")):
        clean_url = "https://" + clean_url
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
        logger.warning(f"fetch_reddit_discussion direct JSON failed for {clean_url}: {e}")
        # Try a full-page markdown extraction (Scrapling/Jina can sometimes reach
        # Reddit where the public JSON endpoint is blocked), then a search snippet.
        try:
            from actions.web_reader import extract_web_content
            page = extract_web_content(clean_url.replace(".json", ""), max_chars=10000)
            if page and len(page.strip()) > 200:
                return page
        except Exception:
            pass
        from actions.web_search import web_search
        return web_search({"query": f"site:reddit.com {url}", "mode": "research"})


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


def fetch_github_search(query: str, max_results: int = 5) -> str:
    """Perform GitHub repository search via public GitHub REST API and return formatted markdown."""
    clean_q = query.strip()
    headers = {"User-Agent": "Zezo-Agent-Reach/2.0"}
    encoded_q = urllib.parse.quote_plus(clean_q)
    api_url = f"https://api.github.com/search/repositories?q={encoded_q}&sort=stars&order=desc&per_page={max_results}"

    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        items = data.get("items", [])
        if not items:
            return f"No GitHub repositories found matching search query: '{clean_q}'"

        lines = [
            f"# GitHub Search Results for: '{clean_q}'",
            f"Showing top {len(items)} repositories sorted by stars:\n",
        ]
        for i, item in enumerate(items):
            full_name = item.get("full_name", "Unknown")
            stars = item.get("stargazers_count", 0)
            forks = item.get("forks_count", 0)
            lang = item.get("language", "N/A")
            desc = (item.get("description") or "").strip()
            html_url = item.get("html_url", f"https://github.com/{full_name}")

            lines.append(
                f"{i+1}. **[{full_name}]({html_url})** — ⭐ {stars:,} stars | 🍴 {forks:,} forks | Language: {lang}\n"
                f"   *{desc}*\n"
            )

        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"fetch_github_search failed for query '{clean_q}': {e}")
        try:
            from actions.web_search import web_search
            return web_search({"query": f"site:github.com {clean_q}", "mode": "research"})
        except Exception:
            return f"Unable to perform GitHub search for '{clean_q}': {e}"



def fetch_twitter_thread(url_or_handle: str) -> str:
    """Fetch Twitter / X status or thread via FixTweet (fxtwitter) API, Nitter instances, or web_reader fallback."""
    raw = url_or_handle.strip()
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    # 1. Try FixTweet (fxtwitter) API if target contains a status ID
    status_match = re.search(r"(?:twitter\.com|x\.com)/(?:[^/]+/)?status/(\d+)", raw)
    if status_match:
        status_id = status_match.group(1)
        api_url = f"https://api.fxtwitter.com/status/{status_id}"
        try:
            req = urllib.request.Request(api_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                tweet = data.get("tweet", {})
                text = tweet.get("text", "")
                author = tweet.get("author", {}).get("name") or tweet.get("author", {}).get("screen_name", "Author")
                likes = tweet.get("likes", 0)
                retweets = tweet.get("retweets", 0)
                if text:
                    return (
                        f"# Tweet by {author}\n"
                        f"**URL:** https://twitter.com/i/status/{status_id}\n"
                        f"**Likes:** {likes:,} | **Retweets:** {retweets:,}\n\n"
                        f"{text}"
                    )
        except Exception as e:
            logger.warning(f"fxtwitter API failed for status {status_id}: {e}")

    # 2. Attempt fetching via Nitter mirrors
    nitter_instances = [
        "https://nitter.privacydev.net",
        "https://nitter.poast.org",
        "https://nitter.cz",
    ]

    path = ""
    match = re.search(r"(?:twitter\.com|x\.com)/([a-zA-Z0-9_]+/status/\d+|[a-zA-Z0-9_]+)", raw)
    if match:
        path = match.group(1)
    elif raw.startswith("@"):
        path = raw.lstrip("@")
    elif not raw.startswith("http"):
        path = raw

    if path:
        for instance in nitter_instances:
            nitter_url = f"{instance}/{path}"
            try:
                req = urllib.request.Request(nitter_url, headers=headers)
                with urllib.request.urlopen(req, timeout=8) as resp:
                    html = resp.read().decode("utf-8", errors="replace")
                    if "tweet-content" in html or "main-thread" in html:
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(html, "html.parser")
                        tweets = soup.find_all("div", class_="tweet-content")
                        if tweets:
                            content = "\n\n".join([f"• {t.get_text().strip()}" for t in tweets[:5]])
                            return f"# Twitter / X Thread ({path})\n\n{content}"
            except Exception:
                continue

    # 3. Fallback to web_reader
    if raw.startswith("http"):
        try:
            from actions.web_reader import extract_web_content
            res = extract_web_content(raw)
            if res and len(res.strip()) > 50 and "JavaScript" not in res and "Enable JavaScript" not in res:
                return f"# Twitter / X Content\nURL: {raw}\n\n{res}"
        except Exception:
            pass

    return "Twitter data unavailable — try pasting the tweet text directly."



def fetch_youtube_channel(channel_url_or_handle: str, max_results: int = 10) -> str:
    """Fetch YouTube channel info, subscriber count, and top videos via yt-dlp."""
    raw = channel_url_or_handle.strip()
    import yt_dlp

    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": True,
        "playlistend": max_results,
    }

    url = raw
    if not url.startswith("http"):
        handle = raw.lstrip("@")
        url = f"https://www.youtube.com/@{handle}"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info:
                channel = info.get("uploader") or info.get("channel") or info.get("title") or "YouTube Channel"
                subscribers = info.get("subscriber_count", "N/A")
                if isinstance(subscribers, int):
                    subscribers = f"{subscribers:,}"
                
                entries = info.get("entries", [])
                lines = [
                    f"# YouTube Channel: {channel}",
                    f"**Subscribers:** {subscribers} | **URL:** {url}\n",
                    f"## Top Videos / Recent Uploads (Max {max_results}):",
                ]
                for i, e in enumerate(entries[:max_results]):
                    title = e.get("title", "Unknown")
                    views = e.get("view_count", "N/A")
                    if isinstance(views, int):
                        views = f"{views:,}"
                    v_url = e.get("url") or f"https://www.youtube.com/watch?v={e.get('id', '')}"
                    lines.append(f"{i+1}. **[{title}]({v_url})** — Views: {views}")

                return "\n".join(lines)
    except Exception as e:
        logger.warning(f"fetch_youtube_channel failed for {url}: {e}")

    return f"Unable to fetch YouTube channel details for: {channel_url_or_handle}"


def fetch_stackoverflow(question_url_or_query: str) -> str:
    """Fetch Stack Overflow question, accepted answer, and top answers via StackExchange API."""
    raw = question_url_or_query.strip()
    headers = {"User-Agent": "Zezo-Agent-Reach/2.0"}

    question_id = None
    m = re.search(r"stackoverflow\.com/questions/(\d+)", raw)
    if m:
        question_id = m.group(1)

    try:
        if question_id:
            api_url = f"https://api.stackexchange.com/2.3/questions/{question_id}?site=stackoverflow&filter=withbody"
        else:
            q = urllib.parse.quote_plus(raw)
            api_url = f"https://api.stackexchange.com/2.3/search/advanced?order=desc&sort=relevance&q={q}&site=stackoverflow&filter=withbody"

        req = urllib.request.Request(api_url, headers=headers)
        import gzip
        with urllib.request.urlopen(req, timeout=12) as resp:
            content = resp.read()
            try:
                content = gzip.decompress(content)
            except Exception:
                pass
            data = json.loads(content.decode('utf-8'))

        items = data.get("items", [])
        if not items:
            return f"No Stack Overflow questions found for: {question_url_or_query}"

        q_item = items[0]
        q_id = q_item.get("question_id")
        title = q_item.get("title", "Stack Overflow Question")
        score = q_item.get("score", 0)
        body = q_item.get("body_markdown") or q_item.get("body") or ""
        clean_body = re.sub(r'<[^>]+>', '', body)

        # Fetch answers
        ans_api = f"https://api.stackexchange.com/2.3/questions/{q_id}/answers?order=desc&sort=votes&site=stackoverflow&filter=withbody"
        ans_req = urllib.request.Request(ans_api, headers=headers)
        answers = []
        try:
            with urllib.request.urlopen(ans_req, timeout=10) as a_resp:
                a_content = a_resp.read()
                try:
                    a_content = gzip.decompress(a_content)
                except Exception:
                    pass
                a_data = json.loads(a_content.decode('utf-8'))
                answers = a_data.get("items", [])
        except Exception:
            pass

        out = [
            f"# Stack Overflow: {title}",
            f"**Score:** {score} | **URL:** https://stackoverflow.com/q/{q_id}\n",
            "## Question Details:",
            clean_body[:1500] if clean_body else "(No details text)",
            "\n## Top Answers:",
        ]

        if not answers:
            out.append("(No answers found yet for this question.)")
        else:
            for i, ans in enumerate(answers[:3]):
                is_accepted = " ✅ [Accepted Answer]" if ans.get("is_accepted") else ""
                a_score = ans.get("score", 0)
                a_body = ans.get("body_markdown") or ans.get("body") or ""
                clean_a_body = re.sub(r'<[^>]+>', '', a_body)
                out.append(f"### Answer {i+1} (Score: {a_score}){is_accepted}:\n{clean_a_body[:1200]}\n")

        return "\n".join(out)

    except Exception as e:
        logger.warning(f"fetch_stackoverflow failed: {e}")
        from actions.web_reader import extract_web_content
        return extract_web_content(raw if raw.startswith("http") else f"https://stackoverflow.com/search?q={urllib.parse.quote_plus(raw)}")


def fetch_hackernews(story_url_or_query: str) -> str:
    """Fetch Hacker News story, score, and top comments via Firebase HN API."""
    raw = story_url_or_query.strip()
    headers = {"User-Agent": "Zezo-Agent-Reach/2.0"}

    story_id = None
    m = re.search(r"item\?id=(\d+)", raw)
    if m:
        story_id = m.group(1)

    try:
        if not story_id:
            # Algolia search API for HN
            q = urllib.parse.quote_plus(raw)
            search_api = f"https://hn.algolia.com/api/v1/search?query={q}&tags=story"
            req = urllib.request.Request(search_api, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                search_data = json.loads(resp.read().decode('utf-8'))
                hits = search_data.get("hits", [])
                if hits:
                    story_id = hits[0].get("objectID")

        if not story_id:
            return f"No Hacker News stories found for: {story_url_or_query}"

        # Fetch story details from Firebase API
        story_api = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
        s_req = urllib.request.Request(story_api, headers=headers)
        with urllib.request.urlopen(s_req, timeout=10) as s_resp:
            story = json.loads(s_resp.read().decode('utf-8'))

        title = story.get("title", "Hacker News Story")
        author = story.get("by", "Unknown")
        score = story.get("score", 0)
        url = story.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
        kids = story.get("kids", [])

        out = [
            f"# Hacker News: {title}",
            f"**Author:** {author} | **Points:** {score} | **Story URL:** {url}",
            f"**HN Discussion:** https://news.ycombinator.com/item?id={story_id}\n",
            "## Top Discussion Comments:",
        ]

        comments_added = 0
        for kid_id in kids[:8]:
            try:
                c_api = f"https://hacker-news.firebaseio.com/v0/item/{kid_id}.json"
                c_req = urllib.request.Request(c_api, headers=headers)
                with urllib.request.urlopen(c_req, timeout=5) as c_resp:
                    comment = json.loads(c_resp.read().decode('utf-8'))
                    c_text = comment.get("text", "").strip()
                    c_by = comment.get("by", "[deleted]")
                    if c_text and not comment.get("deleted") and not comment.get("dead"):
                        # Clean simple HTML tags from HN comments
                        clean_text = re.sub(r'<[^>]+>', '', c_text)
                        out.append(f"- **{c_by}**:\n  {clean_text[:600]}\n")
                        comments_added += 1
                        if comments_added >= 5:
                            break
            except Exception:
                continue

        return "\n".join(out)

    except Exception as e:
        logger.warning(f"fetch_hackernews failed: {e}")
        from actions.web_reader import extract_web_content
        return extract_web_content(raw if raw.startswith("http") else f"https://news.ycombinator.com/")


def fetch_rss_feed(url: str, max_items: int = 5) -> str:
    """Fetch latest items from an RSS/Atom feed using feedparser."""
    raw = url.strip()
    try:
        import feedparser
        feed = feedparser.parse(raw)
        if not feed.entries:
            return f"No entries found in RSS feed: {url}"

        title = feed.feed.get("title", "RSS Feed")
        link = feed.feed.get("link", url)
        lines = [
            f"# RSS Feed: {title}",
            f"**URL:** {link}\n",
            f"## Latest {min(len(feed.entries), max_items)} Posts:",
        ]

        for i, entry in enumerate(feed.entries[:max_items]):
            e_title = entry.get("title", "Untitled Post")
            e_link = entry.get("link", "")
            published = entry.get("published") or entry.get("updated") or "N/A"
            summary = entry.get("summary") or entry.get("description") or ""
            clean_summary = re.sub(r'<[^>]+>', '', summary)[:300]
            lines.append(f"{i+1}. **[{e_title}]({e_link})** ({published})\n   {clean_summary}\n")

        return "\n".join(lines)

    except Exception as e:
        logger.warning(f"fetch_rss_feed failed: {e}")
        return f"Unable to parse RSS feed from '{url}': {e}"


def _resolve_output_path(file_path: str) -> Path:
    raw = str(file_path or "").strip()
    if not raw:
        return Path.home() / "Desktop" / "Research_Report.md"
    if raw.lower().startswith("desktop/") or raw.lower().startswith("desktop\\"):
        sub = raw[8:].lstrip("/\\")
        return Path.home() / "Desktop" / sub
    p = Path(raw)
    if not p.is_absolute():
        p = Path.home() / "Desktop" / raw
    return p


def _run_bounded(fn, timeout: float, default=None):
    """Run fn() in a daemon thread; return its result, or `default` if it overruns/fails.

    Deep extraction touches many third-party hosts; one slow host must never stall
    the whole report, so every fetch is individually time-bounded.
    """
    box = [default]

    def _worker():
        try:
            box[0] = fn()
        except Exception as e:
            logger.debug("bounded call failed: %s", e)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        logger.warning("agent_reach: a fetch exceeded %.0fs and was skipped", timeout)
    return box[0]


def _analyze_resource(title: str, url: str, content: str, max_input: int = 7000) -> str:
    """Turn a FULLY extracted page/transcript/thread into a factual analysis.

    Falls back to a trimmed verbatim extract so the report always carries the real
    body text — never just a one-line search snippet.
    """
    text = (content or "").strip()
    if not text:
        return ""
    try:
        from core.llm_router import generate_text
        out = generate_text(
            f"Resource: {title}\nURL: {url}\n\nFull extracted content:\n{text[:max_input]}\n\n"
            "Write a factual 3-5 sentence analysis of what THIS resource actually says: its main "
            "argument/claim, the concrete tools, methods, numbers or steps it names, and one short "
            "quote if present. Use ONLY the content above. Never invent anything.",
            system="You are a precise research analyst. Be concrete and factual.",
            tier="fast",
            timeout_ms=45000,
        )
        if out and out.strip():
            return out.strip()
    except Exception as e:
        logger.warning("resource analysis failed for %s: %s", url, e)
    return text[:1200] + ("…" if len(text) > 1200 else "")


def _synthesize_research(query: str, digests: list) -> str:
    """Compile an executive summary + key findings from the collected analyses."""
    if not digests:
        return ""
    joined = "\n\n".join(digests)[:14000]
    try:
        from core.llm_router import generate_text
        out = generate_text(
            f"Research topic: {query}\n\n"
            f"Analyses of the real sources that were fully fetched are below.\n\n{joined}\n\n"
            "Write a substantial research synthesis using ONLY the material above:\n"
            "## 🎯 Executive Summary\n8-12 sentences: what the sources collectively say, where they "
            "agree/disagree, and the strongest concrete methods people use.\n\n"
            "## 🔑 Key Findings\n8-12 detailed bullet points, each naming the source it came from.\n\n"
            "## 🛠️ How people actually do it (step by step)\nA practical, ordered playbook drawn "
            "from the sources.\n\n"
            "Never invent facts, tools or numbers that are not in the source analyses above.",
            system="You are a senior research editor writing an exhaustive, factual report.",
            tier="smart",
            timeout_ms=90000,
        )
        if out and out.strip():
            return out.strip()
    except Exception as e:
        logger.warning("research synthesis failed: %s", e)
    return ""


def fetch_multi_platform_search(query: str, output_file: Optional[str] = None, ctx: Any = None) -> tuple[str, list[dict]]:
    """Deep multi-source research compiler.

    Unlike a plain search aggregator, this reads the FULL content behind each
    discovered resource (YouTube transcript, Reddit post + comments, GitHub README,
    Hacker News thread, and web/blog article body), analyses each one, then
    synthesises an executive summary, key findings and a practical playbook.
    """
    clean_q = (query or "").strip()
    subtasks = [
        {"title": "Discover real sources (YouTube, Reddit, GitHub, HN, web)", "status": "running"},
        {"title": "Deep-extract full content per resource", "status": "queued"},
        {"title": "Analyse each resource (full text)", "status": "queued"},
        {"title": "Synthesise executive summary & key findings", "status": "queued"},
        {"title": "Write Markdown report", "status": "queued"},
    ]

    from actions.web_search import _ddg_search
    from actions.web_reader import extract_web_content
    from concurrent.futures import ThreadPoolExecutor

    def _progress(pct, msg):
        if ctx:
            ctx.report(pct, msg)

    _progress(10, f"Discovering real sources for '{clean_q}'...")

    # ── 1. Discovery (URLs only, cheap) ──────────────────────────────────────
    yt_candidates: list = []
    reddit_candidates: list = []
    github_candidates: list = []
    hn_candidates: list = []
    web_candidates: list = []

    try:
        import yt_dlp
        with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True, "extract_flat": True, "playlistend": 5}) as ydl:
            info = ydl.extract_info(f"ytsearch5:{clean_q}", download=False)
        for e in (info or {}).get("entries", [])[:4]:
            t = e.get("title") or "YouTube video"
            u = e.get("url") or f"https://www.youtube.com/watch?v={e.get('id', '')}"
            ch = e.get("uploader") or e.get("channel") or "YouTube"
            yt_candidates.append((f"{t} — {ch}", u))
    except Exception as e:
        logger.warning(f"multi discovery YouTube failed: {e}")

    try:
        for r in _ddg_search(f"{clean_q} blog article", max_results=8):
            url = r.get("url", "")
            if url and not any(d in url for d in (
                "youtube.com", "youtu.be", "reddit.com", "github.com",
                "news.ycombinator.com", "twitter.com", "x.com", "facebook.com",
            )):
                web_candidates.append((r.get("title") or url, url))
    except Exception as e:
        logger.warning(f"multi discovery web failed: {e}")

    try:
        for r in _ddg_search(f"site:reddit.com {clean_q}", max_results=8):
            url = r.get("url", "")
            if "reddit.com" in url:
                reddit_candidates.append((r.get("title") or url, url))
    except Exception as e:
        logger.warning(f"multi discovery reddit failed: {e}")

    try:
        gh_raw = fetch_github_search(clean_q, max_results=5)
        for m in re.finditer(r"\[([^\]]+)\]\((https://github\.com/[^)]+)\)", gh_raw):
            github_candidates.append((m.group(1), m.group(2)))
    except Exception as e:
        logger.warning(f"multi discovery github failed: {e}")

    try:
        api = (
            "https://hn.algolia.com/api/v1/search?query="
            f"{urllib.parse.quote_plus(clean_q)}&tags=story&hitsPerPage=6"
        )
        req = urllib.request.Request(api, headers={"User-Agent": "Zezo-Agent-Reach/2.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            hits = json.loads(resp.read().decode("utf-8")).get("hits", [])
        for h in hits[:5]:
            oid = h.get("objectID")
            if oid:
                hn_candidates.append(
                    (h.get("title") or "Hacker News story", f"https://news.ycombinator.com/item?id={oid}")
                )
    except Exception as e:
        logger.warning(f"multi discovery HN failed: {e}")

    subtasks[0]["status"] = "done"
    subtasks[1]["status"] = "running"
    _progress(25, "Deep-extracting full content per resource...")

    # ── 2. Deep extraction (full body per resource, time-bounded, parallel) ──
    def _extract_all(candidates, extractor, limit, per_timeout):
        picked = candidates[:limit]
        if not picked:
            return []
        results: list = [None] * len(picked)

        def _job(i, title, url):
            text = _run_bounded(lambda: extractor(url), per_timeout, default="") or ""
            results[i] = (title, url, text)

        with ThreadPoolExecutor(max_workers=min(4, len(picked))) as ex:
            for f in [ex.submit(_job, i, t, u) for i, (t, u) in enumerate(picked)]:
                f.result()
        return [r for r in results if r]

    yt_extracted = _extract_all(
        yt_candidates,
        lambda u: fetch_youtube_transcript(u, max_chars=40000, allow_audio_fallback=False),
        3,
        25,
    )
    reddit_extracted = _extract_all(reddit_candidates, lambda u: fetch_reddit_discussion(u, max_comments=8), 3, 25)
    github_extracted = _extract_all(github_candidates, fetch_github_repository, 2, 25)
    hn_extracted = _extract_all(hn_candidates, fetch_hackernews, 3, 25)
    web_extracted = _extract_all(web_candidates, lambda u: extract_web_content(u, max_chars=12000), 4, 30)

    subtasks[1]["status"] = "done"
    subtasks[2]["status"] = "running"
    _progress(55, "Analysing each resource using the full extracted text...")

    def _digest(items):
        out = []
        for title, url, text in items:
            analysis = _analyze_resource(title, url, text)
            if analysis:
                out.append((title, url, analysis))
        return out

    yt_digests = _digest(yt_extracted)
    reddit_digests = _digest(reddit_extracted)
    github_digests = _digest(github_extracted)
    hn_digests = _digest(hn_extracted)
    web_digests = _digest(web_extracted)

    groups = (web_digests, reddit_digests, hn_digests, yt_digests, github_digests)
    all_flat = [x for g in groups for x in g]
    all_digests = [f"[{t}] {u}\n{a}" for (t, u, a) in all_flat]

    subtasks[2]["status"] = "done"
    subtasks[3]["status"] = "running"
    _progress(75, "Synthesising executive summary & key findings...")
    synthesis = _synthesize_research(clean_q, all_digests)

    subtasks[3]["status"] = "done"
    subtasks[4]["status"] = "running"
    _progress(90, "Writing the Markdown report...")

    import time
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")

    def _render_section(heading, group):
        lines = [f"## {heading}", ""]
        if not group:
            lines.append("*(No extractable resource found for this source.)*")
            lines.append("")
            return lines
        for i, (title, url, analysis) in enumerate(group, 1):
            lines.append(f"### {i}. [{title}]({url})")
            lines.append(f"**Source:** {url}")
            lines.append("")
            lines.append(analysis)
            lines.append("")
        return lines

    report_lines = [
        f"# Deep Research Report: {clean_q}",
        f"*Compiled by ZEZO on {now_str} — {len(all_flat)} resources fully extracted and analysed.*",
        "",
        "## 🎯 Executive Summary & Key Findings",
        synthesis if synthesis else "*(Synthesis unavailable — see the per-source analyses below.)*",
        "",
        "---",
    ]
    report_lines += _render_section("📝 Web Articles & Blogs (full-text analysed)", web_digests)
    report_lines += ["---"] + _render_section("💬 Reddit Discussions (full thread analysed)", reddit_digests)
    report_lines += ["---"] + _render_section("🍊 Hacker News Discussions (full thread analysed)", hn_digests)
    report_lines += ["---"] + _render_section("🎥 YouTube Videos (transcript analysed)", yt_digests)
    report_lines += ["---"] + _render_section("💻 GitHub Repositories (README analysed)", github_digests)

    report_lines += ["", "---", "## 📚 All Sources"]
    for i, (title, url, _a) in enumerate(all_flat, 1):
        report_lines.append(f"{i}. [{title}]({url})")

    final_report = "\n".join(report_lines)

    # ── 3. Save to disk if output_file specified ─────────────────────────────
    if output_file:
        try:
            target_path = _resolve_output_path(output_file)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(final_report, encoding="utf-8")
            logger.info(f"Research report saved to {target_path}")
            _progress(100, f"Report saved to {target_path.name}")
        except Exception as e:
            logger.warning(f"Failed to write research report to {output_file}: {e}")

    subtasks[4]["status"] = "done"
    return final_report, subtasks





def fetch_instagram_content(url_or_target: str) -> str:
    """Extract captions, spoken transcript, creator intelligence, and video metadata from Instagram Reels or Posts."""
    raw = url_or_target.strip()
    # Clean tracking parameters from URL
    clean_url = raw.split("?")[0] if "instagram.com" in raw else raw

    # 1. High-speed metadata & caption extraction via yt-dlp
    try:
        import yt_dlp
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": False,
            "socket_timeout": 8,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clean_url, download=False)
            if info:
                title = info.get("title") or "Instagram Content"
                desc = info.get("description") or ""
                uploader = info.get("uploader") or info.get("uploader_id") or "Creator"
                likes = info.get("like_count")
                views = info.get("view_count")
                comments = info.get("comment_count")
                tags = info.get("tags") or []

                metrics = []
                if likes: metrics.append(f"❤️ {likes:,} Likes")
                if views: metrics.append(f"👁️ {views:,} Views")
                if comments: metrics.append(f"💬 {comments:,} Comments")
                metric_str = " | ".join(metrics) if metrics else "Public Post"
                tag_str = ", ".join(f"#{t}" for t in tags[:10]) if tags else "None"

                # If it is a reel or video, transcribe the spoken audio
                transcript = None
                if "/reel/" in clean_url or "/reels/" in clean_url or "/p/" in clean_url:
                    transcript = _transcribe_video_audio(clean_url)

                sections = [
                    f"# Instagram Reel Intelligence: {title}",
                    f"**Creator / Uploader:** @{uploader} | **Metrics:** {metric_str}",
                    f"**URL:** {clean_url}",
                    f"**Tags:** {tag_str}\n",
                ]

                if transcript:
                    sections.append(f"## 🎙️ Spoken Audio Transcript:\n{transcript}\n")

                sections.append(f"## 📝 Caption & Post Text:\n{desc if desc else '[No text caption provided in post]'}\n")

                return "\n".join(sections)
    except Exception as e:
        logger.warning(f"yt-dlp Instagram extraction failed: {e}")

    # 2. Fallback: r.jina.ai Markdown extraction
    try:
        jina_url = f"https://r.jina.ai/{clean_url}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        req = urllib.request.Request(jina_url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            content = resp.read().decode("utf-8", errors="replace").strip()
            if content and len(content) > 60:
                return (
                    f"# Instagram Content Intelligence\n"
                    f"**Source URL:** {clean_url}\n\n"
                    f"## Extracted Content:\n"
                    f"{content[:3000]}"
                )
    except Exception as e:
        logger.debug(f"Jina Instagram fallback failed: {e}")

    # 3. Fallback: General web reader
    from actions.web_reader import extract_web_content
    return extract_web_content(clean_url)


def fetch_tiktok_content(url_or_target: str) -> str:
    """Extract video transcript, captions, and creator metadata from TikTok."""
    raw = url_or_target.strip()
    clean_url = raw.split("?")[0] if "tiktok.com" in raw else raw
    try:
        import yt_dlp
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": False,
            "socket_timeout": 8,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clean_url, download=False)
            if info:
                title = info.get("title") or "TikTok Video"
                desc = info.get("description") or ""
                uploader = info.get("uploader") or info.get("uploader_id") or "Creator"
                likes = info.get("like_count")
                views = info.get("view_count")

                transcript = _transcribe_video_audio(clean_url)

                sections = [
                    f"# TikTok Video Intelligence: {title}",
                    f"**Creator:** @{uploader} | **Likes:** {likes:, if likes else 'N/A'}",
                    f"**URL:** {clean_url}\n",
                ]

                if transcript:
                    sections.append(f"## 🎙️ Spoken Audio Transcript:\n{transcript}\n")

                sections.append(f"## 📝 Caption & Text:\n{desc if desc else '[No caption]'}\n")

                return "\n".join(sections)
    except Exception as e:
        logger.warning(f"yt-dlp TikTok extraction failed: {e}")

    from actions.web_reader import extract_web_content
    return extract_web_content(clean_url)


def agent_reach_action(parameters: dict, player=None, speak=None) -> str:
    """Action handler called by core.action_loader."""
    platform = (parameters.get("platform") or "auto").lower()
    target = parameters.get("target") or parameters.get("url") or parameters.get("query") or ""

    if not target:
        return "Please provide a target URL, channel, query, or social media link."

    low_target = target.lower()

    # Canonical URL Domain Priority:
    # If the target URL points explicitly to a specific platform, override any mismatched platform parameter
    # (e.g., if LLM passed platform='youtube' while target is an Instagram Reel or TikTok)
    if "instagram.com" in low_target or "instagr.am" in low_target:
        platform = "instagram"
    elif "tiktok.com" in low_target:
        platform = "tiktok"
    elif "reddit.com" in low_target:
        platform = "reddit"
    elif "github.com" in low_target and " " not in low_target:
        platform = "github"
    elif "stackoverflow.com" in low_target:
        platform = "stackoverflow"
    elif "news.ycombinator.com" in low_target:
        platform = "hackernews"
    elif "twitter.com" in low_target or "x.com" in low_target:
        platform = "twitter"
    elif "youtube.com" in low_target or "youtu.be" in low_target:
        if any(k in low_target for k in ("/channel", "/@", "/c/")):
            platform = "youtube_channel"
        else:
            platform = "youtube"
    elif platform == "auto":
        if "rss" in low_target or "feed" in low_target or low_target.endswith(".xml"):
            platform = "rss"
        elif low_target.startswith("@"):
            platform = "twitter"
        else:
            platform = "web"

    # For heavy extraction operations, submit to task_manager for async background execution & Task Queue visibility
    if platform in ("multi", "youtube", "youtube_channel", "instagram", "tiktok", "reddit", "github", "twitter", "stackoverflow", "hackernews", "rss"):
        from core.task_manager import get_task_manager
        tm = get_task_manager()

        def _worker(p: dict, ctx):
            ctx.report(10, f"Extracting {platform} content for '{target}'...")
            subtasks_list = None
            out_file = p.get("output_file") or p.get("output_path") or p.get("file_path") or ""
            if platform == "multi":
                res, subtasks_list = fetch_multi_platform_search(target, output_file=out_file, ctx=ctx)
            elif platform == "youtube":
                v_id = _extract_youtube_id(target)
                res = fetch_youtube_transcript(target) if v_id else fetch_youtube_search(target, max_results=5)
            elif platform == "youtube_channel":
                res = fetch_youtube_channel(target)
            elif platform == "instagram":
                res = fetch_instagram_content(target)
            elif platform == "tiktok":
                res = fetch_tiktok_content(target)
            elif platform == "reddit":
                if _is_direct_reddit_url(target):
                    res = fetch_reddit_discussion(target)
                else:
                    from actions.web_search import web_search
                    clean_q = re.sub(r'\bsite:reddit\.com\b', '', target, flags=re.IGNORECASE).strip()
                    res = web_search({"query": f"site:reddit.com {clean_q}", "mode": "research"})
            elif platform == "github":
                if "github.com" in target or ("/" in target and " " not in target and not target.startswith("topic:")):
                    res = fetch_github_repository(target)
                else:
                    res = fetch_github_search(target, max_results=5)
            elif platform == "twitter":
                res = fetch_twitter_thread(target)
            elif platform == "stackoverflow":
                res = fetch_stackoverflow(target)
            elif platform == "hackernews":
                res = fetch_hackernews(target)
            elif platform == "rss":
                res = fetch_rss_feed(target)
            else:
                res = f"Completed extraction for {target}"

            ctx.report(100, "Done.")
            if player and hasattr(player, "show_content") and res:
                header_title = f"RESEARCH REPORT — {target[:25].upper()}" if platform == "multi" else f"AGENT REACH — {platform.upper()}"
                player.show_content(header_title, res)

            summary_msg = res if isinstance(res, str) else ""
            if platform == "multi" and out_file:
                summary_msg = (
                    f"The deep research report on '{target}' is complete and saved to {out_file} on your Desktop. "
                    "I read the full text of each source (articles, Reddit threads, Hacker News discussions, "
                    "YouTube transcripts and GitHub READMEs) and included a per-source analysis plus an executive summary."
                )

            return {
                "output": res,
                "summary": summary_msg,
                "result": res,
                "full_content": res,
                "subtasks": subtasks_list or [],
            }

        task_id = tm.submit(f"agent_reach:{platform}", _worker, parameters)
        return f"Searching {platform} for '{target}'. Task ID: {task_id}. Results will appear in HUD Live Display Canvas."

    # Synchronous web extraction fallback
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
        "Extract deep content, video transcripts, social discussions, repository intelligence, and multi-platform research across platforms. "
        "Supports YouTube (transcripts & channels), Instagram (Reels, posts & captions), TikTok (videos & captions), Reddit (posts & top comments), GitHub (README & search), Twitter/X threads, Stack Overflow (questions & answers), Hacker News, RSS feeds, and multi-platform research aggregator ('multi'). "
        "IMPORTANT: 'multi' does NOT just list search snippets — it FULLY FETCHES the body of every discovered source (web/blog article text, Reddit post+comments, Hacker News thread, YouTube transcript, GitHub README), analyses each one, synthesises an executive summary + key findings, and saves the report to an output file. Use it whenever the user asks for a research report, a deep summary, or to 'extract all the posts and analyze them'."
    ),
    "risk": "external_mutation",
    "enabled": True,
    "behavior": "NON_BLOCKING",
    "scheduling": "WHEN_IDLE",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "target": {
                "type": "STRING",
                "description": "The URL, video ID, channel, research topic query, Instagram reel/post URL, TikTok video URL, Reddit thread, Twitter link/handle, GitHub repository, or RSS feed to extract.",
            },
            "platform": {
                "type": "STRING",
                "enum": [
                    "auto",
                    "multi",
                    "youtube",
                    "youtube_channel",
                    "instagram",
                    "tiktok",
                    "reddit",
                    "github",
                    "twitter",
                    "stackoverflow",
                    "hackernews",
                    "rss",
                    "web",
                ],
                "description": "Platform to extract from or 'multi' for cross-platform research aggregator. Defaults to 'auto'.",
            },
            "output_file": {
                "type": "STRING",
                "description": "Optional file path (e.g. 'desktop/Rust_vs_Go_Research_Report.md') where the compiled research report should be written automatically.",
            },
        },
        "required": ["target"],
    },
    "handler": agent_reach_action,
}


