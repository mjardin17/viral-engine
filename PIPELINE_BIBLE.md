# Viral Engine — Video Pipeline Bible

## What This System Does
Fully automated AI YouTube documentary pipeline. Input: a topic. Output: a finished 18-20 minute MP4 episode with narration, images, music, and Ken Burns motion effects — ready to upload.

---

## Stack
- **Python 3** — core scripting language
- **edge-tts** — Microsoft neural TTS (free, high quality)
- **FFmpeg** — video rendering, Ken Burns zoom/pan, audio mixing
- **Pollinations.ai** — free AI image generation (primary)
- **Google Gemini** — image generation fallback (GEMINI_API_KEY env var)
- **battle_epic.mp3** — background music, mixed at 0.08 volume

---

## Episode Format (JSON Script)

Every episode is a JSON file with 24 scenes. Each scene has:

```json
{
  "scene_number": 1,
  "type": "cold_open",
  "title": "Scene Title",
  "duration_sec": 47,
  "narration": "90-120 words of spoken narration for this scene.",
  "visual_prompt": "Detailed image generation prompt. Gods & Glory cinematic documentary style. 16:9.",
  "bg_colors": ["#1A1A2E", "#C9A227", "#8B1A1A"]
}
```

**Scene types (in order):**
cold_open → context → character_intro → historical → battle → pivotal_action → battle_climax → aftermath → analysis → legacy → modern_connection → summary → outro_cta

**Episode structure:**
- 24 scenes × ~47s average = ~18-20 min total
- Minimum 600s total duration to qualify as "full" (not a stub)
- 4 images generated per scene (scene_NN_1.jpg through scene_NN_4.jpg)

**Full episode JSON wrapper:**
```json
{
  "channel": "GG",
  "episode_number": 1,
  "episode_id": "GG_EP001",
  "title": "Episode Title",
  "subtitle": "Subtitle",
  "tagline": "One-line hook",
  "duration_target_sec": 1150,
  "viral_hook": "The thing that makes someone click",
  "youtube_title": "SEO-optimized YouTube title",
  "lesson": "What the viewer takes away",
  "highlight_scene": 12,
  "scenes": [ ... ]
}
```

---

## Pipeline Flow (auto_render.py)

```
1. LOAD SCRIPT
   └── find_episode_json(episode_id)
       └── searches prompts/**/*.json
       └── gods_glory/ subdirectory takes priority (full scripts win over stubs)

2. FOR EACH SCENE:
   a. GENERATE 4 IMAGES
      └── Pollinations API (3 attempts per image)
      └── Fallback → Gemini if image < 20KB
      └── Saved as: output/GG_EP001/scene_01_1.jpg through scene_01_4.jpg

   b. GENERATE NARRATION AUDIO
      └── edge-tts (en-US-GuyNeural voice)
      └── Saved as: output/GG_EP001/scene_01.mp3

   c. RENDER SCENE CLIP
      └── FFmpeg Ken Burns filter_complex
      └── 4 images × (duration/4) seconds each
      └── Zoom/pan motion on each image
      └── Audio synced to images
      └── Saved as: output/GG_EP001/scene_01.mp4

3. CONCAT ALL CLIPS
   └── FFmpeg concat demuxer
   └── Saved as: output/GG_EP001/GG_EP001_concat.mp4

4. MIX MUSIC
   └── battle_epic.mp3 at 0.08 volume
   └── Mixed under narration
   └── Saved as: output/GG_EP001/GG_EP001_final.mp4

5. DONE — episode ready to upload
```

---

## File Structure

```
video-bot-pipeline/
├── auto_render.py              ← Core pipeline (run this)
├── patch_fallbacks.py          ← Fix broken/tiny images
├── script_guard.py             ← Protect scripts from stub downgrades
├── script_registry.json        ← Registry of approved full scripts
├── render_ep006.bat            ← Re-render broken EP006
├── council_run.bat             ← Launch all 9 council bots
├── assets/
│   └── battle_epic.mp3         ← Background music
├── prompts/
│   ├── gods_glory/             ← Full GG episode scripts (24 scenes each)
│   │   ├── scene_prompts.gg_ep001.final.json
│   │   ├── scene_prompts.gg_ep002.final.json
│   │   └── ... (EP001–EP020 exist, EP021–025 pending)
│   ├── machine_learning/       ← ML channel scripts
│   └── little_olympus/         ← LO channel scripts
├── output/
│   ├── GG_EP001/               ← Images, clips, final MP4
│   ├── GG_EP002/
│   └── ...
└── council/                    ← Self-healing bot system
    ├── council.py
    ├── bot_base.py
    ├── bots/
    │   ├── bot_01_guardian.py
    │   ├── bot_02_script_guard.py
    │   ├── bot_03_image_healer.py
    │   ├── bot_04_clip_rebuilder.py
    │   ├── bot_05_final_assembler.py
    │   ├── bot_06_render_queue.py
    │   ├── bot_07_stub_expander.py
    │   ├── bot_08_auto_renderer.py
    │   └── bot_09_quality_checker.py
    └── state/                  ← Bot state JSON files
```

---

## How to Run

```bash
# Render one episode
py auto_render.py --episode GG_EP001 --music battle_epic.mp3

# Run all 9 council bots (self-healing check)
council_run.bat

# Re-render broken EP006
render_ep006.bat

# Check/register scripts
py script_guard.py --audit
py script_guard.py --register
```

---

## Channels

| ID | Name | Style |
|----|------|-------|
| GG | Gods & Glory | History/battle documentaries. Dark cinematic. Gold/black palette. |
| ML | Machine Learning | Second channel (TBD) |
| LO | Little Olympus | Kid-friendly mythology. Little Zeus. |

---

## Current Episode Status

| Episode | Title | Status |
|---------|-------|--------|
| GG EP001 | Thermopylae | ✅ Final rendered (1219s) |
| GG EP002 | Alexander the Great | ✅ Final rendered (1186s) |
| GG EP003 | Julius Caesar | ✅ Final rendered (1124s) |
| GG EP004 | Genghis Khan | ✅ Final rendered (1150s) |
| GG EP005 | Spartans | ✅ Final rendered (941s) |
| GG EP006 | Pearl Harbor | ❌ BROKEN — 21 empty clips, needs re-render |
| GG EP007–011 | WWII series | ⚠️ Rendered but short (stubs) |
| GG EP012–020 | Season 3 | ✅ Scripts written, not yet rendered |
| GG EP021–025 | Season 3 | ⏳ Scripts still needed |

---

## Council Bot System

9 self-healing bots that run automatically and fix pipeline failures:

| Bot | What It Does |
|-----|-------------|
| bot_01_guardian | Scans for broken/tiny clips, short finals |
| bot_02_script_guard | Prevents stub scripts from being re-rendered |
| bot_03_image_healer | Re-fetches images under 20KB |
| bot_04_clip_rebuilder | Re-renders 0KB video clips |
| bot_05_final_assembler | Rebuilds final MP4 from good clips |
| bot_06_render_queue | Tracks what's ready to render next |
| bot_07_stub_expander | Tracks 84 stub episodes needing full scripts |
| bot_08_auto_renderer | Renders 1 episode per run automatically |
| bot_09_quality_checker | ffprobe duration + audio RMS validation |

---

## Image Generation Rules
- 4 unique images per scene — NO reuse within or across episodes
- Primary: Pollinations.ai (free, no key needed)
- Fallback: Gemini (requires GEMINI_API_KEY in environment)
- Min size: 20KB — anything smaller is re-fetched automatically
- Prompt style: "Gods & Glory cinematic documentary. [scene description]. 16:9."

---

## Quality Standards
- Full episode: 24 scenes, ≥600s total duration
- Stub (unusable): <10 scenes or <600s
- Each clip must be >500KB
- Final MP4 must be >300s
- Audio RMS must be > -40.0 dBFS (not silent)
