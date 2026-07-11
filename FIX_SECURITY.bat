@echo off
REM FIX_SECURITY.bat — Removes .env from git tracking + commits .gitignore files
REM
REM PREREQUISITES (do these BEFORE running this script):
REM   1. Rotate Anthropic key:  https://console.anthropic.com/settings/keys
REM   2. Rotate Google key:     https://aistudio.google.com/app/apikey
REM   3. Rotate OpenAI key:     https://platform.openai.com/api-keys
REM   4. Rotate Pexels key:     https://www.pexels.com/api/
REM   5. Rotate ElevenLabs key: https://elevenlabs.io/app/settings/api-keys
REM   6. Update .env with NEW keys (do NOT commit them)

cd /d C:\Users\jjard\claude\video-bot-pipeline

echo [1/6] Clearing git lock if present...
if exist .git\index.lock del /f .git\index.lock

echo [2/6] Pulling latest...
git pull origin main

echo [3/6] Removing .env from git tracking (keeps file on disk)...
git rm --cached empire-os-patch/apps/empire-os-server/.env

echo [4/6] Staging .gitignore files...
git add empire-os-patch/.gitignore
git add empire-os-patch/apps/crosspost-enterprise/.gitignore
git add empire-os-patch/AUDIT_REPORT.md
git add empire-os-patch/SECURITY_REPORT.md
git add empire-os-patch/MISSING_COMPONENTS.md
git add empire-os-patch/PROJECT_HEALTH.md
git add empire-os-patch/PERFORMANCE_REPORT.md
git add empire-os-patch/TECH_DEBT.md

echo [5/6] Committing...
git commit -m "[CLAUDE] security: remove .env from git, add .gitignore, add audit reports

- CRITICAL: apps/empire-os-server/.env was tracked — untrack it (keys must be rotated)
- Add empire-os-patch/.gitignore to prevent future .env commits
- Add empire-os-patch/apps/crosspost-enterprise/.gitignore
- Add Phase 2 audit documents (AUDIT_REPORT, SECURITY_REPORT, MISSING_COMPONENTS,
  PROJECT_HEALTH, PERFORMANCE_REPORT, TECH_DEBT)"

echo [6/6] Pushing to GitHub...
git push origin main

echo.
echo ============================================================
echo DONE. .env is no longer tracked by git.
echo.
echo IMPORTANT: Update empire-os-patch/apps/empire-os-server/.env
echo with your NEW API keys before starting Empire OS.
echo ============================================================
pause
