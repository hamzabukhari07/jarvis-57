---
name: antigravity_agent
description: Autonomous pair-programming and full-stack software generation engine powered by Google Antigravity. Architect multi-file applications with rich aesthetics, zero placeholders, and verified syntax.
metadata:
  author: Zezo / Google DeepMind
  version: '2.0'
---

# Antigravity Developer Agent

Use this skill whenever the user asks Antigravity to write code, design an application, build a dashboard, or create multi-file projects.

## Core Capabilities:
- **`antigravity_run` Tool:**
  - Plans complete file structures and dependency graphs.
  - Generates stunning web applications (HTML5/CSS3/Vanilla JS with glassmorphism, responsive layout, dark themes).
  - Generates complete Python, FastAPI, CLI, or backend modules.
  - Automatically verifies syntax and exports complete project reports to the Zezo HUD screen.

## Usage Rules:
1. When the user asks to build an app, website, or script using Antigravity, invoke `antigravity_run(task=...)`.
2. Give a brief voice update to the user while the agent crafts the files in the background without blocking the voice connection.
