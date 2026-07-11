@echo off
title Empire OS - Social Media Setup Wizard
set PYTHON=C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe
set BASE=%~dp0

echo.
echo ============================================================
echo   EMPIRE OS - SOCIAL MEDIA SETUP WIZARD
echo   Set up all 4 channels across all platforms
echo   One at a time. Content pre-written. Just create + save.
echo ============================================================
echo.
echo   Commands:
echo     SOCIAL_SETUP.bat              -- full setup walkthrough
echo     SOCIAL_SETUP.bat --status     -- see what's done
echo     SOCIAL_SETUP.bat --generate   -- print all profile content
echo     SOCIAL_SETUP.bat --channel gg -- just Gods and Glory
echo.

"%PYTHON%" "%BASE%social_setup\wizard.py" %*
pause
