@echo off
cd /d "%~dp0"
echo ================================================
echo  Installing New YouTube OAuth Credentials
echo ================================================
echo.

set DOWNLOADS=%USERPROFILE%\Downloads
set DEST=%~dp0credentials.json

echo Looking for downloaded client_secret file in Downloads...
echo.

for /f "delims=" %%f in ('dir /b /o-d "%DOWNLOADS%\client_secret_*.json" 2^>nul') do (
    echo Found: %%f
    copy /Y "%DOWNLOADS%\%%f" "%DEST%"
    echo.
    echo SUCCESS: Credentials installed to:
    echo   %DEST%
    echo.
    echo You can now run UPLOAD_NOW.bat to upload your videos!
    goto done
)

echo ERROR: No client_secret_*.json found in %DOWNLOADS%
echo.
echo Make sure you clicked "Download JSON" in Google Cloud Console.

:done
echo.
pause
