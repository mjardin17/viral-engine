@echo off
REM ============================================================
REM GODS & GLORY — Render ALL Episodes to 45+ Minutes
REM EP001-EP011 (S1+S2) + EP012-EP025 (S3)
REM Runs overnight — 8-16 hours total
REM ============================================================

setlocal
cd /d "%~dp0"

REM ---- Python 3.14 confirmed at this path (FIND_PYTHON.bat verified 7/7/2026) ----
set PYTHON=%LOCALAPPDATA%\Programs\Python\Python314\python.exe

if not exist "%PYTHON%" (
    echo ERROR: Python 3.14 not found at:
    echo   %PYTHON%
    echo Run FIND_PYTHON.bat to locate Python, then update this file.
    pause
    exit /b 1
)

REM ---- Add local ffmpeg to PATH ----
set FFBIN=%~dp0ffmpeg_bin
if exist "%FFBIN%\ffmpeg.exe" goto :use_local_ffmpeg
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ERROR: ffmpeg not found!
    echo Run INSTALL_FFMPEG.bat first, then come back here.
    pause
    exit /b 1
)
goto :ffmpeg_ready

:use_local_ffmpeg
set "PATH=%FFBIN%;%PATH%"
echo ffmpeg found locally: %FFBIN%

:ffmpeg_ready

echo.
echo ================================================
echo  GODS ^& GLORY — Full 45-Min Render Run
echo  Python: %PYTHON%
echo  %date% %time%
echo ================================================
echo.

REM ---- Install required packages once ----
echo Installing required packages...
"%PYTHON%" -m pip install requests pillow edge-tts --quiet
echo Packages ready.
echo.

REM ---- SEASON 1 + 2 (EP001-EP011) ----
echo [S1/S2] Rendering EP001 through EP011...
echo.

"%PYTHON%" auto_render.py --episode GG_EP001
"%PYTHON%" auto_render.py --episode GG_EP002
"%PYTHON%" auto_render.py --episode GG_EP003
"%PYTHON%" auto_render.py --episode GG_EP004
"%PYTHON%" auto_render.py --episode GG_EP005
"%PYTHON%" auto_render.py --episode GG_EP006
"%PYTHON%" auto_render.py --episode GG_EP007
"%PYTHON%" auto_render.py --episode GG_EP008
"%PYTHON%" auto_render.py --episode GG_EP009
"%PYTHON%" auto_render.py --episode GG_EP010
"%PYTHON%" auto_render.py --episode GG_EP011

REM ---- SEASON 3 (EP012-EP025) ----
echo.
echo [S3] Rendering EP012 through EP025...
echo.

"%PYTHON%" auto_render.py --episode GG_EP012
"%PYTHON%" auto_render.py --episode GG_EP013
"%PYTHON%" auto_render.py --episode GG_EP014
"%PYTHON%" auto_render.py --episode GG_EP015
"%PYTHON%" auto_render.py --episode GG_EP016
"%PYTHON%" auto_render.py --episode GG_EP017
"%PYTHON%" auto_render.py --episode GG_EP018
"%PYTHON%" auto_render.py --episode GG_EP019
"%PYTHON%" auto_render.py --episode GG_EP020
"%PYTHON%" auto_render.py --episode GG_EP021
"%PYTHON%" auto_render.py --episode GG_EP022
"%PYTHON%" auto_render.py --episode GG_EP023
"%PYTHON%" auto_render.py --episode GG_EP024
"%PYTHON%" auto_render.py --episode GG_EP025

echo.
echo ================================================
echo  ALL DONE — 25 episodes rendered
echo  Check renders\ folder for finals
echo  %date% %time%
echo ================================================
echo.
pause
