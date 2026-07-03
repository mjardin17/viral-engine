@echo off
title VIRAL ENGINE — RESUME Render (keeps existing progress)
set MUSIC=%~dp0music\battle_epic.mp3

echo.
echo ============================================================
echo   RESUME RENDER — keeps scenes already done, fills the rest
echo ============================================================
echo.

if not exist "%MUSIC%" (
    echo ERROR: music\battle_epic.mp3 not found!
    pause
    exit /b
)

echo [1/4]  Resuming GG_EP002 — Gaugamela...
py "%~dp0auto_render.py" --episode GG_EP002 --skip-images --music "%MUSIC%"
echo.

echo [2/4]  Resuming GG_EP003 — Cannae...
py "%~dp0auto_render.py" --episode GG_EP003 --skip-images --music "%MUSIC%"
echo.

echo [3/4]  Resuming GG_EP004 — Mongols...
py "%~dp0auto_render.py" --episode GG_EP004 --skip-images --music "%MUSIC%"
echo.

echo [4/4]  Resuming GG_EP005 — Constantinople...
py "%~dp0auto_render.py" --episode GG_EP005 --skip-images --music "%MUSIC%"
echo.

echo ============================================================
echo   ALL DONE!  Check renders\ folder:
echo     GG_EP002_final.mp4
echo     GG_EP003_final.mp4
echo     GG_EP004_final.mp4
echo     GG_EP005_final.mp4
echo ============================================================
echo.
pause
