@echo off
REM ═══════════════════════════════════════════════════════════════
REM  Empire OS — One-shot setup + start
REM  Works from ANY directory — uses absolute paths throughout
REM ═══════════════════════════════════════════════════════════════

cd /d "%~dp0"
set ROOT_DIR=%~dp0empire-os-patch
set SERVER_DIR=%ROOT_DIR%\apps\empire-os-server
set ENV_FILE=%SERVER_DIR%\.env
set ENV_EXAMPLE=%ROOT_DIR%\.env.example
set PNPM=C:\Users\jjard\AppData\Roaming\npm\pnpm.cmd

REM Step 1 — Create .env if it doesn't exist
if not exist "%ENV_FILE%" (
    copy "%ENV_EXAMPLE%" "%ENV_FILE%" >nul
    echo .env created.
)

REM Step 2 — Open .env so Josh can add his API key
echo Opening .env — add your ANTHROPIC_API_KEY, then save and close Notepad.
echo.
notepad "%ENV_FILE%"

REM Step 3 — Install from workspace root (resolves workspace:* and build approvals)
echo Installing dependencies...
cd /d "%ROOT_DIR%"
call "%PNPM%" install
if errorlevel 1 (
    echo pnpm install failed. Trying npm...
    cd /d "%SERVER_DIR%"
    npm install
)

REM Step 4 — Start the server
echo.
echo Starting Empire OS on http://localhost:3001 ...
echo Press Ctrl+C to stop.
echo.
cd /d "%SERVER_DIR%"
call "%PNPM%" exec tsx server.ts
if errorlevel 1 npx tsx server.ts

pause
