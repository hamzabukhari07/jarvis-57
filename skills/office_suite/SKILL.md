---
name: office_suite
description: Office productivity document generation, Word (.docx), Excel (.xlsx), and PDF publication standards for business reports and analytics.
metadata:
  author: ZEZO / Hamza Bukhari
  version: '2.0'
---

# Office Suite & Technical Documentation Protocol

Use this skill when generating structured technical reports, executive summaries, tabular datasets, or printable documents.

## Formatting Guidelines:
1. **Executive Summaries:** Include clear problem statements, high-level architecture decisions, and key takeaways.
2. **Tables & Metrics:** Present multi-column benchmarks, telemetry comparisons, and structured tables with explicit column headers.
3. **File Output Standards:**
   - Always persist documents with meaningful snake_case filenames (e.g. `system_architecture_report.md`, `q3_telemetry_summary.xlsx`).
   - Use atomic write operations via `file_controller(action='write')` to prevent duplicate or corrupt files.
