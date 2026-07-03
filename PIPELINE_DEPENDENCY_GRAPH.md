# PIPELINE DEPENDENCY GRAPH
**Viral Engine — Topic → Finished MP4**
*Generated: 2026-07-02*

---

## THE CHAIN (9 stages)

```
TOPIC IDEA
    │
    ▼
[1] RESEARCH ──────────────────────────── ❌ NO FILE
    │                                      Manual / Claude prompt required
    ▼
[2] SCRIPT GENERATION ─────────────────── generate_next_episode.py
    │  Output: episodes/{channel}/{ep}/script.json
    │          prompts/gods_glory/{ep}.final.json
    │  Creates [WRITE: ...] placeholder templates — must be filled before rendering
    ▼
[3] IMAGE GENERATION ──────────────────── generate_images.py
    │  Backends:
    │    • Pollinations.ai (FREE, no key) ──────────── ✅ WORKS
    │    • DALL-E 3 (OPENAI_API_KEY) ─────────────── ❌ KEY NOT SET
    │  Output: images/{episode_id}/scene_01.png … scene_N.png
    │  4 images per scene required (auto_render.py rule)
    ▼
[4] VIDEO GENERATION ──────────────────── providers/
    │  Providers (priority order):
    │    • providers/higgsfield.py  HIGGSFIELD_API_KEY ─── ❌ EMPTY
    │    • providers/kling.py       KLING_API_KEY ─────── ❌ EMPTY
    │    • providers/runway.py      RUNWAY_API_KEY ─────── ❌ EMPTY
    │    • providers/veo.py         VEO_API_KEY ─────────── ❌ EMPTY
    │  FALLBACK: Still image + FFmpeg Ken Burns (zoompan) ─ ✅ ACTIVE
    │  Note: All 4 providers empty → pipeline auto-falls to Ken Burns
    ▼
[5] VOICE GENERATION ──────────────────── voice_video_pipeline.py / auto_render.py
    │  Current TTS_BACKEND = "elevenlabs" (default)
    │  Backends:
    │    • ElevenLabs   ELEVENLABS_API_KEY ─── ❌ PLACEHOLDER ("your_elevenlabs_api_key_here")
    │    • OpenAI TTS   OPENAI_API_KEY ──────── ❌ NOT SET
    │    • edge-tts     TTS_BACKEND=local ────── ✅ FREE, no key, installed
    │  Output: audio/{episode_id}/scene_01.mp3 … scene_N.mp3
    │
    │  ⚠️  DEFAULT WILL FAIL — see MISSING LINK below
    ▼
[6] FFMPEG ASSEMBLY ───────────────────── auto_render.py / voice_video_pipeline.py
    │  Per scene: image + audio → scene_NN.mp4 (zoompan + style filter)
    │  Stitch: all scene clips → stitched.mp4 (xfade transitions)
    │  Music mix: stitched + music → mixed.mp4 (optional)
    │  Loudnorm: 2-pass loudness normalization → {EP}_final.mp4
    │  Output: output/{episode_id}_final.mp4
    │  Status: ✅ WORKS (FFmpeg present per existing renders)
    ▼
[7] SUBTITLE GENERATION ───────────────── caption_finalize_v3.py
    │  Reads: existing final.mp4 + scene_prompts JSON
    │  Burns captions via FFmpeg drawtext (no libass needed)
    │  Output: {EP}_final_captioned.mp4
    │  Status: ✅ WORKS
    │  documentary_render.py has its own built-in PIL subtitle engine
    ▼
[8] THUMBNAIL GENERATION ──────────────── generate_next_episode.py (templates only)
    │  Creates: thumbnail_prompts.md with Higgsfield prompt stubs
    │  Actual generation: Higgsfield ──────────── ❌ NO KEY
    │  Fallback: Manual creation in Canva / generate with DALL-E
    │  Status: ❌ NOT AUTOMATED (templates only)
    ▼
[9] PUBLISHING ────────────────────────── social_machine/councils/youtube/council.py
    │  Bots: YouTubeStrategist → YouTubeWriter → YouTubeClipper → YouTubePoster
    │  Needs: YouTube Data API v3 credentials in social_machine/config.py
    │  Shorts: clips 58s from full episode automatically
    │  Status: ⚠️  CODE EXISTS — credentials unknown
    └──► PUBLISHED TO YOUTUBE
```

---

## FILE RESPONSIBILITY MAP

| Stage | Primary File | Secondary Files | Status |
|-------|-------------|-----------------|--------|
| Research | ❌ NONE | — | Missing |
| Script gen | `generate_next_episode.py` | manual fill or Claude | ✅ Templates exist |
| Image gen | `generate_images.py` | `auto_render.py` (inline) | ✅ Pollinations free |
| Video gen | `providers/higgsfield.py` | `kling.py`, `runway.py`, `veo.py` | ❌ All keys empty → Ken Burns fallback |
| Voice gen | `voice_video_pipeline.py` | `auto_render.py` | ❌ ElevenLabs key placeholder |
| FFmpeg | `auto_render.py` | `voice_video_pipeline.py`, `documentary_render.py` | ✅ Working |
| Subtitles | `caption_finalize_v3.py` | `documentary_render.py` (built-in) | ✅ Working |
| Thumbnails | `generate_next_episode.py` | Higgsfield provider | ❌ No key |
| Publishing | `social_machine/master.py` | `councils/youtube/council.py` | ⚠️ Needs creds |

---

## WHAT'S ALREADY RENDERED

| Channel | Episodes Rendered | Scripts Ready | Gap |
|---------|------------------|---------------|-----|
| GG S1 | EP001–EP005 ✅ | — | — |
| GG S2 | EP006–EP011 ✅ | EP006 broken | Run `render_ep006.bat` |
| GG S3 | ❌ NONE | EP012–EP025 ✅ (26 scripts) | Run `render_season3.bat` |
| ML | EP001 ✅ | EP001 | — |
| LO | ❌ NONE | EP001 | Render pending |

---

## ⚠️  FIRST MISSING LINK — VOICE GENERATION

**The pipeline fails here before it can produce a video.**

**Root cause:** `.env` has `ELEVENLABS_API_KEY=your_elevenlabs_api_key_here` — a placeholder.
`voice_video_pipeline.py` and `auto_render.py` both call `tts_backend()` which returns `"elevenlabs"` by default.
The pipeline will throw `RuntimeError: ELEVENLABS_API_KEY missing` on the first scene.

**Free fix (no API key required):**
Add one line to `.env`:
```
TTS_BACKEND=local
```
This switches the pipeline to `edge-tts` (Microsoft neural TTS, already installed).
Voice: `en-US-GuyNeural` — deep, clear, works for documentary narration.

**To upgrade voice quality later:**
Set `ELEVENLABS_API_KEY` to a real key and remove `TTS_BACKEND=local`.
ElevenLabs voice ID already configured: `JBFqnCBsd6RMkjVDRZzb` (George — cinematic male).

---

## SECOND MISSING LINK — RESEARCH AUTOMATION

No file handles research. `generate_next_episode.py` produces `[WRITE: ...]` placeholder templates.
Someone (Claude, Josh, or a future research bot) must fill in:
- Scene narrations
- Visual prompts per scene

GG S3 scripts are already written (EP012–EP025 in `prompts/gods_glory/`) — so S3 can render now once TTS is fixed.

---

## TO RENDER ONE COMPLETE VIDEO RIGHT NOW

```bash
# Step 1 — Fix TTS (one line in .env)
echo "TTS_BACKEND=local" >> .env

# Step 2 — Render GG S3 (scripts are already written)
render_season3.bat

# Step 3 — Add captions (optional)
python caption_finalize_v3.py --episode GG_EP012

# Step 4 — Publish
python social_machine/master.py --channel gg --episode GG_EP012
```

That's it. **One env var change unlocks the entire render queue.**
