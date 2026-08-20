@echo off
title Boss Listers - Listing Service (LIVE PUBLISHING ARMED)
set PYTHONUTF8=1
set BASE=%~dp0
:: `py` launcher is not on PATH on this machine — use the full interpreter path
set PYEXE=C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe

if "%~1"=="" (
  echo.
  echo ============================================================
  echo   USAGE: START_LISTING_SERVICE_LIVE.bat ebay^|etsy^|ebay,etsy
  echo.
  echo   You must name which platform(s) to arm. Live publishing is
  echo   per-platform on purpose — arming eBay must never accidentally
  echo   arm Etsy, or vice versa.
  echo ============================================================
  echo.
  pause
  exit /b 1
)
set PLATFORMS=%~1

if "%LISTING_SERVICE_TOKEN%"=="" if "%EBAY_LISTING_SERVICE_TOKEN%"=="" (
  echo.
  echo ============================================================
  echo   REFUSING TO START.
  echo   LISTING_SERVICE_TOKEN is not set in this shell.
  echo.
  echo   This is deliberate — live publishing must not be armable
  echo   by just double-clicking a file. Set a real secret first:
  echo.
  echo       set LISTING_SERVICE_TOKEN=some-long-random-value
  echo.
  echo   then run this file again from the SAME shell.
  echo ============================================================
  echo.
  pause
  exit /b 1
)

echo.
echo ============================================================
echo   WARNING: LIVE PUBLISHING WILL BE ARMED FOR: %PLATFORMS%
echo   Requests with dry_run:false, the correct confirm literal,
echo   AND the correct X-Listing-Service-Token header WILL create
echo   real, public, live listings on the real production seller
echo   account for %PLATFORMS%. This is not a drill.
echo ============================================================
echo.
set /p CONFIRM="Type YES to continue: "
if /I not "%CONFIRM%"=="YES" (
  echo Aborted.
  exit /b 1
)

"%PYEXE%" "%BASE%scripts\listing_service.py" --allow-live %PLATFORMS%
