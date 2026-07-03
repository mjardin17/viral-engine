# PROJECT ROADMAP — Video Bot Pipeline
**Last Updated:** 2026-07-02
**Current Phase:** Production (S3 scripts complete, awaiting render)

---

## Phase 1 — Foundation (COMPLETE ✅)
- [x] Auto render pipeline (auto_render.py)
- [x] GG Season 1: EP001–EP005 finalized (187–260MB each)
- [x] GG Season 2: EP006–EP011 (EP006 broken — needs re-render)
- [x] GG Season 3: ALL 14 SCRIPTS WRITTEN (EP012–EP025)
- [x] Council bot system (9 bots, self-healing)
- [x] MCP integration layer (pipeline_mcp.py)

## Phase 2 — Render Season 3 (IMMEDIATE)
- [ ] Run `render_ep006.bat` — fix Pearl Harbor
- [ ] Run `render_season3.bat` — render all 14 S3 episodes (14–28 hours)
- [ ] Verify all finals in renders/ via bot_09_quality_checker

## Phase 3 — Empire OS Integration (AFTER BLUEPRINT APPROVAL)
- [ ] Register Video Bot Pipeline in Empire OS via Project Import
- [ ] Add 3 tools to pipeline_mcp.py: render_start, render_progress, list_renders
- [ ] Wire Empire OS Event Bus: receive render triggers, report completion
- [ ] Replace chatgpt_bot.py OpenAI call with Empire OS Ollama route (/api/ollama/route)
- [ ] Use Empire OS Content Ingress for platform publishing (CrossPost)

## Phase 4 — ML and LO Channels
- [ ] Write full 24-scene scripts for ML EP002–EP012
- [ ] Write full scripts for LO EP002–EP012
- [ ] Render and publish first ML and LO episodes

## Phase 5 — Autonomous Operation
- [ ] Empire OS schedules render queue automatically
- [ ] Completed finals auto-queue to Content Ingress
- [ ] YouTube metadata auto-generated from script JSON
- [ ] Performance telemetry from YouTube back to Empire OS analytics

---

## Standing Constraints
- Never reuse scenes within or across episodes
- 4 images per scene always
- Full script = 24 scenes, ≥600s
- Empire OS event bus integration requires Josh approval before new scheduled tasks
