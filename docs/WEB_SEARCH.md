# JARVIS — Web Search / Internet System

## Overview

JARVIS has multi-mode web search powered by **Gemini Grounded** with **DuckDuckGo fallback**.

**File**: `actions/web_search.py`

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