# PROJECT API — Video Bot Pipeline
**Integration Protocol:** MCP (Model Context Protocol) via FastMCP
**Entry Point:** `pipeline_mcp.py`
**Transport:** stdio (Claude calls it directly via MCP)

---

## Current MCP Tools (pipeline_mcp.py)

| Tool | Inputs | Output | Status |
|---|---|---|---|
| `list_episodes()` | none | List of episode IDs + titles from prompts/ | ✅ Working |
| `get_episode(episode_id)` | episode_id: str | Full script JSON | ✅ Working |
| `dry_run(episode_id)` | episode_id: str | Validation report: scene count, duration, image prompts | ✅ Working |
| `generate_images(episode_id)` | episode_id: str | Generates 4 images per scene via Pollinations.ai | ✅ Working |
| `render_episode(episode_id)` | episode_id: str | Runs auto_render.py; returns status | ✅ Working |
| `get_output_status(episode_id)` | episode_id: str | Clip count, final file exists, file size | ✅ Working |
| `list_images(episode_id)` | episode_id: str | List of generated image files | ✅ Working |

## Missing MCP Tools (to add after blueprint approval)

| Tool | Purpose | Priority |
|---|---|---|
| `render_start(episode_id, music, skip_images)` | Launch auto_render.py subprocess with options | HIGH |
| `render_progress(episode_id)` | Return scene_N.mp4 count + renders/ final state | HIGH |
| `list_renders()` | Scan renders/ for completed finals with size/title | HIGH |

---

## CLI Interfaces (direct command line)

```bash
# Run full render of one episode
py auto_render.py --episode GG_EP012

# Render all Season 3 episodes sequentially
render_season3.bat

# Re-render broken EP006
render_ep006.bat

# Launch all 9 council bots
council_run.bat

# CrossPost queue: add an episode
py crosspost_bridge.py queue --episode GG_EP012 --platforms youtube,tiktok

# CrossPost queue: list pending
py crosspost_bridge.py list

# Social Machine: publish to all platforms
py social_machine/master.py --episode GG_EP001

# Ollama bridge: refine one episode's prompts
py ollama_bridge.py --episode GG_EP012
```

---

## File Protocol (how Empire OS passes data)

Empire OS writes episode JSON to:
```
prompts/gods_glory/scene_prompts.gg_ep{NNN}.final.json
```

Pipeline reads from that location automatically. No API call needed to inject a script — just write the file.

### Episode JSON Schema
```json
{
  "episode_id": "GG_EP012",
  "title": "...",
  "youtube_title": "...",
  "tagline": "...",
  "viral_hook": "...",
  "lesson": "...",
  "scenes": [
    {
      "scene_id": "scene_01",
      "scene_type": "cold_open | battle | aftermath | outro",
      "narration": "...",
      "visual_prompt": "...",
      "duration_seconds": 45
    }
  ]
}
```

---

## Output Locations

| What | Path |
|---|---|
| Scene images | `output/{EP_ID}/images/scene_NN_*.png` |
| Scene audio | `output/{EP_ID}/audio/scene_NN.mp3` |
| Scene clips | `output/{EP_ID}/clips/scene_NN.mp4` |
| Final MP4 | `renders/{EP_ID}_final.mp4` |
| CrossPost queue | `crosspost_queue/{EP_ID}_{ts}.json` |
| Render logs | `empire_runs/{EP_ID}.log` (if empire_api.py used) |

---

## Auth
None currently. All calls are local. Empire OS must run on the same machine or have network access to the MCP stdio transport.
