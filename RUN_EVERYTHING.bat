@echo off
REM Complete automated launcher for Empire OS
REM Verifies setup, ensures Buzz is running, launches all agents

setlocal enabledelayedexpansion

set PYTHON_PATH=C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe

echo.
echo ================================================
echo Empire OS Complete Launch
echo ================================================
echo.

REM Check Python
echo Checking Python...
"%PYTHON_PATH%" --version
if errorlevel 1 (
    echo ERROR: Python not found at %PYTHON_PATH%
    pause
    exit /b 1
)

REM Run environment setup
echo.
echo Running environment checks...
"%PYTHON_PATH%" setup_environment.py
if errorlevel 1 (
    echo ERROR: Environment setup failed
    pause
    exit /b 1
)

REM Check .env exists
if not exist .env (
    echo ERROR: .env file not created
    pause
    exit /b 1
)

echo.
echo ================================================
echo All checks passed. Starting agents...
echo ================================================
echo.

REM Start agents
call START_AGENTS.bat

echo.
echo All systems running. Press Ctrl+C to stop agents.
echo.
pause
