@echo off
title EMPIRE OS — Council — Empire Decoded
set PYTHONUTF8=1
set BASE=%~dp0

if "%1"=="--status" goto status
if "%1"=="--fix" goto fix
if "%1"=="--watch" goto watch
goto normal

:normal
echo.
echo ============================================================
echo   EMPIRE OS COUNCIL — Empire Decoded (ED)
echo ============================================================
py "%BASE%council\council.py" --channel ed
goto end

:watch
py "%BASE%council\council.py" --channel ed --watch 600
goto end

:status
py "%BASE%council\council.py" --channel ed --status
goto end

:fix
py "%BASE%council\council.py" --channel ed --bot bot_image_healer
py "%BASE%council\council.py" --channel ed --bot bot_clip_rebuilder
py "%BASE%council\council.py" --channel ed --bot bot_final_assembler
goto end

:end
echo.
pause
