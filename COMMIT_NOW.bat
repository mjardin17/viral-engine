@echo off
title Empire OS - Git Commit
cd /d %~dp0
del /f ".git\index.lock" 2>nul
del /f ".git\HEAD.lock" 2>nul
del /f ".git\index_tmp.lock" 2>nul
git add -A
git commit -m "[CLAUDE] feat: social setup wizard, merch platform tracker, MBA uploader, store catalog builder"
git push origin main
echo.
echo Done. Press any key to close.
pause >nul
