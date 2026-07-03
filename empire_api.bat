@echo off
title EMPIRE OS — Viral Engine API (port 5757)
set PYTHONUTF8=1
set BASE=%~dp0

echo.
echo ============================================================
echo   EMPIRE OS — VIRAL ENGINE API
echo   http://localhost:5757
echo ============================================================
echo.

:: Install Flask if needed
py -c "import flask" 2>nul || (
    echo Installing Flask...
    py -m pip install flask --quiet
)

:: Optional: set Ollama model (default: llama3)
:: set OLLAMA_MODEL=llama3
:: set OLLAMA_URL=http://localhost:11434

:: Optional: set Gemini key (or set it in .env)
:: set GEMINI_API_KEY=your_key_here

:: Optional: change port
:: set EMPIRE_API_PORT=5757

echo Starting API server...
echo.
echo Endpoints:
echo   GET  http://localhost:5757/health
echo   POST http://localhost:5757/render/start
echo   GET  http://localhost:5757/render/status/GG_EP012
echo   GET  http://localhost:5757/render/log/GG_EP012
echo   GET  http://localhost:5757/outputs
echo   POST http://localhost:5757/publish/GG_EP012
echo   POST http://localhost:5757/ollama/refine
echo   POST http://localhost:5757/gemini/research
echo.

py "%BASE%empire_api.py"
pause
