# 💳 ZEZO — Commercial Launch, Licensing & Update System Plan

> **Project:** ZEZO (Autonomous Desktop AI Operating System v2)  
> **Creator & Lead Architect:** Hamza Bukhari  
> **Doc Purpose:** Turn ZEZO from a source-distributed dev project into a paid, license-controlled, admin-managed commercial product.  
> **Scope:** Installer, activation, license server, admin panel, update system, security, launch.  
> **Status:** 📋 **Planning — Not Yet Executed**  
> **Last Updated:** 2026-10-19

---

## 1. Executive Summary

ZEZO today is a **developer-run Python application**: a user installs Python, runs `setup.py`, then `python main.py`, and pastes their own Gemini API key. There is **no packaging, no version number, no licensing, no activation, no update system, and no admin control**.

To sell ZEZO, four things must exist that do not exist today:

1. A **signed installer** that ships compiled binaries, not plaintext Python source.
2. An **activation + heartbeat system** that binds a license key to machines and lets you revoke access remotely.
3. A **signed update channel** with version gating.
4. A **launch operation**: payments, legal, support, pricing.

### Governing principle

> **Client-side licensing on a Python desktop app is economic deterrence, not hard enforcement.**  
> Design for honest paying users (≈99%). Make bypassing inconvenient and traceable, never assume it is impossible. Any design that depends on unbreakable client checks is rejected.

### Non-goals (v1)

- No custom-built license server (use a vendor in Phase 1; self-host in Phase 3).
- No anti-tamper arms race, no kernel drivers, no obfuscation-vs-cracker projects.
- No macOS/Linux commercial builds at launch (Windows primary only).
- **No changes to the audio/voice pipeline.** Per repo rules, `main.py` live loops, `core/audio_devices.py`, `core/wake_word.py`, and `core/hotkey.py` are hands-off unless a licensing requirement is impossible without them.

---

## 2. Verified Ground Truth (Audited 2026-10-19)

This plan is based on the actual repository state, not assumptions.

| # | Finding | Evidence | Commercial Impact |
| :- | :--- | :--- | :--- |
| G1 | Users install from source: `pip install -r requirements.txt` then `python main.py` | `setup.py` lines 61–135 | **Zero license protection.** Source is readable and patchable in seconds. |
| G2 | No real version string — `APP_VERSION = "ZEZO"` | `ui.py:69` | Version gating, update checks, min-version enforcement, and support all require semver. Cheapest high-leverage fix. |
| G3 | No licensing/activation/fingerprint/updater code anywhere in repo | Repo-wide search | Greenfield: no regression risk, design it correctly once. |
| G4 | API keys stored **plaintext** in `config/api_keys.json` | `ui.py:67`, `core/gemini.py:86`, `core/llm_client.py:41`, `config/__init__.py:5` | Customer secrets exposed. Must be fixed before charging money. |
| G5 | **20+ modules read that JSON directly** | `actions/desktop.py:29`, `actions/web_search.py:87`, `actions/quick_snippet.py:38`, `actions/flight_finder.py:23`, `actions/screen_processor.py:46`, `actions/file_processor.py:36`, `actions/youtube_video.py:63`, `actions/computer_settings.py:43`, `actions/send_message.py:31`, `actions/computer_control.py:39`, `remote/server.py:65`, `core/gemini.py:212` | A naive storage migration would touch 20+ files. Requires a single accessor shim + legacy fallback. |
| G6 | Heavy dependency surface: PyQt6+WebEngine, Playwright, faster-whisper, rapidocr, opencv, pandas, yt-dlp, `agent-browser` npm global | `requirements.txt`, `setup.py:71–102` | Installer payload ~1–2 GB. Packaging/update delivery is a **bigger engineering risk than licensing**. |
| G7 | A local FastAPI remote dashboard already exists (TLS, pairing, device revoke) | `remote/server.py:591–865` | Existing FastAPI/TLS experience; do **not** confuse this dashboard with product licensing. |
| G8 | Modular monolith: every tool is a self-describing file in `actions/` with `TOOL` + `handler()` | `AGENTS.md` Rule 4, `core/action_loader.py` | Licensing must be a **single gate at engine startup**, not per-action checks scattered across `actions/`. |

---

## 3. Decisions To Lock Before Coding (Phase 0)

Nothing below can be implemented cleanly until these are decided. Recommended defaults are given; each is reversible except D2.

| ID | Decision | Options | Recommended Default |
| :- | :--- | :--- | :--- |
| D1 | **Pricing model** | One-time perpetual / subscription / hybrid | **Hybrid:** one-time license including 12 months of updates, then optional annual renewal for continued updates. Offline-friendly, low "my subscription lapsed" support debt. |
| D2 | **Key model (most important)** | (a) User supplies own Gemini key (BYOK) / (b) You provide managed key with fair-use caps / (c) Both | **Both**, with managed-key as a premium tier. BYOK = near-zero COGS but weak kill switch; managed key = true remote control + recurring revenue but you pay for inference. |
| D3 | **Target market** | Consumer / prosumer / business | Prosumer at launch; business tier in Phase 3 (offline licenses, SSO, DPA, invoices). |
| D4 | **Business registration & payout rails** | Where you invoice from; Stripe availability | Determines payment stack. If payouts cannot flow via Stripe directly, a Merchant-of-Record is mandatory. **Verify for your country before committing.** |
| D5 | **Offline tolerance** | Always-online / 7–14 day grace / long offline | 7–14 day grace **plus** launch-count cap. |
| D6 | **License server** | Vendor SaaS / self-hosted | **Vendor SaaS** at launch; self-host in Phase 3. |
| D7 | **Launch platforms** | Windows only / + macOS / + Linux | **Windows only.** Each extra platform multiplies packaging, signing and update work. |
| D8 | **Telemetry stance** | None / opt-in minimal / full | **Opt-in minimal**: app version, heartbeat, crash counts. Never screen/mic/file content. |
| D9 | **Year-1 volume + budget** | 10s / 100s / 1000s of licenses | Budget ~$40–120/month (license vendor + code-signing) regardless of volume. |
| D10 | **Team & time** | Solo / with help | Plan assumes 1 developer full-time, ~5–6 weeks for Phase 1. |

---

## 4. Target Architecture

```
                      ┌────────────────────────────┐
   Buyer ──────────▶  │  CHECKOUT (Merchant of     │  VAT/GST, invoices, chargebacks,
                      │  Record: Paddle/Polar/LS)  │  payouts handled by vendor
                      └──────────────┬─────────────┘
                          order.paid / refund webhooks
                                     │
              ┌──────────────────────▼───────────────────────┐
              │  LICENSE SERVICE  (Keygen.sh / Cryptlex)      │
              │  keys · seats · machine fingerprints ·         │
              │  Ed25519-signed tokens · heartbeat · revoke    │
              └───────┬───────────────────────┬──────────────┘
                      │ activate              │ manifest
        HTTPS         │ heartbeat             │ (Ed25519-signed)
                      │                       ▼
                      │            ┌─────────────────────────┐
                      │            │  CDN / R2 (Cloudflare)  │
                      │            │  signed installers +    │
                      │            │  signed update manifests│
                      │            └─────────────────────────┘
                      ▼
   ┌─────────────────────────────────────────────────────────────┐
   │  ZEZO DESKTOP  (Nuitka onedir build, signed Zezo.exe)       │
   │  ┌──────────────────────┐  ┌──────────────────────────────┐ │
   │  │ core/licensing/      │  │ core/updater/                │ │
   │  │  client · fingerprint│  │  manifest verify · download  │ │
   │  │  store (DPAPI) · gate│  │  silent install · rollback   │ │
   │  └──────────────────────┘  └──────────────────────────────┘ │
   │  Existing engine (audio loop, actions, HUD) — UNCHANGED     │
   └─────────────────────────────────────────────────────────────┘

   ┌──────────────────────────┐
   │  ADMIN                   │  Phase 1: vendor dashboard + payment dashboard
   │  licenses · machines     │  Phase 2: thin custom admin w/ audit log + rules
   │  revoke · force update   │
   └──────────────────────────┘
```

### 4.1 Component decisions

| Layer | Choice | Rationale |
| :--- | :--- | :--- |
| Packaging | **Nuitka `--standalone`** (onedir) | Far harder to decompile than PyInstaller; fewer AV false positives; faster start. `--onefile` is explicitly rejected (AV flags + slow extraction). |
| Installer | **Inno Setup**, per-user install to `%LOCALAPPDATA%\Zezo` | No UAC prompt; updater can replace files without elevation. |
| Updater helper | Small signed `ZezoUpdater.exe` | Runs after app exit; performs verify → silent install → relaunch → rollback on failure. |
| License vendor | **Keygen.sh** (primary) / **Cryptlex** (alternative) | Both provide fingerprints, seat limits, signed license files, heartbeat/dead-man's-switch, entitlements, webhooks, admin dashboards. |
| Payments | **Merchant of Record** (Paddle / Polar / Lemon Squeezy) | Removes global VAT/GST/invoicing/chargeback burden. Required if Stripe payouts are not available in your country. |
| Delivery | **Cloudflare R2 behind license-gated URLs** | Paid build is never a public download link. |
| Admin | Vendor dashboard first; custom thin admin later | Avoid building an admin panel before you have users. |

### 4.2 Proposed module layout (implementation reference, not yet built)

```
core/
  licensing/
    __init__.py
    config.py        # endpoints, pinned Ed25519 public key, channel, grace policy
    fingerprint.py   # hash( MachineGuid + volume serial + CPU/SMBIOS + install_id )
    store.py         # DPAPI (Windows) / Keychain / secretstorage token cache
    client.py        # activate() · heartbeat() · deactivate() · refresh_token()
    gate.py          # is_licensed() · lock_reason() · degraded modes
    state.py         # local state machine: ACTIVE/LICENSED_OFFLINE/GRACE/EXPIRED/REVOKED
  updater/
    __init__.py
    manifest.py      # fetch + Ed25519 verify + sha256 verify + min_version gate
    apply.py         # download → temp → launch ZezoUpdater.exe → exit
  telemetry/
    heartbeat.py     # version + uptime only (opt-in, non-blocking thread)

config/
  secure_store.py    # NEW single accessor shim for API keys (see §8.1)
```

**Integration points (deliberately minimal):**

| Point | Location | Rule |
| :--- | :--- | :--- |
| Startup gate | Existing startup/setup-screen path in `main.py`/`ui.py` | One gate. Extend the existing Gemini-key setup screen; do not add a second onboarding flow. |
| Heartbeat | Background daemon thread | Must be non-blocking; never stall the voice loop (Repo Rule 5). |
| API key access | `config/secure_store.py` shim | Migrate readers incrementally; legacy JSON remains a read fallback (Repo Rule 2 — no regression). |
| Actions | `actions/` | **Not touched.** No per-action license checks. |

---

## 5. License Key & Activation Specification

### 5.1 Key format

- Crockford Base32, 5 groups × 4 chars + check digit: `ZEZO-8K3M-P7QX-2YH4-9TWD`
- Server-generated only, high entropy, no embedded meaning (no plan/date encoded in the key).
- Client-side parsing is for UX only (grouping, typo check). **Validity is always server-side.**

### 5.2 Endpoint contract

```
POST /v1/activate    { key, fingerprint, install_id, version, os, channel }  → { token }
POST /v1/heartbeat   { token, version, os, uptime }                          → { revoked, entitlements, notices[], min_version, flags{} }
POST /v1/deactivate  { token }                                               → { ok }        # frees a seat
GET  /v1/updates/check?channel=stable&version=1.4.2                          → { manifest }
```

### 5.3 Signed license token

Ed25519-signed; public key pinned inside the compiled binary; private key lives only in the license service.

```json
{
  "sub": "lic_9f2c...",
  "plan": "pro",
  "entitlements": ["voice", "automation", "fleet"],
  "seats": 2,
  "machine_id": "a91c...",
  "iat": 1760000000,
  "exp": 1760086400,
  "grace_until": 1760691200,
  "kid": "2026-01",
  "sig": "base64..."
}
```

### 5.4 Activation sequence

1. Buyer pays → `order.paid` webhook → license created with plan/seats/expiry → key emailed.
2. First launch → activation screen → user pastes key.
3. `POST /v1/activate` → seat available? bind fingerprint → return token. Seats exhausted → clear error + "deactivate a device" link.
4. Token cached **encrypted**: DPAPI `CryptProtectData` on Windows; Keychain / `secretstorage` elsewhere. **Never** in `config/*.json`.
5. Background heartbeat every 6–24 h → refreshes token, applies `revoked` / `min_version` / `flags`.
6. Revocation UX is graceful: preserve all user data, explain why ("license refunded / deactivated"), offer a support link. **Never delete user data.**

### 5.5 State machine

| State | Trigger | Behavior |
| :--- | :--- | :--- |
| `ACTIVE` | Fresh token from server | Full functionality |
| `LICENSED_OFFLINE` | Network unreachable, within grace | Full functionality; retry silently |
| `GRACE` | Token expired, within `grace_until` and launch cap | Full functionality + subtle notice |
| `DEGRADED` | Subscription lapsed / soft-limit | Voice or automation disabled; app opens; upgrade CTA |
| `EXPIRED` | Grace exhausted (time **or** launch count) | Activation screen; user data intact |
| `REVOKED` | Server says revoked | Blocked with reason + support path; user data intact |
| `TAMPER_SUSPECT` | Clock rollback detected | Treated as offline-expired; logged for telemetry |

### 5.6 Machine fingerprint rules

- Inputs: `MachineGuid` (`HKLM\SOFTWARE\Microsoft\Cryptography`), system volume serial, CPU brand + SMBIOS UUID, plus random `install_id` written at first run.
- Send only `sha256(salt + signals)` — never raw serials.
- **Fuzzy match:** ≥3 of 4 signals match → same machine, silent re-bind. Below that → new activation slot.
- **Clock-rollback defense:** persist `last_seen_server_time`; system time earlier than stored → treat as offline-expired. Also cap offline use by **launch count**, not just elapsed time.
- Concurrent-heartbeat detection: same license active from multiple IPs/machines simultaneously → flag in admin.

### 5.7 Grace policy (write this down, then code it)

| Rule | Value (initial) |
| :--- | :--- |
| Token TTL | 24–72 hours |
| Offline grace | 14 days **or** 30 launches, whichever comes first |
| Heartbeat interval | 6 hours (jittered), non-blocking |
| Fail behavior | **Never fail-closed instantly.** Transient network errors keep the app running. |
| Revocation lag | Up to grace window — accept and document this |

---

## 6. Update System Specification

> An auto-updater is a **remote code execution channel into customer machines.** Treat it as security-critical infrastructure.

### 6.1 Versioning (prerequisite — do this first)

- Real `MAJOR.MINOR.PATCH+build` semver exposed via a `--version` flag and in the HUD.
- Replace `APP_VERSION = "ZEZO"` (`ui.py:69`) as the source of truth; keep the display name intact so existing window-title logic (`ui.py:174–177`) is unaffected.

### 6.2 Signed manifest

```json
{
  "version": "1.5.0",
  "min_version": "1.3.0",
  "mandatory": false,
  "channel": "stable",
  "rollout_pct": 25,
  "url": "https://cdn.example/Zezo-1.5.0-setup.exe",
  "sha256": "…",
  "sig": "…",
  "notes_url": "https://…",
  "released_at": "2026-11-02T10:00:00Z"
}
```

### 6.3 Update flow

```
App start / daily timer
   → GET /v1/updates/check
   → verify Ed25519 signature of manifest (public key pinned in binary)
   → compare version, honor channel + rollout_pct + min_version
   → download to %TEMP% (resumable)
   → verify sha256 + signature BEFORE execution
   → launch ZezoUpdater.exe → app exits → silent Inno install
     (/VERYSILENT /NORESTART /SUPPRESSMSGBOXES) → relaunch
   → failure ⇒ rollback to previous package (kept on disk)
```

### 6.4 Rules

| Rule | Reason |
| :--- | :--- |
| Signature verification is mandatory, never optional | Prevents a compromised CDN from pushing malware to paying customers |
| Never allow downgrade below `min_version` | Min-version is your compatibility/kill-switch lever |
| Signed emergency rollback manifest is the only downgrade path | Lets you pull a bad release safely |
| Staged rollout by `rollout_pct` + channel | Contains blast radius of a broken release |
| Sign `Zezo.exe`, `ZezoUpdater.exe`, and the installer; RFC-3161 timestamp everything | SmartScreen trust + signature validity after cert expiry |
| Submit each release to Microsoft's false-positive portal | AV flags are a silent conversion killer |
| Delta updates are Phase 2, not MVP | Full-package replacement is slow but correct and simple |

### 6.5 Packaging strategy (the 1–2 GB problem)

| Option | Trade-off | Recommendation |
| :--- | :--- | :--- |
| Ship everything in one installer | ~1–2 GB, weak conversion, metered-connection failures | MVP only if unavoidable |
| Core + downloadable "packs" (automation, vision, transcription) | Smaller download, more moving parts | **Preferred** for the parts already lazily used (`playwright install`, wake-word model, OCR models) |
| Delta/differential packages | Best UX, most engineering | Phase 2 |

---

## 7. Admin Panel Specification

### 7.1 Phase 1 — vendor dashboards (zero build cost)

License service dashboard + payment dashboard cover: license list, plan/seat edits, revoke, refunds, webhook log.

### 7.2 Phase 2 — thin custom admin (only what vendors cannot do)

**Visibility**

- Licenses: key (masked), plan, seats used/total, expiry or perpetual, status, owner email, created date, notes.
- Machines: `install_id`, hashed fingerprint, OS, app version, first/last seen, country/city (not full IP), activation history.
- Events: activation, deactivation, heartbeat gap, revoked, forced update, refund/chargeback.
- Aggregate: active installs by version, by channel, by plan; churn from heartbeat gaps.

**Control**

- Revoke / reinstate a license or a single machine.
- Reset seats; move a license to a new machine (support's #1 request).
- Extend expiry; change plan/entitlements; apply feature flags.
- Force update: raise `min_version` per channel.
- Kill a specific build/version.

**Automation rules**

| Rule | Action |
| :--- | :--- |
| Refund or chargeback received | Auto-suspend license |
| Same license online concurrently from > seats machines | Flag for review |
| Version below `min_version` for 30 days | Force update prompt |
| Heartbeat gap > grace window | Downgrade to `EXPIRED` state on next contact |

**Security of the admin itself**

- Mandatory TOTP 2FA; IP allowlist; individual named accounts (no shared logins).
- Append-only audit log: actor, action, target, before→after, IP, timestamp. No edit/delete.
- No raw database access from the UI. An admin panel that can brick installs is **payment-tier sensitive infrastructure**.

---

## 8. Security Requirements

### 8.1 Secret storage (fixes finding G4/G5)

- New `config/secure_store.py` exposing `get_key(name)` / `set_key(name, value)` / `delete_key(name)`.
- Backend: Windows Credential Manager / DPAPI (`keyring` or `pywin32`), Keychain on macOS, `secretstorage` on Linux.
- **Migration strategy:** the shim reads the new store first, then falls back to legacy `config/api_keys.json`, so the 20+ existing readers (`actions/*`, `core/gemini.py`, `core/llm_client.py`, `remote/server.py`) keep working untouched. Migrate call sites incrementally; delete the plaintext file only at the end.
- Never log key values. Never transmit user keys to your servers. Never bundle your own Gemini key in the binary.

### 8.2 Code signing

| Item | Detail |
| :--- | :--- |
| Certificate | OV/EV from a CA, or **Azure Trusted Signing** (~$10/mo, requires ~3 years verifiable org history) |
| Constraint | Since 2023, OV/EV private keys must live on hardware token/HSM — budget lead time |
| Lead time | **1–3 weeks of validation. Start on day 1 — this blocks launch.** |
| Sign | `Zezo.exe`, all bundled DLLs, `ZezoUpdater.exe`, Inno installer, update manifests |
| Timestamp | RFC-3161 on every artifact |
| Risk | Unsigned binaries → SmartScreen warnings → lost sales |

### 8.3 Anti-bypass (proportionate effort)

| Lever | Effect |
| :--- | :--- |
| Nuitka compilation (no `.py` shipped) | Raises effort from "notepad edit" to "reverse engineering" |
| Integrity self-check against a signed manifest of critical modules | Deters casual patching; not unbreakable |
| Per-customer watermark (license ID embedded in build metadata) | Trace leaked copies to a buyer |
| Rate limiting on activation attempts per key/IP | Blocks brute-force and key-sharing automation |
| Server-side validation of anything valuable | The only genuinely strong control you have |

**Explicitly rejected:** kernel drivers, VM detection, aggressive obfuscation, "unbreakable" claims. A determined cracker wins; the goal is that the honest 99% find paying easier than patching.

### 8.4 Transport & abuse prevention

- HTTPS only, TLS 1.2+, HSTS. Skip aggressive certificate pinning (breaks legitimate rotation and offline users); **signing payloads is stronger and safer**.
- Unique-card/email fingerprint on trials; chargeback → auto-revoke; key from many IPs → flag.
- Seat limits enforced **concurrently via heartbeat**, not only at activation time.

### 8.5 Privacy (launch blocker, not a later nicety)

- ZEZO sees screen, microphone and files. Telemetry must be opt-in and content-free (version, uptime, crash counters).
- Hash machine identifiers; document retention; publish a privacy policy; prepare a DPA template for business buyers.
- EULA must include an acceptable-use clause (scraping/automation abuse), liability cap, and warranty disclaimer.

---

## 9. Limitations & Risks (what you cannot control)

| Risk | Reality | Mitigation |
| :--- | :--- | :--- |
| Offline / air-gapped machines | Admin disable only applies on next contact; grace window delays revocation | Choose grace window deliberately; document the lag |
| BYOK + Python | You can stop *your app*, not the user's capability; patched binaries skip checks | Managed-key tier; Nuitka; watermarks; fast updates |
| VM cloning / disk imaging | Cloned fingerprints look identical | Concurrent-heartbeat detection + per-install random id |
| Hardware drift | Motherboard/RAM changes cause false lockouts | Fuzzy matching + self-serve seat reset |
| License server outage | Paying users locked out of their product | Grace window + retry messaging; never fail-closed instantly |
| AV false positives | Mic/screen-capturing Python app flags easily | Nuitka onedir + signing + Microsoft FP portal submissions |
| Installer size (~1–2 GB) | Weak conversion, failed downloads | Core + packs strategy; delta updates later |
| Payment/chargeback fraud | Money risk | Merchant of Record absorbs most of it |
| Support load | ~80% of desktop-software tickets are license/activation issues | Self-serve device deactivation + excellent error copy + runbook |
| Consumer law | EU/UK 14-day withdrawal rights on digital goods | Explicit waiver consent at checkout + clear refund policy |
| Piracy | Cracked build in week 1 hurts | Watermarking, gated downloads, rapid releases, server-side value |

---

## 10. Phased Roadmap

### Phase 0 — Decisions & Foundations (week 0)

- [ ] Lock D1–D10 (§3).
- [ ] Add real semver + `--version` (fixes G2).
- [ ] Begin code-signing certificate procurement (**lead time 1–3 weeks**).
- [ ] Create payment (MoR) + license service accounts.
- [ ] Write a one-page **activation / offline / grace / revocation policy** (this document, §5.5–5.7).
- [ ] Confirm payout rails for your country.

**Exit criteria:** D1–D10 locked; cert ordered; vendor accounts live; policy written.

### Phase 1 — MVP Commercial Launch (weeks 1–6)

- [ ] **Packaging:** Nuitka onedir build + Inno Setup per-user installer; verified on a clean Windows VM.
- [ ] **Signing:** `Zezo.exe`, `ZezoUpdater.exe`, installer, manifests.
- [ ] **Licensing client:** `core/licensing/` — fingerprint, activation screen, DPAPI token store, heartbeat thread, all seven states (§5.5).
- [ ] **License server:** vendor account configured with plans/seats/entitlements + `order.paid` webhook → license creation.
- [ ] **Payments:** checkout → email key → activate, end-to-end, tested with a real card and a real refund.
- [ ] **Gated download:** paid installer behind license-key URL.
- [ ] **Updater:** signed manifest, check-for-updates, verify-before-run, silent install, rollback, `min_version` enforcement.
- [ ] **Secret storage:** `config/secure_store.py` shim + incremental call-site migration (fixes G4/G5).
- [ ] **Legal:** EULA, privacy policy, refund policy.
- [ ] **Support:** support inbox, ticket tracker, license-issue runbook, self-serve seat reset.
- [ ] **Verification:** 3-layer verification per repo rules (§12).

**Exit criteria:** A stranger with no Python installed can buy, install, activate, use, receive an update, get their machine reset, and get refunded — all without you touching a terminal.

### Phase 2 — Post-Launch Hardening (weeks 6–12, ticket-driven)

- [ ] Self-serve customer portal: deactivate device, download invoices, manage seats.
- [ ] Custom thin admin: audit log + automation rules (§7.2).
- [ ] Delta/differential updates.
- [ ] Opt-in crash/telemetry reporting.
- [ ] Feature flags, time-limited trials, coupon/promo infrastructure.
- [ ] Staged rollout controls surfaced in admin.
- [ ] Core + packs packaging to cut installer size.

**Exit criteria:** Support tickets per 100 licenses trending down; no manual intervention needed for common license problems.

### Phase 3 — Scale & Business Features (months 3–6)

- [ ] Seats/teams + SSO; business invoicing.
- [ ] True offline license files (signed, expiring) for enterprise.
- [ ] Self-hosted license server (full control, no vendor fees).
- [ ] macOS/Linux commercial builds (repeats Phase 1 packaging work per OS).
- [ ] Usage analytics + cohort retention.
- [ ] Affiliate/reseller program.
- [ ] Compliance posture if selling to businesses.

**Exit criteria:** Enterprise-ready control surface; revenue not dependent on a single vendor.

---

## 11. Launch Checklist

**Legal**
- [ ] Business entity; ability to receive international payments
- [ ] EULA + acceptable-use clause (automation/scraping abuse), liability cap, warranty disclaimer
- [ ] Privacy policy covering screen/mic/file access
- [ ] Refund policy incl. EU/UK 14-day withdrawal waiver at checkout
- [ ] DPA template (for business buyers)
- [ ] Trademark check on "Zezo"

**Payments**
- [ ] MoR account verified; payouts tested end-to-end
- [ ] Tax handled by MoR; invoices correct
- [ ] Purchase → key email → activation tested with a real card
- [ ] Refund + chargeback procedure written and rehearsed

**Pricing**
- [ ] Price on value, not on Gemini API cost (BYOK ⇒ COGS ≈ 0)
- [ ] Tiers defined: Solo / Pro / Team-seats
- [ ] One-time license incl. 12 months of updates, + annual renewal option
- [ ] No lifetime deals that trade cash for permanent support debt

**Documentation**
- [ ] Install guide + system requirements
- [ ] Activation & troubleshooting guide
- [ ] API key setup guide (and where keys are stored now)
- [ ] Changelog + update guide
- [ ] FAQ with an honest "what ZEZO cannot do" section

**Release process**
- [ ] Version bump → signed build → signed manifest → staged rollout → changelog → rollback plan → AV FP submission

**Go-to-market**
- [ ] 60-second demo video (voice + desktop agency demos extremely well)
- [ ] Launch channels: Product Hunt, X/YouTube, Discord community
- [ ] Support SLA and response templates
- [ ] 5–10 paid beta users running Phase 1 before any public launch

---

## 12. Verification Plan (Repo Rules 7 & 2.6)

Applies when this plan is executed; every phase must pass all three layers before being marked verified.

**Layer 1 — Static**
- `python -m py_compile` on every touched file.
- Confirm no new imports break the existing action loader.
- Confirm no file outside the declared blast radius is modified.

**Layer 2 — Runtime**
- Clean Windows 10/11 VM with no Python: install → activate → use → update → rollback.
- Forced-failure tests: license server down (grace works), wrong key, seat limit reached, revoked mid-session, system clock moved backwards, network unplugged for 15 days.
- Updater tests: tampered manifest rejected, tampered installer rejected (sha256 mismatch), interrupted download, failed install rollback.

**Layer 3 — Regression**
- `pytest tests/...` — full existing suite green.
- Manual: voice loop, wake word, PTT, HUD, `remote/` dashboard unaffected.
- Explicit confirmation that audio/voice pipeline files were not touched.

**Blast-radius guardrail:** this plan must never edit `main.py` live audio loops, `core/audio_devices.py`, `core/wake_word.py`, or `core/hotkey.py`.

---

## 13. Aggregate Risk Register

| # | Risk | Severity | Likelihood | Mitigation | Phase |
| :- | :--- | :--- | :--- | :--- | :--- |
| R1 | Source-distributed Python = trivially cracked | High | Certain (today) | Nuitka compilation + signed distribution | 1 |
| R2 | Plaintext API keys on customer disk | High | Certain (today) | `secure_store.py` + DPAPI | 1 |
| R3 | Installer too large → poor conversion | High | High | Core + packs; delta later | 1–2 |
| R4 | AV/SmartScreen blocks install | High | High | Signing + onedir + Microsoft FP portal | 1 |
| R5 | Code-signing lead time delays launch | Medium | High | Start Phase 0 day 1 | 0 |
| R6 | Fail-closed licensing bricks paying users | High | Medium | Grace window + never fail-closed instantly | 1 |
| R7 | Hardware drift false lockouts | Medium | High | Fuzzy fingerprints + self-serve seat reset | 1 |
| R8 | Payout rails unavailable in your country | High | Unknown | MoR with compatible payouts (D4) | 0 |
| R9 | Revoked offline user keeps running | Medium | Certain | Accept + document grace lag | 1 |
| R10 | Admin panel compromised | Critical | Low | 2FA, allowlist, audit log, no DB access | 2 |
| R11 | Privacy/liability complaint (screen+mic access) | High | Medium | Privacy policy, opt-in telemetry, EULA | 1 |
| R12 | Update channel abused as malware vector | Critical | Low | Signed manifests, pinned key, verify-before-run | 1 |

---

## 14. Top Mistakes To Avoid

1. Shipping plaintext Python to paying customers.
2. Bundling your own Gemini key inside the binary.
3. Building a custom license server before having paying users.
4. Fail-closed licensing that bricks customers on transient network errors.
5. Hard machine binding with no fuzzy matching.
6. A custom admin panel with no 2FA and no audit log.
7. Silent auto-update without signature verification.
8. Ignoring installer size and AV flags until launch week.
9. Treating anti-piracy as a solvable engineering problem.
10. No real version number, changelog, or rollback plan (you have `APP_VERSION = "ZEZO"` today).

---

## 15. Open Questions (blocking final architecture)

| # | Question | Blocks |
| :- | :--- | :--- |
| Q1 | One-time perpetual, subscription, or one-time + 12 months of updates? | Pricing, license schema, heartbeat design |
| Q2 | BYOK, managed key, or both? | Entire control model (§5, §9) and pricing |
| Q3 | Consumer, prosumer, or business/enterprise? | Admin features, telemetry, legal |
| Q4 | Business registration country + required payout rails? | Payment stack selection |
| Q5 | Offline requirement: fully offline, or 7–14 day grace acceptable? | Grace policy, token TTL |
| Q6 | Windows only at launch, or macOS/Linux too? | Packaging/update scope (multiplies work) |
| Q7 | Expected year-1 license volume? | Vendor tier, budget, infra sizing |
| Q8 | Vendor SaaS license server, or self-hosted from day 1? | Phase 1 duration |
| Q9 | Telemetry: none, opt-in minimal, or full? | Privacy policy, admin analytics |
| Q10 | Solo or team; hours/week available? | Phase 1 timeline realism |

---

## 16. Zero-Cost Launch Stack (Free-Only Variant)

> **Constraint (owner decision):** launch with **$0 out-of-pocket**. Nothing is purchased — no certificate, no vendor license server, no domain, no monthly subscription. Everything below is either free-for-commercial open source or a permanent free tier that requires **no credit card**.

### 16.1 Two kinds of "paid" — what is actually being eliminated

| Type | Definition | Status under this variant |
| :--- | :--- | :--- |
| **A. Out-of-pocket** | Money leaving Hamza's account on a schedule (cert, server, domain, vendor SaaS) | ✅ **Reduced to $0** |
| **B. Per-sale fee** | Deducted from the customer's payment (MoR 5% + $0.50) | ⚠️ Not out-of-pocket. Eliminated only by taking payment manually (bank transfer / PayPal invoice) and issuing keys by hand. |

**Acceptance:** at low volume, per-sale fees are not a cash cost. They matter later, not at launch.

### 16.2 Hidden paid requirement this plan previously missed (repo-specific)

| ID | Finding | Evidence | Resolution under this variant |
| :- | :--- | :--- | :--- |
| G9 | **PyQt6 + PyQt6-WebEngine are GPL v3 / commercial.** Distributing a closed-source paid product on the GPL version means releasing ZEZO's source under the GPL | `requirements.txt:2–3`; Riverbank license FAQ ("If your license is incompatible with the GPL then you need a commercial PyQt license") | **Migrate to PySide6 (LGPLv3)** — free for closed-source commercial use. LGPL obligations: ship Qt license notices, keep Qt dynamically linked, allow relinking against a modified Qt. Alternatively open-source ZEZO under GPL (rejected — kills the paid model). |
| G10 | **Azure Artifact Signing is not available to this project** despite the $9.99/mo sticker | Microsoft docs: paid Azure subscription required (no free/trial); organization validation needs **3+ years verifiable tax history**; regions limited to USA/Canada/EU/UK | No free signing path exists. v1 ships **unsigned** with SHA-256 hashes published and a SmartScreen install guide. |
| G11 | Gemini Live free tier **does include** the model ZEZO already targets | Google pricing page: `gemini-3.1-flash-live-preview` = "Free of charge" for input and output on the Free Tier; no credit card needed in AI Studio | Development/testing is free. Two caveats: rate limits, and free-tier content **is used to improve Google's products** (privacy). |

### 16.3 Free component replacements (supersedes the paid vendors in §4)

| Layer | Paid option in §4 | **Free option (this variant)** | Free limits / caveats |
| :--- | :--- | :--- | :--- |
| UI framework | PyQt6 commercial license | **PySide6** (LGPLv3) | Free for commercial closed-source; API ~95% compatible with PyQt6 |
| License server | Keygen Cloud ($49/mo) | **Cloudflare Workers + D1**, minimal license API written in-house | ✅ No credit card. Workers Free 100k req/day; D1 Free 5M row reads/day, 100k row writes/day, 5 GB storage. Limits reset daily 00:00 UTC. |
| License server (alt.) | Cryptlex | **Deno Deploy + Deno KV** | ✅ No card. 1M requests/month, 20 GB egress, 1 GiB KV, 450k KV reads/month |
| License server (alt.) | Keygen CE self-hosted | **Keygen CE** on Oracle Cloud Always Free | Free for commercial self-hosting, but Docker + Postgres + Redis = ops burden; Oracle signup requires card verification (not charged) |
| Binary hosting | Cloudflare R2 | **GitHub Releases** in a separate **public** releases-only repo | Free, no card, **max 2 GB per asset**. Private-repo release downloads need auth → unusable for customers. Source stays in the private repo. |
| Update delivery | CDN | Same GitHub Releases + signed manifest served by the Worker | Free |
| Domain / TLS | Custom domain ($10–15/yr) | `*.workers.dev` subdomain; site on Cloudflare Pages / GitHub Pages | Free, HTTPS included |
| Payments | MoR (5% + $0.50) | **Ko-fi Shop free plan**, or manual PayPal invoice | Ko-fi free plan: 5% on shop sales, **0% on tips**; pays out to **your own** PayPal/Stripe → Ko-fi is **not** an MoR, so tax is on you |
| Admin panel | Custom build | Worker-hosted admin page behind **Cloudflare Access (Zero Trust free tier, up to 50 users)** | Free; Google-login gated; audit log in D1 |
| AI backend | Paid Gemini tier | **Free-tier AI Studio key** for testing/QA; **users bring their own key (BYOK)**; **Ollama** local as the free fallback (already in the LLM ladder) | Rate limits + free-tier data usage. BYOK moves both cost and privacy responsibility to the customer. |
| Email / key delivery | Paid transactional email | Gmail SMTP + app password (or Resend free 3k/mo) | Free (~500/day Gmail) |
| CI / build | — | GitHub Actions Free | 2,000 min/month on private repos |
| Error tracking / analytics | Paid APM | Sentry free (5k errors), Cloudflare Web Analytics | Free |
| Legal docs | Lawyer-drafted EULA | Free EULA/privacy generators + templates, refund policy | Free. Not a substitute for legal review once revenue exists. |
| Business entity | LLC / registration | **Sole proprietor**, no entity | Free, but personal liability and tax filing are on the owner |
| Trademark | Registration | None | Free; brand unenforced |
| Packaging | — | Nuitka (Apache-2.0) + Inno Setup | Already free |

**Resulting out-of-pocket run rate: $0/month.**

### 16.4 Free license-server capacity (why this is not a toy)

| Quota | Free limit | Practical need (1,000 active users) | Headroom |
| :--- | :--- | :--- | :--- |
| Worker requests/day | 100,000 | ~4,000 (1,000 users × 4 heartbeats/day) | ~25× |
| D1 rows written/day | 100,000 | ~4,000 | ~25× |
| D1 rows read/day | 5,000,000 | ~10,000–50,000 | ~100× |
| D1 storage (account) | 5 GB | Licenses + machines ≈ a few MB | Enormous |
| GitHub Releases asset size | 2 GB / file | Installer 1–2 GB | Fits |

Free tier therefore covers roughly the **low thousands of licenses**; revisit at ~25,000 heartbeat-ing installs or ~25,000 Worker requests/day.

### 16.5 Free license server shape (same contract as §5, free implementation)

```
Cloudflare Worker (free, no card)
  ├── POST /v1/activate    key + fingerprint → Ed25519-signed token
  ├── POST /v1/heartbeat   token → revoked? entitlements? min_version? flags?
  ├── POST /v1/deactivate  token → free a seat
  ├── GET  /v1/updates/check  → Ed25519-signed manifest (asset on GitHub Releases)
  └── GET  /admin          → Cloudflare Access–protected management page
  │
  └── D1 (SQLite) tables: licenses · machines · activations · heartbeats · audit_log
```

| Requirement | Free implementation |
| :--- | :--- |
| Key signing | **Ed25519 via WebCrypto** in the Worker; private key stored as a Worker **secret**, never in the client |
| Machine fingerprint | Unchanged from §5.6 (salted SHA-256 of MachineGuid + volume serial + CPU/SMBIOS + random install_id) |
| Remote disable | `revoked = true` on the machine/license row → next heartbeat (within grace window, §5.7) locks the app |
| Offline grace | Unchanged from §5.7 (14 days **or** 30 launches) — protects users from free-tier hiccups and daily-limit resets |
| Admin auth | Cloudflare Access (free tier ≤50 users) + a second static token check in code |
| Audit log | `audit_log` table in D1 (append-only by convention) |
| Backups | `wrangler d1 export` on demand into the private source repo (no paid backup product) |

**Free-tier failure mode to design around:** D1 free plan **fails queries** once daily read/write limits are hit (hard failure, reset at 00:00 UTC). Mitigation: the client's offline grace window (§5.7) means a limit hit degrades gracefully rather than locking paying users out.

### 16.6 New decisions to lock (add to §3)

| ID | Decision | Value | Why |
| :- | :--- | :--- | :--- |
| D11 | UI framework | **PySide6** (migrate off PyQt6) | Removes the GPL-vs-commercial-license cost and legal risk entirely; cost is dev time only |
| D12 | Code signing at v1 | **Unsigned**, publish SHA-256 for every artifact, ship an install guide | No free signing path exists (§16.2 G10); buying an OV cert becomes the **first purchase once revenue exists** |
| D13 | License backend at v1 | **Cloudflare Workers + D1** (in-house minimal API) | Free tier, no card, ample capacity (§16.4); Keygen CE remains the migration target if ops burden grows |
| D14 | Payments at v1 | **Ko-fi Shop free plan** or manual PayPal invoice; keys issued from the free admin page | Zero out-of-pocket; MoR migration happens only if volume justifies it |
| D15 | AI backend at v1 | **BYOK** for users (their own AI Studio key) + **Ollama** fallback; owner uses the free AI Studio key for QA only | Zero COGS, zero managed-key exposure, and it sidesteps free-tier data-training concerns for customers |

### 16.7 What "free" costs (accepted trade-offs)

| Free choice | Trade-off | Severity |
| :--- | :--- | :--- |
| Unsigned installer (D12) | SmartScreen "Unknown publisher" block screen; a share of buyers will not click through | **High** — the main business cost of this variant |
| Free-tier Gemini key usage by customers | Rate limits (429s) on heavy sessions; free-tier content is used to improve Google's products | Medium — mitigated by BYOK + Ollama fallback |
| Ko-fi / manual PayPal (D14) | Owner becomes the merchant of record → VAT/GST/sales-tax registration and filing is on the owner | Medium — grows with international volume |
| In-house license API (D13) | Security, uptime and rate-limit handling become the owner's responsibility; no vendor SLA | Medium — mitigated by the grace window and a tiny attack surface |
| No entity | Personal liability; payouts land in a personal account | Medium |
| Public releases repo | Installer URL is public and downloadable by anyone | Low — the app is useless without a valid license |
| Hand-issued keys | One manual step per sale | Low at 10–20 sales, must be automated beyond that |

### 16.8 Free-path execution order

1. **PySide6 migration feasibility pass** on `ui.py` / `frontend` (decides D11 before anything else is built).
2. Add real semver (fixes G2).
3. Create the Cloudflare account; scaffold the Worker + D1 + `audit_log`.
4. Implement the four worker endpoints (§16.5) with Ed25519 signed tokens.
5. `core/licensing/` client: fingerprint, activation screen, DPAPI token store, heartbeat thread, state machine (§5.5).
6. Nuitka (onedir) build + Inno Setup installer; publish SHA-256.
7. Public releases-only repo on GitHub; upload the installer.
8. Update check + signed manifest + min-version gate.
9. Ko-fi Shop (or PayPal invoice) live; first license hand-issued from the admin page.
10. Free EULA / privacy / refund-policy drafts + Discord + support email.

### 16.9 Effect on the Phase 1 exit criteria (§10)

Phase 1's exit criteria **do not change** — a stranger must still be able to buy, install, activate, use, receive an update, get their machine reset, and get refunded without the owner touching a terminal. Under this variant, three items move from third-party signup to in-house build (license API, admin page, manifest endpoint), so Phase 1 is **longer, not cheaper in effort** — only cheaper in cash. The blast-radius guardrail in §12 still applies: **no edits to `main.py` live audio loops, `core/audio_devices.py`, `core/wake_word.py`, or `core/hotkey.py`.**

---

## 17. Change Log

| Date | Change | Author |
| :--- | :--- | :--- |
| 2026-10-19 | Initial commercial launch / licensing / update plan created; grounded in repository audit (G1–G8). No code modified. | Planning pass |
| 2026-10-19 | Added §16 Zero-Cost Launch Stack: free-only variant ($0 out-of-pocket), repo-specific findings G9–G11 (PyQt6 GPL, Azure signing ineligibility, Gemini free-tier eligibility), free component replacements, free-tier capacity math, Worker+D1 license-server shape, decisions D11–D15, accepted trade-offs, and a revised execution order. No code modified. | Planning pass |
