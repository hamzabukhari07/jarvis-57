# JARVIS — Security

## Data Privacy
Everything stays on your machine. No MARK server, no telemetry, no account required.

## Stored Data
| Data | Location | Notes |
|------|----------|-------|
| API key | config/api_keys.json | Plaintext — protect like a password |
| TLS certs | config/certs/ | Self-signed, never leaves machine |
| Memory | memory/long_term.json | Delete to reset |
| WhatsApp sessions | config/whatsapp_web/ | Never commit |
| OAuth tokens | **/token*.json | Never commit |

## Encryption
Dashboard uses AES-256-CBC with session-key-derived key. Self-signed TLS for HTTPS.

## Access Control
PIN-based pairing (6-char one-time keys). Bearer token authentication. Device token revocation.

## Firewall
Auto-configured on first run: port 8000 HTTP, 8001 HTTPS.