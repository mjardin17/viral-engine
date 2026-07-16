@echo off
title EMPIRE OS — Re-Render Broken Episodes (EP008-011 + EP014)
set MUSIC=%~dp0music\battle_epic.mp3

echo.
echo ============================================================
echo   GODS AND GLORY — Render Missing S2 Episodes
echo   EP008 Stalingrad / EP009 Iwo Jima
echo   EP010 Vietnam / EP011 Ia Drang+Khe Sanh+Tet
echo.
echo   EP006 Pearl Harbor (41min) + EP007 D-Day (39min) ALREADY DONE.
echo   This bat renders the 4 episodes still stuck as short stubs.
echo ============================================================
echo.

echo [1/4] EP008 — Stalingrad: The City That Broke an Empire...
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe "%~dp0auto_render.py" --episode GG_EP008 --music "%MUSIC%"
echo.

echo [2/4] EP009 — Iwo Jima: The Island That Wouldn't Fall...
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe "%~dp0auto_render.py" --episode GG_EP009 --music "%MUSIC%"
echo.

echo [3/4] EP010 — The Vietnam War: America's Longest War...
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe "%~dp0auto_render.py" --episode GG_EP010 --music "%MUSIC%"
echo.

echo [4/5] EP011 — Ia Drang, Khe Sanh, and Tet: Vietnam's Defining Battles...
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe "%~dp0auto_render.py" --episode GG_EP011 --music "%MUSIC%"
echo.

echo [5/5] EP014 — Waterloo: Napoleon's Final Gamble (re-render from 54-scene script)...
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe "%~dp0auto_render.py" --episode GG_EP014 --music "%MUSIC%"
echo.

echo ============================================================
echo   DONE — 5 episodes re-rendered from full 54-scene scripts.
echo   EP008 Stalingrad / EP009 Iwo Jima / EP010 Vietnam
echo   EP011 Ia Drang+Khe Sanh+Tet / EP014 Waterloo
echo   Each should be 38-45 min when done.
echo   Run bot_10_frame_inspector QC before uploading.
echo ============================================================
pause
