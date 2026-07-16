@echo off
title Empire OS Hub
cd /d C:\Users\jjard\claude\video-bot-pipeline

if not exist "empire-os-hub\node_modules" (
    echo empire-os-hub not installed. Run SETUP_HUB.bat first.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Empire OS Hub — Starting
echo ============================================================
echo.
echo [1/2] Starting Vite dev server on port 5173...
cd empire-os-hub
start "Empire OS Hub (Vite)" cmd /c "npm run dev"
cd ..

echo [2/2] Waiting for server to start...
timeout /t 4 /nobreak >nul

echo Starting ngrok tunnel...
echo.
echo ============================================================
echo   Open the ngrok URL on your phone to access Empire OS Hub
echo ============================================================
echo.
where ngrok >nul 2>&1
if errorlevel 1 (
    echo WARNING: ngrok not found in PATH.
    echo Install from https://ngrok.com/download and add to PATH.
    echo.
    echo Hub is running at: http://localhost:5173
    pause
) else (
    ngrok http 5173
)
