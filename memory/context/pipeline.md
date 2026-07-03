# Pipeline Context
_Last updated: 2026-07-02_

## Autonomous Pipeline (NEW — 2026-07-02)

### Zero-prompt end-to-end command
```
python pipeline_run.py --channel gg
```
Runs all 7 stages without any manual input:
1. `research_agent.py`     → topic discovery + Gemini research + scoring + 24-scene script
2. `generate_images.py`    → Pollinations (free, no key)
3. `voice_video_pipeline.py` → TTS + FFmpeg assembly
4. `caption_finalize_v3.py` → burned captions
5. Thumbnail               → Pollinations (inline in pipeline_run.py)
6. Metadata JSON           → YouTube-ready metadata
7. `social_machine/master.py` → publish

### Resume from a stage
```
python pipeline_run.py --channel gg --start-at images   # skip research
python pipeline_run.py --channel gg --episode GG_EP027  # use existing script
python pipeline_run.py --channel gg --skip-publish      # stop before upload
```

### Research Agent (`research_agent.py`)
- Reads existing `prompts/gods_glory/` to dedup topics automatically
- Evaluates up to 5 candidates per run via Gemini API
- Scoring: Drama(25) + Visual Richness(25) + Historical Accuracy(25) + YouTube Virality(25) = 100
- Reject threshold: 72/100
- Output: fully populated `prompts/gods_glory/scene_prompts.gg_ep027.final.json` (no [WRITE:] placeholders)
- Uses GEMINI_API_KEY from .env (already set)

### TTS Status (CRITICAL)
- ELEVENLABS_API_KEY in .env = placeholder ("your_elevenlabs_api_key_here") — NOT configured
- `pipeline_run.py` auto-detects this and patches .env with `TTS_BACKEND=local` on first run
- Free fallback: edge-tts → `en-US-GuyNeural` voice
- To upgrade: set real ELEVENLABS_API_KEY, remove TTS_BACKEND=local line

### New files added 2026-07-02
- `research_agent.py`          — autonomous research + script generation
- `pipeline_run.py`            — zero-prompt pipeline orchestrator
- `PIPELINE_DEPENDENCY_GRAPH.md` — full stage-by-stage dependency map

---

## Episode JSON Format
```json
{
  "channel": "GG",
  "episode_number": 12,
  "episode_id": "GG_EP012",
  "title": "...",
  "scenes": [
    {
      "scene_number": 1,
      "type": "cold_open",
      "title": "...",
      "duration_sec": 47,
      "narration": "90-120 words",
      "visual_prompt": "Gods & Glory cinematic documentary. [detail]. 16:9.",
      "bg_colors": ["#hex1", "#hex2", "#hex3"]
    }
  ]
}
```

## Scene Types (in order)
cold_open → context → character_intro → historical → battle → pivotal_action →
battle_climax → dramatic → aftermath → analysis → legacy → modern_connection → summary → outro_cta

## Quality Standards
- Full episode: 24 scenes, ~47s avg, 1100-1150s total (~18-20 min)
- Narration: 90-120 words per scene
- Visual prompt: Always starts with "Gods & Glory cinematic documentary."
- bg_colors: Array of 3 hex colors matching scene mood
- No scene/image reuse EVER

## Council Bot State Files
- council/state/render_queue.json — episodes pending/in_progress/done
- council/state/stub_backlog.json — 84 stubs needing full scripts
- council/state/bot_guardian.json — broken episodes list
- council/state/bot_image_healer.json — images needing re-fetch
- council/runs/ — timestamped run logs

## Scheduled Tasks (PAUSED — burned credits)
- check-episode-rebuild-progress: was every 20 min, just a status checker, no output
- legend-empire-pipeline: weekly Monday, Empire Decoded shot lists
Both disabled 2026-06-28. Re-enable only with Josh's explicit approval.

## Known Issues
1. GG_EP006: Pearl Harbor, 21/24 clips are 0KB — needs render_ep006.bat
2. GG_EP007-011: rendered but short (786s, 767s, 655s, 790s, 606s) — under 18 min target
3. 84 stub episodes across all channels awaiting full scripts
