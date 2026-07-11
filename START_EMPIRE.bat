@echo off
REM ================================================================
REM  START EMPIRE — One click. Everything up.
REM  Kills stale processes, starts Empire OS, opens dashboard.
REM  Path: C:\Users\jjard\claude\video-bot-pipeline\START_EMPIRE.bat
REM ================================================================

setlocal
set EMPIRE_DIR=C:\Users\jjard\claude\video-bot-pipeline\empire-os-patch\apps\empire-os-server
set EMPIRE_URL=http://localhost:3001

echo.
echo  ========================================
echo   EMPIRE OS — Starting up...
echo  ========================================
echo.

REM 1. Kill anything on port 3001
echo [1/3] Clearing port 3001...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3001 " ^| findstr LISTENING 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
)
timeout /t 1 /nobreak >nul

REM 2. Launch Empire OS server in its own window
echo [2/3] Launching Empire OS server...
start "Empire OS" cmd /k "cd /d %EMPIRE_DIR% && echo. && echo  Empire OS starting on %EMPIRE_URL% && echo  Press Ctrl+C to stop. && echo. && npx tsx server.ts"

REM 3. Wait for server to boot, then open the dashboard
echo [3/3] Waiting for server to boot...
timeout /t 4 /nobreak >nul
start "" "%EMPIRE_URL%"

echo.
echo  ========================================
echo   Empire OS  →  %EMPIRE_URL%
echo   Dashboard  →  %EMPIRE_URL%/empire-dashboard/
echo   Health     →  %EMPIRE_URL%/health
echo  ========================================
echo.
echo  Server window is open. Check it for startup logs.
echo  Press any key to close this launcher.
pause >nul
