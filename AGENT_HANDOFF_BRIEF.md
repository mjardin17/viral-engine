# Empire OS — Agent Handoff Brief
**Prepared:** 2026-07-18 | **For:** Next session pickup (credits reset ~2026-07-22)

Paste this entire file at the start of your next Claude session (or hand to any other agent — Grok, Gemini, Claude Code). Read it fully before doing anything.

---

## WHO I AM / STANDING RULES (NEVER BREAK)
- Josh Jardin (justifiedmagnificent@gmail.com) — CTO/architect of Empire OS, a multi-channel AI YouTube content empire.
- **Always start every response with "Josh"**
- No scene reuse, ever. 4 photos per scene, no exceptions.
- Never idle — always find the next task.
- Only the truth — no silent failures, no faked output, no fabricated APIs/commands.
- API keys/credentials go in files directly — never typed/pasted into chat by the assistant.
- **Double-check before every action** — read current state, confirm target, confirm nothing good gets overwritten.
- Full rule set lives in `CLAUDE.md` at repo root — read it in full before acting.

## CANONICAL LOCATION
`C:\Users\jjard\claude\video-bot-pipeline\` — this IS the repo. No forks, no parallel copies.
GitHub: `https://github.com/mjardin17/viral-engine` (branch `main`)
**Public repo + secret scanning** — always push via `PUSH_NOW.bat`, never raw `git push`.

---

## CHANNELS
| Channel | Status | Format |
|---|---|---|
| **Gods & Glory (GG)** | EP001-007 NEW FORMAT scripted (12 scenes, ~10min, punchy). EP006/EP007 old-format uploaded. S3 EP012-025 all scripted. | Static images + Ken Burns + Kokoro — Higgsfield rarely needed |
| **Little Olympus (LO)** | EP001 rendered (455MB Higgsfield). EP002-004 scripted (24-scene). | Cartoon — Higgsfield ESSENTIAL, credit-hungry |
| **Iron Legends (IL)** | EP001 scripted | 80s mech anime — Higgsfield essential |
| **Empire Decoded (ED)** | EP001 scripted | Tech/AI channel |
| **Echoes of Eternity (EOE)** | EP001 pending | New channel |

---

## THIS SESSION'S WORK (most recent first)

### 1. AI Orchestration Router — BUILT, committed `52dbb47`, NOT PUSHED
Full modular AI routing system, additive only, zero existing code removed:
- `ai_router/router.py` — central router, 14 task types (PLANNING, IMAGE_GENERATION, VIDEO_GENERATION, LIP_SYNC, etc.), health-informed fallback chains
- `ai_router/adapters/` — 20 adapters: Claude, OpenAI, Gemini, FLUX (via FAL), FLUX Kontext, MuseTalk, SkyReels, Wan 2.2, Higgsfield, ElevenLabs, Kokoro, Piper, Whisper, FFmpeg, FreePD, Openverse, Picsum, Pollinations, AI Horde, Uploader
- `ai_router/model_health.py` — tracks latency/success/cost per model, auto-recommends routing
- `council/roles/` — 10 new council members (Director, Producer, Screenwriter, Storyboard Artist, Prompt Engineer, Video Editor, Audio Engineer, QA Engineer, Publisher, Performance Analyst) — extend existing `CouncilBot` base
- `pipeline_validator.py` — validates prompts/images/video/audio/subtitles/render/copyright-risk/brand-consistency at every stage
- `dry_run.py` — tests all connectivity/auth/deps/paths without spending money — writes `DRY_RUN_REPORT.md`
- `report_generator.py` — writes `PIPELINE_ENGINEERING_REPORT.md` after every render (models used, routing decisions, fallbacks, errors, quality scores)
- Wired into `empire_render.py` with `--dry-run` flag — 42 lines added, 0 deletions, guarded import so router failure can never kill a render

**STILL TO DO:** `pip install openai-whisper` to activate subtitle generation. Update `AGENT_MEMORY.md` + `memory/context/pipeline.md` with the router architecture (repo rule: doc updates ship in the same push as structural changes).

### 2. Zero-signup free providers — BUILT, committed `29b9efb`, NOT PUSHED
No accounts, no API keys, all working right now:
- `providers/wikiart.py` — 250k historical paintings, **verified LIVE**
- `providers/openverse.py` — 700M CC images (fixed dead endpoint → `api.openverse.org`)
- `providers/lexica_search.py` — AI image search
- `providers/ai_horde.py` — anonymous Stable Diffusion, **verified LIVE**
- `providers/freepd_music.py` — 5 cached battle tracks, permanent local cache
- `free_tool_scout.py` — discovery brain, finds new free tools automatically
- `council/bots/bot_13_tool_scout.py` — runs scout daily, queues findings to MISSION_BOARD, never auto-wires without review
- Waterfall order updated: Wikimedia → WikiArt → Openverse → Lexica → Gemini → Cloudflare → Pollinations → AI Horde → Picsum → **Higgsfield last (10s paid warning intact)**
- **ACTION NEEDED:** run `RUN_TOOL_SCOUT.bat` once on Josh's machine (sandbox proxy blocks the live scan)

### 3. Research findings — free tools that mimic paid AI video
- **Wan 2.2** (Apache 2.0, free, open source) — this is literally the model Higgsfield's Wan 2.7 is built on. Runs locally on 12GB+ VRAM GPU, or via Replicate/FAL cheaply. **Josh's machine only has 8GB RAM — local won't run.** Cloud path (Replicate/FAL) is the option.
- **FLUX.1 Kontext** — the "puzzle piece" character-compositing technique Josh saw on YouTube. Open source, also on FAL (~$0.02/image). Wired as `flux_kontext_adapter.py`.
- **MuseTalk** (Tencent, free, open source) — best free lip sync, beats Wav2Lip/SadTalker. Wired as `musetalk_adapter.py` via HuggingFace.
- **SkyReels V2/V3** — free, unlimited-length cinematic video gen, on HuggingFace Spaces. Wired as `skyreels_adapter.py`.
- Conclusion given to Josh: free/local tools are good enough for GG (documentary/static+KenBurns), but **not yet competitive with Higgsfield for LO/IL cartoon quality**. The router now lets Higgsfield stay in the loop for peak moments while routing everything else free/cheap.

### 4. Credit-stretching plan for Higgsfield (LO/IL) — PLANNED, not yet built
Josh's core complaint: one 25-min cartoon episode burns all Higgsfield credits. 6-lever plan presented and approved in concept:
1. **Cut episode length** — LO at 24 scenes/18min is too long for the platform norm (top kids channels run 3-8 min). Recommend 10-12 scenes/~8min → doubles episode output per credit budget.
2. **Higgsfield only on 3-5 peak scenes per episode** (cold open, climax, resolution, stinger) — everything else Higgsfield-image-only or free tools + Ken Burns.
3. **Character sheet caching** — generate each character once via Soul Cast, reuse across all scenes/episodes instead of regenerating every time.
4. **Background library** — same idea for recurring locations (Olympus throne room, etc.)
5. **Model routing per scene type** — Hailuo for dialogue (cheap), Wan 2.7 for action, Soul Cast for character-critical, Ken Burns for narration/montage.
6. **Clip length targeting** — generate only 3-5s of real motion per scene, loop via FFmpeg to cover full narration length.

**NOT YET BUILT:** `scene_classifier.py`, `episode_credit_planner.py`, `assets/characters/` + `assets/backgrounds/` caching, updated LO/IL script format with `render_tier` field. **This is the next high-value build** — ask Josh to confirm before starting since it touches the script format.

### 5. Billing issues (informational, no code impact)
- Higgsfield: $75 refund credit vanished, escalated to human support after auto-support denied it. Unresolved as of this writing — check status.
- Anthropic/Claude: separate $75 credit issue, second request sent via support.claude.com. Unresolved as of this writing — check status.
- OpenAI API key added to `.env` — account `massgains1731@gmail.com`, $10 balance confirmed. Not yet wired to test end-to-end (adapter built, untested live).

---

## KEY FILES / PATHS
- `CLAUDE.md` — full standing rules, read in full before any work
- `empire_render.py` — main boss render tool, now has `--dry-run` and router wired in
- `ai_router/router.py` — central AI routing brain (NEW this session)
- `providers/waterfall.py` — free-first provider chain, Higgsfield last with paid warning
- `council/council.py` — 13 bots (bot_01–bot_13) + `council/roles/` (10 new specialized roles, run via `run_roles.py`)
- Python: `C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe` (never `py`, not in PATH)
- ffmpeg: `C:\ffmpeg\ffmpeg-8.1.2-essentials_build\bin\ffmpeg.exe`

## .env STATUS (keys present, do not ask Josh to re-paste — check first)
Working: ElevenLabs, Gemini, VEO, HF_TOKEN, Replicate, FAL, OpenAI (new). Empty/unused: Higgsfield (rotate — was exposed in git history), Kling, Luma, Pika, Minimax, Cloudflare, Groq, Pixabay.

## IMMEDIATE NEXT ACTIONS (in priority order)
1. Run `PUSH_NOW.bat` — two unpushed commits (`29b9efb`, `52dbb47`) waiting
2. `pip install openai-whisper` on Josh's machine to activate subtitles
3. Run `RUN_TOOL_SCOUT.bat` once to seed `free_tools_discovered.json`
4. Update `AGENT_MEMORY.md` + `memory/context/pipeline.md` with router architecture, commit together
5. Build the credit-stretching system (scene_classifier.py, episode_credit_planner.py, character/background asset caching) — confirm with Josh first, touches script format
6. Rotate `token_gg.pickle` + Higgsfield key (both exposed in git history at some point)
7. Test OpenAI adapter live (image gen + GPT-4o compositing) now that key is confirmed working

## LESSONS LEARNED (add to CLAUDE.md's Lessons section, don't duplicate)
- Sandbox proxy blocks ALL outbound Python HTTP — never trust a "dead" scan result from this environment; always give Josh a `.bat` to run real connectivity tests on his machine.
- Josh has explicitly and repeatedly refused new API signups/accounts — always default to zero-signup or already-in-.env solutions first, ask before suggesting any new account.
- Higgsfield credit burn from repeated clip regenerations without approval was a past failure — the 10-second paid warning + Ctrl+C window is now hard-wired and must never be removed.
