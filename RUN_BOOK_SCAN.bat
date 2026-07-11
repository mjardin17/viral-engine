@echo off
title Empire OS - Niche Scanner
set PYTHON=C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe
set BASE=%~dp0

echo.
echo Scanning Amazon bestsellers for winning niches...
echo.
"%PYTHON%" -m pip install requests beautifulsoup4 --break-system-packages --quiet
"%PYTHON%" "%BASE%storyforge\scanner.py" --top 10
echo.
echo Results in storyforge\NICHE_BOARD.json
pause
