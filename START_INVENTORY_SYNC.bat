@echo off
setlocal

REM Inventory sync — list active Supabase products on eBay

cd /d "%~dp0"

echo.
echo Inventory Sync - DRY RUN (preview mode)
echo ============================================================
echo.

python scripts\inventory_sync.py

if errorlevel 1 (
    echo.
    echo ERROR: Sync failed. Check error above.
    echo To go LIVE, edit scripts/inventory_sync.py and set DRY_RUN = False
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Sync complete. To go LIVE, edit scripts/inventory_sync.py
echo and set DRY_RUN = False, then run this script again.
echo.
pause
