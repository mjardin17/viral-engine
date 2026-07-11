@echo off
REM COMMIT_PHASE3.bat — Commits Phase 3: One-Click Video Pipeline
REM
REM What this commits:
REM   empire_server.py          — FastAPI render bridge at port 8002
REM   empire-dashboard.module.ts — Render Episode UI panel
REM   server.ts                  — video-pipeline module wired in
REM   START_EMPIRE_PIPELINE.bat  — launch script for both servers
REM   requirements_empire_server.txt
REM   AGENT_MEMORY.md            — updated with Phase 3 architecture

cd /d C:\Users\jjard\claude\video-bot-pipeline

echo [1/4] Clearing git lock...
if exist .git\index.lock del /f .git\index.lock

echo [2/4] Pulling latest...
git pull origin main

echo [3/4] Staging Phase 3 files...
git add empire-os-patch/apps/video-pipeline/empire_server.py
git add empire-os-patch/apps/empire-os-server/empire-dashboard.module.ts
git add empire-os-patch/apps/empire-os-server/server.ts
git add requirements_empire_server.txt
git add START_EMPIRE_PIPELINE.bat
git add AGENT_MEMORY.md

echo [4/4] Committing...
git commit -m "[CLAUDE] feat: Phase 3 — one-click video pipeline

- empire_server.py: FastAPI bridge at port 8002
  - GET /api/episodes    — scan prompts/ for all episode scripts
  - POST /api/render     — spawn auto_render.py as subprocess
  - GET /api/render/status — live job status (percent, scene, stage)
  - GET /api/render/logs   — polling + SSE streaming
  - POST /api/cancel     — SIGTERM/taskkill running render
  - GET /api/council/status — council bot status

- server.ts: wire VideoPipelineModule (proxies /video-pipeline/* to :8002)

- empire-dashboard: Render Episode page
  - Episode dropdown populated from prompts/ scan
  - Live progress bar + log viewer
  - Job history table
  - Cancel button

- START_EMPIRE_PIPELINE.bat: launch Empire OS + empire_server.py together
- requirements_empire_server.txt: fastapi + uvicorn
- AGENT_MEMORY.md: updated with Phase 3 architecture"

echo Pushing to GitHub...
git push origin main

echo.
echo ============================================================
echo DONE. Phase 3 committed.
echo.
echo NEXT STEP — Install and launch:
echo   pip install fastapi uvicorn
echo   START_EMPIRE_PIPELINE.bat
echo.
echo Then open: http://localhost:3001/empire-dashboard/
echo Click "Render Episode" in the sidebar.
echo ============================================================
pause
