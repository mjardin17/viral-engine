# Empire OS — Health Report
**Generated:** 2026-07-04T18:54:52Z  
**Source:** Live probe via Chrome MCP + code audit

---

## Overall Status: 🟢 OPERATIONAL

| Component | Status | Details |
|-----------|--------|---------|
| Empire OS Server | ✅ ONLINE | :3001 responding |
| Ollama | ✅ ONLINE | qwen2.5-coder:7b loaded |
| Open WebUI | ✅ ONLINE | :42004 (Pinokio) |
| Anthropic Claude | ✅ ACTIVE | 3 models registered |
| Google Gemini | ✅ ACTIVE | 2 models registered |
| OpenAI | ⚪ OPTIONAL | Set OPENAI_API_KEY to enable |
| Goose Agent | ⚪ OPTIONAL | Install from github.com/block/goose |

---

## Module Health (from `GET /health` — live)

| Module | Status | Key Metrics |
|--------|--------|-------------|
| empire-assistant | ✅ healthy | 6 models, memory boot OK |
| model-manager | ✅ healthy | uptime: 417s |
| discovery | ✅ healthy | uptime: 417s |
| health-monitor | ✅ healthy | uptime: 418s |
| media-engine | ✅ healthy | uptime: 418s |
| knowledge-base | ✅ healthy | uptime: 418s |
| store | ✅ healthy | uptime: 418s |
| installer | ✅ healthy | uptime: 418s |
| empire-dashboard | ✅ healthy | uptime: 418s |
| discovery-engine | ✅ healthy | 15 entries, last scan: startup |
| benchmark-engine | ✅ healthy | 0 runs, not running |
| self-improvement | ✅ healthy | 1 pending recommendation |
| video-factory | ✅ healthy | 19 depts, 20 stages, 2 providers |
| executive | ✅ healthy | 10 workers, 7 tasks, 0 failed |
| provider-registry | ✅ healthy | Unified provider layer (stream/vision/embeddings) |
| watchdog | ✅ healthy | 60s polling + auto-restart + hourly backups |
| logger | ✅ healthy | BLACKSMITH — 5000-entry ring buffer + daily log files |
| metrics-engine | ✅ healthy | BLACKSMITH — P50/P95/P99 per module (1000-req window) |
| job-scheduler | ✅ healthy | BLACKSMITH — 4 built-in jobs (backup/discovery/self-check/log-rotate) |
| service-registry | ✅ healthy | BLACKSMITH — 26 services registered, dependency graph |
| notification | ✅ healthy | BLACKSMITH — event queue active, 500-max capacity |

**Total modules: 21 (added 5 Operation Blacksmith modules)**

---

## AI Models Available

| Model | Provider | Cost | Use Case |
|-------|----------|------|----------|
| qwen2.5-coder:7b | Ollama (local) | Free | Code, routine tasks |
| claude-opus-4-8 | Anthropic | $$$ | Complex reasoning |
| claude-sonnet-4-6 | Anthropic | $$ | Code, architecture |
| claude-haiku-4-5-20251001 | Anthropic | $ | Fast tasks |
| gemini-1.5-pro | Google | $$ | Research, long context |
| gemini-1.5-flash | Google | ¢ | Fast research |

---

## Watchdog Monitor (60-second intervals)

Services checked by Health Watchdog:
- Empire OS Server → `http://localhost:3001/health`
- Ollama → `http://localhost:11434/api/tags`
- Open WebUI → `http://127.0.0.1:42004/`
- Empire Assistant → `http://localhost:3001/empire-assistant/health`
- Health Monitor → `http://localhost:3001/health-monitor/health`
- Knowledge Base → `http://localhost:3001/knowledge-base/health`
- Video Factory → `http://localhost:3001/video-factory/health`
- Executive → `http://localhost:3001/executive/health`
- Discovery Engine → `http://localhost:3001/discovery-engine/health`
- Media Engine → `http://localhost:3001/media-engine/health`

**Live status:** `GET http://localhost:3001/watchdog/status`  
**Persisted to:** `.empire-data/watchdog-status.json`

---

## Fixes Applied This Session

| Fix | Impact |
|-----|--------|
| `LAUNCH_EMPIRE.bat` path corrected | Server now actually launches |
| `START_EMPIRE_OS.bat` path corrected | Backup launcher works |
| `START_EMPIRE.bat` created | Single-click launcher + auto-open browser |
| `executive.module.ts` `/status` route added | Dashboard no longer gets 404 |
| `executive.module.ts` error responses include `timestamp` | Consistent error format |
| `provider.registry.ts` added | Unified AI provider HTTP layer |
| `health-watchdog.ts` added | Background 60s monitoring daemon |
| `EMPIRE_LIVE_DASHBOARD.html` Open WebUI port updated to 42004 | Correct Pinokio port |
| `ollama_bridge.py` default model patched to `qwen2.5-coder:7b` | Correct installed model |

---

## Operation Blacksmith Endpoints

```
GET http://localhost:3001/logger/recent          ← last 100 log entries
GET http://localhost:3001/metrics-engine/summary ← P50/P95/P99 per module
GET http://localhost:3001/job-scheduler/jobs     ← scheduled job status
GET http://localhost:3001/service-registry/health-matrix ← all 26 services
GET http://localhost:3001/notification/unread    ← unread alerts
```

---

## Known Gaps (Non-Critical)

| Gap | Impact | Priority |
|-----|--------|----------|
| Open WebUI not authenticated in Watchdog | 302 redirect may show as "degraded" | LOW |
| `knowledge-base` try/catch gaps | 2 routes unprotected from exceptions | LOW |
| Goose not installed | POST /goose/run returns 503 | INFO |
| Logger `qp()` helper reads from `x-qp-*` headers | Query params in GET /logger/search need X-Qp headers or server-side routing update | LOW |

---

## To Restart Empire OS

```bat
C:\Users\jjard\claude\video-bot-pipeline\START_EMPIRE.bat
```

This kills port 3001, starts the server, and opens the dashboard automatically.

## To Check Health

```
http://localhost:3001/health
http://localhost:3001/watchdog/status
```
