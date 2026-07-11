@echo off
cd /d "%~dp0"

:: Try the new Python install first (added to PATH)
python --version >nul 2>&1
if %errorlevel%==0 (
    echo Found Python in PATH
    python -m pip install google-auth-oauthlib google-api-python-client requests --quiet
    python youtube_polish.py
    pause
    exit /b 0
)

:: Fallback: try known paths
set PYTHON=
if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" set PYTHON=%LOCALAPPDATA%\Programs\Python\Python314\python.exe
if "%PYTHON%"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set PYTHON=%LOCALAPPDATA%\Programs\Python\Python312\python.exe
if "%PYTHON%"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set PYTHON=%LOCALAPPDATA%\Programs\Python\Python311\python.exe

if "%PYTHON%"=="" (
    echo ERROR: Python not found. Restart your computer after installing Python, then try again.
    pause
    exit /b 1
)

echo Found Python: %PYTHON%
"%PYTHON%" -m pip install google-auth-oauthlib google-api-python-client requests --quiet
"%PYTHON%" youtube_polish.py
pause
