@echo off
title Empire OS - Merch Uploader
set PYTHON=C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe
set BASE=%~dp0

echo Installing dependencies...
"%PYTHON%" -m pip install playwright requests --break-system-packages --quiet
"%PYTHON%" -m playwright install chromium --quiet

echo.
echo Uploading merch to Redbubble, Printful, Spring...
echo.
"%PYTHON%" "%BASE%merch_empire\uploader.py" %*
pause
