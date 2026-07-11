@echo off
title Empire OS - Merch Pipeline
set PYTHON=C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe
set BASE=%~dp0

echo.
echo ============================================================
echo   EMPIRE OS - MERCH EMPIRE PIPELINE
echo   Scan Trends - Design - Format All Platforms - Queue
echo ============================================================
echo.

echo Installing dependencies...
"%PYTHON%" -m pip install requests beautifulsoup4 Pillow --break-system-packages --quiet

echo.
echo Running merch pipeline (top 5 niches, 3 style variants each)...
echo.

"%PYTHON%" "%BASE%merch_empire\pipeline.py" %*

echo.
echo ============================================================
echo   Done. Designs in merch_empire\designs\
echo   Upload queue in merch_empire\UPLOAD_QUEUE.json
echo ============================================================
pause
