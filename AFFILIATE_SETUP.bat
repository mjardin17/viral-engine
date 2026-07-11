@echo off
title Empire OS - Affiliate Empire Setup
set PYTHON=C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe
set BASE=%~dp0

echo.
echo ============================================================
echo   EMPIRE OS - AFFILIATE EMPIRE
echo   Apply for every program. Stack commissions on everything.
echo ============================================================
echo.
echo   Commands:
echo     AFFILIATE_SETUP.bat              -- show status
echo     AFFILIATE_SETUP.bat --all        -- walk through every program
echo     AFFILIATE_SETUP.bat --apply nordvpn     -- apply to one program
echo     AFFILIATE_SETUP.bat --mark-joined nordvpn --id YOUR_ID
echo.

"%PYTHON%" "%BASE%affiliate_empire\tracker.py" %*
pause
