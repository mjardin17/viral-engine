# Claude Code — Render Little Olympus EP001

**Version:** 2026-08-08 | **Priority:** HIGH — First full render with character library  
**Channel:** Little Olympus | **Episode:** LO_EP001 | **Format:** 24 scenes, ~17 min, kids 2–8

---

## Quick Start

```bash
cd C:\Users\jjard\claude\video-bot-pipeline
python C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe empire_render.py --channel LO --episode 1
```

Or manually:

```bash
# 1. Load script
python scene_classifier.py prompts/little_olympus/LO_EP001.json

# 2. Dry-run cost estimate
python episode_credit_planner.py prompts/little_olympus/LO_EP001.json --budget 50

# 3. Render (NO Higgsfield, use free providers only)
python C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe auto_render.py prompts/little_olympus/LO_EP001.json

# 4. Council QA
council_run.bat

# 5. Verify output
ls -lh renders/little_olympus/LO_EP001_final.mp4
```

---

## What This Render Uses

**Character Library:** `characters/little_olympus/` (Zeus, Athena, Poseidon, Hermes, Hestia, Hades, Apollo)

**Script:** `prompts/little_olympus/LO_EP001.json` (24 scenes, ~17 min)

**Image Generation:** 
1. WaveSpeed Desktop (local, unlimited, FREE)
2. Fallback: Pollinations (free web)
3. Fallback: Gemini (free API)

**Video Assembly:**
1. Wan 2.7 (free on Hugging Face, unlimited)
2. Fallback: LTX-Video (free, real-time)
3. Fallback: HyperFrames (local HTML→MP4, free)

**Audio:**
- Kokoro TTS (local, unlimited, FREE) via voice-music-factory/tts_cli.py
- Music: FreePD (free royalty-free library)

**Rendering:**
- FFmpeg (video assembly, local)

**QA:**
- council_run.bat (all 9 bots)

---

## Script Structure

**LO_EP001:** "How Little Zeus Got His Lightning Bolt" (24 scenes)

Each scene:
- Scene number + name
- Scene description
- Character(s) involved (from character library)
- Narration text
- Expected duration (0.5–1 min per scene)

Total expected runtime: ~17 minutes

---

## Execution Flow

### Step 1: Pre-flight Check
```
✓ Script exists at prompts/little_olympus/LO_EP001.json
✓ Character library populated at characters/little_olympus/
✓ Kokoro TTS working (test: voice-music-factory/tts_cli.py --test)
✓ FFmpeg installed and in PATH
✓ OmniRoute running on localhost:20128 (fallback router)
```

### Step 2: Estimate Costs
```bash
python scene_classifier.py prompts/little_olympus/LO_EP001.json
# Expected output:
# Scenes classified into render tiers
# Free: ~20 scenes (Pollinations/Gemini)
# Wan 2.7: ~4 scenes (if needed)
# Higgsfield: 0 (disabled for this render)
```

### Step 3: Render Scenes
For each of the 24 scenes:
1. Load scene prompt
2. Select character from library (Zeus, Athena, etc.)
3. Route image gen: WaveSpeed → Pollinations → Gemini
4. Route video gen: Wan 2.7 → LTX-Video → HyperFrames
5. Generate TTS narration (Kokoro)
6. Log each scene completion

### Step 4: Assembly
```bash
# Compose all 24 scenes + audio + music into one MP4
ffmpeg -f concat -safe 0 -i scene_list.txt -c copy LO_EP001_final.mp4
```

### Step 5: QA
```bash
council_run.bat
# Runs:
# - bot_09_audio_check (RMS normalization, no clipping)
# - bot_10_frame_inspector (4 images per scene, dimensions correct)
# - bot_14_credit_guardian (budget tracking)
# - bot_12_manual_playback (YOU watch first 30 seconds, verify quality)
```

### Step 6: Output
```
renders/little_olympus/LO_EP001_final.mp4
Expected: 400–500MB, ~17 min runtime, kids-friendly 3D animation
```

---

## Critical Rules

### DO
- ✅ Use WaveSpeed for character images (local, unlimited)
- ✅ Use Wan 2.7 for video (free, unlimited)
- ✅ Use Kokoro for TTS (local, unlimited, FREE)
- ✅ Use FreePD for music (free, royalty-free)
- ✅ Run council_run.bat before declaring done
- ✅ Log every step (scene gen, provider selected, cost estimated)
- ✅ Watch the first 30 seconds manually (YOU, not bot — quality check)

### DO NOT
- ❌ Use Higgsfield (save credits for emergencies only)
- ❌ Skip council_run.bat
- ❌ Assume a scene is "done" without bot verification
- ❌ Upload to YouTube without Josh approval
- ❌ Retry failed scenes more than 3x without escalating

---

## Expected Timeline

```
Pre-flight check:        2 min
Cost estimation:         3 min
Render 24 scenes:        40–60 min (parallel where possible)
Assembly:                5 min
Council QA:              10 min
Manual playback check:   5 min
Total:                   ~75–90 min (1.5 hours)
```

---

## Fallback Chain

If Wan 2.7 fails:
1. Try LTX-Video (same quality, fallback from Wan)
2. If LTX fails, try HyperFrames (local, always works)
3. If HyperFrames fails, escalate to Higgsfield (costs credits)

If WaveSpeed image gen fails:
1. Try Pollinations (free web API)
2. If Pollinations fails, try Gemini (free API key)
3. If Gemini fails, escalate to FLUX (costs $)

---

## Success = 

✅ `renders/little_olympus/LO_EP001_final.mp4` exists  
✅ File size 400–500MB  
✅ Duration ~17 minutes  
✅ Audio clear, volume consistent  
✅ Characters visible (no placeholders)  
✅ Council bots all pass  
✅ YOU watched first 30 seconds and confirmed quality  

---

## If Anything Breaks

**Image gen failure?**
→ Check WaveSpeed Desktop is running
→ If not, restart it: `C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe scene_classifier.py --dry-run`

**Video gen failure?**
→ Check Wan 2.7 access (Hugging Face API key in .env)
→ Check internet connection

**Audio failure?**
→ Check Kokoro TTS: `voice-music-factory/tts_cli.py --test "Hello"`

**FFmpeg failure?**
→ Check FFmpeg is installed: `ffmpeg -version`

**Council bot failure?**
→ Run: `council_run.bat --verbose`

---

**GO. Render LO_EP001. Report back when done or when blocked.**
