@echo off
echo ============================================================
echo   Start empire_server.py (port 8002) — Video Pipeline Bridge
echo ============================================================

set PYTHON=
if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" set PYTHON=%LOCALAPPDATA%\Programs\Python\Python314\python.exe
if "%PYTHON%"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set PYTHON=%LOCALAPPDATA%\Programs\Python\Python313\python.exe
if "%PYTHON%"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set PYTHON=%LOCALAPPDATA%\Programs\Python\Python312\python.exe
if "%PYTHON%"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set PYTHON=%LOCALAPPDATA%\Programs\Python\Python311\python.exe
if "%PYTHON%"=="" if exist "C:\Python314\python.exe" set PYTHON=C:\Python314\python.exe

if "%PYTHON%"=="" (
    echo ERROR: Python not found!
    pause
    exit /b 1
)
echo Found Python: %PYTHON%

echo Installing FastAPI / uvicorn if needed...
"%PYTHON%" -m pip install fastapi "uvicorn[standard]" --quiet --break-system-packages 2>nul || "%PYTHON%" -m pip install fastapi "uvicorn[standard]" --quiet

echo Starting empire_server.py on port 8002...
start "Empire Pipeline Server (port 8002)" cmd /k "cd /d C:\Users\jjard\claude\video-bot-pipeline && "%PYTHON%" empire-os-patch\apps\video-pipeline\empire_server.py"

echo Done! empire_server.py starting on port 8002.
echo Check the new CMD window for startup output.
pause
