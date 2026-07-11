# Empire OS — Services Map
**Updated:** 2026-07-04  
**Live System:** All services probed, status confirmed

---

## Service Topology

```
┌─────────────────────────────────────────────────────────────────┐
│                    JOSH'S MACHINE (localhost)                     │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │            EMPIRE OS SERVER  :3001                        │    │
│  │                                                           │    │
│  │  AI LAYER                    MODULE LAYER                 │    │
│  │  ──────────────────          ─────────────────────────    │    │
│  │  OllamaAdapter               empire-assistant             │    │
│  │  AnthropicAdapter            model-manager                │    │
│  │  GeminiAdapter               discovery                    │    │
│  │  OpenAIAdapter               health-monitor               │    │
│  │  GooseExecutor               media-engine                 │    │
│  │                              knowledge-base               │    │
│  │  CORE SERVICES               store / installer            │    │
│  │  ──────────────────          empire-dashboard             │    │
│  │  AIRouter                    discovery-engine             │    │
│  │  MemoryBus (.empire-data/)   benchmark-engine             │    │
│  │  EventBus (.empire-data/)    self-improvement             │    │
│  │  WorkflowEngine              video-factory                │    │
│  │  PluginRegistry              executive                    │    │
│  │  ModuleGateway               provider-registry (NEW)      │    │
│  │                              watchdog                     │    │
│  │  BLACKSMITH LAYER            logger                       │    │
│  │  ──────────────────          metrics-engine               │    │
│  │  EmpireLoggerModule          job-scheduler                │    │
│  │  MetricsEngineModule         service-registry             │    │
│  │  JobSchedulerModule          notification                 │    │
│  │  ServiceRegistryModule                                    │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌────────────────┐   ┌────────────────┐   ┌─────────────────┐   │
│  │  OLLAMA :11434 │   │  OPEN WEBUI    │   │  GOOSE AGENT    │   │
│  │                │   │  :42004        │   │  (CLI binary)   │   │
│  │  qwen2.5-coder │   │  (Pinokio-     │   │  ~/.local/bin/  │   │
│  │  :7b           │   │  managed)      │   │  goose.exe      │   │
│  └────────────────┘   └────────────────┘   └─────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                             │
                    CLOUD PROVIDERS
                    (key-gated)
            ┌────────┬────────┬────────┐
            │Anthropic│ Google │ OpenAI │
            │Claude   │ Gemini │ GPT    │
            └────────┴────────┴────────┘
```

---

## Service Registry

| Service | Port | URL | Status | Notes |
|---------|------|-----|--------|-------|
| Empire OS | 3001 | `http://localhost:3001` | ✅ LIVE | Main server |
| Ollama | 11434 | `http://localhost:11434` | ✅ LIVE | qwen2.5-coder:7b |
| Open WebUI | 42004 | `http://127.0.0.1:42004` | ✅ LIVE | Pinokio-managed |
| Anthropic Claude | — | api.anthropic.com | ✅ Key set | Via ANTHROPIC_API_KEY |
| Google Gemini | — | generativelanguage.googleapis.com | ✅ Key set | Via GOOGLE_API_KEY |
| OpenAI GPT | — | api.openai.com | Opt-in | Via OPENAI_API_KEY |
| Goose Agent | — | CLI binary | Opt-in | Auto-detected |

---

## Module Map

| moduleId | Path Prefix | Type | Data Persistence |
|----------|-------------|------|-----------------|
| `empire-assistant` | `/empire-assistant/` | AI orchestration | `.empire-data/` |
| `model-manager` | `/model-manager/` | UI + Ollama proxy | None |
| `discovery` | `/discovery/` | Model catalog | None |
| `health-monitor` | `/health-monitor/` | System monitor | None |
| `media-engine` | `/media-engine/` | Media routing | None |
| `knowledge-base` | `/knowledge-base/` | Memory store | `.empire-data/` |
| `store` | `/store/` | Software catalog | None |
| `installer` | `/installer/` | Install manager | In-memory jobs |
| `empire-dashboard` | `/empire-dashboard/` | Frontend SPA | None |
| `discovery-engine` | `/discovery-engine/` | Live discovery | `.empire-data/` |
| `benchmark-engine` | `/benchmark-engine/` | Benchmarks | `.empire-data/` |
| `self-improvement` | `/self-improvement/` | Recommendations | `.empire-data/` |
| `video-factory` | `/video-factory/` | Film production | `.empire-data/` |
| `executive` | `/executive/` | AI company OS | `.empire-data/` |
| `provider-registry` | `/provider-registry/` | Provider layer | None (cache only) |
| `watchdog` | `/watchdog/` | Health daemon | `.empire-data/watchdog-status.json` |
| `logger` | `/logger/` | Centralized logger | `.empire-data/logs/empire-YYYY-MM-DD.log` |
| `metrics-engine` | `/metrics-engine/` | API performance metrics | In-memory (rolling 1000 req/module) |
| `job-scheduler` | `/job-scheduler/` | Background job runner | In-memory |
| `service-registry` | `/service-registry/` | Service discovery + dependency graph | In-memory |
| `notification` | `/notification/` | Event-driven notification queue | In-memory (500 max) |

---

## AI Provider Routing

```
Request → AIRouter
         │
         ├─ strategy: "cost"       → Ollama (qwen2.5-coder:7b, free)
         ├─ strategy: "quality"    → Claude Sonnet (best quality)
         ├─ strategy: "speed"      → Gemini Flash (fast + cheap)
         ├─ strategy: "local-only" → Ollama only (no cloud)
         │
         └─ Task type routing:
              code        → Anthropic → Ollama → OpenAI
              research    → Gemini → Anthropic → Ollama
              script      → Gemini → Anthropic → Ollama
              copy        → Ollama → OpenAI → Anthropic
              summary     → Ollama → Anthropic → Gemini
              classification → Ollama → Anthropic → Gemini
```

---

## Data Flow: Video Production

```
Josh → POST /video-factory/projects
     → VideoFactoryModule creates project (stage: idea)
     → POST /video-factory/projects/:id/advance
     → AIRouter.complete() with script-department prompt
     → Ollama (cost) or Claude (quality) generates script
     → Script stored in CharacterEngine / TimelineEngine
     → Advance through 20 stages to final export
```

## Data Flow: Executive Briefing

```
Server startup → ExecutiveModule.init()
             → bootstrapInitialQueue() seeds 7 tasks
             → generateBriefing() creates daily brief
             → GET /executive/ → renderBriefingHTML()
             → GET /executive/workers → 10 worker status
             → POST /executive/workers/ceo/run → AIRouter.complete()
```

## Data Flow: AI Chat

```
POST /empire-assistant/agent/chat { message }
  → MemoryBus.read(scope=empire-assistant) for context
  → AIRouter.complete(messages+context, strategy=quality)
  → OllamaAdapter OR AnthropicAdapter (whichever wins routing)
  → MemoryBus.write(reply, scope=empire-assistant)
  → return { reply, model, provider, durationMs }
```

---

## File System Layout

```
C:\Users\jjard\claude\video-bot-pipeline\
├── empire-os-patch\              ← canonical Empire OS source
│   ├── apps\
│   │   ├── empire-os-server\     ← Node.js/tsx server
│   │   │   ├── server.ts         ← entry point
│   │   │   ├── adapters\         ← 4 AI provider adapters
│   │   │   ├── video-factory\    ← 5 module files
│   │   │   ├── executive\        ← 4 module files
│   │   │   ├── provider.registry.ts  ← NEW unified providers
│   │   │   ├── health-watchdog.ts    ← NEW 60s monitor
│   │   │   └── *.module.ts       ← 11 other modules
│   │   ├── empire-assistant\     ← Empire Assistant V2
│   │   └── crosspost-enterprise\ ← CrossPost (port 3000)
│   ├── packages\
│   │   └── core\                 ← shared interfaces + impls
│   └── .empire-data\             ← file-backed persistence
│
├── START_EMPIRE.bat              ← ONE COMMAND TO START ALL
├── EMPIRE_LIVE_DASHBOARD.html    ← local monitor page
├── API_DOCUMENTATION.md
├── SERVICES_MAP.md
├── HEALTH_REPORT.md
└── BACKEND_AUDIT.md
```

---

## Port Assignment

| Port | Service | Managed By |
|------|---------|-----------|
| 3001 | Empire OS | `npx tsx server.ts` |
| 3000 | CrossPost Enterprise | `npx tsx server.ts` (separate) |
| 11434 | Ollama | `ollama serve` |
| 42004 | Open WebUI | Pinokio |
| 8080 | Fallback WebUI port | — |
