# PROJECT_SYNC.md — Viral Engine Shared Repository Protocol
_Version 1.0 — 2026-07-02_

## Repository

**GitHub:** `https://github.com/mjardin17/viral-engine`
**Branch:** `main`
**Owner:** Josh Jardin (mjardin17)

## Single Source of Truth

This repository is the canonical source for the entire Viral Engine production system.

**There is one production project. It lives here. Nowhere else.**

Every AI assistant, every bot, every automated system must read from and write to this repository. No AI is permitted to maintain a private copy, a parallel fork, or a "local version" of this codebase.

## What Is in This Repository

| Category | What | Why Git-tracked |
|---|---|---|
| Python pipeline | `auto_render.py`, `research_agent.py`, `pipeline_run.py`, etc. | Code is the system |
| Episode scripts | `prompts/gods_glory/*.json`, `prompts/mech_legends/*.json`, etc. | Scripts are creative assets |
| Council bots | `council/bots/bot_01` through `bot_09` | Monitoring logic |
| AI protocol docs | `CLAUDE.md`, `GEMINI.md`, `GOOSE.md`, `AI_PROTOCOL.md` | Shared operating rules |
| Brand bibles | `viral_engine_bible.json`, `viral_engine_show_bible.md` | Identity |
| Memory system | `memory/` | Context for all AIs |
| Config templates | `.env.example`, `.env.social.template` | Reference (never secrets) |

## What Is NOT in This Repository

| Category | Why excluded |
|---|---|
| `renders/*.mp4` | 2+ GB of final videos — stored locally only |
| `output/` | 4+ GB of render working files |
| `FINISHED_EPISODES/` | Archived copies — redundant with renders/ |
| `character_images/` | Generated PNGs — regenerated on demand |
| `assets/sfx_cache/` | Generated audio — regenerated on demand |
| `.env` | Contains API keys — NEVER in git |

## How Every AI Must Work

### Before Starting Any Task
1. Pull the latest main branch
2. Read `AGENT_MEMORY.md` for current architecture
3. Read `AI_PROTOCOL.md` for collaboration rules
4. Read `CLAUDE.md` for standing rules (all AIs must follow these)

### After Making Any Change
1. Commit with a descriptive message
2. Push to main
3. If architecture changed: update `AGENT_MEMORY.md`
4. If pipeline changed: update `memory/context/pipeline.md`

### Commit Message Format
```
[AGENT] [ACTION]: brief description

Examples:
[CLAUDE] feat: add research_agent.py autonomous pipeline stage
[GEMINI] fix: correct scene count validation in script generator
[GOOSE] docs: update AI_PROTOCOL.md with new orchestration rules
[SYSTEM] chore: rotate .env template with new TTS backend key
```

## Branch Rules
- `main` is always production-ready
- No experimental branches without Josh's approval
- No force pushes to main
- If a push breaks the pipeline, revert immediately

## Conflict Resolution
If two AIs modify the same file simultaneously:
1. The one with the more recent Josh instruction wins
2. When in doubt: ask Josh before merging
3. Never silently overwrite another AI's work

## What Constitutes "Production Ready"
A commit is production-ready when:
- `auto_render.py` runs without errors
- At least one episode JSON in `prompts/gods_glory/` is valid (24 scenes, no `[WRITE:]` placeholders)
- `.env.example` has accurate documentation of all required keys
- `AGENT_MEMORY.md` reflects the current state

## Repository Setup (First Time)
```powershell
# Clone
git clone https://github.com/mjardin17/viral-engine.git
cd viral-engine

# Configure identity
git config user.email "justifiedmagnificent@gmail.com"
git config user.name "Josh Jardin"

# Copy your real .env (never commit this)
copy .env.example .env
# Then add your actual API keys to .env
```
