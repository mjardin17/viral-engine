@echo off
title Empire OS — Auto Upload Watcher
cd /d C:\Users\jjard\claude\video-bot-pipeline

echo.
echo ============================================================
echo   AUTO UPLOAD WATCHER — Gods & Glory
echo   Checks every 5 min for finished renders
echo   Auto-uploads anything 35+ minutes long
echo   Leave this window open overnight
echo ============================================================
echo.

C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe auto_upload_watcher.py
pause
