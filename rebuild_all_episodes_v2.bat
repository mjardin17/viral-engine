@echo off
title VIRAL ENGINE v2 — Full rebuild: unique images, neural voice, all 5 episodes
set MUSIC=%~dp0music\battle_epic.mp3

echo.
echo ============================================================
echo   FULL REBUILD — fixes applied:
echo     - 2 unique images per scene, never repeated
echo     - no stock "_reference_" photos used as final visuals
echo     - EP1 rebuilt through the proper pipeline (real neural
echo       voice instead of the old robotic fallback)
echo     - self-healing render with automatic corruption checks
echo ============================================================
echo.
echo This will take a long time (5 episodes x 24 scenes x 2 images).
echo You can leave it running in the background.
echo.

echo [1/5] EP001 — Thermopylae (full rebuild, fresh images + neural voice)...
py "%~dp0auto_render.py" --episode GG_EP001 --music "%MUSIC%"
echo.

echo [2/5] EP002 — Gaugamela (regenerating duplicated scenes)...
py "%~dp0auto_render.py" --episode GG_EP002 --skip-images --music "%MUSIC%"
echo.

echo [3/5] EP003 — Cannae (regenerating duplicated scenes)...
py "%~dp0auto_render.py" --episode GG_EP003 --skip-images --music "%MUSIC%"
echo.

echo [4/5] EP004 — Mongols (regenerating duplicated scenes)...
py "%~dp0auto_render.py" --episode GG_EP004 --skip-images --music "%MUSIC%"
echo.

echo [5/5] EP005 — Constantinople (regenerating duplicated scenes)...
py "%~dp0auto_render.py" --episode GG_EP005 --skip-images --music "%MUSIC%"
echo.

echo ============================================================
echo   ALL DONE — renders\ now has all 5 rebuilt episodes
echo ============================================================
pause
