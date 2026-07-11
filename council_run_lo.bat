@echo off
title EMPIRE OS — Council — Little Olympus
set PYTHONUTF8=1
set BASE=%~dp0

if "%1"=="--status" goto status
if "%1"=="--fix" goto fix
if "%1"=="--watch" goto watch
goto normal

:normal
echo.
echo ============================================================
echo   EMPIRE OS COUNCIL — Little Olympus (LO)
echo ============================================================
py "%BASE%council\council.py" --channel lo
goto end

:watch
py "%BASE%council\council.py" --channel lo --watch 600
goto end

:status
py "%BASE%council\council.py" --channel lo --status
goto end

:fix
py "%BASE%council\council.py" --channel lo --bot bot_image_healer
py "%BASE%council\council.py" --channel lo --bot bot_clip_rebuilder
py "%BASE%council\council.py" --channel lo --bot bot_final_assembler
goto end

:end
echo.
pause
