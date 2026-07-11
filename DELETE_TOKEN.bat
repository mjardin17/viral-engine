@echo off
cd /d "%~dp0"
if exist token.pickle (
    del /f token.pickle
    echo DELETED: token.pickle
) else (
    echo Already gone: token.pickle not found
)
echo.
echo Now run UPLOAD_NOW.bat and sign in as justifiedmagnificent@gmail.com
echo That account already has the Gods ^& Glory YouTube channel.
echo.
pause
