@echo off
title TEST — new pipeline, images-only mode, EP002
py "%~dp0auto_render.py" --episode GG_EP002 --skip-images --images-only
echo.
echo ============================================================
echo If you see "IMAGES READY FOR REVIEW" above with no Python
echo errors, the new code works correctly.
echo ============================================================
pause
