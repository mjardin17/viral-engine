@echo off
title VIRAL ENGINE — Audio Fix + Re-Render (with Music)
set MUSIC=%~dp0music\battle_epic.mp3

echo.
echo ============================================================
echo   AUDIO FIX — Voice narration + Epic battle music
echo ============================================================
echo.

if not exist "%MUSIC%" (
    echo ERROR: music\battle_epic.mp3 not found!
    echo Download from: https://incompetech.com/music/royalty-free/mp3-royaltyfree/Crusade.mp3
    echo Save to: %MUSIC%
    pause
    exit /b
)

echo Clearing old render files...
del /q "%~dp0output\GG_EP002\*.mp3" 2>nul
del /q "%~dp0output\GG_EP002\*.mp4" 2>nul
del /q "%~dp0output\GG_EP003\*.mp3" 2>nul
del /q "%~dp0output\GG_EP003\*.mp4" 2>nul
del /q "%~dp0output\GG_EP004\*.mp3" 2>nul
del /q "%~dp0output\GG_EP004\*.mp4" 2>nul
del /q "%~dp0output\GG_EP005\*.mp3" 2>nul
del /q "%~dp0output\GG_EP005\*.mp4" 2>nul
echo Done clearing.
echo.

echo [1/4]  Rendering GG_EP002 — Gaugamela...
py "%~dp0auto_render.py" --episode GG_EP002 --skip-images --music "%MUSIC%"
echo.

echo [2/4]  Rendering GG_EP003 — Cannae...
py "%~dp0auto_render.py" --episode GG_EP003 --skip-images --music "%MUSIC%"
echo.

echo [3/4]  Rendering GG_EP004 — Mongols...
py "%~dp0auto_render.py" --episode GG_EP004 --skip-images --music "%MUSIC%"
echo.

echo [4/4]  Rendering GG_EP005 — Constantinople...
py "%~dp0auto_render.py" --episode GG_EP005 --skip-images --music "%MUSIC%"
echo.

echo ============================================================
echo   ALL DONE!  Voice + music in renders/:
echo     GG_EP002_final.mp4
echo     GG_EP003_final.mp4
echo     GG_EP004_final.mp4
echo     GG_EP005_final.mp4
echo ============================================================
echo.
pause
