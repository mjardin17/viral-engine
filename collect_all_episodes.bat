@echo off
title VIRAL ENGINE — Collecting All Completed Episodes
echo.
echo Copying all completed episodes to renders\ folder...
echo.

copy /Y "%~dp0output\gg_ep001_final.mp4" "%~dp0renders\GG_EP001_final.mp4"
echo [1] GG_EP001_final.mp4  (Gods Glory - Thermopylae)

copy /Y "%~dp0output\ML_EP001_final.mp4" "%~dp0renders\ML_EP001_final.mp4"
echo [2] ML_EP001_final.mp4  (Mech Legends - EP001)

echo.
echo ============================================================
echo   ALL EPISODES IN renders\ folder:
dir /B "%~dp0renders\*_final.mp4" 2>nul
echo ============================================================
echo.
pause
