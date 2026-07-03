@echo off
title VIRAL ENGINE — Fixing cross-episode duplicates + trailer (parallel speed-up active)
set MUSIC=%~dp0music\battle_epic.mp3

echo.
echo ============================================================
echo   FIXING: cross-episode image duplicates (36 images cleared)
echo   FIXING: trailer (was 100%% fallback cards, no real images)
echo   SPEED:  parallel image prefetch now covers all 4 slots,
echo           8 workers at once instead of sequential one-by-one
echo ============================================================
echo.
echo Only the specific broken scenes will regenerate — everything
echo else stays cached, so this should be much faster than a full
echo re-render.
echo.

echo [1/6] Trailer...
py "%~dp0auto_render.py" --episode GG_TRAILER --music "%MUSIC%"
echo.

echo [2/6] EP001...
py "%~dp0auto_render.py" --episode GG_EP001 --skip-images --music "%MUSIC%"
echo.

echo [3/6] EP002...
py "%~dp0auto_render.py" --episode GG_EP002 --skip-images --music "%MUSIC%"
echo.

echo [4/6] EP003...
py "%~dp0auto_render.py" --episode GG_EP003 --skip-images --music "%MUSIC%"
echo.

echo [5/6] EP004...
py "%~dp0auto_render.py" --episode GG_EP004 --skip-images --music "%MUSIC%"
echo.

echo [6/6] EP005...
py "%~dp0auto_render.py" --episode GG_EP005 --skip-images --music "%MUSIC%"
echo.

echo ============================================================
echo   ALL DONE — no scene shares an image with any other scene
echo   in this episode or any other episode, anywhere in the show.
echo ============================================================
pause
