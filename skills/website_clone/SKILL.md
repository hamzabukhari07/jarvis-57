---
name: website_clone
description: "Master protocol for exact offline website cloning, asset localization, and reverse-engineering rebuilds using the Uncage Hybrid Engine."
domain: web_dev
author: "Hamza Bukhari"
version: "1.0.0"
required_tools: [clone_website, browser_control, web_read_page, file_controller]
triggers: ["clone website", "copy website", "offline website", "download site", "uncage website", "rebuild website", "website clone", "rip website", "clone", "cloning", "cloner", "download website"]
tags: ["clone", "web_dev", "offline", "uncage", "rebuild"]
auto_activate: true
---

# 🌐 Master Website Cloning Protocol (`website_clone`)

> **Lead Architect & Creator:** Hamza Bukhari  
> **Core Subsystem:** Uncage Hybrid Engine & Reverse-Engineering Capture Pipeline  
> **Target Audience:** Google Antigravity Agent, OpenCode, Kilo Code, Autonomous Office Fleet, and all ZEZO core orchestrators.  
> **Core Axiom:** High-fidelity offline preservation and safe downstream reverse engineering. The raw capture directory is strictly an **IMMUTABLE AUDIT TRAIL**; downstream rebuilds land in separate artifacts (`rebuilt.html` or `rebuilt_app/`) without ever corrupting or mutating the raw extracted assets.

---

## 🛠️ 1. Uncage Hybrid Engine Architecture

The Uncage Hybrid Engine provides two distinct execution paths tailored to the orchestrator model and runtime context:

```text
                                  ┌───────────────────────────────┐
                                  │      Target URL Ingestion     │
                                  └───────────────┬───────────────┘
                                                  │
                       ┌──────────────────────────┴──────────────────────────┐
                       ▼                                                     ▼
      ┌─────────────────────────────────┐                   ┌─────────────────────────────────┐
      │   Path A: Python Action Tool    │                   │   Path B: Direct CLI Execution  │
      │   `clone_website` Handler       │                   │   `tools/uncage/bin/uncage.js`  │
      ├─────────────────────────────────┤                   ├─────────────────────────────────┤
      │ • Invoked by: Groq / Gemini     │                   │ • Invoked by: Fleet Agents      │
      │ • Features: 2-step confirmation │                   │   (Antigravity CLI / OpenCode)  │
      │   gate, background task queue,  │                   │ • Features: Direct terminal     │
      │   auto-preview server on :9400  │                   │   execution, custom node flags, │
      │ • Non-blocking async execution  │                   │   zero IPC middleware overhead  │
      └────────────────┬────────────────┘                   └────────────────┬────────────────┘
                       │                                                     │
                       └──────────────────────────┬──────────────────────────┘
                                                  │
                                                  ▼
                                 ┌─────────────────────────────────┐
                                 │    Uncage Playwright Browser    │
                                 │  - Headless DOM Extraction      │
                                 │  - CSS/Font/Asset Downloader    │
                                 │  - Local Path Rewriter          │
                                 └────────────────┬────────────────┘
                                                  │
                                                  ▼
                                 ┌─────────────────────────────────┐
                                 │     Verified Clone Package      │
                                 │  - index.html                   │
                                 │  - assets/                      │
                                 │  - asset-map.json               │
                                 │  - antigravity_clone.html       │
                                 └─────────────────────────────────┘
```

### Path A: Python Action Tool (`clone_website`)
- **Primary Driver:** ZEZO Session Orchestrator (Groq / Gemini live conversational loop).
- **Execution:** Invokes `actions/website_cloner.py` with parameters:
  - `url` (str): Target web address.
  - `mode` (str): `"single_page"` (default, depth 1) or `"full_site"` (depth 2, max 25 pages).
  - `output_format` (str): `"capture_only"`, `"single_file_html"`, or `"react_tailwind"`.
  - `target_dir` (str, optional): Target folder path (defaults to `Desktop/<domain>_clone`).
  - `confirmed` (bool): 2-Step stateless gate confirmation flag.
- **Benefits:** Built-in two-step stateless confirmation read-back, automatic background worker management (`TaskManager`), and automatic launch of local HTTP preview server (`ThreadingHTTPServer` on ports 9400–9480).

### Path B: Direct CLI Execution (`uncage.js`)
- **Primary Driver:** Autonomous Fleet Agents (Antigravity CLI `agy`, OpenCode, Kilo Code).
- **Execution:** Direct headless Node.js Playwright invocation via subprocess or terminal:
  ```bash
  node tools/uncage/bin/uncage.js <url> -o <target_dir> --no-purge --timeout 30000
  ```
- **Key Flags:**
  - `-o, --output <dir>`: Target destination directory.
  - `--no-purge`: Preserves dynamic runtime CSS classes and pseudo-states.
  - `--timeout <ms>`: Per-page navigation budget (30,000 ms single page / 45,000 ms crawl).
  - `--skip-deps`: Fallback mode if initial extraction stalls on deep JavaScript bundle dependencies.
- **Benefits:** Instant shell integration, scriptable in complex multi-step build pipelines, zero Python IPC overhead.

---

## 📋 2. Standard Operating Procedure (5-Phase SOP)

Every clone operation must execute systematically across five distinct phases:

### Phase 1: Target Discovery
1. **URL Validation & Normalization:** Validate scheme (`http://` or `https://`), resolve redirects, and isolate root domain.
2. **Tech-Stack Fingerprinting:** Run a fast (<200ms) HTTP HEAD/GET probe inspecting headers (`server`, `x-powered-by`) and initial markup:
   - Identify CMS or framework: Next.js, Nuxt, React, Webflow, Framer, WordPress, Shopify, Wix, or static HTML.
3. **Scope Definition:**
   - Single Page: Marketing landing pages, auth forms, isolated component pages.
   - Full Site: Multi-page business sites, documentation, blog archives (capped at depth 2, max 25 pages).
4. **Read-Back Commitment Gate:**
   - Always confirm destination path and clone scope before launching crawlers.

### Phase 2: Asset Extraction
1. **Headless Browser Launch:** Spawn Chromium instance via Playwright inside `uncage.js`.
2. **DOM Snapshotting:** Wait for network idle (`networkidle` or `domcontentloaded` with timeout) to allow client-side hydration.
3. **Comprehensive Asset Crawl:**
   - Stylesheets: Linked `.css` files and `@import` rules.
   - Fonts: Web fonts (`.woff2`, `.woff`, `.ttf`, Google Fonts stylesheets).
   - Images & Media: Raster graphics (`.png`, `.jpg`, `.webp`), vectors (`.svg`), and background CSS images.
   - Scripts: Embedded vendor scripts, client bundles, and critical runtime logic.
4. **Retry on Stall:** If extraction stalls during JavaScript compilation, automatically re-run with `--skip-deps` to salvage DOM and visual assets.

### Phase 3: Sanitization & Localization
1. **Relative Path Rewriting:** Convert all absolute remote URLs (`https://domain.com/static/...`) into localized relative paths (`./assets/...`).
2. **Asset Map Generation:** Produce `asset-map.json` documenting every local asset mapping and hash checksum.
3. **Tracker & Noise Removal:**
   - Strip analytics beacons: Google Analytics (`gtag`), Google Tag Manager, Facebook Pixel, Hotjar, Mixpanel.
   - Remove anti-crawler overlays, cookie consent banners (where appropriate), and malicious script tags.
4. **Base64 Bloat Sanitization:** Truncate or decouple oversized base64 data URIs into distinct static files in `assets/` to keep HTML lean.

### Phase 4: Fidelity Verification
1. **Asset Integrity Gate (`verify_local_assets`):**
   - Check every referenced file in `./assets/` to ensure 0 broken local links.
   - Verify `index.html` and `asset-map.json` exist and are fully populated.
   - Ensure no leftover temporary crawl files (`captured-raw*.html`) exist.
2. **Offline Standalone Mirror:** Verify `antigravity_clone.html` loads offline without console network errors.
3. **Preview Verification:** Serve via local HTTP server on available port in range `9400–9480` and inspect DOM layout fidelity.

### Phase 5: Delivery & Rebuild Handoff
1. **Preservation Guarantee:** The raw capture directory (`Desktop/<domain>_clone/`) is sealed and never mutated.
2. **Format Handoff:**
   - `capture_only`: Deliver raw verified offline capture folder directly to the user.
   - `single_file_html`: Synthesize bundled, self-contained `rebuilt.html` in the root of the clone folder.
   - `react_tailwind`: Scaffold modular Vite + React + Tailwind project in `rebuilt_app/`.
3. **Summary Notification:** Report completed task ID, target directory, total asset count, detected tech stack, and preview URL.

---

## 🛡️ 3. Safety Invariants & Operational Rules

- **Anti-Regression:** Never bypass the asset verification step. A clone without localized assets is considered failed.
- **Zero In-Place Overwrites:** Rebuild engines must never overwrite `index.html` from the raw capture; all transformed deliverables must reside in `rebuilt.html` or `rebuilt_app/`.
- **Non-Blocking Guarantee:** Crawling and asset downloading must run asynchronously in background tasks or isolated subprocesses. Never block the main session loop.
- **Graceful Error Handling:** If network rate limits or anti-bot defenses trigger (Cloudflare 403/503), log the exact failure and provide clear diagnostic guidance rather than silently failing.
