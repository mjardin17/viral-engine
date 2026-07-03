@echo off
title SOCIAL MACHINE — Master Orchestrator
color 0A

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║          SOCIAL MACHINE — STARTING UP                   ║
echo ║          Five Councils. Three Channels. One Empire.     ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

:: Find Python
where python >nul 2>&1
if %errorlevel%==0 (
    set PYTHON=python
) else (
    where python3 >nul 2>&1
    if %errorlevel%==0 (
        set PYTHON=python3
    ) else (
        echo [ERROR] Python not found. Please install Python 3.10+
        pause
        exit /b 1
    )
)

:: Change to pipeline root
cd /d "%~dp0"

echo [1] Check machine status...
%PYTHON% social_machine\master.py --status
echo.

echo [2] Running full machine (all platforms, all channels)...
echo     To run a single platform: python social_machine\master.py --platform youtube
echo     To dry-run first:         python social_machine\master.py --dry-run
echo.

%PYTHON% social_machine\master.py

echo.
echo ══════════════════════════════════════════════════════════
echo  Machine run complete. Check social_machine\logs\ for details.
echo ══════════════════════════════════════════════════════════
pause
