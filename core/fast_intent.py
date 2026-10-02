"""
core/fast_intent.py — High-Performance Zero-Latency Intent Matcher & Registry.

Deterministic command dispatcher that executes desktop, system, app, and media
controls with 0ms LLM overhead. Extensible registry pattern.
Lead Architect: Hamza Bukhari
"""
from __future__ import annotations

import datetime
import re
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class IntentResult:
    intent: str
    target: Optional[str] = None
    confidence: float = 1.0
    action: Optional[str] = None
    response_text: Optional[str] = None
    executed: bool = False
    execution_result: Optional[str] = None


# Known application name mappings (normalized name -> canonical search alias)
APP_CANONICAL_MAP: Dict[str, str] = {
    "calculator": "calculator",
    "calc": "calculator",
    "hisab kitab": "calculator",
    "chrome": "chrome",
    "google chrome": "chrome",
    "browser": "chrome",
    "firefox": "firefox",
    "edge": "edge",
    "ms edge": "edge",
    "microsoft edge": "edge",
    "brave": "brave",
    "opera": "opera",
    "safari": "safari",
    "vs code": "vscode",
    "vscode": "vscode",
    "code": "vscode",
    "visual studio code": "vscode",
    "visual studio": "vscode",
    "notepad": "notepad",
    "text editor": "notepad",
    "spotify": "spotify",
    "music": "spotify",
    "discord": "discord",
    "telegram": "telegram",
    "whatsapp": "whatsapp",
    "slack": "slack",
    "zoom": "zoom",
    "teams": "teams",
    "microsoft teams": "teams",
    "terminal": "terminal",
    "command prompt": "cmd",
    "cmd": "cmd",
    "powershell": "powershell",
    "task manager": "task manager",
    "taskmgr": "task manager",
    "file explorer": "explorer",
    "explorer": "explorer",
    "files": "explorer",
    "my computer": "explorer",
    "settings": "settings",
    "system settings": "settings",
    "control panel": "control panel",
    "paint": "paint",
    "mspaint": "paint",
    "steam": "steam",
    "postman": "postman",
    "figma": "figma",
    "blender": "blender",
    "word": "word",
    "ms word": "word",
    "excel": "excel",
    "ms excel": "excel",
    "powerpoint": "powerpoint",
    "obsidian": "obsidian",
    "notion": "notion",
    "vlc": "vlc",
}

# Filler prefixes and polite phrases to strip cleanly
_FILLER_PREFIXES = re.compile(
    r"^(can you please|could you please|please can you|please could you|would you please|"
    r"can you|could you|would you|please|zezo please|jarvis please|zezo|jarvis|bhai|yaar|meharbani karke)\s+",
    re.IGNORECASE,
)

_FILLER_SUFFIXES = re.compile(
    r"\s+(please|for me|now|quickly|jaldi|karo|kar do|chalao|kholo|band karo)$",
    re.IGNORECASE,
)


def normalize_command_text(text: str) -> str:
    """Normalize input speech by removing polite framing, punctuation, and excess spaces."""
    if not text:
        return ""
    cleaned = text.strip().lower()
    # Strip apostrophes directly to preserve contractions like what's -> whats, today's -> todays
    cleaned = re.sub(r"['’]", "", cleaned)
    # Strip other non-alphanumeric characters to spaces
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Strip filler prefixes iteratively
    prev = None
    while prev != cleaned:
        prev = cleaned
        cleaned = _FILLER_PREFIXES.sub("", cleaned).strip()
        cleaned = _FILLER_SUFFIXES.sub("", cleaned).strip()

    return cleaned


class FastIntentMatcher:
    """Extensible deterministic pattern and rule matcher."""

    def __init__(self):
        self._rules: List[Tuple[str, re.Pattern, Callable[[re.Match, str], Optional[IntentResult]]]] = []
        self._register_default_rules()

    def register(self, intent: str, pattern: str | re.Pattern, handler: Callable[[re.Match, str], Optional[IntentResult]]):
        compiled = re.compile(pattern, re.IGNORECASE) if isinstance(pattern, str) else pattern
        self._rules.append((intent, compiled, handler))

    def _extract_app_target(self, raw_target: str) -> Optional[str]:
        target = raw_target.strip().lower()
        target = re.sub(r"^(the|a|an|app|application|program|software)\s+", "", target).strip()
        target = re.sub(r"\s+(app|application|program|software)$", "", target).strip()
        if not target:
            return None

        # Check canonical map directly
        if target in APP_CANONICAL_MAP:
            return APP_CANONICAL_MAP[target]

        # Substring / partial match against canonical map
        for alias, canonical in APP_CANONICAL_MAP.items():
            if alias == target or alias in target or target in alias:
                return canonical

        # Return sanitized raw target if non-empty (for unmapped apps like e.g. "github desktop")
        return target

    def _register_default_rules(self):
        # ── 1. Stop / Cancel / Be Quiet ──────────────────────────────────────
        self.register(
            "stop",
            r"^(stop|cancel|chup|chup ho ja|shut up|be quiet|ruk ja|ruk jao|bas karo|silence)$",
            lambda m, raw: IntentResult(
                intent="stop",
                confidence=1.0,
                action="stop",
                response_text="Stopped.",
            ),
        )

        # ── 2. Media Controls (Play / Pause / Next / Prev) ────────────────────
        self.register(
            "media_play_pause",
            r"^(play\s+pause|play|pause|resume|pause video|play video|pause music|play music|gana roko|gana chalao)$",
            lambda m, raw: IntentResult(
                intent="media_control",
                target="play_pause",
                confidence=1.0,
                action="play_pause",
                response_text="Playback toggled.",
            ),
        )
        self.register(
            "media_next",
            r"^(next\s+track|next\s+song|next\s+video|skip\s+track|skip\s+song|next|agla gana)$",
            lambda m, raw: IntentResult(
                intent="media_control",
                target="next_track",
                confidence=1.0,
                action="next_track",
                response_text="Skipped to next track.",
            ),
        )
        self.register(
            "media_prev",
            r"^(previous\s+track|prev\s+track|previous\s+song|prev\s+song|previous|pichhla gana)$",
            lambda m, raw: IntentResult(
                intent="media_control",
                target="prev_track",
                confidence=1.0,
                action="prev_track",
                response_text="Playing previous track.",
            ),
        )

        # ── 3. Volume & Audio Control ─────────────────────────────────────────
        self.register(
            "volume_mute",
            r"^(mute|unmute|mute volume|unmute volume|mute audio|unmute audio|sound off|sound on|awaz band|awaz kholo)$",
            lambda m, raw: IntentResult(
                intent="volume_control",
                target="unmute" if "unmute" in m.group(0) or "sound on" in m.group(0) or "kholo" in m.group(0) else "mute",
                confidence=1.0,
                action="mute",
                response_text="Unmuted." if "unmute" in m.group(0) or "sound on" in m.group(0) or "kholo" in m.group(0) else "Muted.",
            ),
        )
        self.register(
            "volume_up",
            r"^(volume up|increase volume|raise volume|turn it up|louder|make it louder|awaz barha do|awaz tez karo|awaz barhao|up volume)$",
            lambda m, raw: IntentResult(
                intent="volume_control",
                target="up",
                confidence=1.0,
                action="volume_up",
                response_text="Volume increased.",
            ),
        )
        self.register(
            "volume_down",
            r"^(volume down|decrease volume|lower volume|turn it down|quieter|make it quieter|awaz kam kar do|awaz kam karo|down volume)$",
            lambda m, raw: IntentResult(
                intent="volume_control",
                target="down",
                confidence=1.0,
                action="volume_down",
                response_text="Volume decreased.",
            ),
        )

        # ── 4. Open / Launch Application ──────────────────────────────────────
        self.register(
            "open_app",
            r"^(open|launch|start|run|kholo|chalao|start up)\s+(.+)$",
            self._handle_open_app_match,
        )

        # ── 5. Close / Terminate Application ──────────────────────────────────
        self.register(
            "close_app",
            r"^(close|exit|terminate|kill|quit|band karo|shut down)\s+(.+)$",
            self._handle_close_app_match,
        )

        # ── 6. Time & Date ───────────────────────────────────────────────────
        self.register(
            "time_query",
            r"^(whats the time|what is the time|what time is it|current time|time kya hai|kitne baje hain)$",
            lambda m, raw: IntentResult(
                intent="time_query",
                confidence=1.0,
                action="get_time",
                response_text=f"It is {datetime.datetime.now().strftime('%I:%M %p')}.",
            ),
        )
        self.register(
            "date_query",
            r"^(whats the date|what is the date|what is todays date|what is today date|todays date|today date|current date|date kya hai|aaj kya date hai|aaj ki date)$",
            lambda m, raw: IntentResult(
                intent="date_query",
                confidence=1.0,
                action="get_date",
                response_text=f"Today is {datetime.datetime.now().strftime('%A, %B %d, %Y')}.",
            ),
        )

    def _handle_open_app_match(self, match: re.Match, raw: str) -> Optional[IntentResult]:
        raw_target = match.group(2).strip()
        app_target = self._extract_app_target(raw_target)
        if not app_target:
            return None
        return IntentResult(
            intent="open_app",
            target=app_target,
            confidence=1.0,
            action="open",
            response_text=f"Opening {app_target.title()}.",
        )

    def _handle_close_app_match(self, match: re.Match, raw: str) -> Optional[IntentResult]:
        raw_target = match.group(2).strip()
        # Avoid matching system shutdowns
        if raw_target in ("computer", "system", "pc", "laptop", "down"):
            return None
        app_target = self._extract_app_target(raw_target)
        if not app_target:
            return None
        return IntentResult(
            intent="close_app",
            target=app_target,
            confidence=1.0,
            action="close",
            response_text=f"Closed {app_target.title()}.",
        )

    def match(self, text: str) -> Optional[IntentResult]:
        """Match normalized text against all intent rules."""
        if not text:
            return None
        normalized = normalize_command_text(text)
        if not normalized:
            return None

        for intent_name, pattern, handler in self._rules:
            m = pattern.match(normalized)
            if m:
                res = handler(m, text)
                if res is not None:
                    return res
        return None


# Global singleton instance
_matcher = FastIntentMatcher()


def match_fast_intent(text: str) -> Optional[IntentResult]:
    """Public high-confidence deterministic intent matching entrypoint."""
    return _matcher.match(text)


def execute_fast_intent(res: IntentResult) -> bool:
    """Execute the deterministic action directly with 0ms LLM overhead."""
    if not res:
        return False

    try:
        if res.intent == "stop":
            import sounddevice as sd
            sd.stop()
            res.executed = True
            res.execution_result = "Stopped audio playback."
            return True

        if res.intent == "volume_control":
            from actions import computer_settings
            if res.target == "up":
                computer_settings.volume_up()
                vol = computer_settings.volume_get()
                res.response_text = f"Volume increased{' to ' + str(vol) + '%' if vol else ''}."
            elif res.target == "down":
                computer_settings.volume_down()
                vol = computer_settings.volume_get()
                res.response_text = f"Volume lowered{' to ' + str(vol) + '%' if vol else ''}."
            elif res.target in ("mute", "unmute"):
                computer_settings.volume_mute()
            res.executed = True
            res.execution_result = "Volume adjusted."
            return True

        if res.intent == "media_control":
            try:
                import pyautogui
                if res.target == "play_pause":
                    pyautogui.press("playpause")
                elif res.target == "next_track":
                    pyautogui.press("nexttrack")
                elif res.target == "prev_track":
                    pyautogui.press("prevtrack")
                res.executed = True
                res.execution_result = f"Media action '{res.target}' triggered."
                return True
            except Exception as e:
                print(f"[FastIntent] Media key error: {e}")
                return False

        if res.intent == "open_app" and res.target:
            from actions.open_app import open_app
            out = open_app({"app_name": res.target, "action": "open"})
            res.executed = True
            res.execution_result = out
            return True

        if res.intent == "close_app" and res.target:
            from actions.open_app import open_app
            out = open_app({"app_name": res.target, "action": "close"})
            res.executed = True
            res.execution_result = out
            return True

        if res.intent in ("time_query", "date_query"):
            res.executed = True
            res.execution_result = res.response_text
            return True

    except Exception as e:
        print(f"[FastIntent] Execution exception for {res.intent}: {e}")
        return False

    return False
