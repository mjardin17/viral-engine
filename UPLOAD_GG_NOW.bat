@echo off
title Empire OS — GG Full Episode Uploader
cd /d C:\Users\jjard\claude\video-bot-pipeline

echo.
echo ============================================================
echo   GODS ^& GLORY — Smart Batch Uploader
echo   Rule: Only episodes ^>= 40 min get uploaded
echo   Auto-retries 3x on any error
echo   Skips already-uploaded episodes automatically
echo ============================================================
echo.

:: First do a dry run to show what will upload
echo === DRY RUN (what WOULD be uploaded) ===
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe upload_gg_full.py --min-min 38

echo.
echo ============================================================
echo  Review the list above.
echo  Press any key to START UPLOADING, or close this window to cancel.
echo ============================================================
pause

echo.
echo === UPLOADING NOW ===
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe upload_gg_full.py --min-min 38 --go

echo.
echo Log saved to: upload_gg_full.log
pause
