@echo off
REM Video Pipeline Agent launcher
REM Connects to Buzz relay and monitors render jobs

setlocal enabledelayedexpansion

REM Agent keypair (from Buzz relay)
set BUZZ_PRIVATE_KEY=31a697cb1a00d32c0ef5ef7b03dee1567e24d7798cb225302864f886d2af0f04
set BUZZ_RELAY_URL=ws://localhost:3000

REM Python path (from CLAUDE.md)
set PYTHON_PATH=C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe

echo.
echo ============================================
echo Video Pipeline Agent Launcher
echo ============================================
echo Relay: %BUZZ_RELAY_URL%
echo Agent: %BUZZ_PRIVATE_KEY:~0,16%...
echo.

%PYTHON_PATH% agents\video_pipeline_agent.py

pause
