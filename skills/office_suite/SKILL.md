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
   - Always persist documents with meaningful filenames (e.g. `Hamza_Bukhari_Resume.pdf`, `random_data.xlsx`, `system_report.docx`).
   - Use atomic write operations via `file_controller(action='write', path='...', content='...')`.
   - **PDF Generation (`.pdf`):** Provide structured markdown in `content` with `# Title`, `## Sections`, bullet points `-`, and paragraphs. `file_controller` will automatically compile and format it into a professional PDF document.
   - **Word Generation (`.docx`):** Provide structured markdown in `content`. `file_controller` will automatically construct a native Word document with styled headings and lists.
   - **Excel Generation (`.xlsx`):** Provide comma-separated (`CSV`), tab-separated, or pipe-separated lines in `content`. `file_controller` will automatically build a native `.xlsx` workbook.
