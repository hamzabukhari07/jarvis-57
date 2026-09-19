---
name: system_diagnostics
description: Step-by-step diagnostic workflow for PC telemetry, temperature, CPU, RAM, and GPU health analysis.
metadata:
  author: Zezo / FatihMakes
  version: '1.0'
---

# System Diagnostics & Health Inspection

Use this skill when the user asks about PC performance, overheating, slow performance, or hardware telemetry.

## Execution Steps:
1. **Fetch Hardware Telemetry:**
   - Call `system_status` tool to read instantaneous CPU, RAM, GPU, and temperature values.
2. **Threshold Analysis:**
   - CPU / RAM > 85%: Flag as heavy load. Recommend identifying top processes.
   - Temperature > 85°C: Issue thermal warning; advise checking cooling fans/airflow.
   - Storage free space < 15%: Advise disk cleanup.
3. **Format Voice & Visual Response:**
   - Give a concise, reassuring verbal summary (e.g. *"Sir, your CPU is at 24% and temperatures are cool at 48°C."*).
   - If anomalies exist, report specific offending metrics first.
