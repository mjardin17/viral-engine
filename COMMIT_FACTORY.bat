@echo off
title Empire OS — Commit Factory Fix
cd /d C:\Users\jjard\claude\video-bot-pipeline

echo Clearing git lock if present...
if exist .git\index.lock del /f .git\index.lock

echo.
git add voice_music_factory.py run_factory.py
git commit -m "[CLAUDE] fix: voice_music_factory imports, video pipeline, emotion passthrough in run_factory"
echo.
echo Done. Run PUSH_NOW.bat to push.
pause
