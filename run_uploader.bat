@echo off
cd /d "%~dp0"
echo ================================================
echo  GODS & GLORY — YouTube Auto Uploader
echo ================================================
echo.

REM Try every possible Python location
set PYTHON=

if exist "C:\Users\jjard\jjclaudevideobot\Scripts\python.exe" (
    set PYTHON=C:\Users\jjard\jjclaudevideobot\Scripts\python.exe
    goto found
)
if exist "C:\Users\jjard\AppData\Local\Programs\Python\Python312\python.exe" (
    set PYTHON=C:\Users\jjard\AppData\Local\Programs\Python\Python312\python.exe
    goto found
)
if exist "C:\Users\jjard\AppData\Local\Programs\Python\Python311\python.exe" (
    set PYTHON=C:\Users\jjard\AppData\Local\Programs\Python\Python311\python.exe
    goto found
)
if exist "C:\Users\jjard\AppData\Local\Programs\Python\Python310\python.exe" (
    set PYTHON=C:\Users\jjard\AppData\Local\Programs\Python\Python310\python.exe
    goto found
)
if exist "C:\Python312\python.exe" (
    set PYTHON=C:\Python312\python.exe
    goto found
)
if exist "C:\Python311\python.exe" (
    set PYTHON=C:\Python311\python.exe
    goto found
)

REM Try py launcher (Windows Python Launcher)
where py >nul 2>&1
if %errorlevel%==0 (
    set PYTHON=py
    goto found
)

echo ERROR: Cannot find Python on this computer.
echo Please run find_python.bat and tell Claude what it says.
pause
exit /b 1

:found
echo Found Python: %PYTHON%
echo Installing required packages...
"%PYTHON%" -m pip install google-auth-oauthlib google-api-python-client --quiet
echo.
echo Starting uploader...
"%PYTHON%" easy_youtube_uploader.py
echo.
pause
