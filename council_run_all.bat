@echo off
title EMPIRE OS — Council — ALL CHANNELS
set PYTHONUTF8=1
set BASE=%~dp0

:: ============================================================
::  EMPIRE OS — All-Channel Council
::
::  Usage:
::    council_run_all.bat           — run all channels once (sequential)
::    council_run_all.bat --rotate  — round-robin: 1 channel per run,
::                                    picks up where last run left off
::    council_run_all.bat --status  — status for all channels
:: ============================================================

if "%1"=="--status" goto status
if "%1"=="--rotate" goto rotate
goto all

:all
echo.
echo ============================================================
echo   EMPIRE OS COUNCIL — ALL CHANNELS (sequential)
echo ============================================================
echo.
py "%BASE%council\council.py" --channel all
goto end

:rotate
:: Round-robin: read last channel from rotate_state.txt, run next one
echo.
echo ============================================================
echo   EMPIRE OS COUNCIL — ROTATE (one channel per run)
echo ============================================================
echo.

set STATE_FILE=%BASE%council\state\rotate_channel.txt
set CHANNELS=gg il lo ed

:: Read current channel from state file
set CURRENT=gg
if exist "%STATE_FILE%" set /p CURRENT=<"%STATE_FILE%"

:: Pick next channel in rotation
set NEXT=gg
if "%CURRENT%"=="gg" set NEXT=il
if "%CURRENT%"=="il" set NEXT=lo
if "%CURRENT%"=="lo" set NEXT=ed
if "%CURRENT%"=="ed" set NEXT=gg

echo   This run: %NEXT%
echo   (Last run was: %CURRENT%)
echo.

:: Write next state
echo %NEXT%> "%STATE_FILE%"

:: Run council for this channel
py "%BASE%council\council.py" --channel %NEXT%
goto end

:status
echo.
echo ============================================================
echo   EMPIRE OS COUNCIL — STATUS ALL CHANNELS
echo ============================================================
py "%BASE%council\council.py" --channel gg --status
py "%BASE%council\council.py" --channel il --status
py "%BASE%council\council.py" --channel lo --status
py "%BASE%council\council.py" --channel ed --status
goto end

:end
echo.
pause
