@echo off
REM ============================================================
REM COMMIT_VIDEOPIPELINE.bat
REM Copies Video Bot Pipeline Empire integration into empire-os
REM and commits to GitHub.
REM
REM Run AFTER COMMIT_CROSSPOST.bat has already run.
REM ============================================================

echo [COMMIT_VIDEOPIPELINE] Step 1: Pull latest from empire-os...
cd /d C:\Users\jjard\empire-os
git pull origin main
if ERRORLEVEL 1 (
    echo ERROR: git pull failed.
    pause
    exit /b 1
)

echo [COMMIT_VIDEOPIPELINE] Step 2: Copy video-pipeline empire-module...
xcopy /E /I /Y "C:\Users\jjard\claude\video-bot-pipeline\empire-os-patch\apps\video-pipeline" "C:\Users\jjard\empire-os\apps\video-pipeline"
if ERRORLEVEL 1 (
    echo ERROR: xcopy failed for video-pipeline.
    pause
    exit /b 1
)

echo [COMMIT_VIDEOPIPELINE] Step 3: Copy empire_server.py into apps\video-pipeline\...
copy /Y "C:\Users\jjard\claude\video-bot-pipeline\empire_server.py" "C:\Users\jjard\empire-os\apps\video-pipeline\empire_server.py"

echo [COMMIT_VIDEOPIPELINE] Step 4: Copy updated docs...
copy /Y "C:\Users\jjard\claude\video-bot-pipeline\empire-os-patch\ARCHITECTURE.md" "C:\Users\jjard\empire-os\ARCHITECTURE.md"
copy /Y "C:\Users\jjard\claude\video-bot-pipeline\empire-os-patch\AGENT_MEMORY.md" "C:\Users\jjard\empire-os\AGENT_MEMORY.md"
copy /Y "C:\Users\jjard\claude\video-bot-pipeline\INVENTORY.md" "C:\Users\jjard\empire-os\INVENTORY.md"

echo [COMMIT_VIDEOPIPELINE] Step 5: Verify module file exists...
if not exist "C:\Users\jjard\empire-os\apps\video-pipeline\empire-module\video-pipeline.module.ts" (
    echo ERROR: video-pipeline.module.ts not found. Do not commit.
    pause
    exit /b 1
)
echo   - VideoPipelineModule confirmed.

echo [COMMIT_VIDEOPIPELINE] Step 6: git add...
cd /d C:\Users\jjard\empire-os
git add -A

echo [COMMIT_VIDEOPIPELINE] Step 7: git commit...
git commit -m "[CLAUDE] feat: add Video Bot Pipeline EmpireModule wrapper

- empire_server.py: Python FastAPI bridge (port 8002)
  - GET /empire/health — health + active render count + autoRenderPresent check
  - GET /empire/status — full descriptor: 3 channels, 5 capabilities, 8 endpoints
  - POST /empire/event — bridges Empire OS events; script.created auto-queues render
  - GET/POST /api/episodes, /api/render, /api/renders, /api/council/status
  - Publishes render.queued / render.started / render.completed / render.failed
  - Runs auto_render.py as background subprocess; non-blocking
- empire-module/video-pipeline.module.ts: VideoPipelineModule extends BaseModule
  - Registers with ModuleGateway on init
  - Subscribes to script.created → queues render via handleEvent()
  - handleRequest(): HTTP proxy with 120s timeout (renders are slow)
  - health(): polls /empire/health with 5s timeout
- empire-module/package.json: @empire-os/video-pipeline-module v1.0.0
- Updated ARCHITECTURE.md: Video Pipeline = ACTIVE
- Updated AGENT_MEMORY.md: Video Pipeline = ACTIVE"

if ERRORLEVEL 1 (
    echo ERROR: git commit failed.
    pause
    exit /b 1
)

echo [COMMIT_VIDEOPIPELINE] Step 8: git push...
git push origin main
if ERRORLEVEL 1 (
    echo ERROR: git push failed.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo SUCCESS: Video Bot Pipeline wrapper committed to GitHub.
echo.
echo Repo: https://github.com/mjardin17/empire-os
echo.
echo To start the pipeline bridge:
echo   cd C:\Users\jjard\claude\video-bot-pipeline
echo   pip install fastapi uvicorn --break-system-packages
echo   python empire_server.py
echo   ^> Running at http://localhost:8002
echo ============================================================
pause
