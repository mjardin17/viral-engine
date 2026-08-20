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

REM DISABLED 2026-08-20: Platform Sync, Sales Tracker, Price Sync, and Whatnot
REM Specialist all import lib/platform_connectors.py, which was audited today
REM and found non-functional -- 10 of its 16 connectors have zero credentials
REM configured anywhere, 2 more (Facebook/Mercari) read the wrong env var name
REM so real credentials that DO exist are never found, and several hit API
REM endpoints that don't correspond to any real public developer program
REM (Depop/Grailed/Vinted/Vestiaire). This has been launching since 2026-08-09
REM without ever completing one real sync. Left auto-starting only what's
REM real: Video Pipeline (rendering) and Crosslister (local inventory
REM monitoring, no external platform dependency). Re-enable per-agent only
REM after lib/platform_connectors.py is fixed or replaced -- see CLAUDE.md
REM "2026-08-20 -- platform_connectors.py audited, found non-functional".
start "Video Pipeline Agent" cmd /c "%PYTHON_PATH% agents\video_pipeline_agent.py"
timeout /t 2
start "Crosslister Agent" cmd /c "%PYTHON_PATH% agents\crosslister_agent.py"

echo.
echo 2 agents started (Platform Sync / Sales Tracker / Price Sync / Whatnot
echo Specialist disabled 2026-08-20 -- see CLAUDE.md, they never worked).
echo.
echo Agents:
echo   - Video Pipeline (renders episodes + commercials)
echo   - Crosslister (monitor inventory for auctions)
echo.
echo Council Bots (quality + optimization):
echo   - Bot 18: Whatnot Quality Checker
echo   - Bot 19: Whatnot Bid Analyzer
echo   - Bot 20: Whatnot ROI Optimizer
echo.
echo Monitor in Buzz: http://localhost:3000
echo.
pause
