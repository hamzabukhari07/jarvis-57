---
name: opencode
description: Autonomous coding and refactoring delegation via OpenCode CLI using OpenCode Zen free models.
metadata:
  author: Zezo / OpenCode Zen
  version: '1.0'
---

# OpenCode Zen Autonomous Coding Protocol

Use this skill when the user explicitly requests to use OpenCode or delegates complex multi-file engineering, bug fixes, or test generation tasks.

## OpenCode Zen Free Models Matrix:
1. **`zen/nemotron-3-super-free`** *(Default)*: NVIDIA 1M context model — optimal for multi-file refactoring and architectural changes.
2. **`zen/big-pickle`**: Stealth agentic coding model for difficult, ambiguous bug fixes.
3. **`zen/minimax-m2.5-free`**: Optimized for tool calling, CLI commands, and automated test writing.
4. **`zen/mimo-v2.5-free`**: Xiaomi high-speed code generator.
5. **`zen/gpt-5-nano`**: Ultra-fast syntax checkups and single-function edits.

## Execution Rules:
- When the user asks to run OpenCode on a task, invoke the `opencode_run` action.
- Pass `task` and optional `model` override if the user requested a specific model (e.g. `zen/big-pickle`).
- If no model is specified, `opencode_run` automatically uses your configured Zen free model from settings.
- Summarize the final diff and report to the user in concise voice and mirror the details to the HUD content panel.
