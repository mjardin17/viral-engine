@echo off
title VIRAL ENGINE — Full Render Batch
echo.
echo ============================================================
echo   VIRAL ENGINE  —  FULL RENDER BATCH
echo   EP002 Gaugamela  /  EP003 Cannae
echo   EP004 Mongols    /  EP005 Constantinople
echo ============================================================
echo.

echo [1/5]  Saving today's images from Downloads to character_images...
py "%~dp0copy_new_images.py"
echo.

echo [2/5]  Rendering GG_EP002 — Gaugamela: The Battle That Ended an Empire...
py "%~dp0auto_render.py" --episode GG_EP002
echo.

echo [3/5]  Rendering GG_EP003 — Cannae: The Perfect Battle...
py "%~dp0auto_render.py" --episode GG_EP003
echo.

echo [4/5]  Rendering GG_EP004 — The Mongol War Machine...
py "%~dp0auto_render.py" --episode GG_EP004
echo.

echo [5/5]  Rendering GG_EP005 — Constantinople 1453: The End of an Age...
py "%~dp0auto_render.py" --episode GG_EP005
echo.

echo ============================================================
echo   ALL DONE!  Check the  renders/  folder for your MP4s:
echo     renders\GG_EP002_final.mp4
echo     renders\GG_EP003_final.mp4
echo     renders\GG_EP004_final.mp4
echo     renders\GG_EP005_final.mp4
echo ============================================================
echo.
pause
