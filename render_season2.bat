@echo off
title VIRAL ENGINE — Rendering Season 2 (WWII + Vietnam)
set MUSIC=%~dp0music\battle_epic.mp3

echo.
echo ============================================================
echo   RENDERING GODS AND GLORY — SEASON 2
echo   EP006 Pearl Harbor / EP007 D-Day / EP008 Stalingrad
echo   EP009 Iwo Jima / EP010 Vietnam Overview / EP011 Ia Drang+Khe Sanh+Tet
echo ============================================================
echo.

echo [1/6] EP006 — Pearl Harbor...
py "%~dp0auto_render.py" --episode GG_EP006 --music "%MUSIC%"
echo.

echo [2/6] EP007 — D-Day...
py "%~dp0auto_render.py" --episode GG_EP007 --music "%MUSIC%"
echo.

echo [3/6] EP008 — Stalingrad...
py "%~dp0auto_render.py" --episode GG_EP008 --music "%MUSIC%"
echo.

echo [4/6] EP009 — Iwo Jima...
py "%~dp0auto_render.py" --episode GG_EP009 --music "%MUSIC%"
echo.

echo [5/6] EP010 — Vietnam War Overview...
py "%~dp0auto_render.py" --episode GG_EP010 --music "%MUSIC%"
echo.

echo [6/6] EP011 — Ia Drang, Khe Sanh, and Tet...
py "%~dp0auto_render.py" --episode GG_EP011 --music "%MUSIC%"
echo.

echo ============================================================
echo   SEASON 2 COMPLETE — check renders\ for all 6 episodes
echo ============================================================
pause
