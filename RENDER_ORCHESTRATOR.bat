@echo off
REM ============================================================================
REM  RENDER ORCHESTRATOR — parallel multi-worker episode renderer
REM  Empire OS / Viral Engine  ·  MISSION m004
REM
REM  Usage:
REM    RENDER_ORCHESTRATOR.bat --episodes GG_EP012,GG_EP013 --workers 2
REM    RENDER_ORCHESTRATOR.bat --season 3 --channel gg --workers 3
REM    RENDER_ORCHESTRATOR.bat --pending
REM    RENDER_ORCHESTRATOR.bat --season 3 --channel gg --dry-run
REM    RENDER_ORCHESTRATOR.bat --self-test
REM
REM  Hard limit: 3 workers (RAM). Higher values are clamped automatically.
REM ============================================================================
setlocal

set "PY=C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe"
set "REPO=%~dp0"

if not exist "%PY%" (
    echo [ERROR] Python not found at:
    echo   %PY%
    echo Edit RENDER_ORCHESTRATOR.bat and set PY to your python.exe
    exit /b 1
)

pushd "%REPO%"
"%PY%" render_orchestrator.py %*
set "EXITCODE=%ERRORLEVEL%"
popd

if not "%EXITCODE%"=="0" (
    echo.
    echo [WARN] Orchestrator exited with code %EXITCODE% — at least one episode
    echo        failed or was interrupted. Check render_log.json.
)

endlocal & exit /b %EXITCODE%
