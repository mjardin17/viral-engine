# REBUILD RECIPE — Empire OS
**Generated: 2026-07-04 | Complete blueprint for rebuilding from scratch using ONLY this repository**

This document is the blueprint for rebuilding Empire OS from zero, assuming the repo is the only thing that survived.

---

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Node.js | 20 LTS | TypeScript runtime |
| pnpm | 9.x | Package manager (Turborepo monorepo) |
| Python | 3.11+ | StoryForge engine |
| Git | any | Clone repos |
| Docker Desktop | any | PostgreSQL + Redis |
| uvicorn | via pip | StoryForge ASGI server |

Install pnpm if not present:
```bash
npm install -g pnpm
```

---

## Step 1: Clone the Empire OS Repository

```bash
git clone https://github.com/mjardin17/empire-os
cd empire-os
```

Read `AGENT_MEMORY.md` before touching anything else.

---

## Step 2: Clone the StoryForge Engine

The Python engine source lives in a separate repo. Clone it into the correct location:

```bash
cd apps/storyforge
git clone https://github.com/mjardin17/storyforge storyforge-engine
```

Verify the directory layout:
```
apps/storyforge/
├── storyforge-engine/     ← Python source (just cloned)
├── empire_hooks/          ← Python additions (already in empire-os)
├── empire-module/         ← TypeScript adapter (already in empire-os)
├── README.md
├── .env.example
└── STORYFORGE_INTEGRATION.md
```

---

## Step 3: Activate the Empire Hooks in StoryForge

Three additive lines in `storyforge-engine/main.py`. Find the line where `_automation_studio` is created (end of file, after Phase 5 AutomationStudio instantiation) and insert:

```python
from empire_hooks.router import empire_router, setup_event_bridge
app.include_router(empire_router)
setup_event_bridge(_automation_studio)
```

Also copy the `empire_hooks/` directory from `apps/storyforge/empire_hooks/` into `storyforge-engine/` so Python can import it:
```bash
cp -r apps/storyforge/empire_hooks/ apps/storyforge/storyforge-engine/empire_hooks/
```

---

## Step 4: Install Dependencies

### TypeScript (Empire OS Core + StoryForge Module)
```bash
cd empire-os
pnpm install
```

This installs all workspace dependencies defined in `pnpm-workspace.yaml` (when it exists — see Note below).

**Note:** `pnpm-workspace.yaml` and root `package.json` are not yet in the repo. They need to be created (see Missing Infrastructure below). For now, install core package manually:
```bash
cd packages/core
pnpm install
```

### Python (StoryForge Engine)
```bash
cd apps/storyforge/storyforge-engine
pip install -r requirements.txt
```

`requirements.txt` contains (from Phase 5):
```
fastapi
uvicorn
pydantic
sqlite-utils
httpx
anthropic
openai
```

---

## Step 5: Configure Environment Variables

### StoryForge Engine
```bash
cd apps/storyforge
cp .env.example .env
# Edit .env with your values
```

Required env vars (from `.env.example`):
```bash
# Empire OS integration
STORYFORGE_BASE_URL=http://localhost:8001
EMPIRE_OS_MEMORY_URL=http://localhost:8000/memory    # optional — activates memory sync
EMPIRE_OS_EVENT_URL=http://localhost:8000/events     # optional — activates event bridge

# AI providers (at least one required)
OPENROUTER_API_KEY=sk-or-...         # primary — OpenRouter for all LLM calls
ANTHROPIC_API_KEY=sk-ant-...         # optional — direct Anthropic
OLLAMA_BASE_URL=http://localhost:11434  # optional — local models

# Image generation (optional — enables Higgsfield cover art)
HIGGSFIELD_API_KEY=...
HIGGSFIELD_API_URL=https://...
OPENAI_API_KEY=sk-...                # optional — DALL-E fallback
COMFYUI_BASE_URL=http://localhost:8188  # optional — local image gen
```

### Empire OS Core
Empire OS core services use in-memory implementations for development. No env vars required to start. For production Redis/PostgreSQL:
```bash
DATABASE_URL=postgresql://...
REDIS_URL=redis://localhost:6379
```

---

## Step 6: Start Infrastructure (Development Mode)

### Option A: Docker (recommended)

Create `docker/docker-compose.yml` (not yet committed — create manually):
```yaml
version: '3.9'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: empire_os
      POSTGRES_USER: empire
      POSTGRES_PASSWORD: empire
    ports: ["5432:5432"]
  redis:
    image: redis:7
    ports: ["6379:6379"]
```

```bash
docker-compose -f docker/docker-compose.yml up -d
```

### Option B: In-memory (no Docker, development only)

The current implementations are all in-memory. Skip Docker entirely and proceed.

---

## Step 7: Start the StoryForge Engine

```bash
cd apps/storyforge/storyforge-engine
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

Verify it's running:
```
GET http://localhost:8001/empire/health
→ {"status":"healthy","moduleId":"storyforge","version":"5.0.0","phases":[1,2,3,4,5],...}
```

---

## Step 8: Bootstrap Empire OS Core (TypeScript)

The bootstrap entry point is `packages/core/src/bootstrap.ts`:

```typescript
import { bootstrap } from '@empire-os/core'
import { StoryForgeModule } from '@empire-os/storyforge-module'

const platform = await bootstrap({
  modules: [new StoryForgeModule()],
  config: {
    storyforge: { baseUrl: 'http://localhost:8001' }
  }
})
```

For now, no `apps/web/` or `apps/api/` exist. The core can be bootstrapped as a library and tested directly.

---

## Step 9: Verify the Integration

### Health check (StoryForge → Empire OS):
```bash
curl http://localhost:8001/empire/health
# Expected: {"status":"healthy","phases":[1,2,3,4,5]}
```

### Module descriptor:
```bash
curl http://localhost:8001/empire/status
# Expected: full ModuleDescriptor with 30+ capabilities
```

### Story science (Phase 1):
```bash
curl -X POST http://localhost:8001/science/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "A soldier discovers the battle was won by accident."}'
# Expected: readability + emotion + plotHoleFlags
```

### World engine (Phase 2):
```bash
curl -X POST http://localhost:8001/worlds \
  -H "Content-Type: application/json" \
  -d '{"project_id": "test-1", "name": "Ancient Rome"}'
```

### Automation studio (Phase 5):
```bash
curl http://localhost:8001/automation/events
```

---

## Step 10: Run Tests

### StoryForge Python tests:
```bash
cd apps/storyforge/storyforge-engine
pytest tests/ -v
```

Test files (from Phase 5 ZIP):
- `tests/test_image_studio_api.py`
- `tests/test_image_studio.py`
- `tests/test_publishing_studio.py`
- `tests/test_automation_studio.py`

### TypeScript type checks:
```bash
cd packages/core
npx tsc --noEmit
```

---

## Repository Structure (Current State)

```
empire-os/
│
├── packages/
│   └── core/                        # @empire-os/core
│       ├── src/
│       │   ├── interfaces/
│       │   │   ├── memory-bus.ts
│       │   │   ├── module-gateway.ts
│       │   │   ├── ai-router.ts
│       │   │   ├── event-bus.ts
│       │   │   ├── workflow-engine.ts
│       │   │   ├── plugin-registry.ts
│       │   │   ├── empire-module.ts
│       │   │   └── index.ts
│       │   ├── implementations/
│       │   │   ├── memory-bus.impl.ts      ← InMemoryMemoryBus
│       │   │   ├── module-gateway.impl.ts  ← HttpModuleGateway
│       │   │   ├── ai-router.impl.ts       ← DefaultAIRouter
│       │   │   ├── event-bus.impl.ts       ← InProcessEventBus
│       │   │   ├── workflow-engine.impl.ts ← InMemoryWorkflowEngine
│       │   │   ├── plugin-registry.impl.ts ← InMemoryPluginRegistry
│       │   │   └── index.ts
│       │   ├── bootstrap.ts
│       │   └── index.ts
│       ├── package.json
│       └── tsconfig.json
│
├── apps/
│   └── storyforge/                  # StoryForge integration
│       ├── storyforge-engine/       # ← CLONE FROM mjardin17/storyforge
│       │   ├── main.py              # FastAPI app (Phase 5, 54KB)
│       │   ├── requirements.txt
│       │   ├── core/
│       │   │   ├── ai/              # AIProvider, OpenRouter, Anthropic, Ollama
│       │   │   ├── science/         # StoryScienceLab (readability, emotion, pacing)
│       │   │   ├── book/            # EPUB 3 exporter
│       │   │   ├── world/           # WorldEngine, WorldMemorySync, continuity
│       │   │   ├── image/           # ImageStudio, Higgsfield/OpenAI/ComfyUI providers
│       │   │   ├── publishing/      # PublishingStudio, marketing
│       │   │   └── automation/      # AutomationStudio, campaigns, formats, workflows
│       │   ├── services/
│       │   │   └── character_lab.py
│       │   └── tests/
│       ├── empire_hooks/            # Python additions (Empire OS seams)
│       │   ├── __init__.py
│       │   ├── memory_sync.py       # EmpireMemorySync → Memory Bus
│       │   └── router.py            # /empire/* endpoints + event bridge
│       ├── empire-module/           # TypeScript EmpireModule adapter
│       │   ├── storyforge.module.ts # StoryForgeModule (Phase 5)
│       │   ├── higgsfield.plugin.ts # HIGGSFIELD_PLUGIN descriptor
│       │   ├── types.ts             # TypeScript mirrors of Python dataclasses
│       │   ├── index.ts
│       │   ├── package.json
│       │   ├── tsconfig.json
│       │   └── workflows/
│       │       └── story-pipeline.ts # 10-step story-to-render-to-publish workflow
│       ├── README.md
│       ├── .env.example
│       └── STORYFORGE_INTEGRATION.md
│
├── ARCHITECTURE.md                  # System design + event topics
├── AGENT_MEMORY.md                  # Claude's persistent context
├── INVENTORY.md                     # This audit
├── RECOVERY_GUIDE.md                # Recovery instructions
└── REBUILD_RECIPE.md                # This document
```

---

## Missing Infrastructure (Not Yet Created)

These are referenced in AGENT_MEMORY.md but do not exist in the repo yet:

| Missing | What it needs to be |
|---|---|
| `pnpm-workspace.yaml` | Lists packages: `['packages/*', 'apps/*/empire-module']` |
| Root `package.json` | `{"name":"empire-os","private":true,...}` with turbo scripts |
| `turbo.json` | Turborepo pipeline config |
| `apps/web/` | Next.js 14 dashboard UI (port 3000) |
| `apps/api/` | FastAPI data + agent API (port 8000) |
| `packages/database/` | Prisma schema (PostgreSQL 15) |
| `docker/docker-compose.yml` | postgres:15 + redis:7 |
| `.gitignore` root | Standard Node + Python ignores |
| `tsconfig.base.json` | Shared TypeScript base config |

---

## Build Order for Future Modules

When new modules are added, follow this order:

1. **Design** — Define `ModuleDescriptor` (id, capabilities, endpoints, baseUrl)
2. **Implement** — Build the service (Python/Go/Node — whatever fits)
3. **Register** — Create `<name>.module.ts extends BaseModule`
4. **Wire events** — Subscribe to relevant Event Bus topics in `onInit()`
5. **Register plugin** (if connector) — `pluginRegistry.register(descriptor)`
6. **Test health** — Module must return healthy from `GET /empire/health`
7. **Commit** — git add -A, commit with `[CLAUDE] feat: <module-name> module`

---

## Packaging Procedure

When all modules are complete and self-contained:

```bash
cd empire-os

# 1. Verify all modules are healthy
# 2. Run full test suite
pnpm test

# 3. Type check
pnpm typecheck

# 4. Create ZIP (exclude large binary files)
zip -r EmpireOS_Ultimate_v1.zip . \
  --exclude "*.mp4" \
  --exclude "*.wav" \
  --exclude "*.mp3" \
  --exclude "renders/*" \
  --exclude "output/*" \
  --exclude "node_modules/*" \
  --exclude ".git/*" \
  --exclude "__pycache__/*" \
  --exclude "*.pyc" \
  --exclude ".env"
```

**The ZIP must include:** source code, all docs (INVENTORY.md, RECOVERY_GUIDE.md, REBUILD_RECIPE.md, ARCHITECTURE.md, AGENT_MEMORY.md, CHANGELOG.md, README.md), tests, build scripts, installation scripts.

**The ZIP must exclude:** .env files, renders/, output/, *.mp4/*.wav/*.mp3, node_modules/, .git/.

---

## Startup Sequence (Full System)

```
1. docker-compose up -d                          # postgres:15, redis:7
2. cd apps/storyforge/storyforge-engine
   uvicorn main:app --port 8001                  # StoryForge engine
3. cd apps/api
   uvicorn main:app --port 8000                  # Empire OS API (not built yet)
4. cd apps/web
   pnpm dev                                      # Next.js dashboard (not built yet)
5. Empire OS bootstrap() via API startup          # Core services init
6. StoryForgeModule.init()                       # Registers with ModuleGateway
7. Higgsfield plugin registers with PluginRegistry
8. story-to-render workflow registers with WorkflowEngine
9. Empire OS polls GET /empire/health every 30s  # Health monitoring
```

---

## AI Routing Rules (from ARCHITECTURE.md)

| Task | Primary | Fallback |
|---|---|---|
| Code / Architecture | Claude (Anthropic) | DeepSeek → GPT |
| Research / Scripts | Gemini (Google) | Claude → GPT |
| Copy / Marketing | GPT (OpenAI) | Claude → Gemini |
| Summary | Claude | Gemini → GPT |
| Local / Offline | Ollama | None |

StoryForge council and listing copy → OpenRouter (honours above routing via model string).

---

## Current Build Status

**What builds today (2026-07-04):**
- ✅ `packages/core/` — TypeScript compiles cleanly (19 files)
- ✅ `apps/storyforge/empire_hooks/` — valid Python package
- ✅ `apps/storyforge/empire-module/` — valid TypeScript package
- ✅ StoryForge engine (from mjardin17/storyforge) — FastAPI runs on port 8001

**What does NOT build today (missing):**
- ❌ Root pnpm workspace (no workspace.yaml)
- ❌ apps/web — Next.js UI
- ❌ apps/api — FastAPI management API
- ❌ packages/database — Prisma schema
- ❌ Any module other than StoryForge
