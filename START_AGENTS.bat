@echo off
REM Start all Empire OS agents
REM Video Pipeline: Renders episodes and commercials
REM Crosslister: Monitors inventory for new items
REM Platform Sync: Pushes items to all resale platforms
REM Sales Tracker: Monitors platforms for sold items
REM Price Sync: Syncs prices bidirectionally

setlocal enabledelayedexpansion

REM Agent keypair
set BUZZ_PRIVATE_KEY=31a697cb1a00d32c0ef5ef7b03dee1567e24d7798cb225302864f886d2af0f04
set BUZZ_RELAY_URL=ws://localhost:3000

REM Python path
set PYTHON_PATH=C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe

REM Force UTF-8 stdout. Without this, Python 3.14 uses the console's cp1252
REM codepage and EVERY print() containing an emoji raises UnicodeEncodeError
REM and kills the agent. There are 447 such print() calls across agents/,
REM lib/ and council/ -- platform_sync_agent and whatnot_specialist_agent die
REM on their startup banner; the rest die on their first status message.
REM Verified 2026-08-15: the same print succeeds with this set and raises without it.
set PYTHONUTF8=1

echo.
echo ================================================
echo Empire OS Agent Coordinator (5 Agents)
echo ================================================
echo Relay: %BUZZ_RELAY_URL%
echo.
echo Agents:
echo   1. Video Pipeline Agent     (render jobs)
echo   2. Crosslister Agent        (monitor inventory)
echo   3. Platform Sync Agent      (push to platforms)
echo   4. Sales Tracker Agent      (monitor sales)
echo   5. Price Sync Agent         (sync prices)
echo.
echo Channels:
echo   #video-pipeline   (render status)
echo   #commercials      (commercial production)
echo   #inventory-sync   (crosslisting status)
echo.

REM Start agents in separate windows
start "Video Pipeline Agent" cmd /c "%PYTHON_PATH% agents\video_pipeline_agent.py"
timeout /t 2
start "Crosslister Agent" cmd /c "%PYTHON_PATH% agents\crosslister_agent.py"
timeout /t 2
start "Platform Sync Agent" cmd /c "%PYTHON_PATH% agents\platform_sync_agent.py"
timeout /t 2
start "Sales Tracker Agent" cmd /c "%PYTHON_PATH% agents\sales_tracker_agent.py"
timeout /t 2
start "Price Sync Agent" cmd /c "%PYTHON_PATH% agents\price_sync_agent.py"
timeout /t 2
start "Whatnot Specialist Agent" cmd /c "%PYTHON_PATH% agents\whatnot_specialist_agent.py"

echo.
echo All 6 agents started. Check their windows for status.
echo.
echo Agents:
echo   - Video Pipeline (renders episodes + commercials)
echo   - Crosslister (monitor inventory for auctions)
echo   - Platform Sync (push to 18 platforms)
echo   - Sales Tracker (monitor sales, update inventory)
echo   - Price Sync (sync prices bidirectionally)
echo   - Whatnot Specialist (orchestrate auctions, optimize ROI)
echo   - Scanner Uploader (Epson ES-400 II → Boss Listers)
echo.
echo Council Bots (quality + optimization):
echo   - Bot 18: Whatnot Quality Checker
echo   - Bot 19: Whatnot Bid Analyzer
echo   - Bot 20: Whatnot ROI Optimizer
echo.
echo Monitor in Buzz: http://localhost:3000
echo.
pause
