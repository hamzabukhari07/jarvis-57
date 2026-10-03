"""
tests/test_scranton_pixel_office_suite.py — Grounded Scranton Pixel Office & Zero-Simulation Tests.

Lead Architect: Hamza Bukhari
Project: ZEZO (Autonomous Desktop AI Operating System v2)
"""

import pytest
from pathlib import Path


class TestScrantonPixelOfficeSuite:
    def test_office_html_exists(self):
        prod_path = Path("frontend/office.html")
        assert prod_path.exists(), "frontend/office.html production file must exist"

    def test_zero_simulation_no_random_cycle(self):
        prod_path = Path("frontend/office.html")
        content = prod_path.read_text(encoding="utf-8")

        assert "runAutonomousFleetCycle" not in content, "runAutonomousFleetCycle must be completely removed"
        assert "setInterval(runAutonomousFleetCycle" not in content, "setInterval autonomous cycle must be eliminated"

    def test_websocket_event_handlers_integrated(self):
        prod_path = Path("frontend/office.html")
        content = prod_path.read_text(encoding="utf-8")

        assert "initWebSocket" in content
        assert "agent_task_started" in content
        assert "task_done" in content
        assert "fleet_updated" in content
        assert "syncBackendState" in content

    def test_grounded_idle_initialization(self):
        prod_path = Path("frontend/office.html")
        content = prod_path.read_text(encoding="utf-8")

        assert "makeAgent" in content
        assert "renderRoster" in content
        assert "selectAgent" in content
        assert "MICHAEL" in content
        assert "DWIGHT" in content
