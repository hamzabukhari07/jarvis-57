---
name: social_research
description: Multi-platform social, video, and code research powered by Agent-Reach. Fetches YouTube transcripts, Reddit discussions, and GitHub repository trees.
metadata:
  author: Zezo / FatihMakes
  version: '1.0'
---

# Social & Multi-Platform Intelligence (Agent-Reach)

Use this skill when investigating community sentiment, video transcripts, GitHub repositories, or Reddit discussions.

## Core Capabilities:
- **`agent_reach` Tool:**
  - **YouTube:** Full timestamped transcript extraction, duration, view count, and channel metadata without relying on browser playback.
  - **Reddit:** Thread post body, score, and top nested comment discussions.
  - **GitHub:** Repository statistics (stars, forks, language), README contents, and architectural summary.
  - **Twitter / X & Web:** Clean thread and article text extraction.

## Usage Rules:
1. When given a YouTube URL or asked "what is this video saying?", call `agent_reach(target=url, platform='youtube')`.
2. When asked to check community opinions or Reddit feedback, call `agent_reach(target=url, platform='reddit')`.
3. When analyzing a GitHub repo link, call `agent_reach(target=url, platform='github')`.
