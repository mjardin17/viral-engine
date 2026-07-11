@echo off
REM COMMIT_LO_STUDIO.bat — Commit LO Studio v1.2 to GitHub

cd /d C:\Users\jjard\claude\video-bot-pipeline

echo [1/4] Clearing git lock if present...
if exist .git\index.lock del /f .git\index.lock

echo [2/4] Staging LO Studio files...
git add lo_studio_server.py lo_studio.html START_LO_STUDIO.bat requirements_lo_studio.txt adapters\ COMMIT_LO_STUDIO.bat

echo [3/4] Committing...
git commit -m "[CLAUDE] feat: LO Studio v1.2 — Character Manager + complete pipeline

- Character Manager: Add/Edit/Delete custom characters with persistent JSON storage
- Reference image upload per character (data/character_images/)
- AI-assisted appearance draft (Ollama → OpenAI fallback)
- AI trait generation: personality, voice, catchphrase, relationships
- Consistency lock toggle (injects appearance into all image prompts)
- Bible characters read-only with override support
- 14-step episode pipeline fully wired (research → activity sheet)
- 15-file ZIP export package
- Fixed server truncation — entry point at line 1879"

echo [4/4] Pushing to GitHub...
git push origin main

echo.
echo Done. LO Studio v1.2 is live on GitHub.
pause
