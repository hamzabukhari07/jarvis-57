# JARVIS — Dashboard / Remote Control

## Overview

JARVIS includes a **local HTTP dashboard** for phone-based remote control. It uses FastAPI with AES-256-CBC encryption.

**File**: `dashboard/server.py` (884 lines)

## Architecture

```
Phone browser
    ↓
HTTPS → localhost:8000 (FastAPI)
    ↓
AES-256-CBC encrypted communication
    ↓
FastAPI endpoints → JarvisLive methods
```

## Technology

| Component | Library | Purpose |
|-----------|---------|---------|
| Server | `fastapi>=0.110,<1` | HTTP/WebSocket server |
| Server | `uvicorn[standard]` | ASGI server |
| Encryption | `cryptography>=42,<50` | AES-256-CBC |
| Uploads | `python-multipart` | File uploads |
| QR codes | `qrcode[pil]` | Pairing QR code |

## Security

| Aspect | Implementation |
|--------|----------------|
| Transport | Plain HTTP on port 8000 |
| Encryption | AES-256-CBC with session-key-derived key |
| Key derivation | SHA-256(sessionKey‖salt), salt = b'JARVIS-DASHBOARD-v1' |
| Key exchange | QR code with auto-login URL |
| Session key | Generated per session, 32 bytes |
| CryptoJS | Auto-downloaded locally, served from static |

## Key Management

```python
def new_key() -> str:
    # Generate a random session key
    # Returns key

def get_url() -> str:
    # Returns dashboard URL

def get_manual_url() -> str:
    # Returns manual connection URL
```

## Pairing Flow

```
1. User opens dashboard in phone browser
2. QR code displayed on HUD
3. Phone scans QR → gets session key
4. Auto-login: URL + key
5. AES-256-CBC encryption established
6. Remote control active
```

## API Endpoints

### Remote Commands
- Text commands → sent to Gemini Live session
- System status queries
- Settings changes
- Media control

### State Synchronization
- Current state mirrored to dashboard
- Activity log synchronized
- Session status updates

## Activation

```python
# Only started when user activates dashboard:
# "Dashboard unavailable. Run: pip install fastapi \"uvicorn[standard]\" cryptography"
```

## Summary

```
Server: FastAPI + uvicorn, port 8000
Encryption: AES-256-CBC
Pairing: QR code with session key
Library: fastapi, uvicorn, cryptography, qrcode
Purpose: Phone-based remote control
Security: CryptoJS auto-downloaded locally
```