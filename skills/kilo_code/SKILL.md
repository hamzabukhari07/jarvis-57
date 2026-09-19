---
name: kilo_code
description: Autonomous coding, multi-file refactoring, and codebase analysis delegation via Kilo Code CLI using official zero-cost Free Models.
metadata:
  author: Zezo / Kilo Code
  version: '1.0'
---

# Kilo Code Autonomous Coding Protocol

Use this skill when the user explicitly requests to use Kilo Code or delegates autonomous coding, multi-file edits, or visual UI refactoring.

## Kilo Code Zero-Cost Free Models Matrix:
1. **`kilo-auto/free`** *(Default)*: Automatically and dynamically routes active requests to the best available free model on the market without manual configuration.
2. **`kilo/hy3:free`**: Top-tested free coding model achieving strong 47.6% on KiloBench evaluation suite.
3. **`kilo/minimax-m3:free`**: Popular community choice with a massive 1-Million token context window completely free ($0/0 token cost).
4. **`kilo/nemotron-3-ultra:free`**: NVIDIA high-capacity free model favored for large, multi-file codebase refactoring.
5. **`kilo/ling-3.0-flash-vl:free`**: Multimodal vision model ideal for visual design-based adjustments alongside code edits.
6. **`kilo/qwen-2.5-coder:free`**: Fast, reliable general coding and syntax generation.

## Execution Rules:
- When the user specifically commands Kilo Code to perform a task, invoke the `kilo_run` action.
- Pass `task`, optional `model` override (e.g. `kilo/hy3:free` or `kilo/minimax-m3:free`), and optional `project_path`.
- If no model is specified, `kilo_run` automatically uses the default `kilo-auto/free` dynamic router.
- After execution, summarize the outcome concisely for voice output and display the code changes or report on the HUD content panel.
