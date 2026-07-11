@echo off
cd /d "%~dp0"
set PYTHON=C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe

REM Usage: Edit CHANNEL and TOPIC below, then double-click
REM CHANNEL options: GG, ED, LO, IL, EO

set CHANNEL=GG
set TOPIC=Battle of Lepanto 1571
set SCENES=60

echo ================================================
echo  Empire OS — Gemini Script Generator
echo  Channel: %CHANNEL%
echo  Topic:   %TOPIC%
echo  Scenes:  %SCENES%
echo ================================================
echo.

"%PYTHON%" gemini_engine.py --channel %CHANNEL% --topic "%TOPIC%" --scenes %SCENES%
pause
