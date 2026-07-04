@echo off
REM ============================================================
REM EMPIRE OS — Commit StoryForge Integration Phase 5 Update
REM Updates empire_hooks + empire-module + docs in empire-os repo
REM ============================================================

set STAGING=C:\Users\jjard\claude\video-bot-pipeline\empire-os-patch
set TARGET=C:\Users\jjard\empire-os

echo ============================================================
echo STEP 1: Ensuring directory structure
echo ============================================================
IF NOT EXIST "%TARGET%\apps\storyforge\empire-module\workflows" mkdir "%TARGET%\apps\storyforge\empire-module\workflows"
IF NOT EXIST "%TARGET%\apps\storyforge\empire_hooks" mkdir "%TARGET%\apps\storyforge\empire_hooks"
echo Directories ready.

echo.
echo ============================================================
echo STEP 2: Copying updated empire_hooks (Phase 5 event bridge)
echo ============================================================
xcopy /E /I /Y "%STAGING%\apps\storyforge\empire_hooks" "%TARGET%\apps\storyforge\empire_hooks"
echo Python hooks updated.

echo.
echo ============================================================
echo STEP 3: Copying updated empire-module (Phase 5 capabilities)
echo ============================================================
xcopy /E /I /Y "%STAGING%\apps\storyforge\empire-module" "%TARGET%\apps\storyforge\empire-module"
echo TypeScript module updated.

echo.
echo ============================================================
echo STEP 4: Copying StoryForge root files
echo ============================================================
copy /Y "%STAGING%\apps\storyforge\README.md" "%TARGET%\apps\storyforge\README.md"
copy /Y "%STAGING%\apps\storyforge\.env.example" "%TARGET%\apps\storyforge\.env.example"
copy /Y "%STAGING%\apps\storyforge\STORYFORGE_INTEGRATION.md" "%TARGET%\apps\storyforge\STORYFORGE_INTEGRATION.md"
echo Root files copied.

echo.
echo ============================================================
echo STEP 5: Copying updated root docs
echo ============================================================
copy /Y "%STAGING%\ARCHITECTURE.md" "%TARGET%\ARCHITECTURE.md"
copy /Y "%STAGING%\AGENT_MEMORY.md" "%TARGET%\AGENT_MEMORY.md"
copy /Y "%STAGING%\INVENTORY.md" "%TARGET%\INVENTORY.md"
copy /Y "%STAGING%\RECOVERY_GUIDE.md" "%TARGET%\RECOVERY_GUIDE.md"
copy /Y "%STAGING%\REBUILD_RECIPE.md" "%TARGET%\REBUILD_RECIPE.md"
echo Docs updated.

echo.
echo ============================================================
echo STEP 6: Git commit and push
echo ============================================================
cd /d "%TARGET%"
git add -A
git commit -m "[CLAUDE] feat: StoryForge Phase 5 + INVENTORY/RECOVERY_GUIDE/REBUILD_RECIPE docs"
git push origin main

echo.
echo ============================================================
echo DONE. Phase 5 integration committed.
echo Verify: https://github.com/mjardin17/empire-os
echo.
echo Phase 5 adds to StoryForge: campaigns, format packages,
echo analytics, improvement engine, workflow designer, scheduler.
echo.
echo Two lines needed in storyforge-engine/main.py:
echo   from empire_hooks.router import empire_router, setup_event_bridge
echo   app.include_router(empire_router)
echo   setup_event_bridge(_automation_studio)
echo ============================================================
pause
