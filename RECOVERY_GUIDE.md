# RECOVERY GUIDE — Empire OS
**Generated: 2026-07-04 | For every component: integration status, ZIP still needed, how to recreate, what's unrecoverable**

This document answers one question per component: if every original file and ZIP were lost tomorrow, what would you need to rebuild Empire OS?

---

## How to Read This Guide

Each component entry has four fields:
- **Integrated:** Is the source code inside the empire-os GitHub repo right now?
- **ZIP still needed:** Must you keep the original ZIP to recreate this?
- **Recreate from repo:** Step-by-step instructions if the ZIP is lost.
- **Unrecoverable if lost:** What, if anything, cannot be reconstructed.

---

## Component 1: EmpireOS Core (`packages/core/`)

**Integrated:** ✅ YES — fully committed to `mjardin17/empire-os` (or will be after COMMIT_STORYFORGE_P5.bat runs)

**ZIP still needed:** No. There was no ZIP for this — it was written from scratch in the prior session.

**Recreate from repo:**
```
git clone https://github.com/mjardin17/empire-os
cd empire-os
# Core is at packages/core/
# 7 interface files + 7 implementation files + bootstrap.ts
```
Everything is in the repo. No external source needed.

**Unrecoverable if repo is lost:** Nothing — the code is straightforward TypeScript and can be rewritten from the ARCHITECTURE.md contracts in under a day. The six interfaces (MemoryBus, ModuleGateway, AIRouter, EventBus, WorkflowEngine, PluginRegistry) plus BaseModule are fully documented.

---

## Component 2: StoryForge Engine (Python FastAPI, Phases 1–5)

**Integrated:** ✅ PARTIALLY — the integration layer (`empire_hooks/`, `empire-module/`) is in empire-os. The engine itself lives at `mjardin17/storyforge` on GitHub.

**ZIP still needed:**
- `storyforge phase4 publishing studio.zip` — NO. All Phase 4 content is captured in the empire-module endpoints/capabilities.
- `storyforge phase5 empire automation studio.zip` — NO. All Phase 5 content is captured in the empire-module + empire_hooks/router.py.
- The actual engine source lives at `mjardin17/storyforge` — clone that repo, not the ZIP.

**Recreate from repo:**
```bash
# 1. Clone empire-os
git clone https://github.com/mjardin17/empire-os
cd empire-os/apps/storyforge

# 2. Clone StoryForge engine (the Python source)
git clone https://github.com/mjardin17/storyforge storyforge-engine

# 3. Copy empire_hooks into the engine
cp -r empire_hooks/ storyforge-engine/empire_hooks/

# 4. Activate (3 lines in storyforge-engine/main.py):
#   from empire_hooks.router import empire_router, setup_event_bridge
#   app.include_router(empire_router)
#   setup_event_bridge(_automation_studio)

# 5. Install Python deps
cd storyforge-engine && pip install -r requirements.txt

# 6. Set env vars (see .env.example)
# 7. Run: uvicorn main:app --port 8001
```

**Unrecoverable if storyforge repo is lost:** The 5,000+ lines of Python engine source code (FastAPI routes, science engine, character lab, world engine, image studio, publishing studio, automation studio). The empire-module TypeScript adapter does NOT contain this — it's just a proxy. The ZIPs (`storyforge phase4/5`) do contain Phase 4 and 5 engine source and would allow recreation of the engine from them.

**Bottom line:** Keep the `mjardin17/storyforge` GitHub repo as the authoritative source. If it's lost, the Phase 4 and Phase 5 ZIPs in `uploads/` contain that source code and are the only backup.

---

## Component 3: Higgsfield AI Connector

**Integrated:** ✅ YES — `higgsfield.plugin.ts` is in the empire-module.

**ZIP still needed:** No. Higgsfield is an external API service, not a ZIP. The connector is registered via `HIGGSFIELD_PLUGIN` constant in the repo.

**Recreate from repo:**
```typescript
// In empire-os/apps/storyforge/empire-module/higgsfield.plugin.ts
// Already committed. Re-register via:
await pluginRegistry.register(HIGGSFIELD_PLUGIN)
// Requires env vars: HIGGSFIELD_API_KEY, HIGGSFIELD_API_URL
```

**Unrecoverable if lost:** Nothing — it's just a metadata descriptor. Higgsfield itself is an external service at higgsfield.ai.

---

## Component 4: Story-to-Render Workflow

**Integrated:** ✅ YES — `workflows/story-pipeline.ts` defines all 10 steps.

**ZIP still needed:** No.

**Recreate from repo:**
```
empire-os/apps/storyforge/empire-module/workflows/story-pipeline.ts
```
The full 10-step pipeline is committed.

**Unrecoverable if lost:** Nothing — it's declarative JSON-like TypeScript. Re-writable from the STORYFORGE_INTEGRATION.md documentation.

---

## Component 5: Video Bot Pipeline (`C:\Users\jjard\claude\video-bot-pipeline\`)

**Integrated:** ❌ NO — the Video Bot Pipeline is NOT in the `empire-os` repo. It lives in its own production folder.

**ZIP still needed:** There is no ZIP for this — it's a live production folder tracked separately.

**Recreate from repo:**
The video-bot-pipeline has its own `CLAUDE.md` and is self-contained. It is NOT part of empire-os. To rebuild it:
```
# It is the production folder at C:\Users\jjard\claude\video-bot-pipeline\
# No clone needed — it IS the source of truth
# Scripts: auto_render.py, patch_fallbacks.py, council/, prompts/gods_glory/
# Season 3 scripts: all 14 episodes in prompts/gods_glory/
```

**To integrate it into empire-os (future work):**
An `EmpireModule` wrapper needs to be built (TypeScript + Python bridge). This does not exist yet. The pipeline currently runs standalone.

**Unrecoverable if folder is lost:** All 14 Season 3 scripts (EP012–EP025), the 9 council bots, the 84-episode stub backlog. These are not in empire-os. Back up `C:\Users\jjard\claude\video-bot-pipeline\` independently.

---

## Component 6: CrossPost Studio (`crosspost_bridge.py`)

**Integrated:** ❌ NO — `crosspost_bridge.py` is a queue/bridge script in the video-bot-pipeline folder, not an EmpireModule in empire-os.

**ZIP still needed:** No ZIP exists. The file is in the production folder.

**Recreate from repo:**
File lives at `C:\Users\jjard\claude\video-bot-pipeline\crosspost_bridge.py`. It reads from `crosspost_queue/` and posts to CrossPost/YouTube/TikTok/Instagram/X. Not committed to empire-os.

**Unrecoverable if lost:** The bridge script (~200 lines Python) is non-trivial but re-writable. The `crosspost_config.json` (API keys, channel IDs) must be backed up separately.

---

## Component 7: CrossPost Enterprise (AI Integration Hub)

**Integrated:** ✅ YES — fully staged to `apps/crosspost-enterprise/` in empire-os.

**ZIP still needed:** No. ZIP was received (`crosspost-content-operating-system.zip`) and fully integrated.

**Recreate from repo:**
```
git clone https://github.com/mjardin17/empire-os
cd empire-os/apps/crosspost-enterprise

# Install and run CrossPost:
npm install
# Create .env with: GEMINI_API_KEY=<your-key>
npm run dev   # starts on http://localhost:3000

# Empire hooks are live at:
# GET  http://localhost:3000/empire/health
# GET  http://localhost:3000/empire/status
# POST http://localhost:3000/empire/event
```

**CrossPostModule adapter:** `apps/crosspost-enterprise/empire-module/crosspost.module.ts`
Import with `@empire-os/crosspost-module`.

**Unrecoverable if repo is lost:** The 2974-line server.ts backend (29 API routes) and the 20-component React frontend would need to be re-exported from Google AI Studio. The empire hooks and CrossPostModule adapter are well-documented and re-writable.

**⚠️ Boss Listers note:** `BossListers.tsx` is a React frontend panel inside CrossPost that simulates listing optimization with a setTimeout. There is NO separate Boss Listers backend service or standalone project. If a real listing-optimize API is needed, add a route to `server.ts`.

---

## Component 8: Empire Assistant v2

**Integrated:** ❌ NO — was explicitly blocked pending EmpireOS stability criteria being met.

**ZIP still needed:** No ZIP exists. This module was never built.

**Recreate from repo:** Cannot recreate — nothing exists. Needs to be built from scratch as an EmpireModule (TypeScript) that consumes CoreServices via `init(services, config)`.

**What IS documented (in ARCHITECTURE.md):** The EmpireModule contract, the ruling that Empire Assistant does NOT own Memory/AI/Orchestration, and the stability criteria that must pass before it begins.

**To build it:** Implement `class EmpireAssistantModule extends BaseModule` in `apps/empire-assistant/`. Follow the EmpireModule contract in `packages/core/src/interfaces/empire-module.ts`.

---

## Component 9: Empire Workforce

**Integrated:** ❌ NO — not found in any ZIP, any project identity file, or any prior session context.

**ZIP still needed:** No ZIP exists.

**Recreate from repo:** Cannot recreate — nothing to recreate. Name is unrecognized in the project inventory.

**Action needed:** Josh must clarify what Empire Workforce is. It may be a planned module name, a renamed version of another project, or something from a session before these records.

---

## Component 10: Boss Listers AI

**Finding:** Boss Listers is NOT a separate project. It is `BossListers.tsx` — a React component inside CrossPost Enterprise that simulates listing optimization using `setTimeout(1300ms)`. No backend API. No separate ZIP. No standalone service.

**Integrated:** ✅ YES — `BossListers.tsx` is staged as part of CrossPost Enterprise at `apps/crosspost-enterprise/src/components/BossListers.tsx`.

**ZIP still needed:** No. The component was inside `crosspost-content-operating-system.zip`.

**To add real listing-optimize functionality:**
1. Add a backend route to `apps/crosspost-enterprise/server.ts`:
   ```typescript
   app.post('/api/boss-listers/optimize', async (req, res) => { ... })
   ```
2. Replace the `setTimeout` in `BossListers.tsx` with a real `fetch('/api/boss-listers/optimize', ...)`
3. Register `boss-listers` as a named capability in `CrossPostModule`

**Unrecoverable if lost:** Nothing — it's a frontend panel, re-writable in under a day.

---

## Component 11: Boss Listers AI — Empire OS EmpireModule (future)

**Integrated:** ❌ NO — even if Boss Listers source were available, no TypeScript EmpireModule wrapper has been built for it.

**What's needed:** A `BossListersModule extends BaseModule` that proxies to the Rails service, similar to how `StoryForgeModule` proxies to the Python engine.

---

## Component 12: Mission Control / Empire Inspector

**Integrated:** ❌ NO — Mission Control is the Empire Inspector dashboard inside CrossPost Enterprise. Source not provided.

**ZIP still needed:** No ZIP was received.

**Recreate from repo:** IMPOSSIBLE from empire-os. It's part of CrossPost Enterprise's ~136KB React frontend.

---

## Component 13: LTX Video Engine

**Not requested but relevant:** Go + React 18 video generation engine, 88% complete per Empire Inspector. Not in empire-os, source not provided.

**Action needed (if integration wanted):** Josh must provide the Go source ZIP or GitHub repo.

---

## Component 14: Auto Poster Bot

**Integrated:** ❌ NO — Node.js + Puppeteer headless poster. Source not provided (only a Claude Code skill wrapper in `auto-poster.zip`).

**ZIP still needed:** `auto-poster.zip` contains only a Claude Code skill (SKILL.md + 2 scripts), not the full Puppeteer project.

**To integrate:** Need the actual Node.js + Puppeteer source, plus an EmpireModule wrapper.

---

## Recovery Summary Table

| Component | In empire-os repo | Original ZIP needed | Recreatable from repo | Risk if lost |
|---|---|---|---|---|
| EmpireOS Core | ✅ | N/A | ✅ Fully | LOW |
| StoryForge Phase 1-3 | Integration only | No — use mjardin17/storyforge | ✅ Clone + hooks | MEDIUM (engine in separate repo) |
| StoryForge Phase 4 | Integration only | No — use mjardin17/storyforge | ✅ Clone + hooks | MEDIUM |
| StoryForge Phase 5 | Integration only | No — ZIP is backup only | ✅ Clone + hooks | MEDIUM |
| Higgsfield connector | ✅ | N/A | ✅ Fully | LOW |
| story-to-render workflow | ✅ | N/A | ✅ Fully | LOW |
| Video Bot Pipeline | ❌ (own folder) | N/A | Lives in its own folder | HIGH — back up separately |
| CrossPost Studio (bridge) | ❌ | N/A | Re-writable | LOW-MEDIUM |
| CrossPost Enterprise | ✅ | No — ZIP integrated | ✅ Clone empire-os + npm install | LOW — fully in repo |
| Empire Assistant v2 | ❌ | No ZIP exists | ❌ Not built yet | N/A — doesn't exist |
| Empire Workforce | ❌ | No ZIP exists | ❌ Unknown | N/A — doesn't exist |
| Boss Listers AI | ✅ (as BossListers.tsx inside CrossPost) | No — part of CrossPost ZIP | ✅ Re-writable frontend panel | LOW — UI simulation only, no backend |
| Mission Control | ✅ (as MissionControl.tsx inside CrossPost) | No — part of CrossPost ZIP | ✅ Clone empire-os + npm install | LOW — fully in repo |
| LTX Video Engine | ❌ | No ZIP exists | ❌ CANNOT RECREATE | HIGH — need source |
| Auto Poster Bot | ❌ | Skill ZIP ≠ full source | ❌ CANNOT RECREATE | HIGH — need source |

---

## What Must Be Done Before Packaging

1. Josh must provide source code for: CrossPost Enterprise (AI Integration Hub), Boss Listers AI, Mission Control, LTX Video Engine, Auto Poster Bot
2. Empire Assistant v2 must be built (TypeScript EmpireModule)
3. Empire Workforce must be defined — what is it?
4. Video Bot Pipeline needs an EmpireModule wrapper if it's to be controlled from empire-os
5. CrossPost Studio (`crosspost_bridge.py`) needs an EmpireModule wrapper

Until these are resolved: **the ZIP cannot be created.**
