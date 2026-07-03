@echo off
title VIRAL ENGINE — Re-Rendering GG_EP006 (Pearl Harbor)
set PYTHONUTF8=1
set BASE=%~dp0
set MUSIC=%BASE%music\battle_epic.mp3

echo.
echo ============================================================
echo   Re-rendering GG_EP006 — Pearl Harbor: The Attack That
echo   Woke a Sleeping Giant  (24 scenes, ~19 min)
echo   Script: prompts\gods_glory\scene_prompts.gg_ep006.final.json
echo ============================================================
echo.
echo Starting render... output goes to console.
echo.

py "%BASE%auto_render.py" --episode GG_EP006 --music "%MUSIC%"

echo.
echo ============================================================
echo   Render complete. Check renders\GG_EP006_final.mp4
echo ============================================================
echo.
pause
