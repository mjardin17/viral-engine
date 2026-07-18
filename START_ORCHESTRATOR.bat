@echo off
REM ============================================================
REM START_ORCHESTRATOR.bat — launch the Empire OS master orchestrator
REM Reads MISSION_BOARD.json every 30s, dispatches missions to agents,
REM writes results back. bot_11_orchestrator_monitor restarts this if it dies.
REM ============================================================
cd /d C:\Users\jjard\claude\video-bot-pipeline
echo [START_ORCHESTRATOR] Launching Empire OS orchestrator...
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe orchestrator\empire_orchestrator.py
echo [START_ORCHESTRATOR] Orchestrator exited with code %ERRORLEVEL%
pause
