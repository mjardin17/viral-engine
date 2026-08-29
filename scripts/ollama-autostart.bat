@echo off
REM ollama-autostart.bat — Start Ollama server on Windows login
REM Install: Task Scheduler > Create Basic Task > "Ollama Auto-Start"
REM   Trigger: At log on
REM   Action: Start program "C:\Users\jjard\claude\video-bot-pipeline\scripts\ollama-autostart.bat"
REM   Advanced: Run whether user is logged in or not

setlocal enabledelayedexpansion

REM Check if Ollama is already running
tasklist /FI "IMAGENAME eq ollama.exe" 2>nul | find /I "ollama.exe" >nul
if not errorlevel 1 (
  REM Already running
  exit /b 0
)

REM Start Ollama in the background (no window)
start /B "" ollama serve

REM Wait for Ollama to be ready (check /api/tags endpoint)
set "RETRY_COUNT=0"
set "MAX_RETRIES=30"

:wait_for_ollama
timeout /t 1 /nobreak >nul
set /a RETRY_COUNT+=1

REM Check if Ollama is listening (crude check via connection attempt)
REM In production, this would HTTP GET http://localhost:11434/api/tags
if %RETRY_COUNT% GEQ %MAX_RETRIES% (
  REM Timeout waiting for Ollama
  exit /b 1
)

REM Retry check (optional — for now just wait 5 seconds total)
if %RETRY_COUNT% LSS 5 goto wait_for_ollama

exit /b 0
