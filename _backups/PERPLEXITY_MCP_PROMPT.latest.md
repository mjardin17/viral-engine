# Perplexity Prompt — Build a local MCP server for the Viral Engine video pipeline

---

## Paste this into Perplexity:

---

Build a Python MCP (Model Context Protocol) server using the `fastmcp` library that wraps a local video production pipeline so Claude can call it directly as a tool from within a desktop session.

**Context — what the pipeline does:**
The pipeline lives at `C:\Users\jjard\claude\video-bot-pipeline\` and contains:
- `voice_video_pipeline.py` — renders an episode JSON into an MP4 using ElevenLabs TTS + FFmpeg
- `generate_images.py` — generates AI images for an episode via Pollinations.ai (free, no key)
- `make_clip_windows.py` — standalone renderer using Windows SAPI TTS (no API key needed)
- Episode JSONs stored under `prompts/**/{channel}/{episode_id}.json`
- Output MP4s written to `output/{episode_id}_final.mp4`
- Images written to `images/{episode_id}/scene_XX.png`

**Build an MCP server at `pipeline_mcp.py` in that same folder with these tools:**

1. `list_episodes()` — scans the `prompts/` directory tree and returns all episode IDs, titles, and channels found

2. `get_episode(episode_id: str)` — reads and returns the full episode JSON for a given ID (searches recursively the same way the pipeline does)

3. `dry_run(episode_id: str)` — runs `python voice_video_pipeline.py --episode {episode_id} --dry-run` and returns stdout

4. `generate_images(episode_id: str, scenes: list[int] | None = None, skip_existing: bool = True)` — runs `python generate_images.py --episode {episode_id}` with optional `--scenes` and `--skip-existing` flags, streams stdout back as the result

5. `render_episode(episode_id: str, music: str | None = None, use_windows_tts: bool = False)` — runs either `voice_video_pipeline.py` or `make_clip_windows.py` depending on `use_windows_tts`, with optional `--music` arg, streams stdout back

6. `get_output_status(episode_id: str)` — checks whether `output/{episode_id}_final.mp4` or `output/{episode_id}_standalone.mp4` exist, returns file size and path if found

7. `list_images(episode_id: str)` — returns which scene images exist vs are missing for a given episode

**Requirements:**
- Use `fastmcp` (`pip install fastmcp`)
- All subprocess calls must use `cwd=BASE_DIR` where `BASE_DIR = Path("C:/Users/jjard/claude/video-bot-pipeline")`
- Stream subprocess output line by line so Claude sees progress, not just the final result
- Return structured dicts not raw strings where possible
- Include a `__main__` block: `mcp.run(transport="stdio")` so it works as a stdio MCP server
- Add a `README` block at the top of the file showing the exact JSON to add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "video-pipeline": {
      "command": "python",
      "args": ["C:/Users/jjard/claude/video-bot-pipeline/pipeline_mcp.py"],
      "env": {}
    }
  }
}
```

- Windows compatible — no Unix-only features
- All tools should handle `FileNotFoundError` gracefully and return a clear error string rather than crashing

Output: the complete `pipeline_mcp.py` file only. No explanation needed, just working code.
