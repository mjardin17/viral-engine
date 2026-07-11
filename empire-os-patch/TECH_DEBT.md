# Empire OS — Technical Debt Register
**Date: 2026-07-05 | Phase 2 Gap Analysis**

Debt items are prioritized by impact × fix effort. Actionable fix included for each.

---

## 🔴 CRITICAL

### TD-001: .env Committed to Git (Active Key Exposure)
- **File:** `apps/empire-os-server/.env`
- **Debt type:** Security
- **Impact:** Live API credentials in git history
- **Fix:** See SECURITY_REPORT.md CRITICAL-1. Keys rotated → `git rm --cached` → `.gitignore`
- **Effort:** 15 minutes (after Josh rotates keys)
- **Blocks:** All other work

---

## 🔴 HIGH

### TD-002: empire_server.py Does Not Exist
- **File:** `apps/video-pipeline/empire_server.py` (missing)
- **Debt type:** Missing implementation (documented as built)
- **Impact:** Empire OS cannot trigger renders or monitor the pipeline
- **Fix:** Build FastAPI server (see MISSING_COMPONENTS.md for spec)
- **Effort:** 2–3 hours

### TD-003: Auth Is Off (EMPIRE_API_KEY blank)
- **File:** `apps/empire-os-server/.env`
- **Debt type:** Security configuration
- **Impact:** All 21 modules are publicly accessible
- **Fix:** Generate key, set in .env, configure callers
- **Effort:** 10 minutes

---

## 🟡 MEDIUM

### TD-004: logger.module.ts qp() Bug
- **File:** `apps/empire-os-server/logger.module.ts`
- **Function:** `private qp(req, key)`
- **Debt type:** Silent bug
- **Impact:** All query params to logger routes silently ignored (`?limit=`, `?level=`, `?q=`)
- **Fix:**
  ```typescript
  private qp(req: GatewayRequest, key: string): string | undefined {
    const qIdx = (req.path ?? '').indexOf('?')
    if (qIdx === -1) return undefined
    return new URLSearchParams(req.path.slice(qIdx + 1)).get(key) ?? undefined
  }
  ```
- **Effort:** 5 minutes

### TD-005: Job Scheduler Hardcoded localhost:3001
- **File:** `apps/empire-os-server/job-scheduler.module.ts`
- **Lines:** `makeHttpJob()` calls, 4 places
- **Debt type:** Configuration hardcode
- **Impact:** Jobs fail if server moves to a different port or host
- **Fix:** Replace `'http://localhost:3001'` with `` `${process.env.EMPIRE_BASE_URL ?? 'http://localhost:3001'}` ``
- **Effort:** 5 minutes

### TD-006: empireEvents Global Guards in CrossPost
- **File:** `apps/crosspost-enterprise/server.ts`
- **Pattern:** `if (typeof empireEvents !== 'undefined') empireEvents.push(...)`
- **Debt type:** Fragile global state
- **Impact:** Empire events silently dropped if variable scope changes; no error surfaced
- **Fix:** Declare `const empireEvents: EmpireEvent[] = []` at module scope (not conditional), remove typeof guards
- **Effort:** 20 minutes

### TD-007: CrossPost server.ts Has No .gitignore
- **File:** `apps/crosspost-enterprise/` — no `.gitignore`
- **Debt type:** Security gap
- **Impact:** CrossPost `.env` (Gemini key, GitHub OAuth credentials) could accidentally be committed
- **Fix:** `echo .env > apps/crosspost-enterprise/.gitignore`
- **Effort:** 1 minute

### TD-008: AGENT_MEMORY.md Inaccuracies
- **File:** `AGENT_MEMORY.md`
- **Debt type:** Documentation drift
- **Impact:** Misleads future development; Video Pipeline marked ✅ ACTIVE when bridge doesn't exist
- **Specific errors:**
  - `apps/video-pipeline/` — marked "✅ ACTIVE" — should be "⚠️ ADAPTER ONLY — empire_server.py missing"
  - Port 8000 FastAPI — marked "planned" but no plan to build
  - `packages/database/` — marked "planned" — recommend DEFERRED
- **Fix:** Update AGENT_MEMORY.md after empire_server.py is built
- **Effort:** 15 minutes

### TD-009: Pexels and ElevenLabs Keys Exposed in Comments
- **File:** `apps/empire-os-server/.env`
- **Lines:** Commented-out `PEXELS_API_KEY` and `ELEVEN_LABS_API_KEY`
- **Debt type:** Security (commented secrets in tracked file)
- **Impact:** Keys visible in git history even though commented
- **Fix:** Rotate both keys. Remove commented secrets from .env. Move to a separate `.env.secrets.example` with placeholder values only.
- **Effort:** 10 minutes (after rotation)

---

## 🟢 LOW

### TD-010: No Tests for Blacksmith Modules (5 modules)
- **Files:** `logger.module.ts`, `metrics-engine.module.ts`, `job-scheduler.module.ts`, `service-registry.module.ts`, `notification.module.ts`
- **Debt type:** Missing test coverage
- **Impact:** Regressions from edits won't be caught automatically
- **Fix:** Add `__tests__/` in empire-os-server/, use vitest. Priority: logger + metrics (core paths)
- **Effort:** 3–4 hours total

### TD-011: recordMetric() Not Called from server.ts
- **File:** `apps/empire-os-server/server.ts` + `metrics-engine.module.ts`
- **Debt type:** Wiring gap
- **Impact:** `MetricsEngineModule` is initialized and serves endpoints, but `recordMetric()` is imported and never called from the HTTP handler. All metrics show 0.
- **Fix:** In server.ts, after every `mod.handleRequest()` call, call `recordMetric(moduleId, durationMs, status, method, path)`
  The import is already there: `import { MetricsEngineModule, recordMetric } from './metrics-engine.module.js'`
  Add: `recordMetric(moduleId, gRes.durationMs ?? 0, gRes.status, req.method ?? 'GET', path)`
- **Effort:** 10 minutes

### TD-012: Service Registry Probe Not On Schedule
- **File:** `apps/empire-os-server/service-registry.module.ts`
- **Debt type:** Missing scheduled re-probe
- **Impact:** Service statuses go stale after the initial 2s probe pass on startup. Health matrix shows outdated data.
- **Fix:** Add a `setInterval(() => this.runProbePass(), 5 * 60 * 1_000)` in `init()` — probe every 5 minutes
- **Effort:** 2 minutes

### TD-013: CORS Wildcard in Production
- **File:** `apps/empire-os-server/server.ts`
- **Line:** `res.setHeader('Access-Control-Allow-Origin', '*')`
- **Debt type:** Security configuration
- **Impact:** Acceptable for local dev; unacceptable for any internet-facing deployment
- **Fix:** Restrict to `localhost:3000` and `localhost:3001` in dev; use env var for production origin list
- **Effort:** 15 minutes

### TD-014: No Rate Limiting
- **File:** `apps/empire-os-server/server.ts`
- **Debt type:** Missing protection
- **Impact:** Unconstrained AI calls could run up API costs; unconstrained installer calls could install unwanted software
- **Fix:** Simple in-memory token bucket per IP. Generous limits (1,000 req/min) just to prevent runaway loops.
- **Effort:** 30 minutes

### TD-015: Logger Daily Files Grow Unbounded
- **File:** `apps/empire-os-server/logger.module.ts`
- **Debt type:** Resource leak (disk)
- **Impact:** `.empire-data/logs/` grows forever. The `weekly-log-rotate` job only deletes files >14 days old, so 14 days of logs accumulate.
- **Fix:** The log rotation job already handles this correctly (14-day window). Just verify it runs — check `/job-scheduler/jobs/weekly-log-rotate`.
- **Status:** Already handled by job scheduler. No immediate action needed.

---

## Debt Summary

| ID | Severity | Hours to Fix |
|----|----------|-------------|
| TD-001 | 🔴 CRITICAL | 0.25 (after key rotation) |
| TD-002 | 🔴 HIGH | 3 |
| TD-003 | 🔴 HIGH | 0.15 |
| TD-004 | 🟡 MEDIUM | 0.1 |
| TD-005 | 🟡 MEDIUM | 0.1 |
| TD-006 | 🟡 MEDIUM | 0.3 |
| TD-007 | 🟡 MEDIUM | 0.02 |
| TD-008 | 🟡 MEDIUM | 0.25 |
| TD-009 | 🟡 MEDIUM | 0.15 |
| TD-010 | 🟢 LOW | 4 |
| TD-011 | 🟢 LOW | 0.15 |
| TD-012 | 🟢 LOW | 0.03 |
| TD-013 | 🟢 LOW | 0.25 |
| TD-014 | 🟢 LOW | 0.5 |
| TD-015 | 🟢 LOW | 0 (handled) |

**Total hours to clear all debt: ~9 hours**
**Total hours to clear Critical + High: ~3.5 hours**

---

## Quick Wins (do these first, <30 min total)
1. TD-003 — Set EMPIRE_API_KEY (10 min)
2. TD-004 — Fix logger qp() bug (5 min)
3. TD-005 — Fix job scheduler URL (5 min)
4. TD-007 — Add crosspost .gitignore (1 min)
5. TD-011 — Wire recordMetric() in server.ts (10 min)
6. TD-012 — Add service registry re-probe interval (2 min)
