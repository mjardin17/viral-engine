@echo off
title Empire OS - Verify GG Account
cd /d C:\Users\jjard\claude\video-bot-pipeline
echo Clearing port 8080...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8080 "') do taskkill /F /PID %%a 2>nul
echo.
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe channel_uploader.py --channel gg --verify
pause
