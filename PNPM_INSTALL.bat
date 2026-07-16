@echo off
title Hub deps install — Empire OS Hub
cd /d C:\Users\jjard\claude\video-bot-pipeline\empire-os-hub

echo.
echo ============================================================
echo   Empire OS Hub — Installing dependencies (npm)
echo ============================================================
echo.

REM pnpm's undici HTTP client fails on this machine (UND_ERR_DESTROYED)
REM npm's HTTP client works fine — use it instead
echo Running: npm install --legacy-peer-deps
npm install --legacy-peer-deps

if errorlevel 1 (
    echo.
    echo ERROR: npm install failed.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Done! node_modules installed via npm.
echo   Run START_HUB.bat to launch Empire OS Hub.
echo ============================================================
echo.
pause
