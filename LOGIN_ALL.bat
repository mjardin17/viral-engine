@echo off
cd /d "%~dp0"

echo.
echo ============================================================
echo  COUNCIL BOT 15: LOGIN COORDINATOR
echo ============================================================
echo.
echo This will log in to all your accounts from accounts.csv
echo.

if not exist accounts.csv (
    echo ERROR: accounts.csv not found
    echo.
    echo 1. Copy accounts_template.csv to accounts.csv
    echo 2. Fill in your real usernames and passwords
    echo 3. Run this script again
    echo.
    pause
    exit /b 1
)

echo Starting login coordinator...
echo.

C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe council\bots\bot_15_login_coordinator.py

pause
