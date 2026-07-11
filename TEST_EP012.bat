@echo off
title Empire OS - Test Render EP012
set PYTHON=C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe
set BASE=%~dp0
set MUSIC=%BASE%music\battle_epic.mp3

echo.
echo Testing EP012 - Fall of Rome...
echo.

"%PYTHON%" "%BASE%auto_render.py" --episode GG_EP012 --music "%MUSIC%"

echo.
echo Done. Check renders\GG_EP012_final.mp4
pause
