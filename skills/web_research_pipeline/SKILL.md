---
name: web_research_pipeline
description: In-depth web investigation protocol featuring query decomposition, ground-truth cross-referencing, and concise bullet summaries.
metadata:
  author: Zezo / FatihMakes
  version: '1.0'
---

# Web Research & Ground-Truth Pipeline

Use this skill when the user asks for deep research, pricing comparisons, breaking news investigations, or technical documentation lookups.

## Execution Steps:
1. **Decompose Research Query:**
   - Break the topic into 2-3 specific search keywords (e.g., official docs, recent changelogs, benchmarks).
2. **Execute Multi-Source Search:**
   - Use `web_search` with appropriate mode (`research` / `price` / `compare` / `news`).
3. **Filter and Synthesize:**
   - Eliminate marketing fluff and outdated information (>1 year old unless historical).
   - Extract key metrics, dates, version numbers, and authoritative URLs.
4. **Deliver Structured Response:**
   - Speak a high-level executive summary in voice.
   - Display key bullet points and comparative tables on the HUD content panel.
