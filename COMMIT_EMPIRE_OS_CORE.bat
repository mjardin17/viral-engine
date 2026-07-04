@echo off
REM ============================================================
REM EMPIRE OS — Commit Core Architecture
REM Copies packages/core + ARCHITECTURE.md + AGENT_MEMORY.md
REM from video-bot-pipeline staging area into empire-os repo
REM then commits and pushes.
REM ============================================================

set STAGING=C:\Users\jjard\claude\video-bot-pipeline\empire-os-patch
set TARGET=C:\Users\jjard\empire-os

echo ============================================================
echo STEP 1: Merging core into empire-os
echo ============================================================

REM Merge packages/core (create if not exists)
IF NOT EXIST "%TARGET%\packages\core\src\interfaces" mkdir "%TARGET%\packages\core\src\interfaces"
IF NOT EXIST "%TARGET%\packages\core\src\implementations" mkdir "%TARGET%\packages\core\src\implementations"

xcopy /E /I /Y "%STAGING%\packages\core" "%TARGET%\packages\core"

REM Copy root docs
copy /Y "%STAGING%\ARCHITECTURE.md" "%TARGET%\ARCHITECTURE.md"
copy /Y "%STAGING%\AGENT_MEMORY.md" "%TARGET%\AGENT_MEMORY.md"

echo Files merged.

echo.
echo ============================================================
echo STEP 2: Update root package.json to include core workspace
echo ============================================================
REM packages/core is already under packages/* so pnpm picks it up automatically.
echo Workspace already covers packages/core via packages/* glob.

echo.
echo ============================================================
echo STEP 3: Git commit and push
echo ============================================================
cd /d "%TARGET%"
git add -A
git commit -m "[CLAUDE] feat: freeze core architecture — 6 interfaces + 6 implementations + bootstrap"
git push origin main

echo.
echo ============================================================
echo DONE. Core is committed.
echo Verify: https://github.com/mjardin17/empire-os
echo ============================================================
pause
