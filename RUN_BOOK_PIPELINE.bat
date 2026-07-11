@echo off
title Empire OS - StoryForge Book + Merch Pipeline
set PYTHON=C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe
set BASE=%~dp0

echo.
echo ============================================================
echo   EMPIRE OS - STORYFORGE PIPELINE
echo   Scan - Generate - Format - Merch - Queue
echo ============================================================
echo.

:: Install dependencies if needed
echo [0/5] Checking dependencies...
"%PYTHON%" -m pip install requests beautifulsoup4 ebooklib reportlab Pillow google-generativeai pytrends --break-system-packages --quiet

echo.
echo [RUNNING] Full auto pipeline...
echo.

"%PYTHON%" "%BASE%storyforge\pipeline.py" %*

echo.
echo ============================================================
echo   Done. Check storyforge\UPLOAD_QUEUE.json for results.
echo ============================================================
pause
