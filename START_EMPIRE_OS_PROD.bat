@echo off
REM ═══════════════════════════════════════════════════════════════
REM  Empire OS — PRODUCTION Start (PM2, restart-on-crash)
REM
REM  First time: run ONCE to install + start
REM  After that: PM2 keeps it running automatically
REM
REM  Monitor:   npx pm2 monit
REM  Logs:      npx pm2 logs empire-os
REM  Stop:      npx pm2 stop empire-os
REM  Restart:   npx pm2 restart empire-os
REM ═══════════════════════════════════════════════════════════════

cd /d "%~dp0empire-os-patch\apps\empire-os-server"

echo [Empire OS] Creating logs directory...
mkdir "..\..\logs" 2>nul

echo [Empire OS] Installing dependencies...
call C:\Users\jjard\AppData\Roaming\npm\pnpm.cmd install --frozen-lockfile 2>nul
if errorlevel 1 npm install

echo [Empire OS] Installing PM2 globally...
call npm install -g pm2 2>nul

echo [Empire OS] Starting Empire OS with PM2...
call npx pm2 start pm2.config.cjs

echo.
echo [Empire OS] Server started under PM2.
echo   Monitor:  npx pm2 monit
echo   Logs:     npx pm2 logs empire-os
echo   Status:   npx pm2 list
echo   Stop:     npx pm2 stop empire-os
echo.

call npx pm2 list
pause
