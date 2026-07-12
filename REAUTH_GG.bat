@echo off
title Empire OS - GG YouTube Auth
cd /d C:\Users\jjard\claude\video-bot-pipeline
echo Clearing port 8080...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8080 "') do taskkill /F /PID %%a 2>nul
echo.
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe gg_auth.py
pause
