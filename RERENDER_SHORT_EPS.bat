@echo off
title Empire OS — Re-render Short Episodes
cd /d C:\Users\jjard\claude\video-bot-pipeline

echo.
echo ============================================================
echo   Re-rendering EP001, EP003, EP004 with FULL scripts
echo   Bug fixed: renderer now always picks .final.json
echo ============================================================
echo.

echo [1/3] Rendering EP001 - 300 Spartans (55 scenes, ~46 min)...
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe auto_render.py --episode GG_EP001
echo.

echo [2/3] Rendering EP003 - Cannae...
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe auto_render.py --episode GG_EP003
echo.

echo [3/3] Rendering EP004 - Mongol War Machine...
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe auto_render.py --episode GG_EP004
echo.

echo ============================================================
echo   ALL DONE. Check renders/ for GG_EP001/003/004_final.mp4
echo ============================================================
pause
