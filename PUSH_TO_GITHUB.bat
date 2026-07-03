@echo off
REM ============================================================
REM VIRAL ENGINE — INITIAL GITHUB PUSH
REM Run this ONCE from PowerShell or Command Prompt as Josh.
REM Repo: https://github.com/mjardin17/viral-engine
REM ============================================================

cd /d C:\Users\jjard\claude\video-bot-pipeline

echo [1/7] Removing broken .git from sandbox attempt...
rmdir /s /q .git

echo [2/7] Initializing git...
git init
git config user.email "justifiedmagnificent@gmail.com"
git config user.name "Josh Jardin"
git branch -M main

echo [3/7] Staging all production files...
git add -A

echo [4/7] Creating initial commit...
git commit -m "[CLAUDE] chore: Initial production commit — Viral Engine pipeline

- 3-channel AI YouTube factory (Gods & Glory, Mech Legends, Little Olympus)
- GG EP001-EP025 scripts in prompts/gods_glory/
- ML EP001-EP012 scripts in prompts/mech_legends/
- LO EP001-EP040 scripts in prompts/
- 9-bot Council self-healing system in council/
- Autonomous pipeline: research_agent.py + pipeline_run.py
- AI protocol files: CLAUDE.md, GEMINI.md, GOOSE.md, CHATGPT.md
- AI_PROTOCOL.md, AGENT_MEMORY.md, PROJECT_SYNC.md
- .gitignore excludes renders/, output/, .env, all media files"

echo [5/7] Setting remote...
git remote add origin https://github.com/mjardin17/viral-engine.git

echo [6/7] Pushing to GitHub...
REM NOTE: You will be prompted for your GitHub username and PAT (Personal Access Token).
REM If you have not created a PAT: GitHub.com > Settings > Developer Settings > Personal Access Tokens > Generate new token
REM Scopes needed: repo (full control of private repositories)
git push -u origin main

echo [7/7] Done!
echo Verify at: https://github.com/mjardin17/viral-engine
pause
