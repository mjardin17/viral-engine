@echo off
title Empire OS - Full Weekly Run
set PYTHON=C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe
set BASE=%~dp0

echo.
echo ============================================================
echo   EMPIRE OS - FULL WEEKLY PIPELINE
echo   Books + Merch - Scan, Create, Upload Everything
echo ============================================================
echo.

echo [1/4] Installing all dependencies...
"%PYTHON%" -m pip install requests beautifulsoup4 ebooklib reportlab Pillow google-generativeai playwright --break-system-packages --quiet
"%PYTHON%" -m playwright install chromium --quiet

echo.
echo [2/4] Running BOOK pipeline (scan + generate + format + queue)...
"%PYTHON%" "%BASE%storyforge\pipeline.py" --books 2

echo.
echo [3/4] Running MERCH pipeline (scan + design + queue)...
"%PYTHON%" "%BASE%merch_empire\pipeline.py" --niches 5

echo.
echo [4/4] Uploading everything...
"%PYTHON%" "%BASE%storyforge\uploader.py"
"%PYTHON%" "%BASE%merch_empire\uploader.py"

echo.
echo ============================================================
echo   WEEKLY RUN COMPLETE
echo   Books: storyforge\upload_log.json
echo   Merch: merch_empire\upload_log.json
echo ============================================================
pause
