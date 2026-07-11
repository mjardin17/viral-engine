# StoryForge Audit Report

**Date:** 2026-07-10
**Auditor:** Claude (subagent audit task)
**Scope:** Entire `video-bot-pipeline` repo — every file matching storyforge / story_forge / StoryForge

---

## Bottom Line

**StoryForge is NOT runnable right now.** The repo contains the *integration layer* for StoryForge (Empire OS adapter, hooks, workflow, docs, a mock UI) — but the actual Python FastAPI engine (`storyforge-engine/`) is **not in this repo**. The repo's own audit docs confirm this: the engine is documented as living at `github.com/mjardin17/storyforge` (external). [Guessing] whether that GitHub repo actually exists — it could not be verified from the sandbox (no network to GitHub; a fetch returned empty, which is what a private or nonexistent repo looks like).

---

## 1. What Was Found (complete inventory)

| Path | What it is | Status |
|------|-----------|--------|
| `empire-os-patch/apps/storyforge/README.md` | Integration + startup guide | Docs only |
| `empire-os-patch/apps/storyforge/STORYFORGE_INTEGRATION.md` | Full Phase 2A integration plan (2026-07-04) | Docs only |
| `empire-os-patch/apps/storyforge/.env.example` | Env template (AI + image provider keys) | Template only |
| `empire-os-patch/apps/storyforge/empire_hooks/` (`router.py`, `memory_sync.py`, `__init__.py`) | Python add-ons meant to be dropped INTO the engine (`/empire/health`, `/empire/status`, event bridge) | Built, but useless without the engine |
| `empire-os-patch/apps/storyforge/empire-module/` (`storyforge.module.ts`, `higgsfield.plugin.ts`, `types.ts`, `index.ts`, `workflows/story-pipeline.ts`) | TypeScript Empire OS adapter — proxies HTTP to `localhost:8001` | Built, but polls a server that isn't there |
| `empire-os-patch/apps/crosspost-enterprise/src/components/StoryForge.tsx` | React UI panel — **MOCK**: "generation" is a `setTimeout` returning hardcoded fake data | Fake/demo |
| `adapters/lo_adapters/storyforge.py` | `StoryForgeAdapter` v0.0.1-stub for `lo_studio_server.py` — all methods `raise NotImplementedError` | Stub |
| `EMPIRE_WORKSPACE/StoryForge/README.md` | 40-byte file: just the title line | Empty shell |
| `memory/projects/PROJECT_IDENTITY.storyforge_engine.md` | Project identity doc (Empire Inspector score 94%) — explicitly says "(Not locally accessible — lives in separate project)" | Docs only |
| `empire_server.py` | Video pipeline bridge (port 8002) — auto-queues a render when a `script.created` event arrives (i.e., when StoryForge creates a script) | Real, but waits on StoryForge events |
| `scripts/batch/COMMIT_STORYFORGE.bat`, `COMMIT_STORYFORGE_P5.bat` | Copy the adapter files into `C:\Users\jjard\empire-os` and commit | Deploy scripts for the adapter only |
| `empire-os-patch/MISSING_COMPONENTS.md` | Flags: "StoryForge Python Backend Not in Monorepo" (LOW) — recommends submodule or `START_STORYFORGE.bat` | Confirms the gap |
| `empire-os-patch/AUDIT_REPORT.md` | "Module adapter present — Python backend is external" | Confirms the gap |

**What does NOT exist anywhere in this repo:** `storyforge-engine/` — no `main.py`, no `core/ai/provider.py`, no `core/image/providers.py`, no `core/world/world_engine.py`, no `core/publishing/`, no `requirements.txt`. Every one of those files is referenced by the docs and hooks but is absent. Also unverified (outside session access): `C:\Users\jjard\empire-os\` (the deploy target) and any local clone of the engine elsewhere on the machine.

---

## 2. What StoryForge Is Supposed To Do

Per `STORYFORGE_INTEGRATION.md` (the most authoritative doc), StoryForge is a **Python FastAPI book/story production engine** (port 8001), built in 5 phases:

| Phase | Module | Function |
|-------|--------|----------|
| 1 | Story Science | Flesch-Kincaid readability, emotion scoring, conflict/pacing analysis, plot-hole detection |
| 1 | Character Memory | SQLite character store, guarded-attribute contradiction detection (409 on canon violation) |
| 1 | Creative Council | 14 AI specialists (Story Architect, Character Designer, Continuity Inspector, etc.) |
| 1 | Book Exporter | **Real EPUB 3 generation, stdlib only** |
| 2 | World Engine | Persistent world memory — maps, timeline, cultures, lore, FTS5 search |
| 3 | Image Studio | Provider-agnostic image gen — Placeholder / ComfyUI / OpenAI DALL-E / Higgsfield |
| 4 | Publishing Studio | Market research, design briefs, AI listing copy, platform export (KDP, Etsy, Shopify, Gumroad, Payhip) |
| 5 | Automation Studio | Format packages (KDP/EPUB/PDF/hardcover/paperback/audiobook/marketing), campaigns, workflows, scheduler, analytics |

## 3. Inputs

From the `story-to-render` workflow trigger schema (`workflows/story-pipeline.ts`):

- `projectId` (required, string)
- `manuscriptText` (required, string) — **it takes a manuscript/premise text, not topic+genre+chapter-count parameters**
- `author` (optional)
- `worldName` (optional)
- `targetPlatforms` (optional: `kdp | etsy | shopify | gumroad | payhip`)

The Empire OS UI (per PROJECT_IDENTITY doc) additionally exposes: working title, core premise/theme, target audience, tone profile, narrative pacing.

## 4. Outputs

- **EPUB 3** — the one confirmed native export (`POST /book/export/epub`)
- Phase 5 format packages: **KDP, EPUB, PDF, hardcover, paperback, audiobook, marketing_package** (via `POST /automation/format-packages/generate-all`)
- Book cover image (Image Studio, `book_cover` type)
- Marketing campaign + listing copy
- No evidence of plain txt/markdown export endpoints.

## 5. APIs / Services It Uses

From `.env.example`:

- **AI:** OpenRouter (`OPENROUTER_API_KEY`), Anthropic direct (`ANTHROPIC_API_KEY`), Ollama local (`OLLAMA_BASE_URL`)
- **Images:** Higgsfield (`HIGGSFIELD_API_KEY` + `HIGGSFIELD_API_URL`), OpenAI DALL-E (`OPENAI_API_KEY`), ComfyUI local (`COMFYUI_BASE_URL`)
- **Empire OS:** Memory Bus (`EMPIRE_OS_MEMORY_URL`), Event Bus (`EMPIRE_OS_EVENT_URL`) on port 3100
- **Storage:** SQLite (local)

## 6. Is It Runnable RIGHT NOW?

**No.** Missing pieces, in order of blocking severity:

1. **The engine itself.** `storyforge-engine/` (FastAPI app, `main.py`, `core/*`, `requirements.txt`) is not in this repo. It must be recovered from `github.com/mjardin17/storyforge` (existence unverified — Josh needs to confirm the repo exists and is accessible), from `C:\Users\jjard\empire-os\`, or from wherever it was originally built. If it can't be found, **it must be rebuilt** — the docs are detailed enough to serve as a spec.
2. **`.env` with real keys** — Anthropic key exists in the pipeline `.env` already (`ELEVENLABS_API_KEY` pattern); StoryForge needs its own `.env` per `.env.example`.
3. **Two additive lines in the engine's `main.py`** to wire Empire OS hooks (only needed for Empire OS integration, not for standalone book generation).
4. Optional: Empire OS core running on port 3100/3001 for workflow orchestration — **not required** for standalone use; the engine's endpoints can be hit directly.

The `lo_adapters/storyforge.py` stub and the mock React UI generate nothing real — no silent-failure risk of thinking it works when it doesn't, because everything either raises `NotImplementedError` or is clearly a demo.

## 7. Exact Command To Generate Book #1

**Cannot be run today** — but once `storyforge-engine/` is recovered/placed at `empire-os-patch/apps/storyforge/storyforge-engine/`, per the README:

```bash
# 1. Start the engine
cd empire-os-patch/apps/storyforge/storyforge-engine
pip install -r requirements.txt
cp ../.env.example .env    # fill in ANTHROPIC_API_KEY at minimum
uvicorn main:app --port 8001

# 2. Generate + export book #1 (direct API, no Empire OS needed)
curl -X POST http://localhost:8001/science/analyze  -H "Content-Type: application/json" -d "{\"text\": \"<manuscript>\"}"
curl -X POST http://localhost:8001/council/review   -H "Content-Type: application/json" -d "{\"project_context\": \"<manuscript>\"}"
curl -X POST http://localhost:8001/book/export/epub -H "Content-Type: application/json" -d "{\"author\": \"Josh Jardin\"}"
```

Or the full pipeline via Empire OS workflow engine: trigger workflow `story-to-render` with `{ projectId, manuscriptText, author, targetPlatforms: ["kdp"] }`.

## 8. What Should Book #1 Be About?

**No book topic is specified anywhere** in CLAUDE.md or memory files — CLAUDE.md only says "StoryForge — Book generation system — built into Empire OS." The only premise found in the codebase is the mock UI's placeholder: *"The Mainframe Ghost"* — a developer discovers a sentient AI in a 1980s mainframe (demo data, not a plan).

[Likely] the highest-leverage choice, consistent with the Empire OS strategy (distribution first, reuse existing assets): **adapt an existing Gods & Glory full script into book #1** — e.g., EP012 "The Last Emperor (Fall of Rome)" from `prompts/gods_glory/` — since the 54-72 scene scripts are ready-made manuscripts, the channel provides built-in marketing, and KDP export is a native StoryForge capability. **Decision needed from Josh.**

---

## Recommended Next Actions

1. **Josh confirms where the StoryForge engine lives** — check `github.com/mjardin17/storyforge` and `C:\Users\jjard\empire-os\` for a `storyforge-engine/` folder. This is the single blocker.
2. If found: clone into `empire-os-patch/apps/storyforge/storyforge-engine/`, create `.env`, start on port 8001, add `START_STORYFORGE.bat` (already recommended by MISSING_COMPONENTS.md).
3. If not found: rebuild the engine from the spec in `STORYFORGE_INTEGRATION.md` + `empire_hooks/router.py` (which enumerates all 25+ endpoints).
4. Josh picks book #1's topic (recommendation: GG EP012 adaptation).
