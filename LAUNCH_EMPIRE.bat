@echo off
REM ================================================================
REM  LAUNCH EMPIRE — Opens Empire OS + CrossPost Enterprise
REM  Double-click to launch your full AI production HQ.
REM ================================================================

echo.
echo  ███████╗███╗   ███╗██████╗ ██╗██████╗ ███████╗     ██████╗ ███████╗
echo  ██╔════╝████╗ ████║██╔══██╗██║██╔══██╗██╔════╝    ██╔═══██╗██╔════╝
echo  █████╗  ██╔████╔██║██████╔╝██║██████╔╝█████╗      ██║   ██║███████╗
echo  ██╔══╝  ██║╚██╔╝██║██╔═══╝ ██║██╔══██╗██╔══╝      ██║   ██║╚════██║
echo  ███████╗██║ ╚═╝ ██║██║     ██║██║  ██║███████╗    ╚██████╔╝███████║
echo  ╚══════╝╚═╝     ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝     ╚═════╝ ╚══════╝
echo.
echo  Viral Engine AI Production HQ
echo  ================================================================
echo.

REM Kill any existing processes on our ports
echo [1/3] Clearing ports 3000 and 3001...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3001 " ^| findstr LISTENING 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000 " ^| findstr LISTENING 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
)
timeout /t 1 /nobreak >nul

REM Launch Empire OS server (port 3001)
echo [2/3] Launching Empire OS on http://localhost:3001 ...
start "Empire OS :3001" cmd /k "cd /d C:\Users\jjard\claude\video-bot-pipeline\empire-os-patch\apps\empire-os-server && npx tsx server.ts"

timeout /t 2 /nobreak >nul

REM Launch CrossPost Enterprise (port 3000) — if it exists
echo [3/3] Launching CrossPost Enterprise on http://localhost:3000 ...
if exist "C:\Users\jjard\claude\video-bot-pipeline\empire-os-patch\apps\crosspost-enterprise\server.ts" (
    start "CrossPost :3000" cmd /k "cd /d C:\Users\jjard\claude\video-bot-pipeline\empire-os-patch\apps\crosspost-enterprise && npx tsx server.ts"
) else (
    echo [!] CrossPost not found — skipping.
)

echo.
echo  ================================================================
echo   Empire OS  →  http://localhost:3001
echo   CrossPost  →  http://localhost:3000
echo  ================================================================
echo.
echo  Two terminal windows have opened. Check them for startup status.
echo  Press any key to close this launcher.
pause >nul
