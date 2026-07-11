@echo off
title Empire OS - Rendering Season 3
set PYTHON=C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe
set BASE=%~dp0
set MUSIC=%BASE%music\battle_epic.mp3

echo.
echo ============================================================
echo   RENDERING GG SEASON 3 (14 episodes)
echo   Output: renders\
echo ============================================================
echo.

echo [1/14] EP012 - The Last Emperor: The Fall of Rome...
"%PYTHON%" "%BASE%auto_render.py" --episode GG_EP012 --music "%MUSIC%"
echo.

echo [2/14] EP013 - The Crusader Kingdoms...
"%PYTHON%" "%BASE%auto_render.py" --episode GG_EP013 --music "%MUSIC%"
echo.

echo [3/14] EP014 - Waterloo...
"%PYTHON%" "%BASE%auto_render.py" --episode GG_EP014 --music "%MUSIC%"
echo.

echo [4/14] EP015 - Marathon...
"%PYTHON%" "%BASE%auto_render.py" --episode GG_EP015 --music "%MUSIC%"
echo.

echo [5/14] EP016 - Agincourt...
"%PYTHON%" "%BASE%auto_render.py" --episode GG_EP016 --music "%MUSIC%"
echo.

echo [6/14] EP017 - Battle of Tours...
"%PYTHON%" "%BASE%auto_render.py" --episode GG_EP017 --music "%MUSIC%"
echo.

echo [7/14] EP018 - Hastings 1066...
"%PYTHON%" "%BASE%auto_render.py" --episode GG_EP018 --music "%MUSIC%"
echo.

echo [8/14] EP019 - Kamikaze...
"%PYTHON%" "%BASE%auto_render.py" --episode GG_EP019 --music "%MUSIC%"
echo.

echo [9/14] EP020 - Vienna 1683...
"%PYTHON%" "%BASE%auto_render.py" --episode GG_EP020 --music "%MUSIC%"
echo.

echo [10/14] EP021 - Midway...
"%PYTHON%" "%BASE%auto_render.py" --episode GG_EP021 --music "%MUSIC%"
echo.

echo [11/14] EP022 - Battle of the Bulge...
"%PYTHON%" "%BASE%auto_render.py" --episode GG_EP022 --music "%MUSIC%"
echo.

echo [12/14] EP023 - Operation Market Garden...
"%PYTHON%" "%BASE%auto_render.py" --episode GG_EP023 --music "%MUSIC%"
echo.

echo [13/14] EP024 - Inchon...
"%PYTHON%" "%BASE%auto_render.py" --episode GG_EP024 --music "%MUSIC%"
echo.

echo [14/14] EP025 - Yorktown...
"%PYTHON%" "%BASE%auto_render.py" --episode GG_EP025 --music "%MUSIC%"
echo.

echo ============================================================
echo   SEASON 3 COMPLETE
echo   GG_EP012_final.mp4 through GG_EP025_final.mp4
echo ============================================================
pause
