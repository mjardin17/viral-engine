# AGENT_MEMORY.md — Permanent Project Architecture
_Last updated: 2026-07-02 by Claude_

Every AI that works on this system must read this file before taking any action.

---

## What This System Is

**Viral Engine** — A 3-channel AI YouTube documentary factory.

- Converts episode JSON scripts → AI images → TTS narration → FFmpeg assembly → final MP4
- Three channels: Gods & Glory (GG), Mech Legends (ML), Little Olympus (LO)
- One production codebase. One GitHub repo. No forks.

**GitHub:** `https://github.com/mjardin17/viral-engine`
**Local:** `C:\Users\jjard\claude\video-bot-pipeline\`
**Owner:** Josh Jardin (justifiedmagnificent@gmail.com)

---

## Production Renderer

`auto_render.py` (1458 lines, modified 2026-06-28) is the canonical renderer.

```
Episode JSON → Pollinations images (4 per scene) → edge-tts/ElevenLabs TTS → FFmpeg Ken Burns → final MP4
```

A newer cinematic renderer `voice_video_pipeline.py` exists with style presets and loudnorm normalization. Both are active; `auto_render.py` is the primary.

---

## Pipeline Stages

```
1.  research_agent.py        Topic Discovery → Gemini Research → Score → 24-scene Script
2.  generate_images.py       Pollinations (free) or DALL-E 3 → 4 images/scene
3.  auto_render.py           TTS + Ken Burns FFmpeg per scene → clips
4.  caption_finalize_v3.py   Burned captions on final MP4
5.  pipeline_run.py          Orchestrates stages 1–7 with zero manual prompts
6.  (inline) Thumbnail       Pollinations 1280x720
7.  (inline) Metadata        YouTube-ready JSON
8.  social_machine/master.py Publish to YouTube
```

**Zero-prompt launch:**
```bash
python pipeline_run.py --channel gg
```

---

## Episode Status

| Channel | Season | Episodes | Status |
|---|---|---|---|
| GG | S1 | EP001–EP005 | ✅ Finals in renders/ (187–260MB each) |
| GG | S2 | EP006 | ❌ BROKEN — 21/24 clips are 0KB. Run `render_ep006.bat` |
| GG | S2 | EP007–EP011 | ✅ Finals in renders/ (but under 18min — stubs) |
| GG | S3 | EP012–EP025 | ✅ Scripts written. Run `render_season3.bat` to produce videos |
| GG | S3+ | EP026 | ✅ Script exists in prompts/gods_glory/ |
| ML | S1 | EP001 | ✅ Final in renders/ |
| ML | S1 | EP002–EP012 | ✅ Scripts in prompts/mech_legends/ |
| LO | S1 | EP001 | ✅ Final in renders/ |
| LO | S1 | EP002–EP040 | ✅ Scripts in prompts/ |

---

## Active Files — Production

| File | Role | Touch? |
|---|---|---|
| `auto_render.py` | Core renderer | Only for bug fixes |
| `voice_video_pipeline.py` | Cinematic renderer | Only for enhancements |
| `research_agent.py` | Autonomous research + script gen | Active development OK |
| `pipeline_run.py` | Zero-prompt orchestrator | Active development OK |
| `generate_images.py` | Image generation | Only for bug fixes |
| `caption_finalize_v3.py` | Caption burning | Only for bug fixes |
| `patch_fallbacks.py` | Image repair | Only for bug fixes |
| `script_guard.py` | Prevents stub downgrades | Do not modify |
| `council/council.py` | Bot runner | Only for bug fixes |
| `council/bots/` | 9 self-healing bots | Only for bug fixes |
| `social_machine/` | Publishing layer | Active development OK |
| `prompts/gods_glory/` | Active GG scripts | Add new scripts only |
| `prompts/mech_legends/` | Active ML scripts | Add new scripts only |

---

## Obsolete Files — Do Not Modify

| File | Era | Status |
|---|---|---|
| `render.py` | Empire Decoded | Obsolete — calls dead Higgsfield API |
| `local_render.py` | Empire Decoded v2 | Obsolete — 6-scene only |
| `documentary_render.py` | GG-specific fork | Superseded by auto_render.py |
| `iron_legends_render.py` | Iron Legends | Channel abandoned |
| `il_batch_render.py` | Iron Legends | Channel abandoned |
| `ep005_final_render.py` | One-off fix | Episode done |
| `pipeline.py` | Legend Empire | Reads stale episode_state.json |
| `bots/gemini_bot.py` | Legend Empire | Replaced by council/bots/ |
| `bots/chatgpt_bot.py` | Legend Empire | Replaced by council/bots/ |
| `iron_legends_bible.json` | Iron Legends brand | Abandoned |
| `episode_state.json` | Empire Decoded state | Stale (shows Episode 16 next, brand "Empire Decoded") |
| `script_registry.json` | Episode registry | Stale (only EP001–EP005 listed) |
| `prompts/gods_and_glory/` | Old directory name | Abandoned — use prompts/gods_glory/ |

---

## Never-Edit Folders

| Folder | Reason |
|---|---|
| `renders/` | Production finals — 2.1GB, read-only archive |
| `FINISHED_EPISODES/` | Old archived copies — redundant |
| `renders/iron_legends/` | Abandoned channel |
| `renders/thermopylae_doc/` | Old test renders |
| `bots/` | Legacy Legend Empire bots |
| `prompts/gods_and_glory/` | Abandoned, use prompts/gods_glory/ |

---

## API Keys Status

| Key | Status | Effect |
|---|---|---|
| `GEMINI_API_KEY` | ✅ Real key set in .env | research_agent.py works |
| `ELEVENLABS_API_KEY` | ❌ Placeholder | pipeline_run.py auto-detects, uses edge-tts fallback |
| `HIGGSFIELD_API_KEY` | ❌ Empty | render.py (obsolete) only |
| `KLING_API_KEY` | ❌ Empty | providers/kling.py only |
| `RUNWAY_API_KEY` | ❌ Empty | providers/runway.py only |
| `VEO_API_KEY` | ❌ Empty | providers/veo.py only |

---

## GitHub — Repos

| Repo | Status | Notes |
|---|---|---|
| `mjardin17/viral-engine` | ✅ PRODUCTION | This repo |
| `mjardin17/Crosspost-ai` | ⚠️ Empty | Placeholder, 1 commit |
| `mjardin17/crosspost` | ⚠️ 1 commit | Unclear purpose |
| `mjardin17/jardin-outpost` | ⚠️ Boilerplate | Next.js boilerplate only |
| `mjardin17/empire-os` | ❌ DOES NOT EXIST | Returns 404 |

---

## Brand History

| Name | Era | Status |
|---|---|---|
| Empire Decoded | 2026-06-15 (earliest) | ABANDONED |
| Legend Empire | 2026-06-16 | ABANDONED |
| Iron Legends | 2026-06-16 | ABANDONED (channel) |
| **Viral Engine** | 2026-06-28–present | **CURRENT** |

---

## Council Bot System

9 bots in `council/bots/`, run via `council_run.bat`.

| Bot | Priority | Function |
|---|---|---|
| bot_01_guardian | 10 | Scans for broken clips and short finals |
| bot_02_script_guard | 15 | Prevents stub downgrades |
| bot_03_image_healer | 20 | Re-fetches fallback images <20KB |
| bot_04_clip_rebuilder | 40 | Re-renders 0KB clips |
| bot_05_final_assembler | 50 | Rebuilds final MP4s |
| bot_06_render_queue | 30 | Tracks episode render status |
| bot_07_stub_expander | 35 | Manages 84-stub backlog |
| bot_08_auto_renderer | 60 | Renders 1 episode per council run |
| bot_09_quality_checker | 55 | ffprobe duration + audio RMS |

---

## Quality Standards

- Full episode: 24 scenes, ~47s avg, 1094–1150s total (~18–20 min)
- Narration: 90–120 words per scene
- Images: 4 per scene (scene_NN_1.jpg through scene_NN_4.jpg)
- Visual prompt: always starts with "Gods & Glory cinematic documentary."
- No scene reuse. Ever. Within or across episodes.

---

## Empire OS — Module Architecture (as of 2026-07-05)

Empire OS server: `empire-os-patch/apps/empire-os-server/server.ts` — 22 modules total.

**Video Pipeline module (new 2026-07-05):**
- `empire-os-patch/apps/video-pipeline/empire-module/video-pipeline.module.ts` → `/video-pipeline/`
- Proxies all requests to `empire_server.py` at `http://localhost:8002`
- Wired in server.ts — proxies `/video-pipeline/*` to port 8002
- `empire_server.py` must be running separately (see START_EMPIRE_PIPELINE.bat)

**empire_server.py (new 2026-07-05):**
- Location: `empire-os-patch/apps/video-pipeline/empire_server.py`
- FastAPI at port 8002 — the one-click render bridge
- Spawns `auto_render.py` as subprocess, captures stdout, tracks progress
- Endpoints: GET /api/episodes, POST /api/render, GET /api/render/status, GET /api/render/logs (SSE + polling), POST /api/cancel, GET /api/council/status
- Start: `python empire-os-patch/apps/video-pipeline/empire_server.py` from repo root
- Or use: `START_EMPIRE_PIPELINE.bat` (starts both Empire OS + empire_server.py)

**empire-dashboard.module.ts updated (2026-07-05):**
- New "Render Episode" page in sidebar under Studio
- Episode dropdown (auto-populated from prompts/ scan)
- Live progress bar + log streaming (polling via /video-pipeline proxy)
- Job history table

**Operation Blacksmith modules (new 2026-07-04):**
- `logger.module.ts` → `/logger/` — centralized structured logging, `empireLog()` singleton
- `metrics-engine.module.ts` → `/metrics-engine/` — P50/P95/P99 per module, `recordMetric()` called in server.ts routing
- `job-scheduler.module.ts` → `/job-scheduler/` — 4 built-in background jobs (backup/discovery/self-check/log-rotate)
- `service-registry.module.ts` → `/service-registry/` — 26 services, dependency graph, health matrix
- `notification.module.ts` → `/notification/` — event queue, `emitNotification()` importable

**All modules are instrumented for metrics** — `recordMetric()` is called at the routing call site in server.ts after every `handleRequest()`.

---

## YouTube Upload System (Working as of 2026-07-07)

**Upload script:** `easy_youtube_uploader.py`
**Launcher:** `UPLOAD_NOW.bat`
**Token:** `token.pickle` (saved after first auth, reused automatically)
**Credentials:** `credentials.json` (OAuth Desktop client — DO NOT COMMIT)

**GCP Project:** `viral-engine-yt` (owner: justifiedmagnificent@gmail.com)
**YouTube channel:** "Gods & Glory" on **godsandgloryai@gmail.com**
**GCP test users:** justifiedmagnificent@gmail.com, godsandgloryai@gmail.com
**CRITICAL:** Always sign in as godsandgloryai@gmail.com for uploads — justifiedmagnificent@gmail.com is NOT verified for long videos and uploads will fail.

### Normal upload flow
1. Double-click `UPLOAD_NOW.bat`
2. If browser opens for auth: sign in as **godsandgloryai@gmail.com** → Allow
3. All videos upload automatically. Token saved — no re-auth on next run.

### If auth breaks (wrong account or expired)
- Delete `token.pickle` from pipeline folder → run `UPLOAD_NOW.bat` again

### If "Access is blocked" error
- Visit: https://console.cloud.google.com/auth/audience?project=viral-engine-yt
- Sign into GCP as justifiedmagnificent@gmail.com
- Scroll to Test users → confirm justifiedmagnificent@gmail.com is listed

### If Chrome doesn't open automatically
- URL is printed in CMD — copy/paste into Chrome manually, complete sign-in there

### Adding more videos to upload
- Edit the `VIDEOS` list in `easy_youtube_uploader.py`

---

## Immediate Actions Needed (as of 2026-07-05)

1. **SECURITY**: Josh must rotate all keys exposed in .env before next commit — see SECURITY_REPORT.md
2. **SECURITY**: Run `FIX_SECURITY.bat` to remove .env from git tracking (after rotating keys)
3. **Install FastAPI**: `pip install fastapi uvicorn` (one-time, for empire_server.py)
4. **Launch**: Run `START_EMPIRE_PIPELINE.bat` — starts both Empire OS (port 3001) and empire_server.py (port 8002)
5. **Test**: Open http://localhost:3001/empire-dashboard/ → click "Render Episode" → pick episode → click Render
6. `render_ep006.bat` — Fix GG_EP006 (Pearl Harbor, 21/24 clips broken)
7. `render_season3.bat` — Render GG_EP012–EP025 (all scripts complete)
8. Set real `ELEVENLABS_API_KEY` in .env (optional — edge-tts fallback works)
