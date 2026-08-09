@echo off
REM Credential Collection Agent Launcher

setlocal enabledelayedexpansion

echo.
echo ============================================================
echo  CREDENTIAL COLLECTION AGENT
echo ============================================================
echo.

REM Check if Python exists
where /q python.exe
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    echo Please ensure Python is installed and in PATH
    pause
    exit /b 1
)

REM Get current directory
cd /d "%~dp0"

echo Starting interactive credential collection for all platforms...
echo.

if "%1"=="" (
    echo Interactive Mode: All 14 Platforms
    echo.
    python agents\credential_collector_agent.py
) else (
    echo Single Platform Mode: %1
    echo.
    python agents\credential_collector_agent.py %1
)

echo.
pause
