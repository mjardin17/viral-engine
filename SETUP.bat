@echo off
title Empire OS - Setup Wizard
set PYTHON=C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe
set BASE=%~dp0

echo.
echo ============================================================
echo   EMPIRE OS SETUP WIZARD
echo   Enter your keys and passwords once. Done forever.
echo ============================================================
echo.

"%PYTHON%" "%BASE%setup_wizard.py" %*

echo.
pause
