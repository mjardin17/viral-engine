# Claude Code — Empire OS Video Pipeline Handoff

**Version:** 2026-07-21 | **Context:** Multi-channel AI content empire (5 YouTube channels)

---

## Mission Brief

Fix **LO_EP001 (Little Olympus Episode 1)** quality issues and implement audio corrections. The episode rendered but has critical quality failures: visuals are placeholder squares instead of gods/characters, and audio is too slow with inconsistent volume levels. Your job: diagnose root causes, fix audio pipeline, and verify quality before upload.

---

## Environment Setup

**Working Directory:** `C:\Users\jjard\claude\video-bot-pipeline\`  
**Repository:** `https://github.com/mjardin17/viral-engine` (main branch)  
**Python Interpreter:** `C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe` (NOT `py`)

### .env Configuration
All API keys in `.env` at repo root (NEVER commit):
- `GEMINI_API_KEY` — image gen fallback
- `OPENAI_API_KEY` — reasoning fallback
- `REPLICATE_API_TOKEN` — video gen
- `FAL_KEY` — fal.ai video
- `HF_TOKEN` — HuggingFace
- `ELEVENLABS_API_KEY` — NOT used in pipeline (Kokoro is primary)
- `HIGGSFIELD_API_KEY` — (empty) — 276 credits were wasted on untested adapter; disable for now

---

## Critical File Locations

### Core Pipeline
```
C:\Users\jjard\claude\video-bot-pipeline\
├── auto_render.py                    # Main pipeline: JSON → images → TTS → FFmpeg → MP4
├── empire_render.py                  # Render orchestrator (if exists)
├── channel_uploader.py               # YouTube uploader (fixed 2026-07-21)
├── council_run.bat                   # Launch all council bots (quality checks)
├── .env                              # API keys (NEVER commit)
├── CLAUDE.md                         # Source of truth (update after every change)
├── AGENT_MEMORY.md                   # Architecture authority
├── MISSION_BOARD.json                # Immediate action queue
│
├── voice-music-factory/
│   └── tts_cli.py                    # Kokoro TTS (local, unlimited, free) — PRIMARY VOICE
│
├── social_clips/
│   ├── clip_generator.py             # Auto-generate 5 platform clips
│   ├── auto_publisher.py             # Post to IG/TikTok/FB/Pinterest
│   └── post_render.py                # Post-render hook
│
├── ai_router/
│   ├── router.py                     # Central routing (14 task types, health scoring)
│   └── adapters/
│       ├── omniroute_adapter.py       # Multi-provider fallback (NEW)
│       ├── higgsfield_adapter.py      # ⚠️ BROKEN — caused 276-credit waste
│       ├── kokoro_adapter.py          # Local TTS
│       ├── ffmpeg_adapter.py          # Video assembly
│       └── [16 others]                # (flux, gemini, openai, etc.)
│
├── council/
│   ├── bots/
│   │   ├── bot_09_audio_check.py      # Audio RMS/presence check (technical only)
│   │   ├── bot_10_frame_inspector.py  # Frame validation (technical only)
│   │   └── bot_14_credit_guardian.py  # Blocks over-budget renders
│   │
│   └── state/
│       ├── gg/render_queue.json       # GG render queue
│       ├── lo/                        # LO episode state
│       └── il/                        # IL episode state
│
├── prompts/
│   ├── gods_glory/
│   │   ├── GG_EP001_thermopylae.json  # EP001 script (NEW FORMAT)
│   │   └── [14 S3 scripts]            # EP012-025
│   │
│   └── little_olympus/
│       ├── LO_EP001_full_script.json  # 24 scenes (BROKEN OUTPUT)
│       ├── LO_EP002_full_script.json  # 24 scenes (queued)
│       └── [EP003, EP004]
│
├── renders/
│   ├── little_olympus/
│   │   └── LO_EP001_final.mp4         # ⚠️ BROKEN VIDEO (placeholders + slow audio)
│   │
│   └── gods_glory/
│       ├── GG_EP001_final.mp4
│       └── [S2/S3 renders]
│
└── [BAT FILES]
    ├── START_OMNIROUTE.bat            # Launch OmniRoute on localhost:20128
    ├── PUSH_NOW.bat                   # Push to GitHub (handles secret scanning)
    ├── RENDER_S2_MISSING.bat          # Render GG S2 missing episodes
    └── render_season3.bat             # Render all GG S3 episodes
```

### YouTube Channels & Tokens
```
Token Locations:
├── token_gg.pickle                   # CORRECT token (GG channel account)
├── credentials.json                  # GCP project credentials (needs rotation — in git history)
└── channel_uploader.py → CHANNEL_MAP
    ├── "GG_EP001" → "GG_EP001_final.mp4" → @godsandgloryai
    ├── "LO_EP001" → "LO_EP001_final.mp4" → @littleolympusai (BROKEN)
    ├── "IL_EP001" → "IL_EP001_final.mp4" → @ironlegendsai
    ├── "ED_EP001" → "ED_EP001_final.mp4" → @empiredecoded
    └── "EOE_EP001" → "EOE_EP001_final.mp4" → @echosofeternitiai
```

---

## LO_EP001 Diagnosis

### What Went Wrong
1. **Visuals:** Higgsfield integration was built but never end-to-end tested before paying 276 credits. Result: placeholder squares rendered instead of god/hero characters.
2. **Audio:** Kokoro TTS speed is robotically slow + volume levels inconsistent (some scenes barely audible at max volume).
3. **Council QA Failed:** bot_09_audio_check and bot_10_frame_inspector only validate technical metrics (RMS, frame count, duration). They passed despite garbage content because they don't do manual playback review.

### LO_EP001 Script Structure
- **24 scenes** (each with 4 images + narration + music)
- **Expected duration:** ~17 minutes
- **Expected visuals:** Greek gods (Zeus, Athena, etc.) and mythological scenes
- **Expected audio:** Natural-sounding Kokoro TTS (~150 wpm), consistent volume levels

### Files to Inspect
```
Inputs:
├── prompts/little_olympus/LO_EP001_full_script.json  # 24-scene JSON script
├── .env                                               # HIGGSFIELD_API_KEY (empty now)

Outputs:
├── renders/little_olympus/LO_EP001_final.mp4         # BROKEN: watch first 30s
├── output/LO_EP001/                                  # Working directory (temp files)

Config:
├── empire_render.py                                  # Routing logic (check Higgsfield routing)
├── ai_router/adapters/higgsfield_adapter.py          # ⚠️ BROKEN — do NOT enable
├── voice-music-factory/tts_cli.py                    # Kokoro speed/volume control
```

---

## Action Plan

### Phase 1: Diagnosis (30 min)
1. **Watch LO_EP001_final.mp4** (first 3 scenes) → note exact failures
2. **Read LO_EP001_full_script.json** → confirm expected content
3. **Check empire_render.py routing** → where did it try to get visuals? (Higgsfield? Pollinations?)
4. **Check Kokoro config** → speech rate parameter (default? too slow?)
5. **Check audio output** → check RMS levels per scene in output/ directory

### Phase 2: Audio Fix (20 min)
- **Locate Kokoro speed control:** voice-music-factory/tts_cli.py → speech_rate parameter
- **Recommended:** Increase from ~1.0x to ~1.25x-1.35x (natural speed for kids content)
- **Volume:** Normalize each scene's RMS to -20dB ±2dB (consistent)
- **Test:** Render 1 scene with new settings, listen, approve

### Phase 3: Visuals Fix (60+ min)
- **DO NOT re-enable Higgsfield.** Cost is too high for untested code.
- **Use Pollinations instead:** empire_render.py defaults to Pollinations for image gen (free)
- **Test:** Render LO_EP001 using Pollinations + Kokoro (fixed) + FFmpeg assembly
- **Validate:** Check frame inspector — all 96 images present (24 scenes × 4 images)

### Phase 4: Quality Verification (30 min)
- **Manual playback:** Watch full episode, verify:
  - ✓ Visuals match script (gods/characters, not placeholders)
  - ✓ Audio speed natural (not robotic slow)
  - ✓ Volume consistent (can hear all scenes at normal volume)
  - ✓ No glitches, scene transitions smooth
- **Run council_run.bat** → bot_09 + bot_10 should PASS
- **Get Josh approval** before uploading to YouTube

### Phase 5: Upload (10 min)
- **Run:** `channel_uploader.py --channel LO_EP001 --verify`
- **Verify:** Check @littleolympusai channel → video live + metadata correct
- **Confirm Josh** saw the correct upload

---

## Standing Rules (NEVER BREAK)

1. **Start every response with "Josh"**
2. **Double-check before acting:** Read current state, confirm target, don't overwrite good work
3. **No silent failures:** Always report what happened (success/error/partial)
4. **CLAUDE.md is source of truth:** Refer to it, update it after every change
5. **MISSION_BOARD.json is immediate queue:** Execute or dispatch, no rot
6. **API keys NEVER in chat:** You add them to .env directly on Josh's machine
7. **No Higgsfield without Josh approval + dry-run on cheap tier first**
8. **YouTube uploads:** Always require Josh's manual approval before executing

---

## Key Contacts & Systems

- **OmniRoute Multi-Provider Router:** Running at `localhost:20128/v1` (10+ providers, auto-failover when Claude credits exhaust)
- **Council Bot System:** `council_run.bat` launches all quality checks (bot_09, bot_10, bot_14, etc.)
- **MISSION_BOARD.json:** Check this first thing — it's the action queue
- **CLAUDE.md Updates:** Do this after every work session (non-negotiable)

---

## Success Metrics

✅ LO_EP001 visuals: god/character images (not placeholders)  
✅ LO_EP001 audio: natural Kokoro speed + consistent volume  
✅ Council QA passes (both technical + manual review)  
✅ Video uploaded to @littleolympusai with Josh verification  
✅ CLAUDE.md updated with work completed + lessons learned  

---

## One Final Note

Josh's last session (2026-07-21) identified that **council QA only validates technical metrics**. The real issue: a bot can pass RMS checks and frame counts while the actual video is garbage (placeholder squares, robotic voice). **The fix is not better bot logic — it's mandatory human playback review before upload.** Make sure you watch the rendered video with your own eyes before calling it "done."

Go fix it.
