@echo off
REM ============================================================
REM  RUN_TOOL_SCOUT.bat — Empire OS free-tool discovery scan
REM  Finds + live-tests ZERO-SIGNUP AI/media APIs and saves the
REM  ledger to free_tools_discovered.json (read by bot_13).
REM  Usage:
REM    RUN_TOOL_SCOUT.bat            run a fresh scan
REM    RUN_TOOL_SCOUT.bat --report   print last results, no re-scan
REM ============================================================
cd /d C:\Users\jjard\claude\video-bot-pipeline
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe free_tool_scout.py %*
pause
