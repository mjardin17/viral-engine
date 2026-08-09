@echo off
REM Credential Collection Agent Launcher

setlocal enabledelayedexpansion
set PYTHON_PATH=C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe

echo.
echo ============================================================
echo  CREDENTIAL COLLECTION AGENT
echo ============================================================
echo.
echo Starting interactive credential collection for all platforms...
echo.

if "%1"=="" (
    echo Interactive Mode: All 14 Platforms
    echo.
    %PYTHON_PATH% agents\credential_collector_agent.py
) else (
    echo Single Platform Mode: %1
    echo.
    %PYTHON_PATH% agents\credential_collector_agent.py %1
)

pause
