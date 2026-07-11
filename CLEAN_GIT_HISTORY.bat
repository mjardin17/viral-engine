@echo off
title Empire OS - Purge Credentials from Git History
cd /d C:\Users\jjard\claude\video-bot-pipeline

echo.
echo ============================================================
echo   Purging credentials from ALL git commits
echo   token_gg.pickle + credentials.json removed from history
echo   Then force-pushing. One-time fix.
echo ============================================================
echo.
echo Press any key to start, Ctrl+C to cancel...
pause >nul

echo.
echo Rewriting history...
git filter-branch --force --index-filter "git rm --cached --ignore-unmatch token.pickle token_gg.pickle token_il.pickle token_lo.pickle token_ed.pickle credentials.json" --prune-empty -- --all

echo.
echo Cleaning refs...
git for-each-ref --format="delete %%(refname)" refs/original/ > refs_to_delete.txt
git update-ref --stdin < refs_to_delete.txt
del refs_to_delete.txt 2>nul
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo.
echo Force pushing...
git push origin main --force

echo.
echo DONE. History is clean. Push protection won't block this again.
echo.
pause
