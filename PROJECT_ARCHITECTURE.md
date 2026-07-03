# PROJECT ARCHITECTURE — Video Bot Pipeline

## System Overview

```
EMPIRE OS
   │
   │  MCP (stdio)
   ▼
pipeline_mcp.py          ← integration layer (FastMCP)
   │
   ├── list_episodes / get_episode / dry_run
   ├── generate_images → Pollinations.ai (FREE)
   │                   → Gemini Imagen (fallback, key SET)
   ├── render_episode  → auto_render.py
   │                   → edge-tts (FREE, narration)
   │                   → FFmpeg (render + Ken Burns + music)
   └── get_output_status / list_images
   
   Parallel:
   council_run.bat  → 9 council bots (self-healing, runs continuously)
   
   Output:
   renders/{EP_ID}_final.mp4
       │
       ▼
   crosspost_bridge.py  → crosspost_queue/ → CrossPost (TBD)
   social_machine/      → YouTube / Instagram / TikTok / Twitter / Facebook
```

---

## Component Map

### Core Rendering Stack
| Component | File | Role |
|---|---|---|
| Episode scripts | `prompts/gods_glory/*.json` | Input: 24-scene JSON scripts |
| Main renderer | `auto_render.py` (76KB) | Orchestrates everything |
| GG renderer | `documentary_render.py` (46KB) | GG-specific variant |
| LO renderer | `little_olympus_render.py` | Little Olympus renderer |
| ML renderer | `mech_legends_render.py` | Mech Legends renderer |
| Local renderer | `local_render.py` (31KB) | Offline/no-cloud variant |
| Image gen | Pollinations.ai (in auto_render) | 4 images/scene, FREE |
| TTS | edge-tts (in auto_render) | Microsoft neural voices, FREE |
| Video | FFmpeg (in auto_render) | Ken Burns + audio + music |
| Music | `music/battle_epic.mp3` | Background score |

### Integration Layer
| Component | File | Role |
|---|---|---|
| MCP server | `pipeline_mcp.py` (7KB, FastMCP) | THE integration point for Empire OS |
| REST API | `empire_api.py` (20KB, Flask) | REDUNDANT — built before audit; may be removed |
| Pipeline state | `pipeline.py` | Episode state machine |

### Self-Healing System
| Component | Location | Role |
|---|---|---|
| Council runner | `council_run.bat` | Launches all 9 bots |
| Guardian | `council/bots/bot_01_guardian.py` | Scans for broken clips |
| Script guard | `council/bots/bot_02_script_guard.py` | Prevents stub downgrades |
| Image healer | `council/bots/bot_03_image_healer.py` | Refetches bad images |
| Clip rebuilder | `council/bots/bot_04_clip_rebuilder.py` | Re-renders 0KB clips |
| Final assembler | `council/bots/bot_05_final_assembler.py` | Rebuilds broken finals |
| Render queue | `council/bots/bot_06_render_queue.py` | Queue management |
| Stub expander | `council/bots/bot_07_stub_expander.py` | Tracks 84 stub episodes |
| Auto renderer | `council/bots/bot_08_auto_renderer.py` | Renders 1 ep per run |
| Quality checker | `council/bots/bot_09_quality_checker.py` | ffprobe + RMS |
| Council state | `council/state/render_queue.json` | Shared state |

### AI Bots
| Component | File | Role |
|---|---|---|
| Gemini bot | `bots/gemini_bot.py` | Scene/script generation (key SET) |
| ChatGPT bot | `bots/chatgpt_bot.py` | QA pass (OpenAI — replace with Ollama) |
| Episode gen | `generate_next_episode.py` | Master episode generation command |
| Ollama bridge | `ollama_bridge.py` | Local prompt refinement (built this session) |

### Publishing
| Component | File | Role |
|---|---|---|
| Social Machine | `social_machine/` | 5-platform publishing councils |
| SM master | `social_machine/master.py` (12KB) | Orchestrates all platforms |
| SM config | `social_machine/config.py` (6KB) | 3 channel configs + credentials |
| YouTube council | `social_machine/councils/youtube/council.py` (14KB) | Upload + metadata |
| Instagram | `social_machine/councils/instagram/council.py` | Reels + carousels |
| TikTok | `social_machine/councils/tiktok/council.py` | Short clips |
| Twitter | `social_machine/councils/twitter/council.py` | Clips + threads |
| Facebook | `social_machine/councils/facebook/council.py` | Posts + Reels |
| CrossPost bridge | `crosspost_bridge.py` | Queue writer (stub — awaiting CrossPost) |

### Premium Video Providers (keys empty, not in use)
| Component | File |
|---|---|
| Higgsfield | `providers/higgsfield.py` |
| Kling AI | `providers/kling.py` |
| Runway ML | `providers/runway.py` |
| Google Veo | `providers/veo.py` |
| Base class | `providers/base.py` |

---

## Data Flow (single episode, full run)

```
1. Empire OS (or Josh manually) picks a topic
2. bots/gemini_bot.py → generates 24-scene JSON script
3. Script saved to prompts/gods_glory/scene_prompts.gg_ep{NNN}.final.json
4. [OPTIONAL] ollama_bridge.py refines visual_prompts + narration per scene
5. auto_render.py reads script:
   a. Pollinations.ai → 4 PNG images per scene (96 images total)
   b. edge-tts → MP3 narration per scene (24 audio files)
   c. FFmpeg → Ken Burns MP4 clip per scene (24 clips)
   d. FFmpeg → concat all clips + mix battle_epic.mp3 → final MP4
6. Final MP4 lands in renders/{EP_ID}_final.mp4 (187-260MB for full GG)
7. crosspost_bridge.py queues publishing job
8. CrossPost (TBD) uploads to YouTube / TikTok / Instagram
```

---

## Key Constraints

| Rule | Detail |
|---|---|
| 4 images per scene | Hard rule — no reuse across scenes or episodes |
| No scene reuse | Every scene unique, within and across episodes |
| Full script = 24 scenes, ≥600s | Stubs (<10 scenes) are rejected by bot_02_script_guard |
| Music path | `music/battle_epic.mp3` — must exist |
| Output naming | `{EP_ID}_final.mp4` in renders/ — exact format required by council bots |

---

## Environment
| Var | Status | Used By |
|---|---|---|
| GEMINI_API_KEY | ✅ SET | gemini_bot.py, auto_render.py (fallback images) |
| ELEVENLABS_API_KEY | ✅ SET | Not yet wired into auto_render.py |
| HIGGSFIELD_API_KEY | ❌ EMPTY | providers/higgsfield.py (unused) |
| KLING_API_KEY | ❌ EMPTY | providers/kling.py (unused) |
| RUNWAY_API_KEY | ❌ EMPTY | providers/runway.py (unused) |
| VEO_API_KEY | ❌ EMPTY | providers/veo.py (unused) |
