@echo off
title Empire OS — Fix YouTube Episode Titles
cd /d C:\Users\jjard\claude\video-bot-pipeline

echo.
echo ============================================================
echo   GODS ^& GLORY — Fix Episode Titles on YouTube
echo   Adds EP001, EP002... prefix to all existing videos
echo ============================================================
echo.

echo === DRY RUN (showing what WOULD change) ===
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe fix_yt_titles.py

echo.
echo ============================================================
echo  Review the changes above.
echo  Press any key to APPLY FIXES on YouTube, or close to cancel.
echo ============================================================
pause

echo.
echo === APPLYING TITLE FIXES ===
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe fix_yt_titles.py --go

echo.
pause
