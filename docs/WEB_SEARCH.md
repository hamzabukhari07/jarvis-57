# JARVIS — Web Search / Internet System

## Overview

JARVIS has multi-mode web search powered by **Gemini Grounded** with **DuckDuckGo fallback**.

**File**: `actions/web_search.py`

> **Grounding policy (2026-09-25):** the Live voice model's knowledge is frozen, so the tool
> description and `core/prompt.txt` now require it to (a) search for any current-fact/product
> question and (b) use the **exact** product/model/version name the user said — never substituting
> an older name it remembers. This fixed a live case where "iPhone 18 Pro Max" was rewritten to
> "iPhone 16 Pro Max" and answered from stale memory even though grounded search returns the real
> iPhone 18 Pro Max (Apple newsroom, Sept-2026).

## Search Modes

| Mode | Description |
|------|-------------|
| `news` | Latest news |
| `research` | In-depth research |
| `price` | Product prices |
| `compare` | Product comparison |
| `search` | General web search |

## Implementation

### Gemini Grounded (Primary)

```python
# Uses the REST Gemini API with grounding_metadata
# Returns sources in candidates[].grounding_metadata
```

### DuckDuckGo Fallback

```python
# ddgs package (successor to duckduckgo-search)
# Used when Gemini grounded search fails
# Falls back automatically
```

## Tool Declaration

```python
TOOL = {
    "name": "web_search",
    "description": "Searches the web...",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query": {"type": "STRING"},
            "mode": {"type": "STRING", "description": "news, research, price, compare, search"},
            "items": {"type": "ARRAY"},
        },
    },
    "behavior": "NON_BLOCKING",
    "scheduling": "WHEN_IDLE",
}
```

## Result Handling

```python
# Results mirrored to on-screen content panel:
self.ui.show_content(label, result)
# Content panel: scrollable display beneath the HUD
```

## Other Web Features

### News
- `actions/web_search.py:_news()` — fetch latest news

### Web Reader (deep page extraction)
- **File**: `actions/web_reader.py` (`web_read_page`)
- Scrapling (Fetcher / StealthyFetcher) when installed, else `requests` + BeautifulSoup.
- **Fail-fast anti-bot fetch (2026-09-26):** StealthyFetcher runs with `timeout=15000, network_idle=False, retries=1`. Its defaults (30s timeout, network-idle wait, 3 attempts) made sites that keep sockets open — e.g. `reddit.com` — hang ~30s per attempt and retry, so a single blocked page cost ~53s (and, in the multi-source research pipeline, minutes). Fail-fast plus a single attempt cut that to ~25s; blocked hosts now fall through to the HTTP fallback quickly. A redundant second StealthyFetcher attempt (a timeout inside the `try` was re-caught by the outer `except`) was also removed.

### Flight Finder
- **File**: `actions/flight_finder.py`
- Live flight price and availability lookup

### Weather
- **File**: `actions/weather_report.py`
- Live weather data for user's city

### YouTube Control
- **File**: `actions/youtube_video.py`
- Search, play, and control YouTube playback

### Game Updater
- **File**: `actions/game_updater.py`
- Steam and Epic Games update management

### Send Message
- **File**: `actions/send_message.py`
- WhatsApp, Telegram, and more

### Browser Control
- **File**: `actions/browser_control.py`
- Open URLs, navigate tabs, interact with browser
- Powered by Playwright (Chromium + Firefox)

## Summary

```
Search: Gemini Grounded + DuckDuckGo fallback
Modes: news, research, price, compare, search
Content: Mirrored to on-screen panel
Other web: Weather, flights, YouTube, messaging
Browser: Playwright-powered automation
```

## Log noise (ADR-057)

`ddgs` uses the Rust `primp` client, which bridges Hickory DNS and HTTP/2 into
Python logging with enormous DEBUG volume (one search emitted >1000 lines and
could roll the 20,000-line ring buffer). `core/log_bus.py` pins
`hickory_net`, `hickory_resolver`, `hickory_proto`, `h2`, `cookie_store`, and
`primp` to `WARNING`. Set `ZEZO_LOG_DEBUG=1` to see the full wire dump when
deliberately debugging.