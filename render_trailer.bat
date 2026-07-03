@echo off
title VIRAL ENGINE — Rendering Channel Trailer
set MUSIC=%~dp0music\battle_epic.mp3

echo.
echo ============================================================
echo   RENDERING GODS AND GLORY CHANNEL TRAILER (~73 seconds)
echo ============================================================
echo.

py "%~dp0auto_render.py" --episode GG_TRAILER --music "%MUSIC%"

echo.
echo ============================================================
echo   DONE — check renders\GG_TRAILER_final.mp4
echo ============================================================
pause
