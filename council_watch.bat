@echo off
title VIRAL ENGINE — Council Watch
set PYTHONUTF8=1
set BASE=%~dp0

echo.
echo ============================================================
echo   VIRAL ENGINE COUNCIL — Pipeline Health Check
echo   %DATE% %TIME%
echo ============================================================
echo.

echo [1/3] Script Guard — checking for stub downgrades...
py "%BASE%script_guard.py" --check
echo.

echo [2/3] Render Guardian — scanning output clips...
py "%BASE%render_guardian.py"
echo.

echo [3/3] Pipeline Status Dashboard...
py "%BASE%council_status.py"
echo.

echo ============================================================
echo   Council check complete. Review output above.
echo ============================================================
echo.
pause
