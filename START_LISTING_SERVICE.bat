@echo off
title Boss Listers - Listing Service (DRY RUN / DRAFT ONLY)
set PYTHONUTF8=1
set BASE=%~dp0
:: `py` launcher is not on PATH on this machine — use the full interpreter path
set PYEXE=C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe

echo.
echo ============================================================
echo   Listing Service (eBay + Etsy) — DRY RUN / DRAFT ONLY
echo   No real eBay listing or Etsy activation can happen while
echo   running this way. Use START_LISTING_SERVICE_LIVE.bat to
echo   enable real publishing for a specific platform.
echo ============================================================
echo.
"%PYEXE%" "%BASE%scripts\listing_service.py"
