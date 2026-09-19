# JARVIS — Dashboard System

FastAPI server on port 8000 for phone remote control.

## Security
PIN-based pairing (6-char keys). Bearer token auth. AES-256-CBC encryption. Self-signed TLS. Auto firewall config.

## Endpoints
GET /, GET /login, POST /login, GET /auto-login, POST /api/command, POST /api/wake, GET /api/files, POST /api/upload, WS /ws, WS /ws/phone-audio.

## Phone Features
Remote voice control, microphone streaming, file sharing, command history.

## Network
HTTP 8000, HTTPS 8001 (self-signed cert). LAN IP discovery.