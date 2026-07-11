@echo off
echo ============================================================
echo   Kill old port 3001 process + restart Empire OS (no cache)
echo ============================================================

echo [1/3] Killing processes on port 3001...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3001 "') do (
    echo   Killing PID %%a
    taskkill /f /pid %%a 2>nul
)
timeout /t 2 /nobreak >nul

echo [2/3] Starting Empire OS Server (tsx --no-cache)...
start "Empire OS Server (port 3001)" cmd /k "cd /d C:\Users\jjard\claude\video-bot-pipeline\empire-os-patch\apps\empire-os-server && set TSX_DISABLE_CACHE=1 && node_modules\.bin\tsx.CMD server.ts"

echo [3/3] Waiting for startup then opening dashboard...
timeout /t 6 /nobreak >nul
start "" "http://localhost:3001/empire-dashboard/"

echo Done!
pause
