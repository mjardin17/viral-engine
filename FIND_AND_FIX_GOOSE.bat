@echo off
cd /d "%~dp0"
set ENV_FILE=%~dp0empire-os-patch\apps\empire-os-server\.env
set FOUND=
set GOOSE_PATH=

echo Searching for Goose...
echo.

REM 1. Check PATH
where goose 2>nul
if not errorlevel 1 (
    for /f "tokens=*" %%i in ('where goose') do (
        if not defined GOOSE_PATH set "GOOSE_PATH=%%i"
    )
    if defined GOOSE_PATH goto :found
)

REM 2. Block installer default
if exist "%USERPROFILE%\.local\bin\goose.exe" (
    set "GOOSE_PATH=%USERPROFILE%\.local\bin\goose.exe"
    goto :found
)

REM 3. AppData\Local\Programs
if exist "%LOCALAPPDATA%\Programs\goose\goose.exe" (
    set "GOOSE_PATH=%LOCALAPPDATA%\Programs\goose\goose.exe"
    goto :found
)
if exist "%LOCALAPPDATA%\goose\goose.exe" (
    set "GOOSE_PATH=%LOCALAPPDATA%\goose\goose.exe"
    goto :found
)

REM 4. Scoop
if exist "%USERPROFILE%\scoop\apps\goose\current\goose.exe" (
    set "GOOSE_PATH=%USERPROFILE%\scoop\apps\goose\current\goose.exe"
    goto :found
)

REM 5. Cargo
if exist "%USERPROFILE%\.cargo\bin\goose.exe" (
    set "GOOSE_PATH=%USERPROFILE%\.cargo\bin\goose.exe"
    goto :found
)

REM 6. Deep search AppData (slower)
echo Doing deep search, please wait...
for /r "%USERPROFILE%\AppData" %%f in (goose.exe) do (
    if not defined GOOSE_PATH set "GOOSE_PATH=%%f"
)
if defined GOOSE_PATH goto :found

echo.
echo Goose NOT found on this machine.
echo Install from: https://github.com/block/goose/releases
pause
exit /b 1

:found
echo Found: %GOOSE_PATH%
echo Verifying...
"%GOOSE_PATH%" --version 2>&1
if errorlevel 1 (
    echo ERROR: Found but --version failed. Check the path manually.
    pause
    exit /b 1
)

REM Write GOOSE_BIN into .env automatically — no pasting needed
echo.
echo Writing GOOSE_BIN to .env...

REM Build a temp copy of .env with GOOSE_BIN filled in
set TEMP_ENV=%TEMP%\empire_env_tmp.txt
if exist "%TEMP_ENV%" del "%TEMP_ENV%"

for /f "usebackq delims=" %%L in ("%ENV_FILE%") do (
    echo %%L | findstr /b "GOOSE_BIN=" >nul
    if not errorlevel 1 (
        echo GOOSE_BIN=%GOOSE_PATH%>> "%TEMP_ENV%"
    ) else (
        echo %%L>> "%TEMP_ENV%"
    )
)

copy /Y "%TEMP_ENV%" "%ENV_FILE%" >nul
del "%TEMP_ENV%"

echo.
echo ═══════════════════════════════════════════════════════
echo  DONE — Goose is wired up.
echo  Path: %GOOSE_PATH%
echo  Written to: %ENV_FILE%
echo.
echo  Now restart Empire OS:
echo    cd empire-os-patch\apps\empire-os-server
echo    npx tsx server.ts
echo ═══════════════════════════════════════════════════════
pause
