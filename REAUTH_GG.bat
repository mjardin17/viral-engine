@echo off
title Empire OS — Re-authenticate Gods & Glory
cd /d C:\Users\jjard\claude\video-bot-pipeline

echo.
echo ============================================================
echo   Re-authenticating Gods and Glory YouTube account
echo   Sign in as: godsandgloryai@gmail.com
echo ============================================================
echo.

C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe channel_uploader.py --channel gg --reauth

echo.
pause
