# Empire OS — Missing Components
**Date: 2026-07-05 | Phase 2 Gap Analysis**

Gap = documented as existing or "planned" but not present on disk.

---

## 🔴 CRITICAL: empire_server.py (Video Pipeline Bridge)

**Status in AGENT_MEMORY.md:** "✅ ACTIVE — empire_server.py + VideoPipelineModule built"
**Reality:** `apps/video-pipeline/` contains only `README.md` and `empire-module/`. The Python FastAPI server does not exist.

**Impact:** 
- `VideoPipelineModule` TypeScript adapter proxies to `http://localhost:8002` — nothing answers on port 8002
- Any Empire OS call to trigger renders will hang or timeout
- The module will report as `offline` in the service registry health matrix

**What needs to be built:**
```
apps/video-pipeline/
├── empire_server.py          ← FastAPI on port 8002
│   Routes needed:
│   GET  /empire/health       → module health
│   GET  /empire/status       → module descriptor
│   POST /empire/event        → receive events
│   GET  /api/episodes        → list episodes by channel
│   POST /api/render          → trigger auto_render.py for an episode
│   GET  /api/renders         → list recent render jobs + status
│   GET  /api/render/status   → status of specific render
│   GET  /api/council/status  → council bot status (9 bots)
├── requirements.txt          ← fastapi, uvicorn, requests
└── START_EMPIRE_PIPELINE.bat ← launches uvicorn on port 8002
```

**Priority:** HIGH — without this, Empire OS has no visibility into the render pipeline.

---

## 🔴 HIGH: Database Layer (PostgreSQL + Prisma)

**Status in AGENT_MEMORY.md:** `packages/database/` — "Prisma schema + client (PostgreSQL) (planned)"
**Reality:** Directory does not exist. Zero schema files anywhere in the monorepo.

**Current state:** All persistence uses flat JSON files in `.empire-data/`:
- Knowledge Base → `.empire-data/kb/`
- Workflow Engine → `.empire-data/workflows/`
- Executive tasks → `.empire-data/executive/`
- Logger → `.empire-data/logs/`
- Video Factory projects → `.empire-data/video-factory/`

**What needs to be built (if DB is desired):**
```
packages/database/
├── schema.prisma             ← Models: Episode, RenderJob, KBEntry, WorkflowRun, etc.
├── package.json
└── src/
    ├── client.ts             ← Prisma client singleton
    └── migrations/
```

**Recommendation:** For current scale (3 YouTube channels, local machine), file-backed JSON is sufficient. Build PostgreSQL layer only when multi-machine or multi-user access is needed. Current file-backed approach is battle-tested and requires no external service.

---

## 🔴 HIGH: Docker Compose (planned infrastructure)

**Status in AGENT_MEMORY.md:** `docker/docker-compose.yml` — "postgres:15 + redis:7 (planned)"
**Reality:** `docker/` directory does not exist.

**Recommendation:** Same as above — hold until DB layer is actually built.

---

## 🟡 MEDIUM: apps/web — Next.js Dashboard

**Status in AGENT_MEMORY.md:** "Next.js 14, port 3000 — dashboard UI (planned)"
**Reality:** Directory does not exist. CrossPost Enterprise currently runs on port 3000.

**Note:** Port 3000 is occupied by CrossPost. If a Next.js dashboard is ever built, it needs a different port or CrossPost moves.

**Recommendation:** The `empire-dashboard` module already serves a glassmorphism SPA from within the empire-os-server on port 3001. A separate Next.js app is redundant unless there's a specific reason for it. Mark this as **CLOSED / NOT NEEDED** unless Josh wants a separate app.

---

## 🟡 MEDIUM: apps/api — FastAPI Backend

**Status in AGENT_MEMORY.md:** "FastAPI, port 8000 — data + agent API (planned)"
**Reality:** Directory does not exist.

**Recommendation:** The empire-os-server already serves a full HTTP API on port 3001. A separate FastAPI backend would only make sense if Python-specific AI libraries (LangChain, HuggingFace Transformers) are needed. Mark as **DEFERRED** unless a specific need arises.

---

## 🟡 MEDIUM: EMPIRE_API_KEY — Auth Not Configured

**Status:** Auth system is fully built and wired, but the key is blank in `.env`.
**Impact:** All Empire OS endpoints are unauthenticated in production.
**Fix:** Generate key, set in `.env`, configure CrossPost and dashboard to send it.

---

## 🟡 MEDIUM: Custom Job Registration via API

**Status:** Job Scheduler has 4 built-in jobs. External modules cannot register custom jobs via HTTP.
**Impact:** Automation workflows that need scheduled jobs must be hardcoded in `job-scheduler.module.ts`.

**What's needed:**
```
POST /job-scheduler/jobs/register   ← add a new job at runtime
Body: { id, name, description, intervalMs, endpoint, method }
```

---

## 🟡 MEDIUM: logger.module.ts qp() Bug

**Status:** Query param filtering on all logger GET routes (`/logger/recent?limit=100`, `/logger/search?level=ERROR`) is silently broken. The `qp()` helper reads from custom headers instead of the URL query string.

**Impact:** All logger query params are ignored. `GET /logger/recent?limit=10` returns 100 entries regardless.

**Fix (5 lines in logger.module.ts):**
```typescript
private qp(req: GatewayRequest, key: string): string | undefined {
  // Parse from path query string
  const pathWithQuery = req.path ?? ''
  const qIdx = pathWithQuery.indexOf('?')
  if (qIdx === -1) return undefined
  const params = new URLSearchParams(pathWithQuery.slice(qIdx + 1))
  return params.get(key) ?? undefined
}
```

---

## 🟢 LOW: StoryForge Python Backend Not in Monorepo

**Status:** StoryForge TypeScript adapter is present. The Python backend is external (`github.com/mjardin17/storyforge`).
**Impact:** Empire OS health polling of StoryForge will show `offline` unless StoryForge is separately running.

**What's needed:** Either include StoryForge as a git submodule, or add a `START_STORYFORGE.bat` that Josh can run to ensure port 8001 is active before starting Empire OS.

---

## 🟢 LOW: No Automated Test Coverage for Blacksmith Modules

**Status:** `@empire-os/core` has a vitest suite. The 5 new Blacksmith modules (logger, metrics-engine, job-scheduler, service-registry, notification) have zero test files.

**What's needed:** At minimum, unit tests for:
- `logger.module.ts` — ring buffer wraparound, search filtering, level ranking
- `metrics-engine.module.ts` — percentile calculation correctness
- `job-scheduler.module.ts` — timer scheduling, enable/disable lifecycle

---

## 🟢 LOW: Job Scheduler Hardcoded Localhost

**Status:** Built-in jobs reference `http://localhost:3001` literally.
**Fix:** Use `process.env.EMPIRE_BASE_URL ?? 'http://localhost:3001'`

---

## Summary

| Component | Severity | Build Required? |
|-----------|----------|-----------------|
| `empire_server.py` (video pipeline) | 🔴 CRITICAL | **YES — build now** |
| Auth (set EMPIRE_API_KEY) | 🔴 HIGH | **YES — configure now** |
| PostgreSQL/Prisma | 🔴 HIGH | Deferred — file JSON is sufficient |
| Docker Compose | 🔴 HIGH | Deferred with DB |
| apps/web (Next.js) | 🟡 MEDIUM | NOT NEEDED — dashboard module covers this |
| apps/api (FastAPI) | 🟡 MEDIUM | DEFERRED |
| Custom job registration API | 🟡 MEDIUM | Build when needed |
| logger qp() bug | 🟡 MEDIUM | **YES — quick fix** |
| StoryForge startup helper | 🟢 LOW | Add START_STORYFORGE.bat |
| Blacksmith module tests | 🟢 LOW | Add when time permits |
| Job scheduler base URL env var | 🟢 LOW | **YES — quick fix** |
