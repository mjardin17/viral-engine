# Empire OS — API Documentation
**Base URL:** `http://localhost:3001`  
**Auth:** None in dev mode. Set `EMPIRE_API_KEY` in `.env` to enable — pass via `X-Empire-Api-Key` header.  
**Format:** All responses are `application/json` unless noted. Errors: `{ "error": "...", "timestamp": "ISO" }`

---

## Global Endpoints

### `GET /`
Redirects to `/empire-dashboard/`

### `GET /health`
Returns health of all 15 modules.
```json
{
  "status": "online",
  "modules": {
    "empire-assistant": { "status": "healthy", "details": { "availableModels": 6 } },
    "executive": { "status": "healthy", "details": { "workers": 10, "totalTasks": 7 } }
  }
}
```

### `GET /providers`
Lists all registered AI providers and Goose status.

---

## Empire Assistant (`/empire-assistant`)
AI orchestration — routes requests through AIRouter to best available model.

| Method | Path | Body | Returns |
|--------|------|------|---------|
| POST | `/ai/complete` | `{ messages, strategy?, model? }` | `{ content, model, provider, tokens }` |
| POST | `/ai/task` | `{ type, prompt, context? }` | AI task result |
| GET | `/ai/models` | — | Array of registered models |
| GET | `/ai/stats` | — | Routing statistics |
| POST | `/agent/chat` | `{ message, sessionId? }` | `{ reply, model, context }` |
| GET | `/agent/memory` | — | Recent MemoryBus entries |
| POST | `/agent/remember` | `{ content, scope? }` | Saved memory entry |
| GET | `/health` | — | Module health |

**Strategies:** `cost` (default, Ollama wins) · `quality` (Claude/Gemini wins) · `speed` · `local-only`

---

## Model Manager (`/model-manager`)
Ollama model browser with install/remove/register UI.

| Method | Path | Returns |
|--------|------|---------|
| GET | `/` | HTML UI |
| GET | `/models` | Installed Ollama models |
| GET | `/packs` | Recommended model packs (coding/writing/research/video/local) |
| POST | `/register` | Register model with AIRouter · Body: `{ model: "name" }` |
| GET | `/health` | Module health |

---

## Discovery (`/discovery`)
Model catalog browser — find and install AI models.

| Method | Path | Returns |
|--------|------|---------|
| GET | `/` | HTML catalog |
| GET | `/catalog` | Full curated model catalog JSON |
| GET | `/trending` | HuggingFace + GitHub trending (1hr cache) |
| GET | `/installed` | Currently installed Ollama models |
| POST | `/install` | Pull model via Ollama · Body: `{ id }` |
| POST | `/remove` | Delete model · Body: `{ id }` |
| POST | `/benchmark` | Run timed inference · Body: `{ model }` |
| GET | `/health` | Module health |

---

## Health Monitor (`/health-monitor`)
System resource monitor with service status.

| Method | Path | Returns |
|--------|------|---------|
| GET | `/` | HTML dashboard |
| GET | `/status` | All services (Ollama, Empire OS, etc.) with latency |
| GET | `/metrics` | RAM, CPU, disk (Windows powershell-backed) |
| GET | `/events` | Last 100 system events |
| POST | `/repair` | Attempt auto-repair · Body: `{ serviceId }` |
| GET | `/health` | Module health |

---

## Media Engine (`/media-engine`)
Routes image/video/audio generation to best available engine.

| Method | Path | Returns |
|--------|------|---------|
| GET | `/` | HTML dashboard |
| GET | `/detect` | All available media engines |
| POST | `/route` | Route task to best engine · Body: `{ category }` |
| POST | `/generate/image` | Generate image · Body: `{ prompt, style? }` |
| POST | `/generate/video` | Generate video · Body: `{ prompt }` |
| POST | `/transcribe` | Speech → text · Body: `{ filePath }` |
| POST | `/tts` | Text → speech · Body: `{ text, voice? }` |
| GET | `/health` | Module health |

---

## Knowledge Base (`/knowledge-base`)
Persistent memory store backed by `.empire-data/`.

| Method | Path | Returns |
|--------|------|---------|
| GET | `/` | HTML browser |
| GET | `/entries` | All entries (optional `?category=`) |
| POST | `/store` | Save entry · Body: `{ content, category, tags? }` |
| GET | `/search` | Search · Query: `?q=keyword` |
| GET | `/benchmarks` | Stored benchmark history |
| DELETE | `/entry/:id` | Remove an entry |
| POST | `/preference` | Save a preference · Body: `{ key, value }` |
| GET | `/export` | Export all as JSON |
| GET | `/health` | Module health |

---

## Empire Store (`/store`)
One-click AI software catalog.

| Method | Path | Returns |
|--------|------|---------|
| GET | `/` | HTML store |
| GET | `/catalog` | Full catalog JSON |
| GET | `/item/:id` | Single item |
| GET | `/category/:cat` | Items by category |
| GET | `/health` | `{ status: "healthy", items: N }` |

---

## Installer (`/installer`)
Downloads, verifies, and configures AI tools.

| Method | Path | Returns |
|--------|------|---------|
| GET | `/` | Status page |
| POST | `/install` | Start install job · Body: `{ id, method, cmd, name? }` |
| GET | `/jobs` | All install jobs |
| GET | `/job/:id` | Single job status |
| DELETE | `/job/:id` | Cancel/remove job |
| GET | `/health` | Module health |

**Methods:** `pip` · `npm` · `winget` · `ollama` · `script` · `url`

---

## Empire Dashboard (`/empire-dashboard`)
Main glassmorphism SPA — Gemini-owned frontend.

| Method | Path | Returns |
|--------|------|---------|
| GET | `/` | Full SPA (HTML) |

---

## Discovery Engine (`/discovery-engine`)
Live multi-source AI model discovery.

| Method | Path | Returns |
|--------|------|---------|
| GET | `/` | Status + counts |
| GET | `/all` | Full discovery list (cached) |
| GET | `/sources` | Which sources are available |
| GET | `/ollama` | Ollama library entries |
| GET | `/huggingface` | Trending HuggingFace models |
| GET | `/github` | Trending GitHub AI repos |
| GET | `/mcp` | MCP server registry |
| GET | `/comfyui` | ComfyUI node registry |
| POST | `/scan` | Trigger full rescan |
| GET | `/health` | Module health |

---

## Benchmark Engine (`/benchmark-engine`)
Model performance benchmarking with persistence.

| Method | Path | Returns |
|--------|------|---------|
| GET | `/` | Status + run counts |
| GET | `/history` | All historical runs |
| GET | `/latest` | Most recent run per model |
| GET | `/models` | Installed models with last benchmark |
| POST | `/run` | Run benchmark · Body: `{ modelId, tests? }` |
| GET | `/scores` | Ranking table sorted by composite score |
| GET | `/health` | Module health |

---

## Self Improvement (`/self-improvement`)
AI model recommendation engine.

| Method | Path | Returns |
|--------|------|---------|
| GET | `/` | Status + pending count |
| GET | `/recommendations` | All pending recommendations |
| POST | `/approve` | Approve · Body: `{ id }` |
| POST | `/dismiss` | Dismiss · Body: `{ id, reason? }` |
| POST | `/analyze` | Trigger fresh analysis |
| GET | `/history` | Approved/dismissed history |
| GET | `/health` | Module health |

---

## Video Factory (`/video-factory`)
19-department AI film production engine.

| Method | Path | Returns |
|--------|------|---------|
| GET | `/` | HTML dashboard |
| GET | `/status` | Engine status + provider availability |
| GET | `/providers` | Provider availability (Veo, Imagen, DALL-E, etc.) |
| GET | `/departments` | All 19 department definitions |
| GET | `/departments/:id` | Single department |
| GET | `/pipeline/stages` | All 20 pipeline stage definitions |
| GET | `/projects` | List all projects |
| POST | `/projects` | Create project · Body: `{ title, genre, targetDuration }` |
| GET | `/projects/:id` | Project details |
| POST | `/projects/:id/advance` | Advance to next pipeline stage |
| POST | `/ai/run` | Run AI department · Body: `{ departmentId, projectId, prompt }` |
| POST | `/generate/image` | Generate image · Body: `{ prompt, style? }` |
| POST | `/generate/video` | Generate video · Body: `{ prompt }` |
| POST | `/generate/voice` | Generate voice · Body: `{ text, voice? }` |
| GET | `/memory/characters` | All saved characters |
| POST | `/memory/characters` | Save character |
| GET | `/memory/environments` | All saved environments |
| POST | `/memory/environments` | Save environment |
| GET | `/memory` | Full memory snapshot |
| GET | `/health` | Module health |

---

## Executive (`/executive`)
10-worker autonomous AI company OS.

| Method | Path | Returns |
|--------|------|---------|
| GET | `/` | Daily briefing HTML |
| GET | `/status` | **NEW** — worker count, task stats, uptime |
| GET | `/briefing` | Latest briefing HTML |
| POST | `/briefing/generate` | Generate new briefing |
| GET | `/briefing/json` | Latest briefing JSON |
| GET | `/briefing/history` | Last 30 briefings |
| GET | `/workers` | All 10 workers |
| GET | `/workers/:id` | Worker details + memory + metrics |
| POST | `/workers/:id/run` | Run worker task · Body: `{ prompt }` |
| POST | `/workers/:id/teach` | Add lesson · Body: `{ lesson }` |
| GET | `/queue` | Master Queue overview |
| GET | `/queue/stats` | Queue statistics |
| GET | `/queue/ready` | Tasks ready to execute |
| GET | `/queue/critical` | Critical tasks only |
| GET | `/queue/tasks` | All tasks (with filters) |
| POST | `/queue/tasks` | Create task |
| GET | `/queue/tasks/:id` | Task details |
| POST | `/queue/tasks/:id/approve` | Approve task |
| POST | `/queue/tasks/:id/complete` | Mark complete |
| POST | `/queue/tasks/:id/fail` | Mark failed |
| POST | `/queue/blueprint` | Generate tasks from blueprint |
| GET | `/health` | Module health |

**Workers:** CEO · PM · Research · Creative · Engineering · Marketing · Publishing · Analytics · Finance · QA

---

## Provider Registry (`/provider-registry`) — EXTENDED
Unified AI provider interface — complete() + stream() + vision() + embeddings() + chat().

| Method | Path | Body | Returns |
|--------|------|------|---------|
| GET | `/` | — | All providers + availability + health |
| GET | `/health` | — | Full health check of every provider |
| GET | `/summary` | — | Capability matrix + routing recommendations |
| GET | `/:id` | — | Single provider info + models + health |
| GET | `/:id/models` | — | Models from that provider |
| GET | `/:id/health` | — | Provider health check |
| POST | `/complete` | `{ prompt, strategy? }` | Auto-routed completion |
| POST | `/:id/complete` | `{ prompt, model? }` | Provider-specific completion |
| POST | `/:id/stream` | `{ prompt, model? }` | Streaming (chunks collected, full content returned) |
| POST | `/:id/vision` | `{ imageBase64, prompt, model?, mediaType? }` | Image + text → string |
| POST | `/:id/embeddings` | `{ text, model? }` | Vector embeddings → `{ embedding: number[], dimensions }` |

**Provider IDs:** `ollama` · `anthropic` · `gemini` · `openai` · `goose`  
**Embeddings:** Ollama (nomic-embed-text or first embed model) · Gemini (text-embedding-004) · OpenAI (text-embedding-3-small). Anthropic not supported.  
**Vision:** All 4 LLM adapters. Goose not supported.

---

## Health Watchdog (`/watchdog`) — EXTENDED
Background 60s monitoring + auto-restart + hourly rolling backups.

| Method | Path | Returns |
|--------|------|---------|
| GET | `/status` | Current health snapshot (cached, refreshes every 60s) |
| GET | `/history` | Last 50 health snapshots |
| GET | `/failures` | Current failures + restart attempts |
| POST | `/check` | Trigger immediate re-check of all 10 services |
| POST | `/backup` | Trigger manual `.empire-data/` backup now |
| GET | `/backups` | List rolling backups with timestamps |
| GET | `/health` | Module health |

**Monitored services:** Empire OS · Ollama · Open WebUI · Empire Assistant · Health Monitor · Knowledge Base · Video Factory · Executive · Discovery Engine · Media Engine  
**Auto-restart:** Ollama restarted automatically if offline (5-min cooldown prevents loops)  
**Backups:** Hourly, `.empire-data/backups/`, 24 copies retained

---

## Goose Agent (`/goose`)
Local AI dev agent — runs shell commands, edits files.

| Method | Path | Body | Returns |
|--------|------|------|---------|
| POST | `/run` | `{ task: "..." }` | `{ output, exitCode, durationMs }` |

---

## Empire Logger (`/logger`) — Operation Blacksmith
Centralized structured logging with 5000-entry ring buffer + daily rotating files.

| Method | Path | Query | Returns |
|--------|------|-------|---------|
| GET | `/` | — | Module summary + endpoint list |
| GET | `/recent` | `?limit=100` | Last N log entries (newest first) |
| GET | `/search` | `?q=&level=ERROR&module=executive&limit=50&since=ISO` | Filtered entries |
| GET | `/stats` | — | Entry counts by level and module |
| GET | `/export` | — | Full NDJSON export (`application/x-ndjson`) |
| GET | `/files` | — | Log files on disk with size |
| POST | `/clear` | — | Clear in-memory ring buffer |
| GET | `/health` | — | Module health |

**LogEntry shape:** `{ id, timestamp, level, module, message, data?, ms? }`  
**Levels:** `DEBUG` · `INFO` · `WARN` · `ERROR`  
**Log files:** `.empire-data/logs/empire-YYYY-MM-DD.log` — NDJSON format, one entry per line

---

## Metrics Engine (`/metrics-engine`) — Operation Blacksmith
Live API performance profiling — per-module P50/P95/P99 latency, error rates, req/min.

| Method | Path | Returns |
|--------|------|---------|
| GET | `/` | System summary + all module metrics |
| GET | `/summary` | Same as `/` |
| GET | `/realtime` | Fast system-wide snapshot (call every few seconds) |
| GET | `/module/:id` | Per-module detail + last 20 requests |
| GET | `/slowest` | Top 20 slowest recent requests system-wide |
| GET | `/errors` | Recent error (4xx/5xx) requests |
| GET | `/export` | Full JSON export |
| POST | `/reset` | Reset all counters |
| GET | `/health` | Module health |

**Rolling window:** 1000 requests per module (sorted insert for O(1) percentiles)  
**Req/min:** sliding 60s timestamp bucket

---

## Job Scheduler (`/job-scheduler`) — Operation Blacksmith
Background job runner with 4 built-in production jobs.

| Method | Path | Body | Returns |
|--------|------|------|---------|
| GET | `/` | — | Status + job count |
| GET | `/jobs` | — | All jobs with last run info |
| GET | `/jobs/:id` | — | Job detail + last 50 runs |
| POST | `/jobs/:id/run` | — | Trigger job immediately (awaits completion) |
| POST | `/jobs/:id/enable` | — | Re-enable a disabled job |
| POST | `/jobs/:id/disable` | — | Disable a job |
| GET | `/history` | — | Last 100 runs across all jobs |
| GET | `/health` | — | Module health |

**Built-in jobs:**
- `hourly-backup` — POST /watchdog/backup every 1h
- `daily-discovery` — POST /discovery-engine/scan every 24h  
- `nightly-self-check` — POST /self-improvement/analyze every 24h
- `weekly-log-rotate` — removes log files >14 days old every 7d

---

## Service Registry (`/service-registry`) — Operation Blacksmith
Automatic service discovery, dependency graph, and health matrix for all 26 registered services.

| Method | Path | Body | Returns |
|--------|------|------|---------|
| GET | `/` | — | Summary + counts |
| GET | `/services` | — | All registered services |
| GET | `/graph` | — | Adjacency list dependency graph |
| GET | `/health-matrix` | — | All services with current status + latency |
| GET | `/startup-order` | — | Topological sort (safe boot sequence) |
| GET | `/shutdown-order` | — | Reverse topological sort (safe teardown) |
| GET | `/dependencies/:id` | — | What service :id depends on |
| GET | `/dependents/:id` | — | What depends on :id |
| POST | `/register` | `{ id, name, kind, description, healthUrl?, dependencies?, critical? }` | Register new service at runtime |
| POST | `/probe/:id` | — | Force-probe one service's health |
| GET | `/health` | — | Module health |

**Service kinds:** `empire-module` · `external` · `adapter` · `background`  
**Registered services:** 26 total (Ollama, Open WebUI, 4 adapters, 19 empire modules, 3 background services)

---

## Notification (`/notification`) — Operation Blacksmith
Event-driven notification queue. Importable `emitNotification()` allows any module to surface critical events.

| Method | Path | Body | Returns |
|--------|------|------|---------|
| GET | `/` | — | Summary (unread count + critical alerts) |
| GET | `/all` | — | All notifications newest-first |
| GET | `/unread` | — | Undismissed notifications only |
| GET | `/dismiss/:id` | — | Dismiss a single notification |
| POST | `/dismiss-all` | — | Dismiss all notifications |
| GET | `/settings` | — | Current settings |
| POST | `/settings` | `{ maxQueue?, autoExpireHours?, criticalRetain? }` | Update settings |
| POST | `/emit` | `{ severity, category, title, message, source, actionUrl?, data? }` | Emit notification |
| GET | `/health` | — | Module health |

**Severities:** `info` (auto-expire after 24h) · `warning` · `error` · `critical` (never auto-expires)  
**Categories:** `system` · `ai` · `job` · `backup` · `update` · `custom`  
**Max queue:** 500 notifications (configurable)
