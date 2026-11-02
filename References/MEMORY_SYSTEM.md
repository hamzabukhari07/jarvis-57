# MEMORY_SYSTEM.md — OpenHuman "Brain": the Memory System, End-to-End

> The full memory feature: backend (Rust core + hosted engine) → agent tool / prompt plumbing → frontend (UI + RPC). Read together with `PROJECT_MAP.md`.
> Generated 2026-11-02; every path cited was verified to exist. Note: `vendor/tinymemory` is **uninitialized** in this checkout — engine internals are inferred from host code + tests; authoritative spec detail lives in `docs/specs/memory-v2.md` (file verified).

## Table of contents
1. [High-level picture](#1-high-level-picture)
2. [Backend: core memory domain](#2-backend-core-memory-domain)
3. [Memory engine + registry](#3-memory-engine--registry)
4. [Scope model (whose brain?)](#4-scope-model-whose-brain)
5. [Agent tool `memory`](#5-agent-tool-memory)
6. [Turn lifecycle (recall / pack / write)](#6-turn-lifecycle-recall--pack--write)
7. [Background jobs & events](#7-background-jobs--events)
8. [RPC surface (35 methods)](#8-rpc-surface-35-methods)
9. [Billing / free-period gate](#9-billing--free-period-gate)
10. [Frontend: pages, components, RPC calls](#10-frontend-pages-components-rpc-calls)
11. [End-to-end flow (one user turn)](#11-end-to-end-flow-one-user-turn)
12. [Errors & gating](#12-errors--gating)
13. ["Where do I change…?"](#13-where-do-i-change)
14. [Known gaps / risky areas](#14-known-gaps--risky-areas)

---

## 1. High-level picture

```
                       ┌────────────────────  One turn  ────────────────────┐
User chat ─► agent turn dispatch (inference::host_runtime::ops::agent_chat_for)
   │            │
   │            ├─ pre_turn:  prefetch::pre_turn → scoped recall → <memory> block in system prompt
   │            ├─ tool loop:  `memory` tool → recall / fetch / learn / forget
   │            │      writes → durable outbox (tool_writes) → background delivery
   │            └─ post_turn: hooks.rs background logging (cached recall pack)
   │
   ├── RPC namespace `memory.*` (35 methods)  ◄──── frontend (memoryApi.ts)
   ├── hosted engine `tinyhumans` (CortexDB via backend /memory/*) ◄─► api.tinyhumans.ai
   ├── local/self-hosted engines (cortexdb, …) — via memory::engine_registry
   └── sources / backfill (files, conversations) → background jobs → engine ingest
```

The engine core itself is the vendored `tinymemory` / `tinycortex` (contract `tinymemory-api`). OpenHuman keeps only the **host side**: scope resolution, the agent tool, budgets, the write outbox, RPC, UI, and the billing gate.

## 2. Backend: core memory domain

Directory: `crates/openhuman-core/src/memory/` (its `README.md` is authoritative).

| File | Purpose |
| --- | --- |
| `mod.rs` | re-exports: `memory_is_on` (`engine::is_on`), `MemoryTool` + `MEMORY_TOOL_NAME`, `all_memory_controller_schemas`, `register_memory_subscribers` |
| `engine.rs` | `resolve(config) -> Binding` (`On(BoundEngine)` / `Off { engine, endpoint, reason }`); `is_on`; `install_host_engine` (test/embed override); `invalidate` (cache); `bind_external` (scrub wrapper) |
| `engine_registry.rs` | id-keyed registry: `EngineEntry { build, free_background }`, `EngineRequest { config, root }` (`None` = legacy tree, `Some("user:<id>")`); `register_memory_engine[_in]`, `register_memory_health_probe`, `register_read_only_engine_factory`, `unregister_memory_engine`, `lookup`, `bound_engine` |
| `scope.rs` | `identity_pins(config)` (`[memory] agent_id` / `root`, `[memory.agents.<def>]`, `recall.enabled`, layout v3 → pins); `user_root(config)` → `user:<id>` (layout v3 root; derived from `config_path` parent `.../users/<id>`, fallback `local_root` install id); `switch_to_v3` |
| `tools.rs` | the single agent tool `memory` (`MEMORY_TOOL_NAME`); implemented over TinyMemory `SingleTool` / `MemoryTools`; `CallFacts` stamping (§5) |
| `tool_budget.rs` | inline reads on a budget: 15 s per call, 30 s aggregate per run, max 8 calls per run |
| `tool_writes.rs` | durable outbox `HostWriteSink`: max 256 entries / 2 MiB per partition; background delivery; an ack means "queued, not yet saved" |
| `ops.rs` | engine list/get/set, recall, fetch, learn, forget, erase_all, items_list, channel cleanup; `saas_confinement`: TinyMemory `Confinement` — `Policy::Refuse` (RPC) / `Policy::Clamp` (SaaS/tool), selected from the profile root |
| `schemas/defs.rs` | RPC: `FUNCTIONS: [&str; 35]`, namespace `memory`; grouped defs in `schemas/defs/{engine,policy,retrieval,conversations,brain,sources,jobs,import,migration}.rs`; thin handlers in `schemas/handlers.rs` |
| `lifecycle/` | turn-time + background lifecycle (§6, §7): `prefetch.rs`, `hooks.rs`, `jobs.rs`, `memory_block.rs`, `sender.rs`, `session_hooks.rs`, `date_hint.rs`, `views.rs`, `plan_notes.rs` |
| `layout_migration/` | legacy (`app:tinymemory/...`) → per-user v3 tree migration; `app_host.rs` (LayoutHost, `FsLegacyClaim` under `<app>/memory/legacy_claims/`), `state.rs`, `ops.rs` |
| `bus.rs` | event subscribers (§7) |
| `import.rs` | legacy import scan/start/status/retry |
| `billing.rs` | `free_period_active(config)` (§9) |
| `error.rs` | RPC error codes in `data.code`: `MEMORY_OFF`, `UNSUPPORTED`, `INVALID_REQUEST`, `UNAUTHORIZED`, `INSUFFICIENT_CREDITS`, `PLAN_REQUIRED`, `UNAVAILABLE`, `ENGINE` |
| `sources.rs`, `brain.rs`, `explore.rs`, `deletion.rs`, `status.rs`, `types.rs` | sources sync, brain ingest, explorer, deletions queue, status |
| `local_root.rs` | `<workspace>/memory/local_root.json` → `user:local-<install-id>` (local / signed-out identity) |

Test coverage:
- `tests/memory_v2_e2e.rs` — in-process core + mock backend (`scripts/mock-api-server.mjs`, CortexDB proxy routes): engines list/get/set + off state + error codes; `learn → items_list → fetch → recall → forget`; `erase_all`; conversations backfill; sources add/sync/list/remove; context.md; explorer; v1 import gate; retired methods.
- `tests/memory_cortexdb_live.rs` — opt-in live CortexDB (internals: needs verification).
- Unit tests: `crates/openhuman-core/src/memory/*_tests.rs` (fixtures in `test_fixtures.rs`).

## 3. Memory engine + registry

Generic, id-keyed registry — any host can register its own engine:

- **Hosted engine `tinyhumans`**: registered in `crates/openhuman-tinyhumans/src/memory/mod.rs::register(_options)` (idempotent; called from `openhuman_tinyhumans::install` / `register_all`). Registers `EngineEntry { build: engine::bind, free_background: Some(billing::free_period_active) }` plus a read-only health probe and read-only engine factory (for doctor).
- `crates/openhuman-tinyhumans/src/memory/engine.rs::bind(request)`:
  - endpoint = `[memory.engines.tinyhumans] endpoint` (config) or the effective backend API URL (`endpoint_for`).
  - requires `resolve_backend_credential`, otherwise `Binding::Off { reason: "sign in to use TinyHumans memory" }`.
  - headers = attribution headers (`x-sdk-name` etc., from `crates/openhuman-tinyhumans/src/backend/headers.rs`).
  - engine built via `tinymemory_integrations::build_cached(TINYHUMANS_ENGINE, EngineSettings { endpoint, headers, .. }, fingerprint = engine|endpoint|config_path|headers + layout)`; `EngineCredential::Dynamic(HostBearer)` — the backend credential is re-resolved on every request.
  - `rooted(...)` applies the layout root + `legacy_user_segment_read`.
  - the tenant root is pinned server-side (`tenant_root: true`); the host does not send it.
- **Self-hosted `cortexdb` engine** calls CortexDB directly with the user's key (runtime in `vendor/tinymemory` — uninitialized in this checkout).
- **Engine off** is an explicit state: `Binding::Off` + the frontend "Pick a memory provider to start remembering" screen (`MemoryOffState.tsx`).

## 4. Scope model (whose brain?)

- **Memory scope never comes from model arguments — it comes from identity/namespace.** Identity is set explicitly: `OpenHumanRunContext.memory_identity` (`crates/openhuman-core/src/agent/turn_env.rs:76`). Sub-agents = `Identity::child`, team members = `Identity::team_member`, RPC/embed = `Identity::root()`.
- TinyMemory layout: `<root>` + `source:<kind>` nodes (the **shared brain**, owned by no single agent) + `agent:<memory-agent-id>` nodes (per-agent turns).
- **Layout v3**: everything lives below the `user:<id>` root (`memory::scope::user_root` → `org:<id>` tenant root on the wire; backend pins it). Signed-out/local users fall back to `user:local-<install-id>` (`local_root.rs`).
- Item ids are **deduplication keys** — the exact merge/replace rule is TinyMemory-side (needs verification).
- Exact `Identity` / `Namespace` types live in `vendor/tinymemory` (`tinymemory-tools::layout::identity`) — needs verification (submodule uninitialized).

## 5. Agent tool `memory`

- Implementation: `crates/openhuman-core/src/memory/tools.rs` (`MEMORY_TOOL_NAME = "memory"`).
- Registration: pushed into the tool list at `crates/openhuman-core/src/tools/ops.rs:280` (gated: absent when memory is off or the component is disabled; tests `tools/ops_tests_capability_gating_tests.rs` + `agent/tinyagents/tool_registration_tests.rs:139`).
- Actions (from the tool description):

| Action | Effect |
| --- | --- |
| `recall` | semantic search → facts + dated conversation lines |
| `fetch` | paged items, 5 per page, with `next_cursor` |
| `learn` | queue a durable fact / preference / procedure / correction (outbox) |
| `forget` | remove by id |

- Reads run inline within budget (`tool_budget.rs`); writes are validated / confined / scrubbed first, then queued in the durable outbox (`tool_writes.rs`) — an ack means "queued, not yet saved".
- `CallFacts` stamps trusted facts: workspace, thread_id, agent_id, tool_call_id, `in_prompt` ThreadWindow, namespace = `resolved.layout.learnings()`, reach = `Reach::subtree(resolved.root())`.
- Every recall publishes `DomainEvent::MemoryRecalled` and records web-chat citations (`web_chat::citations::record_recall_citations`).

## 6. Turn lifecycle (recall / pack / write)

`crates/openhuman-core/src/memory/lifecycle/`:

| File | Purpose |
| --- | --- |
| `prefetch.rs` | `pre_turn` + compaction recall: deadline-bounded current-message recall (`recall_each_turn_ms`); cache 60 s TTL / 64 entries per context; pack cap 64 KiB; 120 s deadlines |
| `memory_block.rs` | on generation starts, renders beliefs → learnings as the `<memory>` system-prompt block |
| `hooks.rs` | `post_turn` background logging |
| `jobs.rs` | background queue `memory/jobs.json`; belief builds after `build_delay_secs` |
| `sender.rs` | channel actor |
| `session_hooks.rs` | turn delivery from `agent/session_host` |
| `date_hint.rs`, `views.rs` | date hints, item views |
| `plan_notes.rs` | plan notes posted to memory on commit |

Plumbing:
- `agent/session_host/runtime_session/session_hooks.rs` → `memory/lifecycle/session_hooks.rs` → `prefetch::pre_turn`.
- `agent/tinyagents/turn_middleware.rs:693` wires `middleware::memory_pack::memory_pack_middleware()` (`agent/tinyagents/middleware/memory_pack.rs`), which wraps TinyAgents' `MemoryPackMiddleware`: each model request gets the TurnPack as an **ephemeral instruction** (never written into the transcript, so provider prefix caches stay warm).
- `agent/tinyagents/memory_summarizer.rs` calls `prefetch::compaction` on compaction.
- `agent/tinyagents/state_block.rs::close_finished_plan` → `memory/lifecycle/plan_notes.rs`.
- Turn indices: user message = `2n`, assistant reply = `2n+1`.

## 7. Background jobs & events

Subscribers in `crates/openhuman-core/src/memory/bus.rs` (`register_memory_subscribers`):

| Trigger | Work |
| --- | --- |
| `CronSystemJobDue` → `memory_sources_sync` | `sources::sync_due` (scheduled source syncs) |
| `memory_background` (every 5 min) | `import::resume_interrupted`, `layout_migration::tick`, `lifecycle::jobs::run_due`, `deletion::drain` |
| `CredentialChanged` → `memory::pending_deletions` | drains `pending_deletions.json` |

The free-period gate (§9) applies to these background jobs.

## 8. RPC surface (35 methods)

`crates/openhuman-core/src/memory/schemas/defs.rs` → `FUNCTIONS` (35 names). Namespace `memory.<fn>` (JSON-RPC) / CLI `openhuman.memory_<fn>`:

- **engines/policy**: `engines_list`, `engine_get`, `engine_set`, `policy_get`, `policy_set`, `pack_preview`
- **retrieval**: `recall`, `fetch`, `learn`, `forget`, `erase_all`, `items_list`, `items_get`, `explore`
- **agents/conversations**: `agents_list`, `conversations_backfill_status`, `conversations_backfill_start`
- **brain**: `brain_sources`, `brain_search`, `brain_ingest`, `brain_forget`
- **sources**: `sources_list`, `sources_add`, `sources_remove`, `sources_sync`
- **jobs**: `jobs_list`, `jobs_run`
- **import/migration**: `import_scan`, `import_start`, `import_status`, `import_retry_failed`, `migration_scan`, `migration_start`, `migration_status`, `migration_retry`

## 9. Billing / free-period gate

`crates/openhuman-core/src/memory/billing.rs::free_period_active(config) -> bool` precedence:

1. Engine registered in the registry → its `free_background` predicate decides (tinyhumans: cached 60 s `GET /memory/free-period`, expects JSON `{ "active": bool }`).
2. No predicate registered = free; self-hosted engines = free.
3. Memory off / unbound = **not free** (paid background work does not run).

Consumers: automatic import resume, layout-migration tick, full-memory background consolidation.

## 10. Frontend: pages, components, RPC calls

Memory has **no standalone route**. All memory UI lives at `/connections?tab=brain` (chips in `app/src/components/memory/memoryChips.ts`; legacy chips `graph`/`goals`/`context` redirect to `ask`). Container page: `app/src/pages/Memory.tsx`.

Settings: `settings/memory-sync` is a pure redirect — `app/src/components/settings/settingsRouteElements.tsx` (~line 129): `<Navigate to="/connections?tab=brain&brain=brain" />`. Same for `memory-engine`, `memory-data`, `memory-debug`. Legacy `/brain?tab=…` deep links redirect via `app/src/components/routing/BrainRedirect.tsx`. (Verified in `settingsRouteElements.test.tsx`.)

Components under `app/src/components/memory/`:

| Component | Purpose | Wire methods |
| --- | --- | --- |
| `MemoryEngineTab.tsx` | engine picker/status (hosted `tinyhumans` vs cortexdb/local) | `memory_engine_get`, `memory_engine_set` |
| `MemoryEngineSetup.tsx`, `MemoryConnectionPanel.tsx` | endpoint/key form, connection state | `memory_engine_*` |
| `MemoryAskTab.tsx` + `MemoryPackPreview.tsx` | "Ask memory" search + pack preview | `memory_recall`, `memory_pack_preview` |
| `MemoryBrainTab.tsx`, `MemorySyncedSources.tsx`, `MemoryAddSourceDialog.tsx` | brain sources + sync controls | `memory_sources_list/add/remove/sync` |
| `MemoryConversationsTab.tsx`, `MemoryConversationsBackfill.tsx` | conversation-derived items + backfill | `memory_items_list` (`kinds:["conversation"]`), `memory_conversations_backfill_*` |
| `MemoryLearningsTab.tsx` | learnings (cursor-paged, belief-tagged) | `memory_items_list`, `memory_items_get` |
| `MemoryExplorerTab.tsx`, `MemoryHitRow.tsx` | file/document explorer | `memory_items_list` (with `path`) |
| `MemoryItemDialog.tsx` | item detail + Forget | `memory_items_get`, `memory_forget` |
| `MemoryMigrationTab.tsx`, `MemoryCortexCard.tsx`, `MemoryCortexAnnouncement.tsx` | engine migration cards/status (+ per-user dismissal via `userScopedStorage`) | `memory_migration_*` |
| `MemoryImportBanner.tsx` | legacy import (scan → consent → start/status/retry) | `memory_import_*` |
| `MemoryBackgroundTab.tsx` | background consolidation / free-work status | — |
| `MemoryEraseAllCard.tsx` | dangerous erase-all (confirm; analytics `memory_erased_all`) | `memory_erase_all` |
| `MemoryOffState.tsx`, `MemoryDisabledCard.tsx`, `MemoryComingSoon.tsx` | off / disabled / coming-soon states | — |
| `MemoryErrorAlert.tsx` | unified alerts; `MEMORY_PLAN_REQUIRED` → `data-kind="plan-required"` + upgrade button | — |
| `MemoryBrainSearch.tsx`, `MemoryBrainIngestDialog.tsx` | brain search / ingest UI | `memory_brain_search`, `memory_brain_ingest` |
| Helpers: `memoryFormat.ts`, `memoryFacetLabels.ts`, `memoryLifecycleLabels.ts`, `memorySourceLabels.ts`, `memoryChips.ts` | labels / formatting / i18n | — |

**No Redux slice for memory** (absent from `app/src/store/index.ts`) — components call the service directly with `useState`/`useEffect`. Typed facade: `app/src/services/api/memoryApi.ts` (+ `memoryApi.test.ts`, which locks the wire names). RPC keys in `app/src/services/rpcMethods.ts` (`CORE_RPC_METHODS`, e.g. `openhuman.memory_engines_list`). Wire types are **snake_case**, mirroring `docs/specs/memory-v2.md`. Exports: `memoryErrorCode` (`MEMORY_OFF`, `UNSUPPORTED`, `INVALID_REQUEST`, `UNAUTHORIZED`, `ENGINE`), `memoryErrorMessage`, `memoryBrainSources`, engine & import ops. Debug flag: `DEBUG=openhuman:memoryApi`.

**Auth nuance**: a hosted 403 containing `[MEMORY_PLAN_REQUIRED]` is deliberately **not** treated as session-expired by `app/src/services/coreRpcClient.ts` (~line 178, issue #8081) — the user is never signed out; the upgrade alert is rendered instead. Gating is exercised by `app/test/e2e/specs/memory-plan-required.spec.ts` (mock backend 403s `/memory/*`; explorer/learnings/conversations tabs render alerts `memory-explorer-error` / `memory-learnings-error` / `memory-conversations-error` with the `memory-upgrade` testid).

**Chat UI memory chips**: `app/src/features/conversations/aui/ChatMemoryChips.tsx` — a tool-call adapter mapping `memory` / `memory_store` / `memory_recall` / `memory_hybrid_search` calls to the vendored element `app/src/components/assistant-ui/elements/memory-chips.tsx` ("remembered {n}" heading + Forget action). Header comment: the `memory_activity` wire event hasn't landed yet; rendering is leniently parsed from tool-call args/result (needs verification once it ships).

**Background activity**: `app/src/features/conversations/hooks/useBackgroundActivity.ts` exposes a `MemorySyncSummary` (from `memory_sources_list`) rendered in `features/conversations/aui/BackgroundInboxCard.tsx`.

## 11. End-to-end flow (one user turn)

1. The user types a message at `/chat` → thread RPC reaches the core.
2. Core `inference::host_runtime::ops::agent_chat_for` performs native agent dispatch (agent's own `CoreContext`).
3. `session_hooks` → `memory/lifecycle/prefetch.rs::pre_turn` performs a scoped recall (inside the user root) → 60 s cached pack → `MemoryPackMiddleware` injects it as the `<memory>` ephemeral instruction of the model request (never into the transcript, so provider prefix caches stay warm).
4. The agent loop runs. When the model chooses to, it calls the `memory` tool:
   - `recall` / `fetch` run inline (15 s / 30 s budgets) → results woven into the reply; `MemoryRecalled` event + web-chat citations recorded.
   - `learn` → queued in the outbox (the tool result tells the user it is queued; frontend chips also offer Forget).
5. After the turn, `post_turn` background logging runs; plan notes are posted to memory on commit.
6. Background: every 5 min the `memory_background` tick runs (source syncs, import resume, deletion drain, migration).
7. Frontend: chat shows `ChatMemoryChips` live; `/connections?tab=brain` chips expose Ask / Learnings / Conversations tabs with cursor-paged lists.

## 12. Errors & gating

`data.code` (core `memory/error.rs`): `MEMORY_OFF`, `UNSUPPORTED`, `INVALID_REQUEST`, `UNAUTHORIZED`, `INSUFFICIENT_CREDITS`, `PLAN_REQUIRED`, `UNAVAILABLE`, `ENGINE`. Frontend mirrors via `memoryApi.ts::memoryErrorCode`; `MemoryErrorAlert.tsx` renders uniform alerts. `PLAN_REQUIRED` applies to the hosted engine only — self-hosted engines never hit the paywall.

## 13. "Where do I change…?"

| Want to… | Go to |
| --- | --- |
| add/change a memory RPC method | `crates/openhuman-core/src/memory/schemas/defs*.rs` + `schemas/handlers.rs`; frontend mirror: `app/src/services/api/memoryApi.ts` |
| tune the memory tool budget / outbox | `crates/openhuman-core/src/memory/tool_budget.rs`, `tool_writes.rs` |
| change recall speed / pack size | `crates/openhuman-core/src/memory/lifecycle/prefetch.rs` (timing/caps), `agent/tinyagents/middleware/memory_pack.rs` |
| change scope / root / identity | `crates/openhuman-core/src/memory/scope.rs` (+ `local_root.rs`); TinyMemory side `vendor/tinymemory` (init required) |
| change hosted engine endpoint / keys | `crates/openhuman-tinyhumans/src/memory/engine.rs`; gate: `billing.rs` |
| background jobs / source syncs | `crates/openhuman-core/src/memory/bus.rs`, `lifecycle/jobs.rs`, `sources.rs` |
| memory UI tabs / panels | `app/src/components/memory/*`, page `app/src/pages/Memory.tsx` |
| chat memory chips | `app/src/features/conversations/aui/ChatMemoryChips.tsx`, `app/src/components/assistant-ui/elements/memory-chips.tsx` |
| memory tests | `tests/memory_v2_e2e.rs` (mock backend), `tests/memory_cortexdb_live.rs` (live), `app/test/e2e/specs/memory-plan-required.spec.ts`; run via `pnpm test:rust` / `scripts/test-rust-with-mock.sh` |

## 14. Known gaps / risky areas

- `vendor/tinymemory` (+ nested `tinycortex`) is UNINITIALIZED in this checkout — runtime semantics are inferred from host code, `tests/memory_*`, and `docs/specs/memory-v2.md`; the exact `Identity`/`Namespace`/sources API surface should be verified after `git submodule update --init --recursive vendor/`.
- The 5-minute `memory_background` tick has no dedicated e2e coverage — behavior is covered only unit-level in `crates/openhuman-core/src/memory/*_tests.rs`.
- Brain features (`brain_search`, `brain_ingest`, `brain_forget`) have partial e2e coverage in `tests/memory_v2_e2e.rs`; the full ingest→search→forget loop deserves coverage (needs design sign-off first).
- Chat chips still parse tool-call args/result because the dedicated `memory_activity` wire event does not exist yet (confirmed by the file header comment).
- Dedup/merge micro-rules for item ids live inside `vendor/tinymemory`; OpenHuman enforces only the entry-point contracts — verify exact semantics upstream before relying on them.

---
*Generated by code exploration + targeted verification. Re-check anything marked "needs verification" before relying on it.*
