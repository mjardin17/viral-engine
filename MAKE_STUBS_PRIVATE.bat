@echo off
title Empire OS — Make All S2 Stub Episodes Private
cd /d C:\Users\jjard\claude\video-bot-pipeline

chcp 65001 >nul
set PYTHONIOENCODING=utf-8

echo.
echo ============================================================
echo   GODS ^& GLORY — Set ALL S2 Stub Episodes to Private
echo   EP006 Greece / EP007 Gaugamela / EP008 Stalingrad
echo   EP009 Iwo Jima / EP010 Vietnam / EP011 Constantinople
echo ============================================================
echo.

echo === DRY RUN (showing what WOULD change) ===
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe make_stubs_private.py > stubs_private_log.txt 2>&1
type stubs_private_log.txt

echo.
echo ============================================================
echo  Review the above. Press any key to SET TO PRIVATE, or close to cancel.
echo ============================================================
pause

echo.
echo === SETTING VIDEOS TO PRIVATE ===
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe make_stubs_private.py --go

echo.
pause
