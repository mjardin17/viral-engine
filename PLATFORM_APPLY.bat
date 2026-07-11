@echo off
title Empire OS - Platform Application Tracker
set PYTHON=C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe
set BASE=%~dp0

echo.
echo ============================================================
echo   EMPIRE OS - PLATFORM APPLICATIONS
echo   Apply to MBA, TikTok Shop, Amazon Associates, Etsy
echo ============================================================
echo.
echo   Commands:
echo     PLATFORM_APPLY.bat                      -- show status
echo     PLATFORM_APPLY.bat --apply mba          -- apply to Merch by Amazon
echo     PLATFORM_APPLY.bat --apply tiktok-shop  -- apply to TikTok Shop
echo     PLATFORM_APPLY.bat --apply etsy         -- set up Etsy Seller
echo     PLATFORM_APPLY.bat --apply amazon-associates -- affiliate program
echo     PLATFORM_APPLY.bat --mark-approved mba  -- mark as approved
echo.

"%PYTHON%" "%BASE%merch_empire\platform_tracker.py" %*
pause
