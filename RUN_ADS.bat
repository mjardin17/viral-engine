@echo off
cd /d "%~dp0"
set PYTHON=C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe
set WEBSITE=https://jardins-outpost.pages.dev

echo ================================================
echo  Empire OS — Self-Advertising Engine
echo  Generating weekly schedule for all 11 services
echo  Platforms: Instagram, TikTok, Facebook, Twitter
echo ================================================
echo.

"%PYTHON%" empire_ads.py --website %WEBSITE%

echo.
echo Done. Load ads_schedule.json into Zernio to post.
pause
