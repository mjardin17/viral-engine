@echo off
echo ============================================================
echo   Start Empire OS Server (port 3001) — fresh with no cache
echo ============================================================

echo Killing any existing process on port 3001...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3001 "') do (
    taskkill /f /pid %%a 2>nul
)
timeout /t 2 /nobreak >nul

echo Starting server...
start "Empire OS (port 3001)" cmd /k "cd /d C:\Users\jjard\claude\video-bot-pipeline\empire-os-patch\apps\empire-os-server && set TSX_DISABLE_CACHE=1 && node_modules\.bin\tsx.CMD server.ts"

echo Done — server starting in new window.
timeout /t 1 /nobreak >nul
