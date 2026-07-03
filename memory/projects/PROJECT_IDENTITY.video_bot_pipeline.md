# PROJECT_IDENTITY — Video Bot Pipeline
**Empire Inspector Score:** Not yet registered (register via ZIP upload)
**Location:** C:\Users\jjard\claude\video-bot-pipeline\
**Stack:** Python, FFmpeg, edge-tts, Pollinations.ai

---

## What This Project Does
Fully automated AI documentary video factory. Takes a JSON episode script → generates 4 AI images per scene → synthesizes narration audio → renders Ken Burns motion video clips per scene → concatenates with background music → outputs a finished MP4. Serves three YouTube channels: Gods & Glory (history docs, ~18 min), Little Olympus (kids mythology, ~63s), Mech Legends (sci-fi action, ~90s).

## What Problems It Solves
- Produces publish-ready documentary MP4s without human editing
- Maintains visual consistency (4 cinematic images per scene, no reuse)
- Self-heals broken renders via 9-bot council system
- Generates 18–20 minute episodes from a single JSON file

## What APIs It Exposes
**MCP Tools (pipeline_mcp.py — FastMCP, stdio transport):**
- `list_episodes()` — all scripts in prompts/
- `get_episode(episode_id)` — full script JSON
- `dry_run(episode_id)` — validate script without rendering
- `generate_images(episode_id)` — fetch 4 images/scene via Pollinations.ai
- `render_episode(episode_id)` — run auto_render.py
- `get_output_status(episode_id)` — clip count + final file check
- `list_images(episode_id)` — list generated image files

**Missing (to add after blueprint approval):**
- `render_start(episode_id, music, skip_images)`
- `render_progress(episode_id)` — scene-level progress
- `list_renders()` — completed finals with metadata

**CLI (Windows bat files):**
- `render_season3.bat` — render EP012–EP025 sequentially
- `render_ep006.bat` — re-render broken EP006
- `council_run.bat` — launch all 9 council bots

## What Files Are Important
| File | Role |
|---|---|
| `auto_render.py` (76KB) | Core rendering engine — DO NOT TOUCH |
| `pipeline_mcp.py` (7KB) | MCP integration layer — THE entry point |
| `council/bots/` | 9 self-healing bots |
| `prompts/gods_glory/` | All 14 S3 scripts (EP012–EP025) |
| `renders/` | Completed finals (S1 + partial S2) |
| `music/battle_epic.mp3` | Background score — required |
| `bots/gemini_bot.py` | Script generation via Gemini |
| `bots/chatgpt_bot.py` | QA pass via OpenAI (replace with Ollama) |
| `social_machine/master.py` | 5-platform publishing orchestrator |
| `.env` | GEMINI_API_KEY ✅, ELEVENLABS_API_KEY ✅, others empty |

## What AI Models It Uses
| Model | Used For | Cost |
|---|---|---|
| Pollinations.ai (Flux) | 4 images/scene | FREE |
| Gemini (via gemini_bot.py) | Script generation | Free tier |
| edge-tts (Microsoft) | Narration TTS | FREE |
| OpenAI GPT (chatgpt_bot.py) | Script QA | PAID — replace with Ollama |
| ElevenLabs | TTS upgrade (key set, not wired in) | PAID |

## What Other Projects It Can Connect To
- **Empire OS / CrossPost** — via Event Bus: receive render triggers, report completion
- **Empire OS Content Ingress** — send finished scripts for platform publishing
- **Empire OS Ollama Center** — replace OpenAI with local inference
- **Empire OS Empire Inspector** — register via ZIP to get CTO audit + score

## What It Should NEVER Duplicate
- Platform publishing logic (CrossPost / Content Ingress already does this)
- AI routing logic (Empire OS AI Router handles this)
- Niche/channel research (Monetization Center handles this)
- Script narrative synthesis (StoryForge Engine handles this)
- Listing/copywriting (Boss Listers handles this)

## Current Completion
- Core pipeline: **100%** (production-proven S1 and S2)
- Season 3 scripts: **100%** (14 episodes written)
- Season 3 renders: **0%** (run render_season3.bat)
- Empire OS integration: **0%** (awaiting blueprint approval)
- ML/LO channels: **~5%** (EP001 scripted only)
- Overall: **~65%**

## Missing Features
- `render_start`, `render_progress`, `list_renders` tools in pipeline_mcp.py
- Ollama path in chatgpt_bot.py (currently OpenAI only)
- Empire OS Event Bus listener
- Content Ingress handoff after render completes
- ML S1 EP002–EP012 scripts
- LO S1 EP002–EP012 scripts
- YouTube Data API v3 upload (currently manual)
- ElevenLabs TTS not wired into auto_render.py (key exists)
