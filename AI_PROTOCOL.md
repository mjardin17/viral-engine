# AI_PROTOCOL.md — Multi-Agent Collaboration Protocol
_Viral Engine Production System — 2026-07-02_

## The Law

There is ONE production codebase: `https://github.com/mjardin17/viral-engine`

Every AI in this ecosystem works from this repository. No exceptions.

No AI may:
- Create a parallel project
- Fork the repository without Josh's approval
- Maintain a private copy of the system
- Redesign the pipeline
- Duplicate code that already exists
- Overwrite another AI's committed work without Josh's instruction

---

## Agent Roster

| Agent | Role | Tools |
|---|---|---|
| **Claude** | Senior DevOps + Architecture | File I/O, bash, MCP tools, browser automation |
| **Gemini** | Research + Script Generation | Gemini API, research_agent.py |
| **Goose** | Pipeline Orchestration | Local shell, council bots, batch runners |
| **ChatGPT** | Creative Copy + YouTube Metadata | Text generation, copy editing |
| **Ollama** | Local Inference Fallback | Offline LLM for when API keys are depleted |
| **DeepSeek** | Code Review + Optimization | Code analysis, performance review |
| **Future Agents** | TBD | Must register in this file before operating |

---

## Authority Hierarchy

```
Josh Jardin (Owner)
  └── Claude (Architecture Authority + Memory Keeper)
       ├── Goose (Execution Orchestrator)
       │    ├── Gemini (Script + Research)
       │    ├── auto_render.py (Rendering)
       │    └── Council Bots (Health Monitor)
       └── ChatGPT (Copy + Distribution)
```

**Josh's instructions override everything.**
**Claude's architecture decisions override other AIs.**
**No AI overrides another without Josh's explicit instruction.**

---

## Shared State Files

These files are the shared memory of the system. Every AI reads them. Every AI that changes them must commit immediately.

| File | Owner | When to Update |
|---|---|---|
| `AGENT_MEMORY.md` | Claude | After any architecture change |
| `memory/context/pipeline.md` | Claude / Goose | After pipeline stage change |
| `council/state/render_queue.json` | Goose / Council | After episode status changes |
| `council/state/stub_backlog.json` | Goose / Bot 07 | After stubs are expanded |
| `script_registry.json` | Claude / Gemini | After new full scripts are committed |
| `CLAUDE.md` | Claude | After memory/rules update |

---

## Task Handoff Protocol

### Research → Script (Gemini → Gemini via research_agent.py)
```
Input:  channel name (gg/ml/lo)
Output: prompts/gods_glory/scene_prompts.gg_ep[###].final.json
Trigger: python research_agent.py (or via pipeline_run.py)
```

### Script → Images (auto_render.py)
```
Input:  episode JSON in prompts/gods_glory/
Output: images/{episode_id}/scene_NN_1.jpg through scene_NN_4.jpg
Trigger: python auto_render.py [episode_json_path]
```

### Images → Video (auto_render.py / voice_video_pipeline.py)
```
Input:  images/{episode_id}/, TTS config
Output: output/{episode_id}/{episode_id}_final.mp4
Trigger: python pipeline_run.py --channel gg --start-at voice
```

### Video → YouTube (social_machine/master.py)
```
Input:  renders/{EPISODE_ID}_final.mp4, youtube_uploads/{EPISODE_ID}_youtube.txt
Output: YouTube upload confirmation
Trigger: python social_machine/master.py (with YouTube credentials)
```

---

## Conflict Prevention Rules

1. **One AI works on one episode at a time.** Check `council/state/render_queue.json` before starting.
2. **Lock the episode** by updating render_queue.json to `"status": "in_progress"` at the start.
3. **Release the lock** by updating to `"status": "done"` after completion.
4. **Announce in commit messages.** Use `[AGENT] action: description` format.
5. **Never silently fix another agent's output.** Document the fix in the commit message.

---

## When Something Breaks

1. Stop immediately. Do not continue past a broken stage.
2. Check `council/state/bot_guardian.json` — the guardian may already know.
3. Run `council_run.bat` to let the 9-bot system attempt auto-repair.
4. If council cannot fix it, document the failure in `guardian_report.json`.
5. Report to Josh with: what broke, what was tried, what is needed.

---

## Adding a New AI to the Ecosystem

Before any new AI can operate on this system:

1. Josh must approve the addition
2. A `[AGENTNAME].md` file must be created in this repo with the agent's role and rules
3. The agent must be added to the Agent Roster in this file
4. The agent must demonstrate it can read `AGENT_MEMORY.md` correctly before making any changes

---

## Scheduled Tasks

No AI may create a scheduled task without Josh's explicit approval. This includes:
- Cron jobs
- Recurring watchers
- Polling loops
- Auto-render schedules

If a task needs to run repeatedly, propose it to Josh first. Josh approves the frequency.

---

## The Non-Negotiables (All Agents)

- `.env` never enters git. Ever.
- `renders/` is read-only — finished episodes are never deleted.
- 24 scenes per full episode. No stubs accepted as final.
- 4 images per scene. No exceptions.
- No scene reuse within or across episodes.
- No silent failures. No faking output.
- API keys are set by Josh. Agents never handle credentials in plaintext.
