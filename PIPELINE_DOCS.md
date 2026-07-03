# VIRAL ENGINE — COMPLETE PIPELINE DOCUMENTATION
**From Idea to Published Video**
*Version 1.0 · June 2026*

---

## TABLE OF CONTENTS

1. [System Overview](#1-system-overview)
2. [Folder Structure](#2-folder-structure)
3. [Phase 1: Idea & Script](#3-phase-1-idea--script)
4. [Phase 2: Asset Generation](#4-phase-2-asset-generation)
5. [Phase 3: Render](#5-phase-3-render)
6. [Phase 4: Post-Production](#6-phase-4-post-production)
7. [Phase 5: Upload & Publish](#7-phase-5-upload--publish)
8. [GENERATE_NEXT_EPISODE Command](#8-generate_next_episode-command)
9. [Render Engine Reference](#9-render-engine-reference)
10. [Troubleshooting](#10-troubleshooting)
11. [Roadmap](#11-roadmap)

---

## 1. SYSTEM OVERVIEW

### What This Pipeline Does
The Viral Engine pipeline takes an episode concept and produces a publish-ready YouTube video — automatically. It handles scene generation, background art, character drawings, subtitles, music synthesis, and video assembly.

### Three Channels, One Pipeline

| Channel | Style | Renderer | Scene Count |
|---------|-------|----------|-------------|
| Little Olympus | Bright kids cartoon | `little_olympus_render.py` | 7 scenes × 9s |
| Mech Legends | Cinematic action anime | `mech_legends_render.py` | 10 scenes × 9s |
| Gods & Glory | Epic documentary | `documentary_render.py` | 6 scenes × 60s |

### Current Capabilities
- ✅ Full automated video assembly (FFmpeg)
- ✅ Scene background generation (PIL/Pillow)
- ✅ Character illustration (PIL procedural drawing)
- ✅ Music synthesis (NumPy, AAC)
- ✅ SRT subtitle generation + burn-in
- ✅ Zoompan camera motion (for clips ≤12s)
- ✅ Title card + end card
- ✅ Batch scene rendering with resume support
- ⬜ Real character art (Higgsfield — needs credits)
- ⬜ Voiceover (ElevenLabs — needs API key)
- ⬜ Thumbnail generation (Higgsfield — needs credits)

---

## 2. FOLDER STRUCTURE

```
video-bot-pipeline/
│
├── MASTER_OPS_DASHBOARD.md        ← Complete pipeline audit
├── PIPELINE_DOCS.md               ← This file
├── CHECKPOINT.md                  ← Project state snapshot
├── generate_next_episode.py       ← Master pipeline command
│
├── ── CHANNEL BIBLES ──
├── Little_Olympus_Master_Bible.md ← Full LO creative bible
├── viral_engine_bible.json        ← All channels master brand
├── iron_legends_bible.json        ← Legacy (keep for reference)
│
├── ── RENDER ENGINES ──
├── little_olympus_render.py       ← LO renderer
├── mech_legends_render.py         ← ML renderer
├── documentary_render.py          ← GG renderer
├── il_batch_render.py             ← Batch runner
│
├── ── EPISODE SCRIPTS ──
├── prompts/
│   ├── scene_prompts.lo_ep001.final.json
│   ├── scene_prompts.lo_ep002.final.json
│   ├── scene_prompts.ml_ep001.final.json
│   ├── scene_prompts.ml_ep002.final.json
│   ├── scene_prompts.ep006-015.final.json  ← Gods & Glory scripts
│   └── ...
│
├── ── EPISODE PACKAGES (standardized) ──
├── episodes/
│   ├── lo/
│   │   ├── lo_ep001/
│   │   │   ├── script.json
│   │   │   ├── voice_script.md
│   │   │   ├── thumbnail_prompts.md
│   │   │   ├── metadata.json
│   │   │   ├── render_job.json
│   │   │   └── README.md
│   │   └── lo_ep002/ ...
│   ├── ml/
│   │   └── ...
│   └── gg/
│       └── ...
│
├── ── RENDERED OUTPUT ──
├── renders/
│   ├── little_olympus/
│   │   ├── lo_ep001.mp4           ← Upload-ready
│   │   ├── lo_ep002.mp4           ← Upload-ready
│   │   └── _work_lo_ep001/        ← Scene working files
│   ├── mech_legends/
│   │   ├── ml_ep001.mp4
│   │   ├── ml_ep002.mp4
│   │   └── _work_ml_ep001/
│   └── thermopylae_final.mp4      ← GG EP005
│
├── ── LAUNCH PACKAGES ──
├── gods_and_glory_launch/
│   ├── channel_copy.md            ← YouTube About tab copy
│   └── episode_titles_and_descriptions.md
├── little_olympus_launch/
│   └── channel_copy.md
├── mech_legends_launch/
│   └── channel_copy.md
│
└── _backups/                      ← ALL files backed up here
    ├── <name>.latest.<ext>        ← Most recent copy
    └── <name>.<UTC-timestamp>.<ext>
```

### The 3x Backup Rule
**Every file saved must be saved three times:**
1. Primary location (the real file)
2. `_backups/<name>.latest.<ext>` — always the most recent version
3. `_backups/<name>.<UTC-timestamp>.<ext>` — permanent point-in-time snapshot

This is enforced for all scripts, bibles, render outputs, and episode packages.

---

## 3. PHASE 1: IDEA & SCRIPT

### Step 1.1 — Choose Episode Concept
Reference the appropriate channel bible:
- **Little Olympus:** `Little_Olympus_Master_Bible.md` — Season 1 episode guide (20 episodes outlined)
- **Mech Legends:** `viral_engine_bible.json` — character bibles + story rules
- **Gods & Glory:** `viral_engine_bible.json` — historical battle timeline

### Step 1.2 — Run GENERATE_NEXT_EPISODE
```bash
python3 generate_next_episode.py --channel lo
# or
python3 generate_next_episode.py --channel ml --title "GRANITE's Sacrifice"
```

This creates `episodes/<channel>/<ep_id>/` with templated files for all assets.

### Step 1.3 — Fill in the Script
Open `episodes/<channel>/<ep_id>/script.json` and fill in every `[WRITE: ...]` placeholder:

| Field | What to write |
|-------|--------------|
| `narration` | 25–35 words. Match the narrator tone. |
| `visual_prompt` | What the viewer sees. Aesthetic + characters + action + colors. |
| `higgsfield_prompt` | Optimized for Higgsfield AI image generation. |
| `lesson` | The episode's core takeaway (1 sentence). |
| `youtube_title` | Hook + emoji + episode number. Under 60 chars. |
| `youtube_description` | 3–5 paras + bullet beats + hashtags. |

### Script Rules by Channel

**Little Olympus:**
- 7 scenes: hook → setup → problem → attempt → solution → resolution → lesson_and_cta
- Narration: warm, playful, 2nd-person ("you"), never condescending
- Lesson emerges from action — never stated directly before it's earned
- Every episode: Baby Hercules breaks something, Athena taps chin 3x, Archie looks at camera

**Mech Legends:**
- 10 scenes: cold_open → hero_intro → villain_intro → villain_dominance → battle_attempt → darkest_moment → crisis → turning_point → hero_action → cliffhanger
- RUMBLE must dominate scenes 1–6. Heroes win in 7–9. Scene 10 is always ominous.
- Victory must feel hard-earned and precarious. RUMBLE always learns something.

**Gods & Glory:**
- 6 scenes: cold_open → historical_context → key_players → rising_tension → climax → aftermath
- Narration: documentary gravitas. Present tense for historical events.
- End with what this battle changed for all time.

---

## 4. PHASE 2: ASSET GENERATION

### Step 2.1 — Voice Script
Once script.json is complete, update `voice_script.md`:
- Copy narration from each scene
- Assign ElevenLabs voice ID per character
- Set stability/similarity/style values

**ElevenLabs integration (when configured):**
```bash
# Coming: auto-generate audio from voice_script.md
python3 generate_voice.py --ep lo_ep003
```

### Step 2.2 — Character Art (Higgsfield)
1. Open `thumbnail_prompts.md` for the episode
2. Copy each `higgsfield_prompt` block
3. Generate in Higgsfield (requires credits)
4. Save output to `episodes/<channel>/<ep_id>/art/`
5. Scene stills go into render working directory

**Current workaround (0 credits):** PIL procedural drawings are used automatically by renderers.

### Step 2.3 — Thumbnails
1. Generate Higgsfield image using thumbnail_prompts.md
2. Open in Canva
3. Add text overlay per spec
4. Export as JPG 1280×720
5. Save to `episodes/<channel>/<ep_id>/thumbnail.jpg`

**Canva workaround (no Higgsfield):**
- Use Canva free stock image + text overlay
- Title text + character emoji or color block

---

## 5. PHASE 3: RENDER

### Render Command Pattern
```bash
# Render in 2-scene batches (never more — 44s bash timeout)
python3 little_olympus_render.py --ep lo_ep003 --scenes 1-2
python3 little_olympus_render.py --ep lo_ep003 --scenes 3-4
python3 little_olympus_render.py --ep lo_ep003 --scenes 5-6
python3 little_olympus_render.py --ep lo_ep003 --scenes 7-7
python3 little_olympus_render.py --ep lo_ep003 --concat

# Or use the auto-render shortcut:
python3 generate_next_episode.py --render-next lo
```

### What the Renderer Does (per scene)
1. **Background** — PIL gradient + clouds/stars/terrain per scene type
2. **Character drawing** — PIL procedural character per scene type
3. **Composite** — Background + character layers merged
4. **Camera motion** — zoompan (≤12s clips) or static (>12s)
5. **Music** — NumPy synthesized AAC audio
6. **Subtitles** — Narration split into ~7-word chunks, timed, burned in
7. **Scene final** — All layers muxed into scene_NN_final.mp4

### What `--concat` Does
1. Renders title card (episode title + tagline)
2. Assembles: title → scene_01 → scene_02 → ... → scene_N → end card
3. Outputs final: `renders/<channel>/<ep_id>.mp4`

### Working File Location
```
renders/little_olympus/_work_lo_ep003/
  scene_01_bg.png        ← background still
  scene_01_char.png      ← character still
  scene_01_clip.mp4      ← zoompan clip (no audio)
  scene_01_music.aac     ← synthesized audio
  scene_01.srt           ← subtitle file
  scene_01_subbed.mp4    ← clip + subtitles
  scene_01_final.mp4     ← scene_01_subbed + audio (DONE)
```

### Corrupted MP4 Fix
If a scene produces "moov atom not found" error:
```bash
rm -f renders/<channel>/_work_<ep_id>/scene_NN_{clip,subbed,final}.mp4
# Then re-render that scene alone
python3 <renderer>.py --ep <ep_id> --scenes N-N
```

### Status Check
```bash
python3 mech_legends_render.py --ep ml_ep003 --status
```

---

## 6. PHASE 4: POST-PRODUCTION

### Current (automated)
- ✅ Subtitles burned in
- ✅ Music mixed under narration
- ✅ Title card + end card

### Planned (when ElevenLabs is configured)
- Real voiceover replaces subtitle-only
- Character voice lines per scene
- Music ducked under voice automatically

### Thumbnail
- Add to video at upload time (YouTube allows changing post-upload)
- A/B test: upload 2 thumbnails, switch after 48 hours if CTR < 5%

---

## 7. PHASE 5: UPLOAD & PUBLISH

### Pre-Upload Checklist
- [ ] Final MP4 in `renders/<channel>/<ep_id>.mp4`
- [ ] Thumbnail ready (JPG 1280×720)
- [ ] `metadata.json` filled out (title, description, tags)
- [ ] YouTube channel exists
- [ ] Channel banner and icon set

### Upload Steps (manual — YouTube Studio)
1. Go to studio.youtube.com
2. Click **Create → Upload video**
3. Select the MP4 file
4. Paste title from `metadata.json → youtube_title`
5. Paste description from `metadata.json → youtube_description`
6. Add tags from `metadata.json → tags`
7. Upload thumbnail from `episodes/<channel>/<ep_id>/thumbnail.jpg`
8. Set audience:
   - Little Olympus: **Yes, made for kids**
   - Mech Legends: **Yes, made for kids**
   - Gods & Glory: **No, not made for kids**
9. Add to playlist
10. Set as channel trailer if EP001
11. Publish or schedule

### Publishing Cadence
- **Target:** 1 video per channel per week
- **Ideal schedule:** Monday (LO) · Wednesday (ML) · Friday (GG)
- **Minimum:** 1 video per week total to maintain algorithm presence

---

## 8. GENERATE_NEXT_EPISODE COMMAND

### Full Reference
```bash
# Show status of all channels
python3 generate_next_episode.py --status

# Generate next episode package (auto-detects EP number)
python3 generate_next_episode.py --channel lo
python3 generate_next_episode.py --channel ml
python3 generate_next_episode.py --channel gg

# Generate with specific episode number and title
python3 generate_next_episode.py --channel lo --ep 3 --title "Perseus and the Tiny Medusa"

# Generate with logline
python3 generate_next_episode.py --channel ml --title "GRANITE's Sacrifice" \
  --logline "RUMBLE knows the pattern now. And he's coming for GRANITE first."

# Find and render the next unrendered episode
python3 generate_next_episode.py --render-next lo
python3 generate_next_episode.py --render-next ml
```

### What It Generates
```
episodes/<channel>/<ep_id>/
├── README.md              ← What to do next
├── script.json            ← Scene prompts template (fill in [WRITE: ...])
├── voice_script.md        ← ElevenLabs-ready voice script
├── thumbnail_prompts.md   ← Higgsfield + Canva specs
├── metadata.json          ← YouTube title/description/tags
└── render_job.json        ← Ordered render commands
```

### Script JSON Structure
```json
{
  "channel": "Little Olympus",
  "episode_id": "LO_EP003",
  "title": "Perseus and the Tiny Medusa",
  "scenes": [
    {
      "scene_number": 1,
      "type": "hook",
      "narration": "[WRITE: narration here]",
      "visual_prompt": "[WRITE: visual description]",
      "higgsfield_prompt": "[WRITE: Higgsfield prompt]",
      "bg_colors": ["#FFD700", "#1A1060", "#00B4E6"],
      "camera": "pull_back",
      "duration_sec": 9
    }
  ],
  "lesson": "[WRITE: episode lesson]",
  "youtube_title": "[WRITE: title]",
  "youtube_description": "[WRITE: description]"
}
```

---

## 9. RENDER ENGINE REFERENCE

### little_olympus_render.py

**Scene types and what they draw:**
| Type | Background | Character |
|------|------------|-----------|
| `hook` | Sunrise sky + Olympus ground | Little Zeus with thunderbolt |
| `setup` | Garden + bright green | Baby Hercules with mountain |
| `clue` / `solution` | Blue-grey sky | Athena pointing + Archie |
| `problem` | Storm clouds + deep purple | Villain of the week |
| `attempt` | Action sky | Group scene |
| `resolution` | Warm golden sky | Full group celebration |
| `lesson_and_cta` | Deep blue + gold | Full group waving |

**Music:** C-major xylophone melody, 120bpm, NumPy WAV → AAC

**Key functions:**
```python
make_sky_background(scene, out)     # PIL gradient + clouds + Olympus
make_character_card(char_type, out) # PIL character drawing
generate_kids_music(duration, out)  # NumPy → WAV → AAC
still_to_video(still, out, dur)     # zoompan or static FFmpeg
render_scene(scene, work_dir, ep)   # full scene pipeline
```

### mech_legends_render.py

**Scene types:**
| Type | Composition |
|------|-------------|
| `cold_open` | Energy lines + darkness |
| `hero_intro` | BLAZE centered, red energy |
| `team_intro` | STORM + GRANITE + BLAZE split |
| `villain_intro` | RUMBLE + BOLT, dark bg |
| `villain_dominance` | RUMBLE alone, dominant scale |
| `crisis` | RUMBLE holding tiny BLAZE |
| `darkest_moment` | Three heroes fallen, BOLT dancing |
| `turning_point` | BLAZE rising with glow rings |
| `hero_action` | Multi-panel action split |
| `cliffhanger` | Standoff: 3 heroes vs RUMBLE+BOLT |

**Music:** 140bpm sawtooth bass + square lead, kick every 4 beats, NumPy → AAC

**Mech drawing:**
```python
draw_mech(draw, cx, cy, color, scale=1.0, style="hero")
# style="hero"    → standard toyetic robot (BLAZE/STORM/GRANITE)
# style="villain" → RUMBLE: 1.6x scale, 4 arms, crown spikes, red eyes
# style="sidekick"→ BOLT: 0.6x scale, lightning bolt markings
```

### documentary_render.py
- Used for Gods & Glory
- Longer scenes (60s)
- Pan/zoom across historical still images
- Documentary-style lower thirds
- Orchestral music (planned)

---

## 10. TROUBLESHOOTING

### "moov atom not found" / Corrupted MP4
**Cause:** FFmpeg killed mid-write by 44s bash timeout.
**Fix:**
```bash
rm -f renders/<channel>/_work_<ep_id>/scene_NN_{clip,subbed,final}.mp4
python3 <renderer>.py --ep <ep_id> --scenes N-N
```
**Prevention:** Never render more than 2 scenes per bash call.

### Scene shows "already done" but file missing
**Cause:** Mount staleness — the file exists in the mount cache but wasn't written.
**Fix:** Delete the work directory for that scene and re-render.

### "0.0s" render time on completed scene
**Not a bug.** This means the scene was already rendered and the renderer skipped it (correct behavior). The `✓ already done` message confirms the file exists.

### episode_state.json backup fails via bash cp
**Cause:** Mount staleness — `cp` in bash may read stale cached file.
**Fix:** Always use the Write tool (not bash) for episode_state.json backups.

### Subtitles not appearing
**Cause:** SRT file empty or FFmpeg subtitle filter path issue.
**Fix:** Check `scene_NN.srt` in work dir. If empty, narration field was blank in script JSON.

### Music sounds wrong
**Cause:** NumPy music uses hard-coded C-major scales. Different scene types get different note patterns.
**Note:** This is expected behavior for the PIL/NumPy draft render. ElevenLabs + licensed music will replace this at launch quality.

---

## 11. ROADMAP

### Current State (June 2026)
- 3 channels built and scripted
- 5 episodes rendered (PIL/NumPy draft quality)
- Full episode package system deployed
- All launch copy ready

### Phase 2 — Quality Upgrade (Next 30 days)
- [ ] Top up Higgsfield credits → real character art for all 3 channels
- [ ] Configure ElevenLabs → real narration voiceover
- [ ] Re-render all episodes with real assets
- [ ] Create YouTube channels + upload all 5 episodes
- [ ] Generate thumbnails

### Phase 3 — Content Scale (Month 2–3)
- [ ] Reach 20 episode backlog across all channels
- [ ] Automate thumbnail generation via Higgsfield API
- [ ] Build intro/outro bumpers
- [ ] Schedule episodes 2 weeks ahead

### Phase 4 — Monetization (Month 6–12)
- [ ] YouTube Partner Program (1K subscribers + 4K watch hours)
- [ ] First brand deal outreach at 10K subscribers
- [ ] Viral Engine sponsor pitch deck
- [ ] Merchandise pilot (print-on-demand)

### Phase 5 — IP Development (Year 2–3)
- [ ] Mech Legends toy prototype
- [ ] Amazon Kids+ / Kidoodle licensing pitch
- [ ] Little Olympus children's book series
- [ ] IP acquisition conversations

### Phase 6 — Exit (Year 3–5)
- [ ] Full IP acquisition by Hasbro / Moonbug / private equity
- [ ] Target: $50M–$500M based on Moonbug comps (paid $3B for CoComelon)

---

*VIRAL ENGINE PIPELINE DOCS v1.0 · 2026-06-16*
*All three channels. One pipeline. Idea to published video.*
