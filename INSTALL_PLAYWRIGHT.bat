@echo off
echo.
echo ============================================================
echo  INSTALLING PLAYWRIGHT (for browser automation)
echo ============================================================
echo.
echo This will install Playwright and browser drivers for:
echo  - Poshmark (automatic listing creation/updates)
echo  - Mercari (automatic listing creation/updates)
echo  - Depop (automatic listing creation/updates)
echo  - Facebook Marketplace (automatic listing creation/updates)
echo.

cd /d "%~dp0"

echo Installing Playwright package...
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe -m pip install playwright -q

echo.
echo Installing browser drivers...
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe -m playwright install chromium

echo.
echo ============================================================
echo ✓ Playwright installed successfully!
echo ============================================================
echo.
echo Next step: Run SETUP_CREDENTIALS.bat to add your login info
echo.
pause
