@echo off
cd /d C:\Users\jjard\claude\video-bot-pipeline

echo ============================================================
echo   Viral Engine -- Install and Launch
echo ============================================================
echo.

echo [1/5] Clearing stale git lock...
if exist .git\index.lock del /f .git\index.lock 2>nul

echo [2/5] Finding Python...
set PYTHON=
if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" set PYTHON=%LOCALAPPDATA%\Programs\Python\Python314\python.exe
if "%PYTHON%"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set PYTHON=%LOCALAPPDATA%\Programs\Python\Python313\python.exe
if "%PYTHON%"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set PYTHON=%LOCALAPPDATA%\Programs\Python\Python312\python.exe
if "%PYTHON%"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set PYTHON=%LOCALAPPDATA%\Programs\Python\Python311\python.exe
if "%PYTHON%"=="" if exist "C:\Program Files\Python314\python.exe" set PYTHON=C:\Program Files\Python314\python.exe
if "%PYTHON%"=="" if exist "C:\Python314\python.exe" set PYTHON=C:\Python314\python.exe

if "%PYTHON%"=="" (
    echo ERROR: Python not found in standard locations.
    echo Please install Python 3.10+ from https://python.org
    echo Common install location: %LOCALAPPDATA%\Programs\Python\Python3XX\
    pause
    exit /b 1
)

echo Found Python: %PYTHON%
"%PYTHON%" --version

echo.
echo [3/5] Installing dependencies...
"%PYTHON%" -m pip install fastapi "uvicorn[standard]" edge-tts --quiet
echo Dependencies OK.

echo.
echo [4/5] Starting empire_server.py (port 8002)...
start "Empire Pipeline Server (port 8002)" cmd /k "cd /d C:\Users\jjard\claude\video-bot-pipeline && "%PYTHON%" empire-os-patch\apps\video-pipeline\empire_server.py"
timeout /t 3 /nobreak >nul

echo [5/5] Starting Empire OS (port 3001)...
start "Empire OS Server (port 3001)" cmd /k "cd /d C:\Users\jjard\claude\video-bot-pipeline\empire-os-patch\apps\empire-os-server && node_modules\.bin\tsx.CMD server.ts"
timeout /t 5 /nobreak >nul

start "" "http://localhost:3001/empire-dashboard/"

echo.
echo ============================================================
echo   Done! Servers starting in their own windows.
echo   Dashboard: http://localhost:3001/empire-dashboard/
echo ============================================================
pause
