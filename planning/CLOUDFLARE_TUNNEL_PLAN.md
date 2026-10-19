# Plan: ZEZO Mobile Remote via Free Cloudflare Tunnel

**Creator & Lead Architect:** Hamza Bukhari
**Goal:** Make ZEZO's existing mobile remote gateway (`remote/server.py`, port 8000) reachable from anywhere on the internet over a free HTTPS URL, with the QR code / "Remote Control" button pointing at the public hostname instead of the LAN IP.
**Approach:** Cloudflare Tunnel (free tier) + minimal code changes + optional free Cloudflare Access gate.

> Scope note: This plan touches only `remote/server.py`, `core/ui_server.py`, `memory/config_manager.py`, and (optionally) `frontend/remote static hint`. It does **not** touch any audio/voice pipeline files (`main.py` live loops, `core/audio_devices.py`, `core/wake_word.py`, `core/hotkey.py`) per the hands-off policy.

---

## Phase 0 — Operator setup (no code, ~5 min)

1. Install cloudflared:
   ```powershell
   winget install Cloudflare.cloudflared
   ```
2. Quick test (while ZEZO is running):
   ```powershell
   cloudflared tunnel --url http://localhost:8000
   ```
   → prints `https://<random>.trycloudflare.com`. Open on phone → `/auto-login?key=<KEY>` (KEY from ZEZO "Remote Control" button, valid 10 min).
3. Verify: command send, phone mic audio stream, telemetry all work over the tunnel URL.

**Acceptance:** Mobile remote fully functional over the `trycloudflare.com` URL with no code changes.

---

## Phase 1 — Code: honor a public URL override (minimal)

So the QR code and "Remote Control" button encode the tunnel hostname instead of the LAN IP.

### 1a. `memory/config_manager.py` — add getter/setter
Following the existing `_save_flag`/`load_api_keys` pattern (config lives in `config/api_keys.json`):

```python
def get_public_url() -> str:
    """Public base URL for the mobile remote gateway (e.g. https://zezo.example.com).
    Empty string means 'use LAN IP' (default)."""
    return str(load_api_keys().get("public_url", "") or "").strip().rstrip("/")

def save_public_url(url: str) -> None:
    ensure_config_dir()
    data = load_api_keys()
    data["public_url"] = str(url or "").strip().rstrip("/")
    _atomic_write_config(data)
```

Also allow env var override `ZEZO_PUBLIC_URL` (checked first) so users can set it without touching config.

### 1b. `remote/server.py` — `DashboardServer.get_url()` / `get_manual_url()`
```python
def get_url(self) -> str:
    import os
    pu = os.environ.get("ZEZO_PUBLIC_URL") or get_public_url()  # from config_manager
    if pu:
        return pu
    return f"http://{self._ip}:{PORT}"

def get_manual_url(self) -> str:
    pu = ...  # same override; return host:port form or just the URL
    if pu:
        return pu.lstrip("https://").lstrip("http://")
    return f"{self._ip}:{PORT}"
```
Keep `_ip` for the self-signed 8001 alias (LAN-only HTTPS) — do not change that path.

### 1c. `core/ui_server.py` — `_resolve_remote_details()`
When `on_remote_clicked` returns empty, fall back to the same override chain (env var → `get_public_url()` → LAN IP) instead of always using LAN IP.

### 1d. Frontend hint (optional, cosmetic)
In `remote/static/app.html`, the "connect via HTTPS:8001" hint line is LAN-only. Hide it when `location.hostname` is not a LAN IP (i.e., when served through a tunnel). Low priority.

**Files touched (Phase 1):** `memory/config_manager.py`, `remote/server.py`, `core/ui_server.py`, optionally `remote/static/app.html`.
**Files NOT touched:** `main.py` live loops, `core/audio_devices.py`, `core/wake_word.py`, `core/hotkey.py`, browser control, UI core.

---

## Phase 2 — Persistent tunnel + auto-start (ops, no code)

For a stable URL that survives reboots:

1. Free Cloudflare account + a domain (domain costs ~$10/yr — if you want $0, stay on `trycloudflare.com` ephemeral URLs from Phase 0; skip named tunnel).
2. `cloudflared tunnel login` → `cloudflared tunnel create zezo`.
3. `~/.cloudflared/config.yml`:
   ```yaml
   tunnel: <id>
   credentials-file: C:\Users\<you>\.cloudflared\<id>.json
   ingress:
     - hostname: zezo.yourdomain.com
       service: http://localhost:8000
     - service: http_status:404
   ```
4. `cloudflared tunnel route dns zezo zezo.yourdomain.com`
5. `cloudflared service install` (runs as Windows service, auto-starts).
6. Set `ZEZO_PUBLIC_URL=https://zezo.yourdomain.com` (env var) or save `public_url` in config via the new getter — ZEZO's QR code then encodes the public URL.

**Acceptance:** After reboot, tunnel comes up automatically and ZEZO QR code points at the public URL.

---

## Phase 3 — Free security gate (recommended)

Add **Cloudflare Access** (free up to 50 users) in front of `zezo.yourdomain.com`:
- Policy: allow only your email (Google/GitHub/OTP login).
- This sits *in front* of ZEZO's own AES/key auth, so strangers can't even load the login page.

If staying on ephemeral `trycloudflare.com` (no domain), skip this — rely on ZEZO's one-time keys + short expiry.

---

## Phase 4 — Verification (3 layers)

- **Layer 1 (Static):** `python -m py_compile memory/config_manager.py remote/server.py core/ui_server.py`.
- **Layer 2 (Runtime):**
  - Set `ZEZO_PUBLIC_URL` to a tunnel URL, restart ZEZO, click "Remote Control" → QR/login_url uses the public hostname.
  - From a different network (phone on cellular), open the URL, enter key → command round-trips, phone mic audio streams, telemetry updates.
  - Test revoke-devices and re-pair flow.
- **Layer 3 (Regression):** `pytest tests/` for affected modules; confirm existing LAN remote still works when `public_url` is empty.

**UNVERIFIED until run:** real cellular-network latency, tunnel WS idle-timeout behavior for `/ws/phone-audio` (verify ping/pong keeps socket alive > 2 min), Cloudflare Access policy interaction.

---

## Rollback

- Unset `ZEZO_PUBLIC_URL` / clear `public_url` in config → reverts to LAN IP behavior. No other changes.
- `cloudflared service uninstall` removes the tunnel; ZEZO continues to work on LAN.

---

## Operational notes

- Keep PC awake on AC power; enable ZEZO autostart (`get_autostart_enabled`).
- Tunnel adds ~20–80 ms; test phone-mic audio latency from real remote location.
- Do **not** expose port 8000 directly via router port-forward without TLS — always go through the tunnel or a TLS-terminating proxy.
- Audio/voice pipeline remains untouched throughout.

---

## Decision needed from user

1. Phase 0 only (ephemeral `trycloudflare.com`, zero code) — can do now, no repo changes.
2. Phase 0 + Phase 1 (code override so QR uses public URL) — recommended.
3. Full Phase 0–3 (persistent tunnel + Access gate) — needs a domain for stable URL + Access.

Reply with which phases to execute and I'll implement. No code has been changed yet.