@echo off
:: ============================================
::  EMPIRE OS — Gods & Glory YouTube Uploader
::  Usage: Double-click, enter episode numbers
::  e.g.  GG_EP002
::        GG_EP002,GG_EP003,GG_EP004
::        (leave blank to upload ALL pending)
:: ============================================
cd /d C:\Users\jjard\claude\video-bot-pipeline

set PYTHON=C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe

echo.
echo ============================================
echo  EMPIRE OS — Gods ^& Glory Uploader
echo ============================================
echo.
echo Episodes ready to upload:
echo   EP001 (243MB) EP002 (434MB) EP003 (213MB)
echo   EP004 (249MB) EP005 (180MB) EP007 (128MB)
echo   EP008 (123MB) EP009 (107MB) EP010 (131MB)
echo   EP011  (99MB)
echo.
echo  NOTE: EP006 is BROKEN (23MB) — skipped automatically
echo.
set /p EPISODES="Enter episodes to upload (e.g. GG_EP002 or GG_EP002,GG_EP003): "

if "%EPISODES%"=="" (
    echo Uploading ALL episodes...
    set EPISODES=GG_EP001,GG_EP002,GG_EP003,GG_EP004,GG_EP005,GG_EP007,GG_EP008,GG_EP009,GG_EP010,GG_EP011
)

echo.
echo [1/2] Verifying token...
%PYTHON% channel_uploader.py --channel gg --verify

echo.
echo [2/2] Uploading: %EPISODES%
%PYTHON% channel_uploader.py --channel gg --episodes %EPISODES% --privacy public

echo.
echo ============================================
echo  DONE — check uploaded_videos.json for URLs
echo ============================================
pause
