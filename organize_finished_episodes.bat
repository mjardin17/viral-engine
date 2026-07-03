@echo off
title Organizing your finished episodes
set DEST=%USERPROFILE%\Desktop\GODS AND GLORY - FINISHED EPISODES
mkdir "%DEST%" 2>nul

echo Copying finished episodes to your Desktop...
echo.

copy /Y "%~dp0renders\GG_EP001_final.mp4" "%DEST%\EP1 - Thermopylae.mp4"
copy /Y "%~dp0renders\GG_EP002_final.mp4" "%DEST%\EP2 - Gaugamela.mp4"
copy /Y "%~dp0renders\GG_EP003_final.mp4" "%DEST%\EP3 - Cannae.mp4"
copy /Y "%~dp0renders\GG_EP004_final.mp4" "%DEST%\EP4 - Mongols.mp4"
copy /Y "%~dp0renders\GG_EP005_final.mp4" "%DEST%\EP5 - Constantinople.mp4"

echo.
echo ============================================================
echo   DONE. Your 5 finished episodes are on your Desktop in:
echo   GODS AND GLORY - FINISHED EPISODES
echo ============================================================
echo.
start "" "%DEST%"
pause
