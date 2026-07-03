@echo off
title VIRAL ENGINE - Patching Fallback Cards
set PYTHONUTF8=1
py "C:\Users\jjard\claude\video-bot-pipeline\patch_fallbacks.py" > "C:\Users\jjard\claude\video-bot-pipeline\patch_log.txt" 2>&1
echo.
echo Done! Check patch_log.txt for results.
pause
