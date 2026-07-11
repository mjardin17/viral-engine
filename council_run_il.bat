@echo off
title EMPIRE OS — Council — Iron Legends
set PYTHONUTF8=1
set BASE=%~dp0

if "%1"=="--status" goto status
if "%1"=="--fix" goto fix
if "%1"=="--watch" goto watch
goto normal

:normal
echo.
echo ============================================================
echo   EMPIRE OS COUNCIL — Iron Legends (IL)
echo ============================================================
py "%BASE%council\council.py" --channel il
goto end

:watch
echo.
echo ============================================================
echo   EMPIRE OS COUNCIL — IL Watch Mode (every 10 min)
echo ============================================================
py "%BASE%council\council.py" --channel il --watch 600
goto end

:status
py "%BASE%council\council.py" --channel il --status
goto end

:fix
py "%BASE%council\council.py" --channel il --bot bot_image_healer
py "%BASE%council\council.py" --channel il --bot bot_clip_rebuilder
py "%BASE%council\council.py" --channel il --bot bot_final_assembler
goto end

:end
echo.
pause
