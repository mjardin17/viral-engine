# Claude Code — Render EP1 for All Four Channels (GG, LO, IL, ED)

**Version:** 2026-07-21 | **Context:** Multi-channel render using OmniRoute failover + credit-stretching system  
**Channels:** Gods & Glory (GG), Little Olympus (LO), Iron Legends (IL), Empire Decoded (ED)

---

## Mission Brief

Render **Episode 1 for all four active channels** using the new production stack:
- **OmniRoute** (localhost:20128) for multi-provider failover when credits exhaust
- **ai_router** with health scoring + dry-run validation before paid generation
- **Credit-stretching system** (scene_classifier.py + episode_credit_planner.py) for LO/IL to minimize Higgsfield spend
- **Kokoro TTS** (local, unlimited, free) for all narration
- **Council bots** for mandatory quality checks before upload

Output: 4 production-ready MP4 files in `renders/{channel}/` directory, all verified by council QA, ready for manual upload.

---

## Environment & Setup

**Working Directory:** `C:\Users\jjard\claude\video-bot-pipeline\`  
**Repository:** `https://github.com/mjardin17/viral-engine` (main branch)  
**Python Interpreter:** `C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe` (NOT `py`)

### Prerequisites (VERIFY BEFORE STARTING)
```bash
# 1. OmniRoute MUST be running
curl http://localhost:20128/v1 || echo "ERROR: Start OmniRoute with START_OMNIROUTE.bat"

# 2. Pull latest code
git pull origin main

# 3. Check .env has required keys
# GEMINI_API_KEY ✓
# OPENAI_API_KEY ✓
# REPLICATE_API_TOKEN ✓
# FAL_KEY ✓
# HF_TOKEN ✓
# (HIGGSFIELD_API_KEY should be EMPTY — do NOT enable)
```

---

## Episode Scripts & Locations

### Scripts (JSON files in prompts/ directory)
```
GG_EP001:
  Path: C:\Users\jjard\claude\video-bot-pipeline\prompts\gods_glory\GG_EP001_thermopylae.json
  Format: NEW FORMAT v3.0 (12–15 scenes, ~10 min, one battle)
  Scene Count: ~12
  Image Source: Wikimedia Commons (free)
  TTS: Kokoro (local, ~150 wpm)
  Expected Output: GG_EP001_final.mp4 (120–180MB)
  YouTube: @godsandgloryai

LO_EP001:
  Path: C:\Users\jjard\claude\video-bot-pipeline\prompts\little_olympus\LO_EP001_full_script.json
  Format: 24-scene full script (kids content)
  Scene Count: 24
  Image Source: Higgsfield (hero/god characters) + Pollinations fallback
  TTS: Kokoro (local, natural speed for kids)
  Expected Output: LO_EP001_final.mp4 (400–500MB)
  YouTube: @littleolympusai
  ⚠️ PRIOR RUN BROKEN — this render fixes it

IL_EP001:
  Path: C:\Users\jjard\claude\video-bot-pipeline\prompts\iron_legends\IL_EP001_full_script.json
  Format: 24-scene full script (80s mech anime)
  Scene Count: 24
  Image Source: Higgsfield (mech/character animation) + Pollinations fallback
  TTS: Kokoro (natural, energetic for action)
  Expected Output: IL_EP001_final.mp4 (400–500MB)
  YouTube: @ironlegendsai

ED_EP001:
  Path: C:\Users\jjard\claude\video-bot-pipeline\prompts\empire_decoded\ED_EP001_full_script.json
  Format: 12–15 scenes (AI/tech education)
  Scene Count: ~12
  Image Source: Pollinations (diagrams, code visuals)
  TTS: Kokoro (professional, clear delivery)
  Expected Output: ED_EP001_final.mp4 (120–180MB)
  YouTube: @empiredecoded (NOT YET LIVE — setup pending)
```

---

## Render Pipeline Architecture

### 1. Script Validation
```python
# For each episode:
# ✓ Confirm script exists at correct path
# ✓ Validate JSON structure (24 scenes for LO/IL, 12–15 for GG/ED)
# ✓ Confirm all scene prompts are non-empty
# ✓ Confirm TTS narration text exists
```

### 2. Credit Estimation (BEFORE spending money)
```python
# For LO/IL ONLY (Higgsfield-heavy):
from scene_classifier import classify_scenes
from episode_credit_planner import estimate_budget

script = load_json("prompts/little_olympus/LO_EP001_full_script.json")
tiers = classify_scenes(script)  # Returns: {higgsfield: N, image: N, composited: N, free: N}
budget = estimate_budget(tiers)  # Estimates total credits needed

# Example output:
# Higgsfield: 8 scenes × 20 credits = 160 credits
# Pollinations: 16 scenes × 0 credits = 0 credits
# Total estimated: ~160 credits

# Show Josh: "LO_EP001 will cost ~160 Higgsfield credits. Approve? (y/n)"
# If no → skip LO/IL, render GG/ED only
# If yes → proceed with render
```

### 3. Image Generation (with failover)
```python
# Route through ai_router with OmniRoute fallback:
from ai_router.router import AIRouter, TaskType

router = AIRouter()

# For each scene in each episode:
result = router.route(
    TaskType.IMAGE_GENERATION,
    {
        "prompt": scene.image_prompt,
        "task_type": "image_generation",
        "dest": f"output/{channel}/scene_{i:03d}.png",
        "budget_usd": 0.05,  # Estimate per image
    },
    preferences={"models": ["pollinations", "gemini_image", "flux", "omniroute"]}
)

# If Pollinations succeeds → use it (free)
# If Pollinations fails → try Gemini (free API key)
# If Gemini fails → try FLUX (paid, $0.04 per image)
# If FLUX fails → OmniRoute tries 20+ fallback providers

# Log every attempt: {scene_id, model_tried, success, latency_ms, cost_usd}
```

### 4. TTS (Kokoro — local, unlimited, free)
```python
# Route through kokoro_adapter:
from voice_music_factory.tts_cli import generate_speech

for scene in script.scenes:
    audio_path = f"output/{channel}/scene_{i:03d}.wav"
    
    generate_speech(
        text=scene.narration,
        output_path=audio_path,
        voice="default",
        speed=1.25,  # Natural speed (LO/IL kids content: 1.35x, GG/ED: 1.25x)
        volume_db=-20,  # Normalize to -20dB ±2dB
    )
    
# No cost, runs locally, instant
```

### 5. Music Selection & Mixing
```python
# For each scene, assign music from free sources:
from providers.freepd import search_freepd_music
from providers.openverse import search_openverse_audio

music_file = search_music_by_mood(
    mood=scene.mood,  # "epic", "mysterious", "action", "calm"
    duration=scene.duration_seconds,
    source="freepd",  # Falls back to openverse if needed
)

# Mix audio: narration + music + ambience at correct levels
# Narration: -6dB (primary)
# Music: -18dB (background)
# Ambience: -24dB (subtle)
```

### 6. Video Assembly (FFmpeg)
```python
# Route through ffmpeg_adapter:
from ai_router.adapters.ffmpeg_adapter import FFmpegAdapter

ffmpeg = FFmpegAdapter()

# For each scene:
# 1. Ken Burns effect on 4 images (slow pan + zoom)
# 2. Fade transition between scenes
# 3. Layer audio (narration + music + ambience)
# 4. Add captions (optional, but recommended for accessibility)

result = ffmpeg.execute({
    "task_type": "rendering",
    "images": [f"output/{channel}/scene_{i:03d}.png" for i in range(num_scenes)],
    "audio": f"output/{channel}/mixed_audio.wav",
    "captions": f"output/{channel}/captions.vtt",
    "output": f"renders/{channel}/{channel.upper()}_EP001_final.mp4",
    "fps": 30,
    "bitrate": "8000k",  # Quality: 1080p60, good for YouTube
})
```

### 7. Council Quality Checks (MANDATORY before upload)
```bash
# Run all council bots:
council_run.bat

# Bots to monitor:
# ✓ bot_09_audio_check: RMS normalization, no clipping
# ✓ bot_10_frame_inspector: 4 images per scene, correct dimensions, no blanks
# ✓ bot_14_credit_guardian: Did NOT exceed approved budget
# ✓ bot_12_manual_playback: (NEW) Watch 30s of each video, verify:
#   - Visuals match script (not placeholders)
#   - Audio natural (not robotic)
#   - Volume consistent (can hear all scenes)
#   - Transitions smooth (no glitches)

# If ANY bot fails → STOP, report failure, DO NOT upload
# If ALL pass → proceed to upload
```

---

## Execution Order (Parallel Safe)

### Channel Render Sequence (CAN RUN IN PARALLEL)
```
Render 1: GG_EP001
  Scripts: prompts/gods_glory/GG_EP001_thermopylae.json
  Scenes: 12
  Render time: ~20 min (12 scenes × image gen + TTS + assembly)
  No Higgsfield needed (Wikimedia free images)
  Output: renders/gods_glory/GG_EP001_final.mp4

Render 2: ED_EP001
  Scripts: prompts/empire_decoded/ED_EP001_full_script.json
  Scenes: 12–15
  Render time: ~20 min
  No Higgsfield needed (Pollinations diagrams)
  Output: renders/empire_decoded/ED_EP001_final.mp4

Render 3: LO_EP001 (SEQUENTIAL, requires credit estimation)
  Scripts: prompts/little_olympus/LO_EP001_full_script.json
  Scenes: 24
  Render time: ~40 min (24 scenes + Higgsfield + credit checks)
  ⚠️ REQUIRES JOSH APPROVAL FOR HIGGSFIELD CREDITS
  Output: renders/little_olympus/LO_EP001_final.mp4

Render 4: IL_EP001 (SEQUENTIAL, requires credit estimation)
  Scripts: prompts/iron_legends/IL_EP001_full_script.json
  Scenes: 24
  Render time: ~40 min (24 scenes + Higgsfield + credit checks)
  ⚠️ REQUIRES JOSH APPROVAL FOR HIGGSFIELD CREDITS
  Output: renders/iron_legends/IL_EP001_final.mp4

RECOMMENDED:
  1. Start GG + ED in parallel (no Higgsfield needed, fast)
  2. While those render, estimate LO/IL credit cost + get Josh approval
  3. Render LO + IL in parallel (use credit-stretching system)
  4. Run council_run.bat on all 4 outputs
  5. Manual playback verification (Josh watches each)
  6. Upload manually (no auto-upload without Josh approval)
```

---

## File Paths Summary

### Input Scripts
```
C:\Users\jjard\claude\video-bot-pipeline\prompts\gods_glory\GG_EP001_thermopylae.json
C:\Users\jjard\claude\video-bot-pipeline\prompts\little_olympus\LO_EP001_full_script.json
C:\Users\jjard\claude\video-bot-pipeline\prompts\iron_legends\IL_EP001_full_script.json
C:\Users\jjard\claude\video-bot-pipeline\prompts\empire_decoded\ED_EP001_full_script.json
```

### Working Directories (Temporary)
```
C:\Users\jjard\claude\video-bot-pipeline\output\gods_glory\
C:\Users\jjard\claude\video-bot-pipeline\output\little_olympus\
C:\Users\jjard\claude\video-bot-pipeline\output\iron_legends\
C:\Users\jjard\claude\video-bot-pipeline\output\empire_decoded\
```

### Output Videos (Final)
```
C:\Users\jjard\claude\video-bot-pipeline\renders\gods_glory\GG_EP001_final.mp4
C:\Users\jjard\claude\video-bot-pipeline\renders\little_olympus\LO_EP001_final.mp4
C:\Users\jjard\claude\video-bot-pipeline\renders\iron_legends\IL_EP001_final.mp4
C:\Users\jjard\claude\video-bot-pipeline\renders\empire_decoded\ED_EP001_final.mp4
```

### Configuration & Tools
```
C:\Users\jjard\claude\video-bot-pipeline\.env                              # API keys
C:\Users\jjard\claude\video-bot-pipeline\ai_router\router.py              # Central router
C:\Users\jjard\claude\video-bot-pipeline\ai_router\adapters\              # 20+ adapters
C:\Users\jjard\claude\video-bot-pipeline\scene_classifier.py              # Credit estimation
C:\Users\jjard\claude\video-bot-pipeline\episode_credit_planner.py        # Budget optimizer
C:\Users\jjard\claude\video-bot-pipeline\voice-music-factory\tts_cli.py   # Kokoro TTS
C:\Users\jjard\claude\video-bot-pipeline\council_run.bat                  # Quality checks
```

---

## Critical Do's & Don'ts

### DO
- ✅ Read CLAUDE.md + MISSION_BOARD.json before starting
- ✅ Verify OmniRoute is running (localhost:20128)
- ✅ Use ai_router for ALL image/TTS/video tasks (never call providers directly)
- ✅ Estimate LO/IL credit cost BEFORE rendering (dry-run with scene_classifier)
- ✅ Get Josh approval for any Higgsfield spend >$10
- ✅ Run council_run.bat after every render (mandatory QA)
- ✅ Watch 30 seconds of each final video (manual playback verification)
- ✅ Update CLAUDE.md after work completes (what rendered, any issues, next action)

### DON'T
- ❌ Do NOT enable Higgsfield adapter (it's broken, wasted 276 credits in prior render)
- ❌ Do NOT commit .env, renders/, or output/ directories
- ❌ Do NOT use `py` launcher (use full Python path: C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe)
- ❌ Do NOT skip council_run.bat (quality checks are non-negotiable)
- ❌ Do NOT upload videos without Josh's manual verification
- ❌ Do NOT assume Pollinations will always work (fallback chain: Pollinations → Gemini → FLUX → OmniRoute)
- ❌ Do NOT render LO/IL without credit approval (Higgsfield is expensive)

---

## Success Checklist

After completing all 4 renders:

- [ ] GG_EP001_final.mp4 exists (renders/gods_glory/)
- [ ] LO_EP001_final.mp4 exists (renders/little_olympus/) — NO PLACEHOLDERS
- [ ] IL_EP001_final.mp4 exists (renders/iron_legends/) — NO PLACEHOLDERS
- [ ] ED_EP001_final.mp4 exists (renders/empire_decoded/)
- [ ] All 4 videos pass council_run.bat (bot_09, bot_10, bot_14)
- [ ] Manual playback: All 4 videos have natural audio + consistent volume + matching visuals
- [ ] CLAUDE.md updated with render completion + any issues encountered
- [ ] Ready for Josh to manually verify + upload to YouTube

---

## One More Thing

**The Higgsfield Lesson:** Prior render (LO_EP001) wasted 276 credits because the adapter was untested. **DO NOT repeat this.** Before rendering LO/IL:

1. **Estimate credit cost** using scene_classifier.py (5 min)
2. **Show Josh the number** and get explicit approval (1 min)
3. **Dry-run ONE scene** on Pollinations first to confirm pipeline works (5 min)
4. **Then render full episode** with approval (30 min)

This 10-min safety check saves hundreds of dollars.

---

**Ready? Start with GG + ED in parallel, then handle LO/IL. Go.**
