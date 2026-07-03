@echo off
REM ============================================================
REM VIRAL ENGINE — NUCLEAR PUSH
REM Wipes the broken .git, starts fresh, commits everything,
REM force pushes to GitHub. Run ONCE from this folder.
REM ============================================================

cd /d C:\Users\jjard\claude\video-bot-pipeline

echo ============================================================
echo STEP 1: Current broken state
echo ============================================================
git log --oneline -5 2>&1
git status --short 2>&1 | find /C "" & echo staged/modified files visible to git
echo.

echo ============================================================
echo STEP 2: Deleting broken .git and starting fresh
echo ============================================================
rmdir /s /q .git
git init
git config user.email "justifiedmagnificent@gmail.com"
git config user.name "Josh Jardin"
git branch -M main
echo Git initialized clean.
echo.

echo ============================================================
echo STEP 3: Staging all production files
echo ============================================================
git add -A
echo Files staged successfully.
echo.

echo ============================================================
echo STEP 4: Committing
echo ============================================================
git commit -m "Viral Engine production pipeline - initial commit"
echo.

echo ============================================================
echo STEP 5: Force pushing to GitHub
echo ============================================================
git remote add origin https://github.com/mjardin17/viral-engine.git
git push -u origin main --force

echo.
echo ============================================================
echo If you see a username/password prompt:
echo   Username: mjardin17
echo   Password: your GitHub Personal Access Token (NOT your password)
echo ============================================================
echo.
echo Verify at: https://github.com/mjardin17/viral-engine
pause
