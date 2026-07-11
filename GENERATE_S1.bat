@echo off
REM GENERATE_S1.bat — Generate all Gods & Glory Season 1 episodes via Ollama (local, free)
REM Claude wrote the research + scene outlines. Ollama writes the narration + visual prompts.
REM Run from C:\Users\jjard\claude\video-bot-pipeline\
REM
REM Prerequisites:
REM   1. Ollama running (ollama serve)
REM   2. qwen2.5-coder:7b installed (or set OLLAMA_MODEL env var)
REM   3. Python 3.x available
REM
REM Each episode takes ~20-40 minutes on a modern GPU.
REM All 5 episodes = ~2-3 hours. Leave running overnight.

echo.
echo ============================================================
echo  Gods ^& Glory Season 1 — Local Generation Pipeline
echo  Using Ollama (local, free) — No API credits consumed
echo ============================================================
echo.

REM Check Ollama is reachable
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Ollama not running. Start it with: ollama serve
    echo         Then retry this script.
    pause
    exit /b 1
)
echo [OK] Ollama is running.
echo.

REM Optional: use a better creative model if available
REM set OLLAMA_MODEL=llama3:8b
REM set OLLAMA_MODEL=mistral:7b

echo Generating EP001 — Thermopylae...
python generate_documentary.py --episode EP001
if errorlevel 1 (echo [WARN] EP001 generation had errors. Check output.) else (echo [OK] EP001 complete.)
echo.

echo Generating EP002 — Gaugamela...
python generate_documentary.py --episode EP002
if errorlevel 1 (echo [WARN] EP002 generation had errors.) else (echo [OK] EP002 complete.)
echo.

echo Generating EP003 — Cannae...
python generate_documentary.py --episode EP003
if errorlevel 1 (echo [WARN] EP003 generation had errors.) else (echo [OK] EP003 complete.)
echo.

echo Generating EP004 — Mongol War Machine...
python generate_documentary.py --episode EP004
if errorlevel 1 (echo [WARN] EP004 generation had errors.) else (echo [OK] EP004 complete.)
echo.

echo Generating EP005 — Constantinople 1453...
python generate_documentary.py --episode EP005
if errorlevel 1 (echo [WARN] EP005 generation had errors.) else (echo [OK] EP005 complete.)
echo.

echo ============================================================
echo  Season 1 Generation Complete
echo  Scripts saved to: prompts\gods_glory\
echo  Files: scene_prompts.gg_ep001.v2.json through ep005.v2.json
echo.
echo  NEXT STEPS:
echo    1. Review each v2 JSON for quality
echo    2. Run ollama_bridge.py to refine narration if needed:
echo       python ollama_bridge.py --episode GG_EP001 --no-visuals
echo    3. Render when approved:
echo       python auto_render.py --episode GG_EP001
echo ============================================================
pause
