@echo off
title Empire OS - Build Store Catalog
set PYTHON=C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe
set BASE=%~dp0

echo.
echo ============================================================
echo   EMPIRE OS - STORE CATALOG BUILDER
echo   Pulls products from all platforms into one catalog
echo   Generates store_widget.html -- drop it on any website
echo ============================================================
echo.

"%PYTHON%" "%BASE%merch_empire\store_sync.py" --html

echo.
echo   Done! store_widget.html is ready to embed on your site.
echo   Find it at: %BASE%merch_empire\store_widget.html
echo.
pause
