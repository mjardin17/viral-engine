@echo off
title VIRAL ENGINE — Rendering Season 3 (24 Scenes Each, ~18-20 min per episode)
set MUSIC=%~dp0music\battle_epic.mp3

echo.
echo ============================================================
echo   RENDERING GODS AND GLORY — SEASON 3  (14 episodes)
echo   Scripts: prompts\gods_glory\
echo   Output:  renders\
echo   Estimated time: 1-2 hours per episode (images + TTS + render)
echo ============================================================
echo.

echo [1/14] EP012 — The Last Emperor: The Fall of Rome...
py "%~dp0auto_render.py" --episode GG_EP012 --music "%MUSIC%"
echo.

echo [2/14] EP013 — The Crusader Kingdoms...
py "%~dp0auto_render.py" --episode GG_EP013 --music "%MUSIC%"
echo.

echo [3/14] EP014 — Waterloo: The Day Napoleon's Genius Ran Out of Miracles...
py "%~dp0auto_render.py" --episode GG_EP014 --music "%MUSIC%"
echo.

echo [4/14] EP015 — Marathon: The 26-Mile Run That Saved Western Civilization...
py "%~dp0auto_render.py" --episode GG_EP015 --music "%MUSIC%"
echo.

echo [5/14] EP016 — Agincourt: How Mud and Arrows Beat French Chivalry...
py "%~dp0auto_render.py" --episode GG_EP016 --music "%MUSIC%"
echo.

echo [6/14] EP017 — Battle of Tours: The Hammer That Stopped Islam's Conquest of Europe...
py "%~dp0auto_render.py" --episode GG_EP017 --music "%MUSIC%"
echo.

echo [7/14] EP018 — Hastings 1066: The Arrow That Forged a Nation...
py "%~dp0auto_render.py" --episode GG_EP018 --music "%MUSIC%"
echo.

echo [8/14] EP019 — Kamikaze: How Two Typhoons Drowned the Mongol Fleet...
py "%~dp0auto_render.py" --episode GG_EP019 --music "%MUSIC%"
echo.

echo [9/14] EP020 — Vienna 1683: The Winged Hussars and the Day Europe Was Saved...
py "%~dp0auto_render.py" --episode GG_EP020 --music "%MUSIC%"
echo.

echo [10/14] EP021 — Midway: Four Minutes That Turned the Pacific War...
py "%~dp0auto_render.py" --episode GG_EP021 --music "%MUSIC%"
echo.

echo [11/14] EP022 — Battle of the Bulge: Hitler's Last Gamble in the Frozen Ardennes...
py "%~dp0auto_render.py" --episode GG_EP022 --music "%MUSIC%"
echo.

echo [12/14] EP023 — Operation Market Garden: A Bridge Too Far...
py "%~dp0auto_render.py" --episode GG_EP023 --music "%MUSIC%"
echo.

echo [13/14] EP024 — Inchon: MacArthur's Impossible Landing...
py "%~dp0auto_render.py" --episode GG_EP024 --music "%MUSIC%"
echo.

echo [14/14] EP025 — Yorktown: The Battle That Ended an Empire...
py "%~dp0auto_render.py" --episode GG_EP025 --music "%MUSIC%"
echo.

echo ============================================================
echo   SEASON 3 COMPLETE — renders\ has all 14 episodes
echo   GG_EP012_final.mp4 through GG_EP025_final.mp4
echo ============================================================
pause
