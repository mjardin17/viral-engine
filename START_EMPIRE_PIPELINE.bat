@echo off
REM START_EMPIRE_PIPELINE.bat
REM
REM Starts BOTH Empire OS (TypeScript, port 3001) AND empire_server.py (Python, port 8002).
REM Run this once — then open http://localhost:3001/empire-dashboard/ in your browser.
REM Click "Render Episode" in the sidebar to start a render.
REM
REM PREREQUISITES (one-time setup):
REM   pip install fastapi uvicorn
REM   cd empire-os-patch && npm install && cd ..

cd /d C:\Users\jjard\claude\video-bot-pipeline

echo ============================================================
echo   Empire OS + Video Pipeline Startup
echo ============================================================

echo [1/3] Clearing any stale git lock...
if exist .git\index.lock del /f .git\index.lock

echo [2/3] Starting empire_server.py (port 8002) in background...
start "Empire Pipeline Server" cmd /k "cd /d C:\Users\jjard\claude\video-bot-pipeline && python empire-os-patch\apps\video-pipeline\empire_server.py"

echo [3/3] Waiting 2s then starting Empire OS (port 3001)...
timeout /t 2 /nobreak >nul

cd empire-os-patch
echo Starting Empire OS...
npm start

REM If npm start exits, hold the window open
pause
