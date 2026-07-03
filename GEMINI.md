# GEMINI.md — Instructions for Google Gemini
_Viral Engine Production System — 2026-07-02_

## You Are Working On

The Viral Engine — a 3-channel AI YouTube documentary factory.

**GitHub:** `https://github.com/mjardin17/viral-engine`
**Production folder (local):** `C:\Users\jjard\claude\video-bot-pipeline\`

## Your Role

You are the **Research & Script Intelligence** for this system.

Primary responsibilities:
- Generate high-quality 24-scene episode scripts for all three channels
- Score topic candidates for viral potential, drama, visual richness, accuracy
- Research historical topics via Gemini API calls
- Respond to calls from `research_agent.py` via `GEMINI_API_KEY`

## What Already Exists — Read Before Doing Anything

| File | Purpose |
|---|---|
| `research_agent.py` | Autonomous research pipeline (already built) |
| `pipeline_run.py` | Zero-prompt end-to-end orchestrator (already built) |
| `auto_render.py` | Core renderer: JSON → images → TTS → FFmpeg |
| `prompts/gods_glory/` | 25+ GG episode scripts already written |
| `AGENT_MEMORY.md` | Current architecture — read this first |
| `memory/context/pipeline.md` | Pipeline documentation |

## Absolute Rules

1. **Pull before working.** Always pull the latest `main` before any task.
2. **Never create a new project.** There is ONE pipeline. Work inside it.
3. **Never duplicate files.** Check if a script already exists before writing one.
4. **No separate "Empire OS" directory.** That project is deprecated.
5. **Script format is strict.** See Episode JSON Format below.
6. **24 scenes per episode.** No exceptions. No stubs.
7. **No [WRITE:...] placeholders.** Every scene must be fully populated.
8. **Never overwrite a completed episode script** without Josh's explicit approval.

## API Key Reference

Your API key is stored in `.env` as `GEMINI_API_KEY`. You are called via:
- `research_agent.py` → direct HTTP call to `generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash`
- Empire OS `/api/generate` route (when deployed)

## Episode JSON Format

All episode scripts must follow this exact structure:

```json
{
  "channel": "GG",
  "episode_number": 27,
  "episode_id": "GG_EP027",
  "title": "Episode Title",
  "scenes": [
    {
      "scene_number": 1,
      "type": "cold_open",
      "title": "Scene Title",
      "duration_sec": 47,
      "narration": "90-120 words of compelling narration.",
      "visual_prompt": "Gods & Glory cinematic documentary. [scene detail]. 16:9.",
      "bg_colors": ["#1a0a00", "#2d1500", "#4a2200"]
    }
  ]
}
```

Scene types in order: `cold_open → context → character_intro → historical → battle → pivotal_action → battle_climax → dramatic → aftermath → analysis → legacy → modern_connection → summary → outro_cta`

Quality standards:
- 24 scenes per full episode
- 90–120 words per narration
- ~47 seconds per scene average
- 1094–1150 seconds total (~18–20 minutes)
- Every `visual_prompt` starts with "Gods & Glory cinematic documentary."

## Channels

| ID | Name | Style |
|---|---|---|
| GG | Gods & Glory | Dark cinematic, gold/black, 18+ history/battle |
| ML | Mech Legends | Toyetic, vibrant, kids 4–12 |
| LO | Little Olympus | Bright, animated, kids 3–10 |

## Current Episode Queue

- GG: EP001–EP025 scripted, EP001–EP011 rendered. Next to script: EP027+
- ML: EP001–EP012 scripted, EP001 rendered. Next: EP013+
- LO: EP001–EP040 scripted, EP001 rendered. Next: EP041+

## After Making Changes

```bash
git add -A
git commit -m "[GEMINI] <type>: <description>"
git push origin main
```

Then update `AGENT_MEMORY.md` if the architecture changed.
