@echo off
title VIRAL ENGINE — Patch EP002 (fix 2 broken scenes + rebuild final)
set MUSIC=%~dp0music\battle_epic.mp3

echo.
echo ============================================================
echo   PATCHING GG_EP002 — regenerating scene_07 and scene_15
echo   then rebuilding the final concatenated video
echo ============================================================
echo.

py "%~dp0auto_render.py" --episode GG_EP002 --skip-images --music "%MUSIC%"

echo.
echo ============================================================
echo   DONE — renders\GG_EP002_final.mp4 rebuilt
echo ============================================================
pause
