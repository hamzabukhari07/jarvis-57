---
name: test_fastapi_deploy
description: Autonomous workflow for running and validating FastAPI apps on port 8000.
metadata:
  author: auto_learned
  version: '1.0'
---

# Test Fastapi Deploy

1. Check if uvicorn is installed.
2. Run uvicorn main:app --reload --port 8000.
3. Verify health endpoint at /health.
