@echo off
REM Install YouTube uploader dependencies (one-time setup)
REM Run this from Command Prompt once, then channel_uploader.py will work

cd /d "%~dp0"

echo Installing Google API libraries for YouTube upload...
echo.

"C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe" -m pip install -r requirements_youtube.txt --break-system-packages

if %ERRORLEVEL% EQU 0 (
  echo.
  echo ✓ Dependencies installed. channel_uploader.py ready to use.
  pause
) else (
  echo.
  echo ✗ Installation failed. Check network/proxy settings.
  pause
  exit /b 1
)
