---
name: web_scraper
description: Anti-bot and Cloudflare-bypassing web scraping engine powered by Scrapling. Extracts clean markdown, structured text, and eliminates paywalls/blocks.
metadata:
  author: Zezo / FatihMakes
  version: '1.0'
---

# Web Scraper (Scrapling Engine)

Use this skill when reading full webpage contents, blog posts, developer documentation, pricing tables, or articles that may be protected by Cloudflare Turnstile, anti-bot scripts, or complex JavaScript rendering.

## Core Capabilities:
- **`web_read_page` Tool:**
  - Fast C-based HTTP/2 fetching via `scrapling.Fetcher`
  - Automatic fallback to `scrapling.StealthyFetcher` for 403 Forbidden / Cloudflare Turnstile challenges
  - Converts HTML directly into readable, clean Markdown
  - Eliminates cookie banners, navigation menus, and script tags

## Usage Rules:
1. When the user shares a link (article, doc, blog, tutorial), invoke `web_read_page(url=...)`.
2. For websites known to have aggressive Cloudflare protection, pass `stealth=True`.
3. Provide a concise conversational voice summary while rendering full details on the HUD content view.
