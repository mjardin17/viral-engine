# Empire OS — Changelog

All notable changes to Empire OS are recorded here.

---

## [Unreleased] — Operation Blacksmith (2026-07-04)

### Added

- **`logger.module.ts`** — Centralized structured logging. Singleton `empireLog(level, module, message, data?, ms?)` importable from any module. 5000-entry in-memory ring buffer + daily rotating files in `.empire-data/logs/`. Routes: `/recent`, `/search`, `/stats`, `/export`, `/files`, `/clear`. WARN/ERROR mirrored to stderr. `logDebug / logInfo / logWarn / logError` convenience aliases.
- **`metrics-engine.module.ts`** — Live API performance profiling. Records every `handleRequest()` call via `recordMetric(moduleId, durationMs, statusCode, method, path)`. Per-module P50/P95/P99 latency using a sorted rolling window (1000 requests). System-wide req/min via sliding 60s timestamp bucket. Routes: `/summary`, `/realtime`, `/module/:id`, `/slowest`, `/errors`, `/export`, `/reset`.
- **`job-scheduler.module.ts`** — Background job scheduler. Four built-in jobs: hourly backup trigger, daily discovery scan, nightly self-improvement analysis, weekly log rotation. First run fires 30s after init (not immediately). Smart timer: uses delay from last run to schedule cleanly across server restarts. Routes: `/jobs`, `/jobs/:id`, `/jobs/:id/run`, `/jobs/:id/enable`, `/jobs/:id/disable`, `/history`.
- **`service-registry.module.ts`** — Automatic service discovery + dependency graph. 26 services registered at boot (all empire-modules, 4 adapters, Ollama, Open WebUI). Topological sort for startup/shutdown ordering. Per-service health probes with 5s timeout. Routes: `/services`, `/graph`, `/health-matrix`, `/startup-order`, `/shutdown-order`, `/dependencies/:id`, `/dependents/:id`, `/register`, `/probe/:id`.
- **`notification.module.ts`** — Event-driven notification queue. Exportable `emitNotification()` for any module. Severities: info/warning/error/critical. Auto-expire info notifications after 24h. Critical notifications never expire. Routes: `/all`, `/unread`, `/dismiss/:id`, `/dismiss-all`, `/settings`, `/emit`.
- **Metrics instrumentation in `server.ts`** — `recordMetric()` called after every `mod.handleRequest()` at the module routing call site. Every module request now tracked automatically with zero per-module code.
- **Startup log section** — "BLACKSMITH" section in server startup output showing all 5 new endpoints.

### Changed

- `server.ts` imports expanded with 5 new Operation Blacksmith module imports
- `server.ts` module init block expanded with 5 new module inits (in dependency order: logger → metrics → scheduler → registry → notification)
- All documentation updated: `SERVICES_MAP.md`, `API_DOCUMENTATION.md`, `HEALTH_REPORT.md`
- Total modules: 15 → 21

---

## [Unreleased] — God Mode Work Cycle (2026-07-04)

### Added

- **Request logging middleware** (`server.ts`) — every HTTP request now logs `STATUS METHOD PATH DURATIONms [correlationId]` on response finish. Makes debugging trivial.
- **`stream()` method** on all 4 adapters — real SSE/NDJSON streaming with `onChunk` callback. Anthropic uses SSE delta events. Gemini uses `:streamGenerateContent`. Ollama uses NDJSON. OpenAI uses standard SSE with `include_usage`.
- **`vision()` method** on all 4 adapters — image + text understanding. Anthropic uses base64 content blocks. Gemini uses `inline_data`. OpenAI uses `image_url` data URLs. Ollama uses `images[]` array for llava/moondream models.
- **`embeddings()` method** on Ollama (POST /api/embeddings), Gemini (`text-embedding-004`), and OpenAI (`text-embedding-3-small`). Anthropic throws with a clear message pointing to alternatives.
- **`chat()` convenience method** on all 4 adapters — single-prompt, single-string-return wrapper around `complete()`.
- **`health()` method** on all 4 adapters — returns `{ status, latencyMs, error? }`.
- **Provider Registry routes** for `stream`, `vision`, `embeddings` — `POST /provider-registry/:id/stream`, `/vision`, `/embeddings`.
- **Auto-restart** in health watchdog — critical services with `restartCmd` defined get an automatic restart attempt when offline, with 5-minute cooldown to prevent restart loops. Ollama is the first service with a restart command.
- **Rolling backups** in health watchdog — `.empire-data/` is backed up every hour, keeping the most recent 24 copies in `.empire-data/backups/`. Manual trigger via `POST /watchdog/backup`.
- **Backup management routes** — `POST /watchdog/backup` (trigger now), `GET /watchdog/backups` (list backups with timestamps).
- **`installer.module.ts` top-level try/catch** — any route exception is now caught and returned as a structured `{ error, timestamp }` JSON response with HTTP 500.

### Changed

- All 4 adapters now have `signal: AbortSignal.timeout(...)` on every fetch — prevents hanging requests on slow networks or unresponsive APIs.
- `health-watchdog.ts` `ServiceCheck` interface extended with optional `restartCmd` and `restartResult` fields.
- `health-watchdog.ts` `CheckResult` extended with `restartAttempted` and `restartResult` fields.
- Watchdog `init()` now starts both the 60s health interval AND the 1-hour backup interval.
- Watchdog `shutdown()` now clears both intervals.

### Fixed

- `installer.module.ts` routes previously unguarded — a malformed request body could throw an unhandled exception and crash the route handler. Now wrapped in try/catch.
- Request logging was completely absent — impossible to trace slow routes or silent 500s without it.

---

## [Phase 5] — Backend Production Hardening (2026-07-04)

### Added

- **`provider.registry.ts`** — `ProviderRegistryModule` at `/provider-registry/`. Unified AI provider layer. All 5 providers (Ollama, Anthropic, Gemini, OpenAI, Goose) accessible via one HTTP interface.
- **`health-watchdog.ts`** — `HealthWatchdogModule` at `/watchdog/`. Background 60-second polling of all 10 services. Persists status to `.empire-data/watchdog-status.json`.
- **`executive/executive.module.ts`** added `/status` route — dashboard was returning 404 on this call.
- **`START_EMPIRE.bat`** — single-command launcher: kills port 3001, starts server, opens browser.
- **`EMPIRE_LIVE_DASHBOARD.html`** updated to probe Open WebUI on port 42004 (Pinokio-assigned).
- **`BACKEND_AUDIT.md`**, **`API_DOCUMENTATION.md`**, **`SERVICES_MAP.md`**, **`HEALTH_REPORT.md`** — full production documentation set.

### Fixed

- `LAUNCH_EMPIRE.bat` and `START_EMPIRE_OS.bat` both pointed to `C:\Users\jjard\empire-os\...` (nonexistent path). Fixed to `empire-os-patch\apps\empire-os-server`.
- `executive.module.ts` error responses were missing `timestamp` field. Fixed.
- `ollama_bridge.py` default model was wrong. Patched to `qwen2.5-coder:7b`.

---

## [Phase 4] — Video Factory + Autonomous Executive (2025-12)

### Added

- **`video-factory/`** — 5-file module: departments (19), pipeline (20 stages), memory (Character/Environment/Timeline engines), providers (Veo, Imagen, Flux, Runway, Kling, Luma, ElevenLabs), main module.
- **`executive/`** — 4-file module: workers (CEO, PM, Research, Creative, Engineering, Marketing, Publishing, Analytics, Finance, QA), Master Queue, Daily Briefing, main module.
- Goose agent integration — `POST /goose/run` delegates dev tasks to local Goose CLI.

---

## [Phase 3] — Discovery, Benchmarking, Self-Improvement (2025-11)

### Added

- `discovery-engine.module.ts` — live multi-source AI model discovery (Ollama library, HuggingFace, GitHub, MCP registry, ComfyUI).
- `benchmark-engine.module.ts` — model performance benchmarking with persistence.
- `self-improvement.module.ts` — recommendation engine for model upgrades.

---

## [Phase 2] — Core Modules (2025-10)

### Added

- `model-manager.module.ts` — Ollama browser + install/remove UI.
- `discovery.module.ts` — curated model catalog.
- `health-monitor.module.ts` — system resource monitor (RAM, CPU, disk).
- `media-engine.module.ts` — image/video/audio generation router.
- `knowledge-base.module.ts` — persistent memory store.
- `store.module.ts` — one-click AI software catalog.
- `installer.module.ts` — download and configure AI tools (pip, npm, winget, ollama).
- `empire-dashboard.module.ts` — glassmorphism SPA (Gemini-owned frontend).

---

## [Phase 1] — Foundation (2025-09)

### Added

- `server.ts` — Empire OS HTTP entry point on port 3001. CORS, auth, module routing, graceful shutdown.
- `packages/core/` — shared interfaces: `EmpireModule`, `GatewayRequest`, `GatewayResponse`, `CoreServices`, `AIRouter`, `AIProviderAdapter`, `MemoryBus`, `EventBus`, `WorkflowEngine`.
- File-backed persistence — `FileMemoryBus`, `FileEventBus`, `FileWorkflowEngine` in `.empire-data/`.
- `adapters/ollama.adapter.ts` — local LLM, auto-discovers models.
- `adapters/anthropic.adapter.ts` — Claude Opus 4, Sonnet 4, Haiku 4.
- `adapters/gemini.adapter.ts` — Gemini 1.5 Pro/Flash.
- `adapters/openai.adapter.ts` — GPT-4o, GPT-4o-mini.
- `empire-assistant/` — AI orchestration, agent chat, memory.
