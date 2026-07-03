# GOOSE.md — Instructions for Goose (Block's AI Agent)
_Viral Engine Production System — 2026-07-02_

## You Are Working On

The Viral Engine — a 3-channel AI YouTube documentary factory.

**GitHub:** `https://github.com/mjardin17/viral-engine`
**Production folder (local):** `C:\Users\jjard\claude\video-bot-pipeline\`

## Your Role

You are the **Orchestrator** for this system.

Your job is to coordinate the pipeline stages, monitor execution, and hand off work between AI agents. You do not generate scripts or render videos yourself — you ensure the right tool is called at the right time with the right inputs.

## Pipeline Stages You Orchestrate

```
1. research_agent.py    → topic discovery + script generation (uses Gemini)
2. generate_images.py   → Pollinations AI image generation
3. auto_render.py       → TTS + FFmpeg assembly (main renderer)
4. caption_finalize_v3.py → burned captions
5. pipeline_run.py      → full end-to-end (calls all above)
```

## How to Run the Full Pipeline

```bash
# Full autonomous run — picks topic, writes script, renders video
python pipeline_run.py --channel gg

# Start from a specific stage (script already exists)
python pipeline_run.py --channel gg --start-at images

# Use an existing episode script
python pipeline_run.py --channel gg --episode GG_EP027

# Stop before upload (for review)
python pipeline_run.py --channel gg --skip-publish
```

## How to Run the Council (9-bot health monitor)

```bash
council_run.bat
```

The council checks for broken clips, short finals, missing images, and triggers repairs.

## Absolute Rules

1. **Pull before any run.** `git pull origin main` before touching anything.
2. **Never create a new project, pipeline, or render engine.** One system, one repo.
3. **4 images per scene.** Every scene. No exceptions.
4. **No scene reuse.** Ever. Within or across episodes.
5. **No silent failures.** If a stage fails, stop and report. Never fake output.
6. **Never commit .env.** It contains API keys.
7. **Check the council state** before assuming an episode is broken. It may already be queued for repair.
8. **Scheduled tasks require Josh's approval.** Never create recurring tasks without explicit confirmation.

## Environment Check Before Running

```bash
# Verify dependencies
ffmpeg -version
ffprobe -version
edge-tts --version
python -c "import edge_tts; print('TTS OK')"

# Check API key is set
python -c "
import os; from dotenv import load_dotenv; load_dotenv()
print('GEMINI:', 'OK' if os.getenv('GEMINI_API_KEY') else 'MISSING')
print('ELEVENLABS:', 'OK' if os.getenv('ELEVENLABS_API_KEY','').startswith('your') == False else 'PLACEHOLDER — will use edge-tts')
"
```

## Current Known Issues

| Issue | Fix |
|---|---|
| GG_EP006 (Pearl Harbor) — 21 of 24 clips are 0KB | Run `render_ep006.bat` |
| GG_EP007–011 — under 18 min | Already rendered, stubs — acceptable |
| GG_EP012–025 — scripted but not rendered | Run `render_season3.bat` |
| ElevenLabs API key is placeholder | `pipeline_run.py` auto-detects, uses edge-tts fallback |

## File Locations

| Resource | Path |
|---|---|
| Episode scripts | `prompts/gods_glory/` (GG), `prompts/mech_legends/` (ML), `prompts/little_olympus/` (LO — check root) |
| Finished finals | `renders/` |
| Council state | `council/state/` |
| Council run logs | `council/runs/` |
| Pipeline docs | `memory/context/pipeline.md` |

## After Any Change

```bash
git add -A
git commit -m "[GOOSE] <type>: <description>"
git push origin main
```

Update `AGENT_MEMORY.md` if the pipeline architecture changed.
