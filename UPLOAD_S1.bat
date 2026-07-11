@echo off
title Empire OS - Upload GG Season 1
set PYTHON=C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe
set BASE=%~dp0

echo.
echo Uploading GG Season 1 (EP001-EP005) to YouTube...
echo.

"%PYTHON%" "%BASE%channel_uploader.py" --channel gg --episodes GG_EP001,GG_EP002,GG_EP003,GG_EP004,GG_EP005 --privacy public --yes

echo.
echo Done. Check YouTube for upload status.
pause
