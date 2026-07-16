@echo off
title EMPIRE OS — Assemble LO EP001 Higgsfield
echo.
echo ============================================================
echo   Little Olympus EP001 — Higgsfield Assembly
echo   Downloads 24 clips from CDN + ElevenLabs TTS
echo   Output: renders\LO_EP001_HIGGSFIELD_final.mp4
echo ============================================================
echo.
echo   NOTE: Requires ELEVENLABS_API_KEY in .env
echo   video_urls.json already restored (24 CDN URLs recovered)
echo.
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe "%~dp0assemble_lo_ep001_higgsfield.py"
echo.
echo ============================================================
echo   DONE — check renders\LO_EP001_HIGGSFIELD_final.mp4
echo ============================================================
pause
