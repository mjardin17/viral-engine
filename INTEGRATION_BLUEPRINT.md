# Integration Blueprint — Viral Engine × Empire OS
**Date:** 2026-07-02
**Status:** DRAFT — Awaiting Josh Approval Before Implementation
**Author:** Claude (Lead Systems Engineer session)

---

## Executive Summary

Empire OS is already running at `ais-dev-7vc3anh5ikstpsjhmaywr7-767455093414.us-east1.run.app` (port 3000 locally). It is a v3.0 Enterprise orchestration system with built-in AI Router, Ollama Center, Content Ingress (CrossPost), Empire Inspector, and Project Import. 

The Video Bot Pipeline is a local Windows production engine. The integration strategy is: **register the pipeline as an Empire OS project, connect via Event Bus, and use Empire OS's existing Content Ingress as the publishing layer.**

Do NOT build new publishing systems — Empire OS already has CrossPost (Content Ingress).
Do NOT build new Ollama integration — Empire OS already has Ollama Center at port 11434.
Do NOT build a new AI router — Empire OS's `/api/empire/ai-router` already does this.

---

## System Inventory (Audited 2026-07-02)

### Empire OS (CrossPost) — What It Has
| Feature | Location in Empire OS | Notes |
|---|---|---|
| AI Router | `/api/empire/ai-router` + AI Router section | Routes to Ollama/Gemini/Claude by task type |
| Ollama Center | `/api/ollama/route` | Connects to `http://127.0.0.1:11434`, auto-routes models |
| Content Ingress | Content Ingress section | Multi-agent publishing pipeline (Analyst + Director/Writer + Critic) |
| Platform publishing | Content Ingress → YouTube, TikTok, Twitter, LinkedIn | Confirmed from cron job: "Sync CrossPost queues to Twitter/LinkedIn" |
| Project registry | Empire Inspector → CTO Action Ledger | 6 systems registered, scored 45–98% |
| Project import | `/api/empire/register` + Project Import section | Accepts GitHub URL, ZIP archive, local folder |
| Event Bus | `GET /api/empire/event-bus` (SSE) + `POST /api/empire/event-bus` | Server-sent events for cross-project communication |
| Automation (cron) | Automation Center | Background cron scheduler, task queue, retry logic |
| Analytics | Analytics section | Revenue tracking, $4,850 MRR, 4.5x yield multiplier |
| Documentary Factory | Documentary Factory section | Built-in documentary configurator (separate from our pipeline) |

### Video Bot Pipeline — What It Has
| Feature | File | Notes |
|---|---|---|
| Render engine | `auto_render.py` (76KB) | Pollinations → edge-tts → FFmpeg → MP4 |
| 14 S3 scripts | `prompts/gods_glory/` | EP012–EP025 complete, not yet rendered |
| MCP server | `pipeline_mcp.py` | FastMCP, Claude's integration point |
| Self-healing | `council/` (9 bots) | Monitors and auto-repairs pipeline |
| Gemini bot | `bots/gemini_bot.py` | Script generation (key set) |
| Social machine | `social_machine/` | 5-platform publishing (may be superseded by Empire OS Content Ingress) |

---

## Architecture

```
EMPIRE OS (browser app, port 3000)
│
├── AI ROUTER (/api/empire/ai-router)
│     ├── SQL/code → Ollama (llama3)
│     ├── Real-time search → Gemini 3.5 Flash
│     └── Deep reasoning → Claude 3.5 Sonnet
│
├── OLLAMA CENTER (/api/ollama/route)
│     └── http://127.0.0.1:11434 (local)
│
├── CONTENT INGRESS (CrossPost)
│     ├── Creator Input → paste script/transcript
│     ├── Platform Select → YouTube, TikTok, Twitter, LinkedIn
│     ├── Multi-Agent Run → Analyst + Director/Writer + Critic
│     └── Platform-ready output
│
├── EMPIRE EVENT BUS (/api/empire/event-bus)
│     ├── GET → SSE stream (listen for events)
│     └── POST → publish event
│
└── EMPIRE INSPECTOR (/api/inspector/health, /api/inspector/advisor)
      └── 6 registered projects: CrossPost, StoryForge, Documentary Factory,
          LTX Video Engine, Auto Poster Bot, Boss Listers

VIDEO BOT PIPELINE (local Windows, C:\Users\jjard\claude\video-bot-pipeline)
│
├── pipeline_mcp.py (FastMCP) ← Claude's entry point
│     ├── list_episodes / get_episode / dry_run
│     ├── generate_images (Pollinations.ai, FREE)
│     ├── render_episode (auto_render.py → FFmpeg)
│     └── [TO ADD] render_start / render_progress / list_renders
│
├── auto_render.py ← the actual render engine (DO NOT TOUCH)
├── council/ ← 9 bots, self-healing (DO NOT TOUCH)
├── prompts/gods_glory/ ← 14 S3 scripts ready
└── renders/ ← completed MP4 finals (S1 + partial S2)
```

---

## Integration Points (5 connections only)

### Connection 1: Project Registration
**Direction:** Video Bot Pipeline → Empire OS
**Method:** Empire OS Project Import (GitHub URL or ZIP)
**What:** Register the pipeline so Empire Inspector tracks it, scores it, and Empire OS knows its capabilities.
**How:**
1. Push `video-bot-pipeline` to GitHub, OR
2. ZIP the pipeline and drag-drop into Empire Inspector → Import & Scrape Repository

**No code needed.** This is a one-time UI action in Empire OS.

---

### Connection 2: Event Bus — Render Triggers
**Direction:** Empire OS → Video Bot Pipeline
**Method:** `POST /api/empire/event-bus` → pipeline reads events
**Protocol:** Empire OS posts event; pipeline_mcp.py listens for it and starts a render

**Event schema (Empire OS sends):**
```json
{
  "type": "render.request",
  "payload": {
    "episode_id": "GG_EP012",
    "music": true,
    "skip_images": false
  }
}
```

**Pipeline response (pipeline posts back):**
```json
{
  "type": "render.started",
  "payload": {
    "episode_id": "GG_EP012",
    "pid": 12345
  }
}
```

**Implementation:** Add event-bus listener to pipeline_mcp.py. 3 tools needed (render_start, render_progress, list_renders — see below).

---

### Connection 3: Render Progress Polling
**Direction:** Empire OS polls Video Bot Pipeline
**Method:** New MCP tool `render_progress(episode_id)` in pipeline_mcp.py

Returns:
```json
{
  "episode_id": "GG_EP012",
  "scenes_done": 14,
  "scenes_total": 24,
  "percent": 58,
  "final_exists": false,
  "final_size_mb": 0
}
```

Empire OS checks this every 60 seconds until `final_exists = true`.

---

### Connection 4: Content Ingress (Publishing)
**Direction:** Video Bot Pipeline → Empire OS Content Ingress
**Method:** HTTP POST to Empire OS Content Ingress API (endpoint TBD from server.ts)
**What:** When a render completes, the pipeline posts the script text and metadata to Content Ingress. Empire OS's multi-agent pipeline generates platform-ready captions, titles, and descriptions, then schedules the upload.

**Pipeline sends:**
```json
{
  "creator_input": "[Full narration text of episode]",
  "episode_id": "GG_EP012",
  "video_path": "C:\\...\\renders\\GG_EP012_final.mp4",
  "platforms": ["youtube", "tiktok"],
  "metadata": {
    "title": "The Last Emperor: Fall of Rome",
    "channel": "Gods & Glory"
  }
}
```

**Note:** The existing `social_machine/` in the pipeline may be replaced by Empire OS Content Ingress, OR it runs alongside it. Josh decides. Recommendation: let Empire OS Content Ingress handle the new S3 episodes going forward.

---

### Connection 5: Ollama Routing (Replace OpenAI in chatgpt_bot.py)
**Direction:** Video Bot Pipeline → Empire OS Ollama Center
**Method:** `POST /api/ollama/route` (already exists in Empire OS)
**What:** Instead of calling OpenAI for script QA, call Empire OS's Ollama router.

**Request:**
```json
{
  "prompt": "[QA task prompt]",
  "task_category": "Content / Script Review",
  "priority": "Medium"
}
```

**Result:** Local DeepSeek/llama3 response. Zero cost. No API key.

---

## What to Build (Minimum Viable Integration)

### Step 1 — pipeline_mcp.py: Add 3 tools
```
render_start(episode_id, music=True, skip_images=False)
  → launches auto_render.py as subprocess
  → returns {"pid": N, "started": true}

render_progress(episode_id)
  → counts output/{EP_ID}/clips/scene_*.mp4
  → checks renders/{EP_ID}_final.mp4
  → returns {"scenes_done": N, "final_exists": bool, "final_size_mb": N}

list_renders()
  → scans renders/ for files > 1MB
  → returns list with episode_id, title, size_mb, path
```

### Step 2 — bots/chatgpt_bot.py: Replace OpenAI → Ollama
```python
# Old:
response = openai.chat.completions.create(...)

# New (try Empire OS first, fallback to direct Ollama):
response = requests.post("http://localhost:3000/api/ollama/route", json={
    "prompt": prompt, "task_category": "Content / Script Review"
})
# Fallback: requests.post("http://localhost:11434/api/generate", ...)
```

### Step 3 — Register Pipeline in Empire OS (UI action, not code)
1. Open Empire OS → Empire Inspector → Import & Scrape Repository
2. Upload the `PROJECT_IDENTITY.md`, `PROJECT_CAPABILITIES.json`, `PROJECT_API.md` files as a ZIP
3. Empire Inspector will audit and score the pipeline
4. It will appear in the CTO Action Ledger alongside CrossPost, StoryForge, etc.

### Step 4 — Content Ingress Wiring (after S3 renders complete)
When `render_progress` returns `final_exists = true`:
1. Load the episode script from `prompts/gods_glory/{EP_ID}.json`
2. Extract all `narration` fields (scene text)
3. POST to Empire OS Content Ingress
4. Empire OS generates YouTube title/description/tags via its multi-agent pipeline
5. Empire OS schedules upload

---

## What NOT to Build

| Thing | Why Not |
|---|---|
| New REST server (empire_api.py) | pipeline_mcp.py + 3 new tools is sufficient |
| New Ollama bridge | Empire OS already has /api/ollama/route |
| New publishing system | Empire OS Content Ingress IS CrossPost |
| New AI router | Empire OS /api/empire/ai-router already routes correctly |
| New cron scheduler | Empire OS Automation Center has cron. Ask Josh before adding schedules. |
| Any new scheduled tasks | Standing rule: always ask Josh first |

---

## Tech Stack Alignment

| Capability | Josh's Spec | Empire OS Has | Video Bot Pipeline Has |
|---|---|---|---|
| Research | Gemini | AI Router → Gemini 3.5 Flash | bots/gemini_bot.py |
| Long-form writing | Claude | AI Router → Claude 3.5 Sonnet | auto_render.py |
| Local reasoning | Ollama | Ollama Center → 127.0.0.1:11434 | ollama_bridge.py (new) |
| Prompt refinement | Ollama | /api/ollama/route | ollama_bridge.py (new) |
| Quality review | Claude Council | Empire Inspector | council/ bots |
| Publishing | CrossPost | Content Ingress | social_machine/ (existing) |

Empire OS already implements Josh's model routing spec. The Video Bot Pipeline needs to CALL Empire OS, not rebuild it.

---

## Approval Required

Before implementing Steps 1–4 above, Josh must approve this blueprint.

**Questions for Josh:**
1. Is `social_machine/` inside the pipeline the same as CrossPost, or does Empire OS Content Ingress replace it for new episodes?
2. Should we add the Video Bot Pipeline to Empire OS via GitHub URL (requires pushing to GitHub) or ZIP upload?
3. Empire OS is running on Cloud Run — does it also run locally at port 3000, or only on the cloud URL?
4. The Automation Center cron runs every 15 min for CrossPost queue sync — should the render trigger also be cron-based, or event-bus-based (push)?

---

## Files Created This Session

| File | Purpose | Status |
|---|---|---|
| `PROJECT_IDENTITY.md` | What this project is | ✅ Written |
| `PROJECT_CAPABILITIES.json` | Machine-readable capability map | ✅ Written |
| `PROJECT_API.md` | MCP tools + CLI interfaces | ✅ Written |
| `PROJECT_ARCHITECTURE.md` | Component map + data flow | ✅ Written |
| `PROJECT_ROADMAP.md` | Phase plan | ✅ Written |
| `EMPIRE_OS_TECH_AUDIT.md` | Technology optimization report | ✅ Written (earlier) |
| `INTEGRATION_BLUEPRINT.md` | This document | ✅ Written |
| `empire_api.py` | Redundant REST server | ⚠️ Superseded — delete after approval |
| `ollama_bridge.py` | Standalone Ollama bridge | ⚠️ Superseded by Empire OS /api/ollama/route |
| `crosspost_bridge.py` | CrossPost queue writer | ⚠️ Replace with Content Ingress call |

---

*Blueprint ready for Josh's review. No production code to be written until approved.*
