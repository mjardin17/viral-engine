@echo off
title VIRAL ENGINE — Patching Fallback Cards
echo.
echo ============================================================
echo   PATCHING FALLBACK CARDS — GODS ^& GLORY SEASON 2
echo   Scans EP006-EP011 for flat-color fallback images,
echo   re-fetches only those slots, rebuilds affected clips.
echo ============================================================
echo.
py "%~dp0patch_fallbacks.py" %*
echo.
pause
