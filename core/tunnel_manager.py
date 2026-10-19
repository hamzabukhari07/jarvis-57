"""
core/tunnel_manager.py — Auto-manage a free Cloudflare quick tunnel for ZEZO's
mobile remote gateway.

Goal: a non-technical user should never have to open a terminal. ZEZO starts
cloudflared in the background, captures the public https://...trycloudflare.com
URL, and surfaces it in the QR code. If cloudflared is not installed, the
manager reports `not_installed` so the UI can show a one-click install hint.

Hands-off: this module does not touch any audio/voice pipeline.
"""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

_URL_RE = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

_COMMON_PATHS = [
    r"C:\Program Files (x86)\cloudflared\cloudflared.exe",
    r"C:\Program Files\cloudflared\cloudflared.exe",
    r"C:\cloudflared\cloudflared.exe",
    "/usr/local/bin/cloudflared",
    "/usr/bin/cloudflared",
    "/opt/homebrew/bin/cloudflared",
]


def find_cloudflared() -> Optional[str]:
    """Return absolute path to cloudflared binary, or None if not installed."""
    p = shutil.which("cloudflared") or shutil.which("cloudflared.exe")
    if p:
        return p
    for c in _COMMON_PATHS:
        if Path(c).exists():
            return c
    return None


def _public_dns_resolves(host: str) -> bool:
    """Ask a public resolver (dns.google) whether the hostname has an A record.

    Deliberately bypasses the local resolver so a router/OS negative cache for
    a not-yet-propagated quick-tunnel hostname cannot produce a false negative.
    """
    import json
    import urllib.request
    req = urllib.request.Request(
        f"https://dns.google/resolve?name={host}&type=A",
        headers={"Accept": "application/dns-json"},
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        data = json.loads(r.read().decode("utf-8", errors="replace"))
    answers = data.get("Answer") or []
    return any(a.get("type") == 1 for a in answers)


def _http_status(url: str) -> int:
    """GET the URL and return the HTTP status code (raises on failure)."""
    import urllib.request
    req = urllib.request.Request(url, method="GET",
                                 headers={"User-Agent": "ZEZO-TunnelCheck/1.0"})
    with urllib.request.urlopen(req, timeout=6) as r:
        return r.status


def _flush_dns_cache() -> None:
    """Best-effort: drop any negatively-cached NXDOMAIN for the tunnel host."""
    try:
        if os.name == "nt":
            subprocess.run(["ipconfig", "/flushdns"],
                           capture_output=True,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception:
        pass


class TunnelManager:
    """Manages a single Cloudflare quick tunnel to a local URL."""

    def __init__(self, local_url: str = "http://localhost:8000"):
        self.local_url = local_url
        self._proc: Optional[asyncio.subprocess.Process] = None
        self._url: str = ""
        self._status: str = "idle"   # idle | starting | running | error | not_installed
        self._error: str = ""
        self._drain_task: Optional[asyncio.Task] = None

    # ── public API ──────────────────────────────────────────────────────────
    @property
    def available(self) -> bool:
        return find_cloudflared() is not None

    @property
    def url(self) -> str:
        return self._url

    @property
    def status(self) -> str:
        return self._status

    @property
    def error(self) -> str:
        return self._error

    async def start(self) -> Optional[str]:
        """Start the tunnel. Returns the public URL when ready, else None.

        Retries a few times because free quick-tunnel hostnames sometimes need
        a moment to propagate through DNS, and the first attempt can fail.
        """
        bin_path = find_cloudflared()
        if not bin_path:
            self._status = "not_installed"
            self._error = "cloudflared not found"
            return None

        if self._status == "running" and self._url:
            return self._url

        _flush_dns_cache()
        last_err = ""
        for attempt in range(3):
            print(f"[Tunnel] attempt {attempt+1}/3", flush=True)
            self._status = "starting"
            self._error = ""
            self._url = ""

            creationflags = 0
            if os.name == "nt":
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

            try:
                self._proc = await asyncio.create_subprocess_exec(
                    bin_path, "tunnel", "--url", self.local_url,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    creationflags=creationflags,
                )
            except Exception as e:
                self._status = "error"
                self._error = f"failed to launch cloudflared: {e}"
                return None

            self._drain_task = asyncio.create_task(self._read_loop())
            # Wait up to 30s for the URL to appear
            for _ in range(300):
                if self._status in ("running", "error"):
                    break
                if self._proc.returncode is not None:
                    self._status = "error"
                    if not self._error:
                        self._error = "cloudflared exited early"
                    break
                await asyncio.sleep(0.1)

            if self._status != "running" or not self._url:
                last_err = self._error or "no URL captured"
                await self.stop()
                await asyncio.sleep(1)
                continue

            # Verify DNS propagation + reachability (wait up to ~10s)
            verified = await self._verify_url(self._url)
            if verified:
                return self._url

            last_err = "tunnel URL did not become reachable"
            await self.stop()
            await asyncio.sleep(1)

        self._status = "error"
        self._error = last_err or "tunnel failed after retries"
        return None

    async def _verify_url(self, url: str) -> bool:
        """Return True when the tunnel hostname is publicly resolvable AND the
        origin answers through the tunnel.

        Free quick-tunnels print the banner BEFORE registering DNS, and the
        local router/OS may also negative-cache the first NXDOMAIN — so we poll
        PUBLIC DNS (dns.google) directly for up to ~90s, then hit the URL.
        """
        host = url.split("//", 1)[1].split("/", 1)[0]
        loop = asyncio.get_event_loop()

        # 1) public DNS propagation (up to ~90s)
        dns_ok = False
        for _ in range(45):
            try:
                dns_ok = await loop.run_in_executor(None, _public_dns_resolves, host)
            except Exception:
                dns_ok = False
            if dns_ok:
                break
            await asyncio.sleep(2)
        if not dns_ok:
            return False

        # 2) give the local origin (port 8000) a moment to be fully ready
        await asyncio.sleep(3)

        # 3) reachability through the tunnel (up to ~15s)
        for _ in range(10):
            try:
                status = await loop.run_in_executor(None, _http_status, url)
                if status and status < 500:
                    return True
                await asyncio.sleep(1.5)
            except Exception as e:
                code = getattr(e, "code", None)
                # HTTPError with a real status code: the tunnel IS up
                # (5xx usually just means the local origin is still warming).
                if code is not None:
                    if code < 500:
                        return True
                    await asyncio.sleep(1.5)
                    continue
                # connection/DNS error -> retry
                await asyncio.sleep(1.5)
        return False

    async def stop(self) -> None:
        if self._drain_task and not self._drain_task.done():
            self._drain_task.cancel()
            try:
                await self._drain_task
            except (asyncio.CancelledError, Exception):
                pass
        self._drain_task = None
        if self._proc is not None:
            try:
                self._proc.terminate()
                await asyncio.wait_for(self._proc.wait(), timeout=5)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
            self._proc = None
        self._status = "idle"
        self._url = ""
        self._error = ""

    async def _read_loop(self) -> None:
        if self._proc is None or self._proc.stdout is None:
            return
        try:
            async for raw in self._proc.stdout:
                text = raw.decode("utf-8", errors="replace")
                if not self._url:
                    m = _URL_RE.search(text)
                    if m:
                        self._url = m.group(0)
                        self._status = "running"
                # continue draining to avoid pipe backpressure
        except asyncio.CancelledError:
            raise
        except Exception as e:
            if self._status not in ("running",):
                self._status = "error"
                self._error = str(e)
        # process ended
        if self._status == "running":
            # unexpected exit after success
            self._status = "error"
            self._error = "tunnel process exited"
        elif self._status == "starting":
            self._status = "error"
            if not self._error:
                self._error = "cloudflared exited without producing a URL"


def install_hint() -> str:
    """Human-readable install instruction for the UI."""
    if os.name == "nt":
        return "winget install Cloudflare.cloudflared"
    if os.uname().sysname == "Darwin" if hasattr(os, "uname") else False:
        return "brew install cloudflared"
    return "https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
