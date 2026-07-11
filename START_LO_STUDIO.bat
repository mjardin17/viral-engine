@echo off
REM START_LO_STUDIO.bat — Launch Little Olympus Studio
REM AI Pipeline: Ollama (local, free) → OpenAI (paid fallback)
REM UI: http://localhost:5050

setlocal

echo.
echo ================================================
echo   Little Olympus Studio v1.0
echo   Production pipeline for @LittleOlympusTV
echo ================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+
    pause & exit /b 1
)

REM Check Flask
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo [SETUP] Flask not installed. Installing requirements...
    pip install -r requirements_lo_studio.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install requirements. Run manually:
        echo         pip install flask flask-cors python-dotenv
        pause & exit /b 1
    )
    echo [OK] Requirements installed.
)

REM Check Ollama (optional — still works without it via OpenAI)
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo [WARN] Ollama not running. AI generation will use OpenAI only.
    echo        For free local AI: start Ollama (ollama serve) first.
) else (
    echo [OK] Ollama is running.
)

REM Check .env for OpenAI key
if exist .env (
    echo [OK] .env found.
) else (
    echo [WARN] No .env file. Create one with OPENAI_API_KEY=sk-... for OpenAI fallback.
)

echo.
echo [STARTING] Little Olympus Studio...
echo [UI]       http://localhost:5050
echo [STOP]     Press Ctrl+C to stop
echo.

REM Start browser after 2 seconds
start /b cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:5050"

python lo_studio_server.py
