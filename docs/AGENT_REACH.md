# 🌐 Agent Reach — Multi-Platform Intelligence & Media Extraction Engine

> **Module:** `actions/agent_reach.py`  
> **Tool Name:** `agent_reach`  
> **Target OS:** Windows, macOS, Linux  
> **Author & Lead Architect:** Hamza Bukhari  

---

## 📌 1. Overview & Purpose

`agent_reach` is ZEZO's deep social and multi-platform intelligence gathering engine. It allows ZEZO to autonomously extract structured content, discussions, media captions, video transcripts, repository telemetry, and engineering discourse from 10+ platforms without requiring complex user API keys or browser automation overhead.

### Key Capabilities:
- **Instagram Reels & Posts:** Metadata, captions, creator profile, engagement metrics (likes/views/comments), and **native Whisper audio speech transcription** of Reels.
- **TikTok Videos:** Video metadata, hashtags, captions, engagement counts, and **native audio speech transcription**.
- **YouTube Intelligence:** Fast oEmbed metadata retrieval, YouTube transcript API extraction with timestamping, channel telemetry, and trending topics via `yt-dlp`.
- **Reddit Discussions:** Submission analysis, upvote ratios, top community comments, and engineering debates.
- **GitHub Repositories:** Repository telemetry, stargazers, README extraction, open issues, and topic search.
- **Twitter / X Threads:** High-speed tweet text extraction and thread assembly via `r.jina.ai` and Syndication APIs.
- **Stack Overflow:** Question details, vote scores, accepted answers, and top voted solutions.
- **Hacker News:** Story points, author analysis, submission links, and top discussion comments via the official Firebase & Algolia APIs.
- **RSS / Atom Feeds:** Feed parsing, article timestamps, and summary snippets.
- **Multi-Platform Research Compiler (`platform="multi"`):** Discovers sources across web/blogs, Reddit, Hacker News, YouTube and GitHub, then **reads the FULL body of every resource** (article text, Reddit thread, HN thread, video transcript/captions, repo README), analyses each with the background LLM router, and synthesises an executive summary + key findings + a step-by-step playbook into one Markdown report.

> **Depth contract (2026-09-25):** the `multi` report no longer emits one-line search snippets. Each source is deep-fetched (bounded per host) and individually analysed; the report ends with an "All Sources" reference list so every claimed finding maps to a real URL.

---

## ⚙️ 2. Architecture & Execution Flow

```
                     ┌──────────────────────────────┐
                     │ User Voice / Text / URL Link │
                     └──────────────┬───────────────┘
                                    │
                                    ▼
                     ┌──────────────────────────────┐
                     │     Gemini Live Session      │
                     │  (Calls agent_reach action)  │
                     └──────────────┬───────────────┘
                                    │
                                    ▼
            ┌───────────────────────────────────────────────┐
            │       Canonical URL Domain Precedence         │
            │ (Auto-corrects platform for Instagram/TikTok) │
            └───────────────────────┬───────────────────────┘
                                    │
                                    ▼
            ┌───────────────────────────────────────────────┐
            │       Background Task Manager (tm.submit)     │
            │   - Non-blocking execution                    │
            │   - Live progress emitted to Task Queue       │
            └───────────────┬───────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ yt-dlp Audio  │   │  Platform API │   │   r.jina.ai   │
│ & Metadata    │   │ (GitHub, HN,  │   │ Markdown Scrape│
│ Extraction    │   │   StackEx)    │   │   Fallback    │
└───────┬───────┘   └───────┬───────┘   └───────┬───────┘
        │                   │                   │
        ▼                   │                   │
┌───────────────┐           │                   │
│ faster-whisper│           │                   │
│ Speech STT    │           │                   │
└───────┬───────┘           │                   │
        └───────────────────┼───────────────────┘
                            │
                            ▼
            ┌───────────────────────────────┐
            │  Markdown Formatted Output    │
            │  - HUD Live Display Canvas    │
            │  - Concise Spoken Summary     │
            └───────────────────────────────┘
```

---

## 🛠️ 3. Platform Extraction Matrix

| Platform | Supported Targets | Primary Engine | Fallback Engine | Transcription |
| :--- | :--- | :--- | :--- | :--- |
| **Instagram** | Reels (`/reel/`), Posts (`/p/`), Profiles | `yt-dlp` info & audio extract | `r.jina.ai` / Web Reader | ✅ `faster-whisper` on Reel audio |
| **TikTok** | Videos (`/@user/video/id`), Links | `yt-dlp` info & audio extract | Web Reader | ✅ `faster-whisper` on Video audio |
| **YouTube** | Video URLs, Shorts, Video IDs | `youtube_transcript_api` + oEmbed | `yt-dlp` + DuckDuckGo search | ✅ Native captions + timestamps |
| **YouTube Channel** | Channel URLs (`/@user`, `/channel/`) | `yt-dlp` channel tab extraction | RSS feed / Web Reader | — |
| **Reddit** | Thread URLs, Query searches | `.json` API + Web Search | DuckDuckGo site search | — |
| **GitHub** | `owner/repo`, URL, Search query | GitHub REST API v3 | Web Reader | — |
| **Twitter / X** | Tweet URL, Thread, `@handle` | `r.jina.ai` / Syndication API | Web Reader | — |
| **Stack Overflow** | Question URL, ID, Error query | StackExchange 2.3 API | Web Search | — |
| **Hacker News** | Story URL, Item ID, Query | Firebase HN API + Algolia | Web Reader | — |
| **RSS / Atom** | XML Feed URL | `feedparser` | Standard HTTP parser | — |
| **Multi-Research** | Search keyword / Topic query | Deep-fetch each source + per-source LLM analysis + synthesis | Combined web/DDG discovery | ✅ captions/transcript (no audio download in batch) |

---

## 🔊 4. Spoken Audio Transcription Pipeline

When extracting YouTube videos (where caption APIs are blocked/rate-limited with 429), Instagram Reels, TikTok videos, or short video media:
1. `_transcribe_video_audio(url)` downloads the best available audio stream via `yt-dlp` directly into a secure temporary working directory (`tempfile.TemporaryDirectory`).
2. The audio is extracted to MP3 via `FFmpegExtractAudio`.
3. `faster_whisper.WhisperModel("base", compute_type="int8")` performs high-speed local inference with timestamps.
4. The transcribed dialogue is injected directly into the structured Markdown response under:
   ```markdown
   ## Video Transcript / Captions:
   [00:00] <Transcribed Speech with Timestamps>
   ```

> **Batch-report guard (2026-09-25):** the `platform="multi"` report calls `fetch_youtube_transcript(..., allow_audio_fallback=False)`. Downloading 12–18 MB of audio per video and running Whisper would turn a research report into a multi-minute, high-bandwidth job, so batch reports use captions + description only. A direct `platform="youtube"` request still uses the full Whisper fallback.

---

## 📋 5. Tool Schema (`TOOL` Contract)

```json
{
  "name": "agent_reach",
  "description": "Extract deep content, video transcripts, social discussions, repository intelligence, and multi-platform search across platforms. Supports YouTube (transcripts & channels), Instagram (Reels, posts & captions), TikTok (videos & captions), Reddit (posts & top comments), GitHub (README & search), Twitter/X threads, Stack Overflow (questions & answers), Hacker News, RSS feeds, and multi-platform search aggregation.",
  "behavior": "NON_BLOCKING",
  "scheduling": "WHEN_IDLE",
  "parameters": {
    "type": "OBJECT",
    "properties": {
      "target": {
        "type": "STRING",
        "description": "The URL, video ID, channel, query, Instagram reel/post URL, TikTok video URL, Reddit thread, Twitter link/handle, GitHub repository, or RSS feed to extract."
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
          "web"
        ],
        "description": "Platform to extract from or 'multi' for cross-platform search aggregator. Defaults to 'auto'."
      }
    },
    "required": ["target"]
  }
}
```

---

## 🔒 6. Resilience & Anti-Bot Protection

1. **YouTube Bot-Verification Resilience:** If YouTube returns a `429 Too Many Requests` or bot-block for transcript extraction, `agent_reach` seamlessly falls back to oEmbed metadata, description extraction, and live search aggregation without failing the task.
2. **Instagram Rate-Limit Resilience:** Clean tracking parameters (`?stkn=...`, `?igsh=...`) are stripped automatically before calling `yt-dlp` or `r.jina.ai`.
3. **Task Queue Asynchrony:** Heavy video downloads and transcription never block the PyQt6 main thread or the Gemini Live audio streaming loop; tasks execute via `core.task_manager` background threads with instant task IDs.
