@echo off
REM ============================================================
REM EMPIRE OS — Commit StoryForge Integration (Phase 2A)
REM Copies apps/storyforge + updated docs from staging area
REM into empire-os repo, then commits and pushes.
REM ============================================================

set STAGING=C:\Users\jjard\claude\video-bot-pipeline\empire-os-patch
set TARGET=C:\Users\jjard\empire-os

echo ============================================================
echo STEP 1: Creating apps/storyforge directory structure
echo ============================================================

IF NOT EXIST "%TARGET%\apps\storyforge\empire-module\workflows" mkdir "%TARGET%\apps\storyforge\empire-module\workflows"
IF NOT EXIST "%TARGET%\apps\storyforge\empire_hooks" mkdir "%TARGET%\apps\storyforge\empire_hooks"

echo Directories ready.

echo.
echo ============================================================
echo STEP 2: Copying empire_hooks (Python additions)
echo ============================================================
xcopy /E /I /Y "%STAGING%\apps\storyforge\empire_hooks" "%TARGET%\apps\storyforge\empire_hooks"
echo Python hooks copied.

echo.
echo ============================================================
echo STEP 3: Copying empire-module (TypeScript EmpireModule)
echo ============================================================
xcopy /E /I /Y "%STAGING%\apps\storyforge\empire-module" "%TARGET%\apps\storyforge\empire-module"
echo TypeScript module copied.

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
echo Docs copied.

echo.
echo ============================================================
echo STEP 6: Git commit and push
echo ============================================================
cd /d "%TARGET%"
git add -A
git commit -m "[CLAUDE] feat: integrate StoryForge as first Empire OS native module"
git push origin main

echo.
echo ============================================================
echo DONE. StoryForge integration committed.
echo Verify: https://github.com/mjardin17/empire-os
echo.
echo apps/storyforge/ is now in empire-os.
echo StoryForge engine source goes in: apps/storyforge/storyforge-engine/
echo (clone or copy the storyforge GitHub repo there)
echo ============================================================
pause
