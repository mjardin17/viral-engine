@echo off
REM ============================================================
REM EMPIRE OS — SCAFFOLD + PUSH
REM Moves empire-os from video-bot-pipeline staging area,
REM inits git, and force pushes to mjardin17/empire-os.
REM Run ONCE from this folder (double-click in File Explorer).
REM ============================================================

echo ============================================================
echo STEP 1: Moving empire-os to C:\Users\jjard\empire-os
echo ============================================================
IF EXIST "C:\Users\jjard\empire-os" (
  echo Found existing C:\Users\jjard\empire-os — backing up...
  move "C:\Users\jjard\empire-os" "C:\Users\jjard\empire-os.bak_%RANDOM%"
)
move "%~dp0empire-os" "C:\Users\jjard\empire-os"
echo Moved.

echo.
echo ============================================================
echo STEP 2: Initializing git
echo ============================================================
cd /d "C:\Users\jjard\empire-os"
git init
git config user.email "justifiedmagnificent@gmail.com"
git config user.name "Josh Jardin"
git branch -M main
echo Git initialized.

echo.
echo ============================================================
echo STEP 3: Staging all files
echo ============================================================
git add -A
echo Files staged.

echo.
echo ============================================================
echo STEP 4: Committing
echo ============================================================
git commit -m "Empire OS - initial scaffold (Next.js 14 + FastAPI + PostgreSQL + Redis)"

echo.
echo ============================================================
echo STEP 5: Pushing to GitHub
echo ============================================================
git remote add origin https://github.com/mjardin17/empire-os.git
git push -u origin main --force

echo.
echo ============================================================
echo DONE. Verify at: https://github.com/mjardin17/empire-os
echo Next: run docker compose up -d in empire-os/docker/
echo ============================================================
pause
