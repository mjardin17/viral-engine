@echo off
REM ============================================================
REM VIRAL ENGINE — FIX PUSH (remote has existing commits)
REM Run from: C:\Users\jjard\claude\video-bot-pipeline
REM ============================================================

cd /d C:\Users\jjard\claude\video-bot-pipeline

echo [1/5] Fetching remote state...
git fetch origin

echo.
echo [2/5] Pulling remote into local with rebase (allow unrelated histories)...
git pull --rebase --allow-unrelated-histories origin main

echo.
echo [3/5] Checking for conflicts...
git status

echo.
echo [4/5] If any conflicts above — accepting LOCAL files over remote...
REM Accept local version for any conflicted files
git diff --name-only --diff-filter=U > %TEMP%\conflicts.txt 2>nul
for /F "usebackq delims=" %%f in ("%TEMP%\conflicts.txt") do (
    echo   Keeping local: %%f
    git checkout --ours "%%f"
    git add "%%f"
)

REM Continue rebase if it was paused by conflicts
git rebase --continue 2>nul

echo.
echo [5/5] Pushing to GitHub...
git push -u origin main

echo.
echo Done. Verify at: https://github.com/mjardin17/viral-engine
pause
