@echo off
REM Install and run OmniRoute with pre-configured fallback routing
REM This connects all your existing providers (Gemini, OpenAI, Replicate, fal.ai, HuggingFace)
REM to a single endpoint at localhost:20128

echo.
echo ========================================
echo  OmniRoute — Multi-Provider Failover
echo ========================================
echo.
echo Installing OmniRoute globally...
echo.

npm install -g omniroute

if %ERRORLEVEL% NEQ 0 (
  echo.
  echo [ERROR] npm install failed. Check your npm/Node installation.
  pause
  exit /b 1
)

echo.
echo ✓ OmniRoute installed.
echo.
echo Starting OmniRoute on localhost:20128...
echo.
echo Dashboard: http://localhost:20128/dashboard
echo API endpoint: http://localhost:20128/v1
echo.
echo Press Ctrl+C to stop.
echo.

REM Change to pipeline directory so omniroute.config.json is found
cd /d "%~dp0"

REM Run with config
omniroute --config omniroute.config.json

if %ERRORLEVEL% NEQ 0 (
  echo.
  echo [ERROR] OmniRoute failed to start.
  pause
  exit /b 1
)

pause
