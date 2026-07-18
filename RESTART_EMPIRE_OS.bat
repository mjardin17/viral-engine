@echo off
echo ============================================================
echo   Restarting Empire OS Server (port 3001) with tsx
echo ============================================================
start "Empire OS Server (port 3001)" cmd /k "cd /d C:\Users\jjard\claude\video-bot-pipeline\empire-os-patch\apps\empire-os-server && node_modules\.bin\tsx.CMD server.ts"
timeout /t 5 /nobreak >nul
start "" "http://localhost:3001/empire-dashboard/"
echo Done! Empire OS starting in new window.
pause
