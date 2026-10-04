#youtube_video.py
import json
import re
import sys
import time
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from urllib.parse import quote_plus

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

try:
    import numpy as np
    _NUMPY = True
except ImportError:
    _NUMPY = False

try:
    import requests
    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    _TRANSCRIPT_OK = True
except ImportError:
    _TRANSCRIPT_OK = False

from config import get_os, is_windows, is_mac, is_linux


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR        = _get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

_YT_VIDEO_FILTER = "EgIQAQ%3D%3D"


def _get_api_key() -> str:
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["gemini_api_key"]


def _open_url(url: str) -> None:
    try:
        if is_mac():
            subprocess.Popen(["open", url])
        elif is_linux():
            subprocess.Popen(["xdg-open", url])
        else:
            subprocess.Popen(["cmd", "/c", "start", "", url], shell=False)
    except Exception as e:
        print(f"[YouTube] ⚠️ open_url failed: {e}")

def _find_video_url(query: str) -> str | None:
    """Find YouTube video URL for a query using yt-dlp search."""
    try:
        import yt_dlp
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": True,
            "playlistend": 1,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            entries = info.get("entries", []) if info else []
            if entries:
                e = entries[0]
                return e.get("url") or f"https://www.youtube.com/watch?v={e.get('id', '')}"
    except Exception as e:
        print(f"[YouTube] ⚠️ yt-dlp search failed: {e}")

    return None


def _extract_video_id(url: str) -> str | None:
    match = re.search(
        r"(?:v=|\/v\/|youtu\.be\/|\/embed\/|\/shorts\/)([A-Za-z0-9_-]{11})", url
    )
    return match.group(1) if match else None


def _is_valid_youtube_url(url: str) -> bool:
    return bool(re.search(r"(youtube\.com|youtu\.be)", url or ""))


def _ask_for_url(prompt_text: str = "YouTube video URL:") -> str | None:
    try:
        import tkinter as tk
        from tkinter import simpledialog

        root = tk._default_root
        if root is None:
            root = tk.Tk()
            root.withdraw()

        url = simpledialog.askstring("J.A.R.V.I.S", prompt_text, parent=root)
        return url.strip() if url else None
    except Exception as e:
        print(f"[YouTube] ⚠️ URL dialog failed: {e}")
        return None


def _summarize_with_gemini(transcript: str, video_url: str) -> str:
    """Summarise via the provider router (Groq → Gemini → Ollama). Falls back to
    Gemini automatically if Groq is unconfigured or rejects the long transcript."""
    from core.llm_router import generate_text

    max_chars = 80000
    truncated = transcript[:max_chars] + ("..." if len(transcript) > max_chars else "")
    try:
        return generate_text(
            f"Please summarize this YouTube video transcript:\n\n{truncated}",
            system=(
                "You are JARVIS, an AI assistant. "
                "Summarize YouTube video transcripts clearly and concisely. "
                "Structure: 1-sentence overview, then 3-5 key points. "
                "Be direct. Address the user as 'sir'. "
                "Match the language of the transcript."
            ),
            tier="smart",
            timeout_ms=60_000,
        ).strip()
    except Exception as e:
        return f"I couldn't summarise that transcript, sir. ({e})"


def _save_summary(content: str, video_url: str) -> str:
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"youtube_summary_{ts}.txt"
    desktop  = Path.home() / "Desktop"
    desktop.mkdir(parents=True, exist_ok=True)
    filepath = desktop / filename

    header = (
        f"JARVIS — YouTube Summary\n"
        f"{'─' * 50}\n"
        f"URL    : {video_url}\n"
        f"Date   : {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"{'─' * 50}\n\n"
    )
    filepath.write_text(header + content, encoding="utf-8")

    try:
        if is_windows():
            subprocess.Popen(["notepad.exe", str(filepath)])
        elif is_mac():
            subprocess.Popen(["open", "-t", str(filepath)])
        else:
            subprocess.Popen(["xdg-open", str(filepath)])
    except Exception as e:
        print(f"[YouTube] ⚠️ Could not open text editor: {e}")

    return str(filepath)


def _handle_play(parameters: dict, player) -> str:
    query = (
        (parameters.get("query") or "").strip()
        or (parameters.get("url") or "").strip()
        or (parameters.get("video_url") or "").strip()
    )
    if not query:
        print("[YouTube] ▶️ No specific query provided, opening YouTube homepage.")
        _open_url("https://www.youtube.com")
        return "Opened YouTube in your browser. Tell me what you'd like to watch."

    if player:
        player.write_log(f"[YouTube] Play: {query}")

    # 1. A pasted YouTube URL: open it directly in the default browser. It must
    #    NOT go through yt-dlp search — "ytsearch1:<url>" treats the URL as a
    #    search term and returns the wrong video (or a search page).
    if _is_valid_youtube_url(query):
        print(f"[YouTube] ▶️ Opening URL directly: {query}")
        _open_url(query)
        return f"Opened in your browser: {query}"

    # 2. A search term: resolve the top video and open it, else the search page.
    print(f"[YouTube] 🔍 Searching via yt-dlp for: {query}")
    video_url = _find_video_url(query)
    if video_url:
        print(f"[YouTube] ▶️ Opening: {video_url}")
        _open_url(video_url)
        return f"Opened '{query}' in your browser: {video_url}"

    print(f"[YouTube] ⚠️ Search failed, opening filtered search page")
    fallback_url = (
        f"https://www.youtube.com/results"
        f"?search_query={quote_plus(query)}"
        f"&sp={_YT_VIDEO_FILTER}"
    )
    _open_url(fallback_url)
    return f"Opened YouTube search for: {query} — pick a video to play."


def _handle_summarize(parameters: dict, player=None, speak=None) -> str:
    url = (
        parameters.get("url", "").strip() or 
        parameters.get("query", "").strip() or 
        parameters.get("video_url", "").strip()
    )

    if url and not _is_valid_youtube_url(url):
        found_url = _find_video_url(url)
        if found_url:
            url = found_url

    if not url:
        url = _ask_for_url("Please paste the YouTube video URL:")

    if not url:
        return "No URL provided, sir. Summary cancelled."
    if not _is_valid_youtube_url(url):
        return f"That doesn't appear to be a valid YouTube URL: '{url}', sir."

    if player:
        player.write_log(f"[YouTube] Summarizing: {url}")
    if speak:
        speak(f"Fetching transcript for video, sir.")

    from actions.agent_reach import fetch_youtube_transcript
    full_content = fetch_youtube_transcript(url)

    if not full_content or "Unable to fetch transcript" in full_content:
        return f"I couldn't retrieve transcript or details for that video ({url}), sir."

    try:
        summary = _summarize_with_gemini(full_content, url)
    except Exception as e:
        return f"Summary generation failed for {url}, sir: {e}"

    if speak:
        speak(summary)

    if parameters.get("save", True):
        saved_path = _save_summary(summary, url)
        return f"Summary complete and saved to Desktop: {saved_path}\n\nSummary:\n{summary}"

    return summary


def _handle_get_info(parameters: dict, player, speak) -> str:
    url = parameters.get("url", "").strip()
    if not url:
        url = _ask_for_url("Please paste the YouTube video URL:")
    if not url or not _is_valid_youtube_url(url):
        return "Please provide a valid YouTube URL, sir."

    if player:
        player.write_log(f"[YouTube] Getting info: {url}")

    from actions.agent_reach import fetch_youtube_transcript
    info_str = fetch_youtube_transcript(url)
    if not info_str or "Unable to fetch transcript" in info_str:
        return "Could not retrieve video information, sir."

    if speak:
        speak("Here's the video info, sir.")

    return info_str


def _handle_trending(parameters: dict, player, speak) -> str:
    region = parameters.get("region", "US").upper()

    if player:
        player.write_log(f"[YouTube] Trending: {region}")

    from actions.agent_reach import fetch_youtube_trending
    trending = fetch_youtube_trending(region=region, max_results=8)
    if not trending:
        return f"Could not fetch trending videos for region {region}, sir."

    lines  = [f"Top trending videos in {region}:"]
    lines += [f"{v['rank']}. {v['title']} — {v['channel']}" for v in trending]
    result = "\n".join(lines)

    if speak:
        top3   = trending[:3]
        spoken = "Here are the top trending videos, sir. " + ". ".join(
            f"Number {v['rank']}: {v['title']} by {v['channel']}" for v in top3
        )
        speak(spoken)

    return result


def _handle_stop(parameters: dict, player=None, speak=None) -> str:
    if player:
        player.write_log("[YouTube] Stopping playback")
    if _PYAUTOGUI:
        pyautogui.press('playpause')
        time.sleep(0.1)
    try:
        from actions.computer_control import _focus_window
        res = _focus_window("YouTube")
        if "Focused" not in res:
            res = _focus_window("chrome")
        if "Focused" in res and _PYAUTOGUI:
            pyautogui.press("k")
    except Exception:
        pass
    return "YouTube playback stopped."


def _handle_close(parameters: dict, player=None, speak=None) -> str:
    if player:
        player.write_log("[YouTube] Closing YouTube tab")
    if _PYAUTOGUI:
        pyautogui.press('playpause')
        time.sleep(0.05)
    try:
        from actions.computer_control import _safe_close_tab, _focus_window
        _focus_window("YouTube")
        time.sleep(0.1)
        return _safe_close_tab()
    except Exception as e:
        return f"Could not close YouTube tab: {e}"


_ACTION_MAP = {
    "play":      _handle_play,
    "summarize": _handle_summarize,
    "get_info":  _handle_get_info,
    "trending":  _handle_trending,
    "stop":      _handle_stop,
    "pause":     _handle_stop,
    "close":     _handle_close,
    "close_tab": _handle_close,
}


def youtube_video(
    parameters:     dict,
    response=None,
    player=None,
    session_memory=None,
    speak=None,
) -> str:
    params = parameters or {}
    action = params.get("action", "play").lower().strip()

    if player:
        player.write_log(f"[YouTube] Action: {action}")
    print(f"[YouTube] ▶️  Action: {action}  Params: {params}")

    handler = _ACTION_MAP.get(action)
    if handler is None:
        return (
            f"Unknown YouTube action: '{action}'. "
            "Available: play, stop, pause, close, summarize, get_info, trending."
        )

    try:
        if action == "play":
            return handler(params, player) or "Done."
        return handler(params, player, speak) or "Done."
    except Exception as e:
        print(f"[YouTube] ❌ Error in {action}: {e}")
        return f"YouTube {action} failed, sir: {e}"


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "youtube_video",
    "description": "Controls YouTube playback and videos. Actions: play (open a YouTube URL directly, or the top result for a search term, in the default browser), stop / pause (stop video playback), close (close YouTube tab), summarize, get_info, trending.",
    "risk": "local_mutation",
    "enabled": True,
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "play | stop | pause | close | summarize | get_info | trending (default: play)"
            },
            "query": {
                "type": "STRING",
                "description": "For play: a full YouTube URL (opened directly) or a search term (opens the top result)"
            },
            "save": {
                "type": "BOOLEAN",
                "description": "Save summary to Notepad (summarize only)"
            },
            "region": {
                "type": "STRING",
                "description": "Country code for trending e.g. TR, US"
            },
            "url": {
                "type": "STRING",
                "description": "Video URL for get_info action"
            }
        },
        "required": []
    },
    "handler": youtube_video,
}
