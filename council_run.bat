@echo off
title VIRAL ENGINE — Council
set PYTHONUTF8=1
set BASE=%~dp0

:: Parse argument
if "%1"=="--watch" goto watch
if "%1"=="--status" goto status
if "%1"=="--list" goto list
if "%1"=="--fix" goto fix
goto normal

:normal
echo.
echo ============================================================
echo   VIRAL ENGINE COUNCIL — Gods ^& Glory (GG)
echo ============================================================
py "%BASE%council\council.py" --channel gg
goto end

:watch
echo.
echo ============================================================
echo   VIRAL ENGINE COUNCIL — GG Watch Mode (every 10 min)
echo ============================================================
py "%BASE%council\council.py" --channel gg --watch 600
goto end

:status
py "%BASE%council\council.py" --channel gg --status
goto end

:list
py "%BASE%council\council.py" --list
goto end

:fix
echo.
echo ============================================================
echo   VIRAL ENGINE COUNCIL — GG Scan + Auto-Fix
echo ============================================================
py "%BASE%council\council.py" --channel gg --bot bot_image_healer
py "%BASE%council\council.py" --channel gg --bot bot_clip_rebuilder
py "%BASE%council\council.py" --channel gg --bot bot_final_assembler
goto end

:end
echo.
pause
