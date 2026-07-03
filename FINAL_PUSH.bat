@echo off
REM ============================================================
REM VIRAL ENGINE — FINAL PUSH (run this once, it will work)
REM Files are in working dir but got dropped from git history.
REM This stages everything, commits, and pushes.
REM ============================================================

cd /d C:\Users\jjard\claude\video-bot-pipeline

echo [1/4] Checking current git state...
git log --oneline -3
git status --short | find /C "" & echo files tracked

echo.
echo [2/4] Staging all production files...
git add -A

echo.
echo [3/4] Committing (single-line message — safe for CMD)...
git commit -m "Initial production commit - Viral Engine pipeline"

echo.
echo [4/4] Pushing to GitHub...
git push origin main

echo.
echo ============================================================
echo Done. Verify at: https://github.com/mjardin17/viral-engine
echo ============================================================
pause
