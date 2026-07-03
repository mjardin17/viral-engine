@echo off
title VIRAL ENGINE — Patch EP003 (rebuild corrupted final video)
set MUSIC=%~dp0music\battle_epic.mp3

echo.
echo ============================================================
echo   PATCHING GG_EP003 — checking scenes, rebuilding final
echo ============================================================
echo.

py "%~dp0auto_render.py" --episode GG_EP003 --skip-images --music "%MUSIC%"

echo.
echo ============================================================
echo   DONE — renders\GG_EP003_final.mp4 rebuilt
echo ============================================================
pause
