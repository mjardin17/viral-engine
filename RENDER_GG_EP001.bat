@echo off
title RENDERING GG_EP001 — Gods ^& Glory Episode 1
echo ============================================================
echo   VIRAL ENGINE — Render GG_EP001 (Gods ^& Glory EP1)
echo ============================================================
echo.

cd /d C:\Users\jjard\claude\video-bot-pipeline

echo [1/3] Checking edge-tts...
python -c "import edge_tts" 2>nul
if errorlevel 1 (
    echo Installing edge-tts...
    pip install edge-tts --quiet
)

echo [2/3] Checking Pillow...
python -c "import PIL" 2>nul
if errorlevel 1 (
    echo Installing Pillow...
    pip install Pillow --quiet
)

echo [3/3] Starting render — this will take 10-30 minutes...
echo Output will be saved to: renders\GG_EP001_final.mp4
echo.
echo Press Ctrl+C to stop at any time.
echo.

python auto_render.py --episode GG_EP001

echo.
if exist renders\GG_EP001_final.mp4 (
    echo ============================================================
    echo   SUCCESS! renders\GG_EP001_final.mp4
    echo ============================================================
) else (
    echo ============================================================
    echo   RENDER DID NOT PRODUCE OUTPUT — check errors above
    echo ============================================================
)
echo.
pause
