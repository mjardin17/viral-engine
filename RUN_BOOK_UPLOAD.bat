@echo off
title Empire OS - Book Uploader
set PYTHON=C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe
set BASE=%~dp0

echo Installing dependencies...
"%PYTHON%" -m pip install playwright requests --break-system-packages --quiet
"%PYTHON%" -m playwright install chromium --quiet

echo.
echo Uploading books to KDP, Draft2Digital, Payhip...
echo.
"%PYTHON%" "%BASE%storyforge\uploader.py" %*
pause
