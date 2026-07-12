@echo off
title Empire OS — LO EP001 Higgsfield Assembly
cd /d C:\Users\jjard\claude\video-bot-pipeline

echo.
echo ============================================================
echo   LITTLE OLYMPUS EP001 — Higgsfield Version (Animated)
echo   "Little Zeus Gets His Thunderbolt"
echo ============================================================
echo.

:: Ensure output dir exists and video_urls.json is in place
mkdir output\LO_EP001_HIGGSFIELD 2>nul
if not exist output\LO_EP001_HIGGSFIELD\video_urls.json (
    copy video_urls.json output\LO_EP001_HIGGSFIELD\video_urls.json >nul
    echo Copied video_urls.json to work dir.
)

:: Run assembly — log everything, then show log
echo Running assemble_lo_ep001_higgsfield.py ...
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe assemble_lo_ep001_higgsfield.py > output\LO_EP001_HIGGSFIELD\assemble_log.txt 2>&1

echo.
echo ---- OUTPUT LOG ----
type output\LO_EP001_HIGGSFIELD\assemble_log.txt
echo ---- END LOG ----
echo.

if %errorlevel% neq 0 (
    echo !! FAILED — see log above. Full log at:
    echo    output\LO_EP001_HIGGSFIELD\assemble_log.txt
) else (
    echo Done! Check renders\LO_EP001_HIGGSFIELD_final.mp4
)
echo.
pause
