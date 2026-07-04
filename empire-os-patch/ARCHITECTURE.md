# Empire OS — Architecture

**Status: CORE FROZEN. StoryForge integrated as first native module. CrossPost Enterprise INTEGRATED. Boss Listers mapped as external module — pending source export.**

---

## The Rule

> Empire Assistant is an Empire OS **module**.
> It **consumes** core services. It does **not** own them.
> Core services are implemented once, injected everywhere.

---

## Six Core Services (packages/core/)

All interfaces are in `packages/core/src/interfaces/`. They are frozen.
All implementations are in `packages/core/src/implementations/`.

| Service | Interface | Implementation | Purpose |
|---------|-----------|---------------|---------|
| **Memory Bus** | `MemoryBus` | `InMemoryMemoryBus` | Shared persistent context. No module owns this. |
| **Module Gateway** | `ModuleGateway` | `HttpModuleGateway` | Routes requests between modules. Modules never call each other directly. |
| **AI Router** | `AIRouter` | `DefaultAIRouter` | Selects and calls the right AI model. No module holds API clients. |
| **Event Bus** | `EventBus` | `InProcessEventBus` | Pub/sub backbone. All cross-module comms happen here. |
| **Workflow Engine** | `WorkflowEngine` | `InMemoryWorkflowEngine` | Orchestrates multi-step pipelines (render, upload, script). |
| **Plugin Registry** | `PluginRegistry` | `InMemoryPluginRegistry` | Source of truth for what exists in the system. |

---

## Module Contract

Every module (including Empire Assistant) implements `EmpireModule`:

```typescript
interface EmpireModule {
  readonly moduleId: string
  init(services: CoreServices, config: ModuleConfig): Promise<void>
  handleRequest(request: GatewayRequest): Promise<GatewayResponse>
  handleEvent(event: DomainEvent): Promise<void>
  health(): Promise<HealthReport>
  shutdown(): Promise<void>
}
```

`CoreServices` is injected by the platform. Modules never instantiate core services.

---

## Registered Modules

### StoryForge Engine (`storyforge`) — ACTIVE
- **Location:** `apps/storyforge/`
- **Language:** Python (FastAPI, port 8001) + TypeScript adapter
- **Type:** HTTP-backed EmpireModule
- **Capabilities:** story-science, character-memory, world-engine, image-generate, publishing-studio, book-export, council-review, automation-studio, campaigns, format-packages, analytics, scheduler
- **Phases:** 1–5 complete
- **Integration seams:** `WorldMemorySync` → Empire Memory Bus; Phase 5 EventBus → Empire Event Bus; `ImageProvider.higgsfield` → Higgsfield connector
- **Source:** `mjardin17/storyforge` (GitHub)

---

## External Connected Modules

These modules **exist** as real projects built in Google AI Studio. They are not missing — they are external services waiting for their source export to be integrated as EmpireModules, following the same adapter pattern as StoryForge.

### CrossPost Enterprise (`crosspost-enterprise`) — ✅ INTEGRATED
- **Source:** Google AI Studio export (`crosspost-content-operating-system.zip`)
- **Language:** Node.js/TypeScript (Express v4 backend + React 19 frontend)
- **Location:** `apps/crosspost-enterprise/`
- **Port (local):** 3000
- **Backend:** `server.ts` — 3084 lines, 29 API routes + empire hooks
- **Frontend:** React 19, Vite, Tailwind CSS v4 — 20 components (MissionControl, EmpireInspector, BossListers, OllamaCommandCenter, AIRouter, StoryForge, VideoCreator, and more)
- **EmpireModule:** `empire-module/crosspost.module.ts` — `CrossPostModule extends BaseModule`
- **Capabilities registered:** content-generate, platform-publish, ai-route, empire-inspect, ollama-manage, video-pipeline, mission-control, boss-listers, analytics, github-audit, cron-manage
- **Empire hooks added to server.ts:** `GET /empire/health`, `GET /empire/status`, `POST /empire/event`
- **Event subscriptions:** `render.completed`, `script.created`, `system.alert`
- **⚠️ Boss Listers note:** `BossListers.tsx` is a UI panel (setTimeout simulation) — no dedicated backend route. A real listing-optimize API can be added to server.ts when needed.
- **Single env var required:** `GEMINI_API_KEY` (Josh adds to .env, never committed)

### Boss Listers AI (`boss-listers`) — EXTERNAL / PENDING SOURCE
- **Built in:** Google AI Studio
- **Language:** TBD (PROJECT_IDENTITY says Ruby on Rails v6, but AI Studio export will confirm actual stack)
- **Port (local):** TBD
- **Completion:** 54% per Empire Inspector
- **Role in Empire OS:** Listing optimizer / conversion copywriter — generates premium headlines, bullet structures, SEO meta tags, pricing models for products/services
- **Planned location:** `apps/boss-listers/`
- **EmpireModule to build:** `BossListersModule extends BaseModule` (TypeScript)
- **Key capabilities to register:** listing-optimize, headline-generate, seo-meta, pricing-model, conversion-funnel
- **Event hooks:** publishes `agent.action` when listing copy is ready; receives `script.created` to auto-generate YouTube descriptions
- **NEEDED TO INTEGRATE:** See "Google AI Studio Export Instructions" below

---

## Google AI Studio Export Instructions

For each project (CrossPost Enterprise, Boss Listers), export as follows:

**In Google AI Studio:**
1. Open the project
2. Click the **download / export icon** (top-right toolbar, looks like `⬇` or `< >`)
3. Select **"Download code"** or **"Export project"**
4. This produces a `.zip` file containing all source files (no `node_modules`, no `.env`)
5. Send that ZIP here

**What the ZIP must contain (for CrossPost Enterprise):**
- `server.ts` (Express backend, ~90KB — all API routes)
- `src/App.tsx` (React frontend, ~136KB — all UI sections)
- `src/types.ts`
- `src/components/` (MathEngine.tsx, SystemArchitecture.tsx, etc.)
- `package.json`
- `tsconfig.json`
- Any `.env.example` or config files
- Do NOT include: `.env`, `node_modules/`, `dist/`

**What the ZIP must contain (for Boss Listers):**
- All server/backend files (controllers, models, routes)
- All frontend files (if any UI exists)
- `package.json` / `Gemfile` / `requirements.txt` (whichever applies)
- Any schema or migration files
- Do NOT include: `node_modules/`, vendor/, `.env`

**Once received:**
1. Extract to `apps/crosspost-enterprise/` or `apps/boss-listers/`
2. Build a TypeScript `EmpireModule` adapter (same pattern as `StoryForgeModule`)
3. Add empire hooks (`/empire/health`, `/empire/status`, `/empire/event`)
4. Register with Module Gateway
5. Wire Event Bus subscriptions

---

## Registered Modules (Full Map)

| Module | ID | Status | Location | Port |
|--------|-----|--------|----------|------|
| StoryForge Engine | `storyforge` | ✅ ACTIVE | `apps/storyforge/` | 8001 |
| CrossPost Enterprise | `crosspost-enterprise` | ✅ ACTIVE — source integrated, empire hooks + module built | `apps/crosspost-enterprise/` | 3000 |
| Boss Listers AI | `boss-listers` | ⏳ EXTERNAL — awaiting source ZIP | `apps/boss-listers/` (planned) | TBD |
| Empire Assistant | `empire-assistant` | 🔲 NOT BUILT — blocked on stability criteria | `apps/empire-assistant/` (planned) | TBD |
| Video Bot Pipeline | `video-pipeline` | ✅ ACTIVE — empire_server.py (port 8002) + VideoPipelineModule built | `apps/video-pipeline/` | 8002 |

### Empire Assistant — PENDING (after stability criteria met)

---

## Registered Connectors (PluginRegistry)

### Higgsfield AI (`higgsfield`)
- **Type:** connector
- **Capabilities:** video-generate, image-generate, audio-generate, voice-clone, motion-control, shorts-studio, upscale-video, upscale-image, remove-background, reframe, dubbing
- **MCP Server:** `mcp__16d46007-5a59-4d9d-8cc0-7748abeda183`
- **Workspace:** f4897b98 (Plus plan)
- **Routing rule:** ALWAYS used for dialogue/lip-sync and character identity lock across episodes
- **Activation:** Set `HIGGSFIELD_API_KEY` + `HIGGSFIELD_API_URL` in StoryForge .env

---

## Registered Workflows (WorkflowEngine)

### story-to-render
```
premise → [science-analyze] → [create-characters] → [build-world]
       → [council-review] → [generate-cover (Higgsfield)] → [export-epub]
       → [human-approval: approve-publish]
```

---

## AI Routing Rules

| Task Type | Primary | Fallback Order |
|-----------|---------|---------------|
| Code / Architecture | Claude (Anthropic) | DeepSeek → GPT |
| Research / Scripts | Gemini (Google) | Claude → GPT |
| Copy / Marketing | GPT (OpenAI) | Claude → Gemini |
| Summary | Claude | Gemini → GPT |
| Local / Offline | Ollama | None |

StoryForge AI calls (council, listing copy) go through OpenRouter by default,
which honours the same routing table above via model string selection.

---

## Event Topics (well-known, stable)

```
render.queued / render.started / render.completed / render.failed
script.created / episode.uploaded
agent.action / agent.error
workflow.started / workflow.step.completed / workflow.completed / workflow.failed
module.registered / module.health.changed
system.alert
world.write                          ← StoryForge World Engine writes
```

Adding a new topic requires updating `TOPICS` in `event-bus.ts` AND this document.

---

## Startup Sequence

```
1. bootstrap() — instantiates all 6 core services
2. pluginRegistry.register() — core platform registers itself
3. eventBus.publish('system.platform.ready')
4. Each module: module.init(services, config)
5. Each module: moduleGateway.register(descriptor)
6. Each module: pluginRegistry.register(descriptor)
7. Traffic begins
```

StoryForge startup (separate process):
```
1. uvicorn main:app --port 8001
2. Empire hooks activate if EMPIRE_OS_MEMORY_URL is set
3. Module Gateway polls /empire/health every 30s
```

---

## Stability Criteria (before Empire Assistant begins)

The core is **stable** when ALL of the following are true:

- [ ] All 6 interface files compile with zero TypeScript errors
- [ ] All 6 implementations pass unit tests (happy path + error path)
- [ ] `bootstrap()` runs end-to-end without errors
- [ ] A test module successfully calls all 6 services via `CoreServices`
- [ ] WorkflowEngine runs a 3-step workflow end-to-end
- [ ] EventBus delivers events across a publish → subscribe cycle
- [ ] MemoryBus read/write/search/subscribe cycle passes
- [ ] AIRouter routes, falls back, and returns stats correctly
- [ ] ModuleGateway routes to a real HTTP endpoint (mock or real module)
- [ ] PluginRegistry validates dependencies correctly

**Empire Assistant does not start until every box above is checked.**

---

## What Empire Assistant Is (future)

Empire Assistant is a **module** that:
- Registers itself in `PluginRegistry` with capability `["chat", "task-planning"]`
- Receives requests via `ModuleGateway` (users talk to it through the gateway)
- Reads/writes memory via `MemoryBus` (conversation context, user prefs)
- Calls AI via `AIRouter` (never holds its own API client)
- Triggers pipelines via `WorkflowEngine` ("render episode 12")
- Subscribes to events via `EventBus` (knows when renders complete)

It does **not** own any of those services.

---

## Production Swap Plan

Current implementations are in-memory (dev-ready). Production swaps:

| Current | Production Replacement |
|---------|----------------------|
| `InMemoryMemoryBus` | Redis (hot) + PostgreSQL MemoryEntry table (cold) |
| `InProcessEventBus` | Redis pub/sub + PostgreSQL EventLog table |
| `InMemoryPluginRegistry` | PostgreSQL PluginDescriptor table |
| `InMemoryWorkflowEngine` | PostgreSQL WorkflowInstance table + BullMQ queue |
| `HttpModuleGateway` | Same impl — already HTTP-based |
| `DefaultAIRouter` | Same impl — add real provider adapters with API keys |

Swap one at a time. Interfaces don't change.
