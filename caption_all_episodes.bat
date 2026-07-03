@echo off
title Caption + Voice Finalize Pass - GG_EP001 to GG_EP005
set MUSIC=%~dp0music\battle_epic.mp3

echo ============================================================
echo   Burns captions onto every already-rendered scene clip,
echo   then rebuilds renders\GG_EPxxx_final.mp4 with music.
echo   Does NOT re-fetch images or redo narration - just adds
echo   subtitles to what's already there and reassembles.
echo   Safe to stop and re-run - it skips scenes already done.
echo ============================================================
echo.

for %%E in (GG_EP001 GG_EP002 GG_EP003 GG_EP004 GG_EP005) do (
    echo.
    echo ==== %%E : captioning scenes ====
    py "%~dp0caption_finalize_v3.py" --episode %%E --mode caption --max-scenes 999
    echo ==== %%E : reassembling final.mp4 ====
    py "%~dp0caption_finalize_v3.py" --episode %%E --mode finalize --music "%MUSIC%"
)

echo.
echo ============================================================
echo   ALL DONE - renders\ now has captioned final.mp4 for EP001-005
echo ============================================================
pause
