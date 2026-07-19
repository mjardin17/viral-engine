# AGENT_MEMORY.md — Permanent Project Architecture
_Last updated: 2026-07-18 by Claude_

Every AI that works on this system must read this file before taking any action.

---

## What This System Is

**Empire OS** — A 5-channel AI YouTube content empire with AI orchestration router.

- Converts episode JSON scripts → AI images → TTS narration → FFmpeg assembly → final MP4
- Five channels: Gods & Glory (GG), Little Olympus (LO), Iron Legends (IL), Empire Decoded (ED), Echoes of Eternity (EOE)
- One production codebase. One GitHub repo. No forks.
- AI Router: 20 adapters (Claude, OpenAI, Gemini, FLUX, MuseTalk, Higgsfield, etc.) with health scoring and fallback chains
- Council Bot System: 14 self-healing bots with priorities, including credit-guardian for LO/IL budget control

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

## Episode Status (Updated 2026-07-18)

| Channel | Season | Episodes | Status | Notes |
|---|---|---|---|---|
| **GG** (Gods & Glory) | NEW FORMAT | EP001–EP007 | ✅ Scripted (Thermopylae/Cannae/Constantinople/Teutoburg/Gaugamela/Vienna/Stalingrad) | Queued for render via empire_render.py |
| GG | S2 | EP006–EP007 | ✅ Uploaded (old 45-min format) | Pearl Harbor (41min), D-Day (39min) |
| GG | S2 | EP008–EP011 | ⚠️ RENDERING NOW | From full 54-scene scripts via RENDER_S2_MISSING.bat |
| GG | S3 | EP012–EP025 | ✅ Scripts written (14 episodes) | Run render_season3.bat to render |
| **LO** (Little Olympus) | S1 | EP001 | ⚠️ BROKEN (4 scenes repeating) | Fix via credit-stretching system (hybrid Higgsfield+free) |
| LO | S1 | EP002–EP004 | ✅ Scripted (24-scene full scripts) | Ready for credit-optimized render |
| **IL** (Iron Legends) | S1 | EP001 | ✅ Scripted | Higgsfield essential for anime |
| **ED** (Empire Decoded) | S1 | EP001 | ✅ Scripted | Tech/AI channel |
| **EOE** (Echoes of Eternity) | S1 | EP001 | 🔄 Pending | New channel |

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

14 bots in `council/bots/`, run via `council_run.bat`.

| Bot | Priority | Function |
|---|---|---|
| bot_01_guardian | 10 | Scans for broken clips and short finals |
| bot_02_script_guard | 15 | Prevents stub downgrades |
| bot_03_image_healer | 20 | Re-fetches fallback images <20KB |
| bot_04_clip_rebuilder | 40 | Re-renders 0KB clips |
| bot_05_final_assembler | 50 | Rebuilds final MP4s |
| bot_06_render_queue | 30 | Tracks episode render status |
| bot_07_stub_expander | 35 | Manages stub backlog |
| bot_08_auto_renderer | 60 | Renders 1 episode per council run |
| bot_09_quality_checker | 55 | ffprobe duration + audio RMS |
| bot_10_frame_inspector | 56 | Visual QC: frame every 30s, catches red/black/white/frozen screens |
| bot_11_orchestrator_monitor | 5 | Watchdog: restarts master orchestrator if heartbeat stale |
| bot_12_social_publisher | 65 | Self-healing social posts: retries failed platform posts (max 3) |
| bot_13_tool_scout | 25 | Discovers free tools daily, queues findings to MISSION_BOARD |
| bot_14_credit_guardian | 45 | Blocks LO/IL episodes over Higgsfield budget or without approved render_plan.json |

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

## Higgsfield Credit-Stretching System (NEW 2026-07-18)

For **LO (Little Olympus)** and **IL (Iron Legends)** episodes, Higgsfield is essential but expensive. New system reduces Higgsfield spend by ~80%.

**Three-step workflow:**

1. **scene_classifier.py** — Assigns each scene a render tier
   - `higgsfield_video` (3-4 peak moments per episode, ~10 credits each)
   - `higgsfield_image` (high-action scenes, ~2.5 credits each)
   - `composited` (cached character + background via FLUX Kontext, ~$0.02 each)
   - `free` (free providers + Ken Burns, $0)

2. **episode_credit_planner.py** — Interactive budget optimizer
   - Shows cost estimate
   - Auto-downgrades low-priority scenes if over budget
   - Outputs `{episode_id}_render_plan.json` (read by bot_14_credit_guardian)

3. **bot_14_credit_guardian** (council bot, priority 45)
   - Checks LO/IL episodes BEFORE render
   - Blocks rendering if render_plan.json missing or over safety threshold (default 50 credits)

**Asset caching** (via asset_cache.py):
- `assets/characters/{channel}/{character}/` — character sheets (reused across scenes)
- `assets/backgrounds/{channel}/{location}/` — backgrounds (reused across scenes)

**Result:** One 24-scene LO episode costs ~30-40 Higgsfield credits (was 200+).

---

## AI Orchestration Router (NEW 2026-07-18)

**Central routing system** at `ai_router/router.py` — handles all AI generation across 20 adapters.

**14 Task Types:**
- PLANNING, RESEARCH, SCRIPT_GENERATION, PROMPT_ENGINEERING
- IMAGE_GENERATION, VIDEO_GENERATION, 3D_GENERATION
- TTS_GENERATION, AUDIO_EDITING, LIP_SYNC
- SUBTITLE_GENERATION, CAPTION_BURNING
- QUALITY_CHECK, PUBLISHING

**20 Adapters:** Claude, OpenAI, Gemini, FLUX, FLUX Kontext, MuseTalk, SkyReels, Wan 2.2, Higgsfield, ElevenLabs, Kokoro, Piper, Whisper, FFmpeg, FreePD, Openverse, Picsum, Pollinations, AI Horde, Uploader

**Health Scoring:** Tracks latency/success/cost per model, auto-recommends routing based on load

**Provider Waterfall (in order):**
Wikimedia → WikiArt → Openverse → Lexica → Gemini → Pollinations → AI Horde → Higgsfield (with 10s paid warning)

**Features:**
- Paid warning: 10-second countdown before Higgsfield charges, Ctrl+C to cancel
- Dry-run mode: test all connectivity/auth/deps without spending money
- Report generator: writes PIPELINE_ENGINEERING_REPORT.md after every render
- Free tools: bot_13_tool_scout discovers new free tools daily, queues via MISSION_BOARD

**Wiring:** Integrated into `empire_render.py` with `--dry-run` flag. No breaking changes to existing render API.

---

## YouTube Upload System (Working as of 2026-07-18)

**Upload script:** `channel_uploader.py` (per-channel uploader with --verify flag)
**Launcher:** Per-channel bat files (UPLOAD_GG.bat, UPLOAD_LO.bat, UPLOAD_IL.bat, UPLOAD_ED.bat, UPLOAD_EOE.bat)
**Token:** `token_gg.pickle` for GG (correct account), NOT `token.pickle` (wrong account)
**Credentials:** `credentials.json` (OAuth Desktop client — DO NOT COMMIT)
**CRITICAL:** Always verify after upload that video URL shows correct channel name before proceeding to next episode

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

## Immediate Actions Needed (as of 2026-07-18)

1. **PUSH COMMITS**: Run `PUSH_NOW.bat` to push commits 29b9efb + 52dbb47 (AI router + free providers) + CLAUDE.md update
2. **INSTALL WHISPER**: `pip install openai-whisper` on Josh's machine to activate subtitle generation in router
3. **RUN TOOL SCOUT**: Execute `RUN_TOOL_SCOUT.bat` once to seed `free_tools_discovered.json` (sandbox proxy blocks HTTP, needs real machine)
4. **UPDATE AGENT_MEMORY.md**: Add AI Router architecture + 5 channels (done in this session — needs commit)
5. **BUILD CREDIT-STRETCHING**: Confirm with Josh, then integrate scene_classifier + episode_credit_planner into render workflow
6. **ROTATE CREDENTIALS**: Higgsfield key + token_gg.pickle (both exposed in git history)
7. **FIX LO_EP001**: Re-render using credit-stretching system (hybrid Higgsfield+free) instead of 4-scene repeat
8. **IMPLEMENT QUICK WINS**: MAX_PARALLEL_SCENES 2→6, POLL_INTERVAL 30→10, batch image fetches (5 min, 2-3x throughput)
8. Set real `ELEVENLABS_API_KEY` in .env (optional — edge-tts fallback works)
