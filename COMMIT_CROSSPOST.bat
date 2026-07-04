@echo off
REM ============================================================
REM COMMIT_CROSSPOST.bat
REM Copies CrossPost Enterprise integration from empire-os-patch
REM into the empire-os repo and commits to GitHub.
REM
REM Run this AFTER COMMIT_STORYFORGE_P5.bat has already run.
REM ============================================================

echo [COMMIT_CROSSPOST] Step 1: Pull latest from empire-os...
cd /d C:\Users\jjard\empire-os
git pull origin main
if ERRORLEVEL 1 (
    echo ERROR: git pull failed. Check your network and repo access.
    pause
    exit /b 1
)

echo [COMMIT_CROSSPOST] Step 2: Copy CrossPost Enterprise source...
xcopy /E /I /Y "C:\Users\jjard\claude\video-bot-pipeline\empire-os-patch\apps\crosspost-enterprise" "C:\Users\jjard\empire-os\apps\crosspost-enterprise"
if ERRORLEVEL 1 (
    echo ERROR: xcopy failed for crosspost-enterprise.
    pause
    exit /b 1
)

echo [COMMIT_CROSSPOST] Step 3: Copy updated root docs...
copy /Y "C:\Users\jjard\claude\video-bot-pipeline\empire-os-patch\ARCHITECTURE.md" "C:\Users\jjard\empire-os\ARCHITECTURE.md"
copy /Y "C:\Users\jjard\claude\video-bot-pipeline\empire-os-patch\AGENT_MEMORY.md" "C:\Users\jjard\empire-os\AGENT_MEMORY.md"
copy /Y "C:\Users\jjard\claude\video-bot-pipeline\INVENTORY.md" "C:\Users\jjard\empire-os\INVENTORY.md"
copy /Y "C:\Users\jjard\claude\video-bot-pipeline\RECOVERY_GUIDE.md" "C:\Users\jjard\empire-os\RECOVERY_GUIDE.md"
copy /Y "C:\Users\jjard\claude\video-bot-pipeline\REBUILD_RECIPE.md" "C:\Users\jjard\empire-os\REBUILD_RECIPE.md"

echo [COMMIT_CROSSPOST] Step 4: Verify empire hooks in server.ts...
findstr /C:"/empire/health" "C:\Users\jjard\empire-os\apps\crosspost-enterprise\server.ts" >nul
if ERRORLEVEL 1 (
    echo ERROR: Empire hooks not found in server.ts. Do not commit.
    pause
    exit /b 1
)
echo   - Empire hooks confirmed in server.ts.

echo [COMMIT_CROSSPOST] Step 5: Verify CrossPostModule adapter...
if not exist "C:\Users\jjard\empire-os\apps\crosspost-enterprise\empire-module\crosspost.module.ts" (
    echo ERROR: crosspost.module.ts not found. Do not commit.
    pause
    exit /b 1
)
echo   - CrossPostModule adapter confirmed.

echo [COMMIT_CROSSPOST] Step 6: git add...
cd /d C:\Users\jjard\empire-os
git add -A

echo [COMMIT_CROSSPOST] Step 7: git commit...
git commit -m "[CLAUDE] feat: integrate CrossPost Enterprise as EmpireModule

- Staged full CrossPost Enterprise source to apps/crosspost-enterprise/
- server.ts: added empire hooks at line 2954 (additive-only, 3084 lines total)
  - GET /empire/health — live health + capabilities + uptime
  - GET /empire/status — full module descriptor (17 endpoints, 11 capabilities)
  - POST /empire/event — bridge for render.completed, script.created, system.alert
- empire-module/crosspost.module.ts: CrossPostModule extends BaseModule
  - Registers with ModuleGateway on init
  - Subscribes to render.completed + script.created + system.alert
  - handleRequest(): HTTP proxy to CrossPost Express server
  - handleEvent(): fire-and-forget forward to /empire/event
  - health(): polls /empire/health with 5s timeout
- empire-module/package.json: @empire-os/crosspost-module v2.1.0
- BossListers finding: BossListers.tsx is a React frontend panel (setTimeout
  simulation) inside CrossPost — NOT a separate service. Awaiting Josh decision
  on whether a real listing-optimize API route should be added to server.ts.
- Updated ARCHITECTURE.md: CrossPost status ACTIVE
- Updated AGENT_MEMORY.md: CrossPost ACTIVE, Boss Listers clarified
- Updated INVENTORY.md: CrossPost integrated, counts updated
- Updated RECOVERY_GUIDE.md and REBUILD_RECIPE.md"

if ERRORLEVEL 1 (
    echo ERROR: git commit failed.
    pause
    exit /b 1
)

echo [COMMIT_CROSSPOST] Step 8: git push...
git push origin main
if ERRORLEVEL 1 (
    echo ERROR: git push failed.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo SUCCESS: CrossPost Enterprise committed and pushed to GitHub.
echo.
echo Repo: https://github.com/mjardin17/empire-os
echo.
echo What was committed:
echo   apps/crosspost-enterprise/          (full CrossPost source)
echo   apps/crosspost-enterprise/server.ts (empire hooks added)
echo   apps/crosspost-enterprise/empire-module/crosspost.module.ts
echo   apps/crosspost-enterprise/empire-module/package.json
echo   ARCHITECTURE.md (CrossPost = ACTIVE)
echo   AGENT_MEMORY.md (CrossPost = ACTIVE, Boss Listers = UI panel)
echo   INVENTORY.md, RECOVERY_GUIDE.md, REBUILD_RECIPE.md
echo.
echo BOSS LISTERS NOTE:
echo   BossListers.tsx is a frontend simulation panel inside CrossPost.
echo   It uses setTimeout (no real API). If you want a real
echo   listing-optimize endpoint, tell Claude to add a route to server.ts.
echo.
echo NEXT STEPS:
echo   1. To run CrossPost locally: cd apps\crosspost-enterprise ^&^& npm install ^&^& npm run dev
echo   2. Create .env with GEMINI_API_KEY (never committed)
echo   3. Empire Assistant is still blocked on stability criteria
echo ============================================================
pause
