@echo off
title EMPIRE OS - Agent Runner (Mission Board)
cd /d "%~dp0"

REM ── Pick Python: canonical install first, then py launcher ──────────────────
set "PY=C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe"
if not exist "%PY%" set "PY=py"

echo.
echo ============================================================
echo   EMPIRE OS AGENT RUNNER
echo   Board: %~dp0MISSION_BOARD.json
echo ============================================================
echo.

REM ── Show the whole board first ───────────────────────────────────────────────
"%PY%" mission_board.py list
if errorlevel 1 (
    echo.
    echo ERROR: mission_board.py failed - check MISSION_BOARD.json exists and is valid JSON.
    pause
    exit /b 1
)

echo.
echo ------------------------------------------------------------
echo   Claiming highest-priority pending mission...
echo   (status will be set to in_progress on the board)
echo ------------------------------------------------------------
echo.

REM ── Claim next mission and print the ready-to-paste Claude Code prompt ──────
"%PY%" mission_board.py next --claim
if errorlevel 1 (
    echo.
    echo ERROR: could not claim next mission.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Copy the prompt above and paste it into Claude Code:
echo     claude
echo   (run from %~dp0)
echo.
echo   When the agent finishes it reports back with:
echo     python mission_board.py complete ^<id^> "result"
echo     python mission_board.py block ^<id^> "error"
echo ============================================================
echo.
pause
