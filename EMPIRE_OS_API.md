# Empire OS — Viral Engine API Contract
**Base URL:** `http://localhost:5757`
**Start:** double-click `empire_api.bat`

---

## Health Check
```
GET /health
```
Returns pipeline state, active renders, completed episodes, Ollama + Gemini status.

---

## Render Control

### Start a Render
```
POST /render/start
{ "episode_id": "GG_EP012", "music": true, "skip_images": false }
```
- `music` (default true) — mix battle_epic.mp3 into final
- `skip_images` (default false) — reuse cached images from output/

Response: `{ "status": "started", "episode_id": "GG_EP012", "pid": 12345 }`

### Check Status
```
GET /render/status/GG_EP012
```
Returns: `{ "state": "running|done|failed|cancelled", "scenes_done": 14, "elapsed_sec": 3240, "output_path": "..." }`

States:
- `running` — actively rendering scenes
- `finalizing` — concat/music mix in progress
- `done` — final MP4 ready in renders/
- `failed` — check log for errors
- `unknown` — no record found

### Tail the Log
```
GET /render/log/GG_EP012?lines=100
```
Returns last N lines of stdout from auto_render.py.

### Cancel
```
POST /render/cancel/GG_EP012
```

---

## Outputs

### List All Completed Finals
```
GET /outputs
```
Returns all files in renders/ > 1MB with episode metadata.

```json
{
  "count": 11,
  "episodes": [
    {
      "episode_id": "GG_EP001",
      "path": "C:\\...\\renders\\GG_EP001_final.mp4",
      "size_mb": 254.5,
      "title": "Thermopylae: The 300 Who Held the Gates of Fire",
      "youtube_title": "Battle of Thermopylae 480 BC: ..."
    }
  ]
}
```

---

## Publish (CrossPost)

### Queue for Publishing
```
POST /publish/GG_EP012
{ "platforms": ["youtube", "tiktok", "instagram"] }
```
Writes a job to `crosspost_queue/` and returns the job metadata.
CrossPost agent monitors `crosspost_queue/` and dispatches.

Configure CrossPost: edit `crosspost_config.json` with your API URL and keys.

### View Queue
```
GET /crosspost/queue
```

---

## Ollama — Local Prompt Refinement

### Refine a Scene
```
POST /ollama/refine
{
  "visual_prompt": "Gods & Glory cinematic...",
  "narration": "September 1944...",
  "scene_type": "battle",
  "episode_title": "Operation Market Garden"
}
```
Returns refined `visual_prompt` and `narration`.

### Check Ollama
```
GET /ollama/status
```
Returns available models and connection status.

**Empire OS workflow:**
1. Load episode JSON
2. For each scene: POST /ollama/refine → get improved prompts
3. Write refined JSON to prompts/gods_glory/
4. POST /render/start with refined episode

---

## Gemini — Research

### Research a Topic
```
POST /gemini/research
{ "topic": "Battle of Waterloo 1815", "num_facts": 10 }
```
Returns structured facts for Empire OS to inject into scene narration.
Requires `GEMINI_API_KEY` env var.

### Verify Episode Accuracy
```
POST /gemini/enrich_episode
{ "episode_id": "GG_EP014", "dry_run": true }
```
Gemini fact-checks each scene and returns corrections.

---

## Empire OS Orchestration Flow

```
Empire OS receives topic request
  │
  ├─ POST /gemini/research        — research the topic
  │   └─ Returns structured facts
  │
  ├─ [Empire OS builds episode JSON using facts]
  │
  ├─ POST /ollama/refine (per scene) — optimize prompts
  │   └─ Returns cinematic visual prompts + tight narration
  │
  ├─ [Empire OS writes refined JSON to prompts/gods_glory/]
  │
  ├─ POST /render/start            — kick off auto_render.py
  │   └─ Returns pid
  │
  ├─ GET /render/status/<id>       — poll every 60s
  │   └─ scenes_done counts progress
  │
  ├─ [state == "done"]
  │
  └─ POST /publish/<id>            — queue for CrossPost
      └─ CrossPost uploads to YouTube/TikTok/Instagram
```

---

## File Locations
| What | Where |
|------|-------|
| Render logs | `empire_runs/<EP_ID>.log` |
| Run state JSON | `empire_runs/<EP_ID>.json` |
| CrossPost jobs | `crosspost_queue/<EP_ID>_<ts>.json` |
| CrossPost config | `crosspost_config.json` |
| Completed finals | `renders/<EP_ID>_final.mp4` |
| Episode scripts | `prompts/gods_glory/<EP_ID>.json` |

---

## Scripts

| File | Purpose |
|------|---------|
| `empire_api.py` | REST API server |
| `empire_api.bat` | Windows launcher |
| `ollama_bridge.py` | Ollama prompt refinement (standalone or imported) |
| `crosspost_bridge.py` | CrossPost queue writer/dispatcher |
| `crosspost_config.json` | CrossPost platform config (auto-created on first run) |
