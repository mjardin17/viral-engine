@echo off
title Empire OS Hub — Setup
cd /d C:\Users\jjard\claude\video-bot-pipeline

echo.
echo ============================================================
echo   Empire OS Hub — First-Time Setup
echo ============================================================
echo.

REM Check if already set up
if exist "empire-os-hub\node_modules" (
    echo [OK] empire-os-hub already installed. Run START_HUB.bat to launch.
    pause
    exit /b 0
)

REM Clone just the empire-os-hub subfolder using sparse checkout
echo [1/4] Cloning empire-os-hub from Attached-Assets...
if exist "_hub_clone" rmdir /s /q "_hub_clone"
git clone --no-checkout --depth=1 https://github.com/mjardin17/Attached-Assets.git _hub_clone
if errorlevel 1 (
    echo ERROR: git clone failed. Make sure you are logged into GitHub.
    pause
    exit /b 1
)

cd _hub_clone
git sparse-checkout init --cone
git sparse-checkout set artifacts/empire-os-hub
git checkout main
cd ..

echo [2/4] Copying to empire-os-hub/...
if exist "empire-os-hub" rmdir /s /q "empire-os-hub"
xcopy "_hub_clone\artifacts\empire-os-hub" "empire-os-hub\" /E /I /Q
rmdir /s /q "_hub_clone"

echo [3/4] Installing dependencies (pnpm)...
cd empire-os-hub
where pnpm >nul 2>&1
if errorlevel 1 (
    echo pnpm not found — installing via npm...
    npm install -g pnpm
)
pnpm install
if errorlevel 1 (
    echo ERROR: pnpm install failed.
    cd ..
    pause
    exit /b 1
)

echo [4/4] Done!
cd ..
echo.
echo ============================================================
echo   Setup complete. Run START_HUB.bat to launch.
echo ============================================================
echo.
pause
