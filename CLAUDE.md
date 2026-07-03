# Memory — Josh Jardin (Viral Engine)

## Me
Josh Jardin (justifiedmagnificent@gmail.com). Building a 3-channel AI YouTube documentary empire called **Viral Engine**. Every response must start with "Josh".

## Standing Rules (NEVER BREAK)
- **Always start every response with "Josh"**
- **No scene reuse** — ever, within or across episodes
- **4 photos per scene** — every scene, no exceptions
- **Never idle** — there is always something to do in this pipeline
- **Only the truth** — no silent failures, no faking output
- **API keys/credentials NEVER in chat** — Josh adds them to files directly
- **Scheduled tasks** — always ask Josh before creating; never run every N minutes unless Josh explicitly approves the frequency

## Projects
| Name | What | Status |
|------|------|--------|
| **Gods & Glory (GG)** | History/battle documentary channel | Season 1 ✅ Season 2 partial Season 3 scripting |
| **Machine Learning (ML)** | Second channel | EP001 scripted |
| **Little Olympus (LO)** | Third channel (Little Zeus) | EP001 scripted |
| **Council Bot System** | Self-healing pipeline monitor (9 bots) | Live |
| **Viral Engine Launch** | Website + YouTube + Store + Apps + Newsletter | Opening day pending |

→ Full details: memory/projects/

## Key Terms
| Term | Meaning |
|------|---------|
| GG | Gods & Glory channel |
| ML | Machine Learning channel |
| LO / Little Zeus | Little Olympus channel |
| EP006 | Pearl Harbor — broken, needs re-render |
| Council | The 9-bot self-healing pipeline system |
| Full script | 24 scenes, ≥600s (~18-20 min) |
| Stub | Short script, <10 scenes, unusable |
| auto_render.py | Core pipeline: JSON → images → TTS → FFmpeg → MP4 |
| patch_fallbacks.py | Surgical fix for broken/tiny images |
| render_ep006.bat | Re-renders GG_EP006 (Pearl Harbor) from scratch |
| council_run.bat | Launches all 9 council bots |
| PROMPTS_DIR | prompts/ — all episode JSON scripts live here |
| gods_glory/ | Subdirectory where full GG scripts live (auto_render picks these over root stubs) |

## Episode Status
| Season | Episodes | Status |
|--------|----------|--------|
| S1 GG | EP001–EP005 | ✅ Finals in renders/ (187–260MB each) |
| S2 GG | EP006–EP011 | EP007–011 finals in renders/ (stubs); EP006 BROKEN — run render_ep006.bat |
| S3 GG | EP012–EP025 | ✅ ALL 14 SCRIPTS WRITTEN — run render_season3.bat to render |
| ML S1 | EP001 | Scripted only |
| LO S1 | EP001 | Scripted only |

## S3 Script Index (all in prompts/gods_glory/)
EP012 The Last Emperor (Fall of Rome) | EP013 Crusader Kingdoms
EP014 Waterloo | EP015 Marathon | EP016 Agincourt | EP017 Battle of Tours
EP018 Hastings 1066 | EP019 Kamikaze/Mongol Fleet | EP020 Vienna 1683
EP021 Midway | EP022 Battle of the Bulge | EP023 Operation Market Garden
EP024 Inchon | EP025 Yorktown

## Council Bots (9 total, C:\Users\jjard\claude\video-bot-pipeline\council\bots\)
| Bot | Priority | Role |
|-----|----------|------|
| bot_01_guardian | 10 | Scans for broken/tiny clips and short finals |
| bot_02_script_guard | 15 | Guards against stub downgrades |
| bot_03_image_healer | 20 | Re-fetches fallback images <20KB |
| bot_04_clip_rebuilder | 40 | Re-renders 0KB clips |
| bot_05_final_assembler | 50 | Rebuilds final MP4s |
| bot_06_render_queue | 30 | Tracks episodes ready to render |
| bot_07_stub_expander | 35 | Tracks 84 stub episodes needing full scripts |
| bot_08_auto_renderer | 60 | Renders 1 episode per council run |
| bot_09_quality_checker | 55 | ffprobe duration + audio RMS check |

## Viral Engine Launch (TODAY)
Josh is launching everything today:
- YouTube channels (already created)
- Website / landing page (needs building)
- Store (platform TBD — need URL from Josh)
- Apps Josh has built (need names/links from Josh)
- Newsletter signup
- Social media opening day posts for all platforms
**STILL NEED FROM JOSH:** website URL, store URL, app names/links

## Preferences
- Direct and concise answers
- Never stop working — always move to next task
- Credits matter — no runaway scheduled tasks
- Josh handles credentials himself
- Wants everything launched, not just planned

→ Full pipeline docs: memory/context/pipeline.md
→ Full episode backlog: memory/projects/viral-engine.md

## Git & GitHub (PRODUCTION RULES)

**Repository:** `https://github.com/mjardin17/viral-engine` (branch: `main`)

### Before every task
```
git pull origin main
```
Read `AGENT_MEMORY.md` before touching any code.

### After every change
```
git add -A
git commit -m "[CLAUDE] <type>: <description>"
git push origin main
```
If architecture changed → update `AGENT_MEMORY.md` in the same commit.

### What is NEVER committed
- `.env` (API keys)
- `renders/` (production MP4s — too large)
- `output/` (render working files)
- `FINISHED_EPISODES/` (archived copies)
- Any `*.mp4`, `*.wav`, `*.mp3`, `*.aac` files

### Commit message format
```
[CLAUDE] feat: description of new feature
[CLAUDE] fix: description of bug fix
[CLAUDE] docs: description of doc update
[CLAUDE] chore: maintenance work
```

### Canonical production folder
`C:\Users\jjard\claude\video-bot-pipeline\` — this IS the repo.
No other folder. No forks. No parallel copies.

### Architecture authority
Claude holds architecture authority. After any structural change:
1. Update `AGENT_MEMORY.md`
2. Update `memory/context/pipeline.md` if pipeline changed
3. Commit both in the same push
4. Notify Josh of what changed
