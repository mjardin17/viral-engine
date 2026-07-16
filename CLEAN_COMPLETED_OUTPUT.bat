@echo off
title EMPIRE OS — Clean Completed Output Folders
echo.
echo This deletes output/ scratch for episodes that have finals in renders/
echo EP016 is skipped (still rendering).
echo.

set BASE=%~dp0output

echo [1/7] GG_EP004 (333 MB - final exists)...
if exist "%BASE%\GG_EP004" (rd /s /q "%BASE%\GG_EP004" && echo Done.) else echo Not found.

echo [2/7] GG_EP009 (209 MB - final exists)...
if exist "%BASE%\GG_EP009" (rd /s /q "%BASE%\GG_EP009" && echo Done.) else echo Not found.

echo [3/7] GG_EP010 (904 MB - final exists)...
if exist "%BASE%\GG_EP010" (rd /s /q "%BASE%\GG_EP010" && echo Done.) else echo Not found.

echo [4/7] GG_EP011 (8 MB - final exists)...
if exist "%BASE%\GG_EP011" (rd /s /q "%BASE%\GG_EP011" && echo Done.) else echo Not found.

echo [5/7] GG_EP014 (154 MB - final exists)...
if exist "%BASE%\GG_EP014" (rd /s /q "%BASE%\GG_EP014" && echo Done.) else echo Not found.

echo [6/7] GG_EP015 (911 MB - final exists)...
if exist "%BASE%\GG_EP015" (rd /s /q "%BASE%\GG_EP015" && echo Done.) else echo Not found.

echo [7/7] LO_EP001_HIGGSFIELD (561 MB - final exists at renders/)...
if exist "%BASE%\LO_EP001_HIGGSFIELD" (rd /s /q "%BASE%\LO_EP001_HIGGSFIELD" && echo Done.) else echo Not found.

echo.
echo ============================================================
echo  FREED ~3.1 GB  (GG_EP016 preserved - still rendering)
echo ============================================================
echo.
echo Also run Windows Disk Cleanup for more space:
echo   Press Win+R, type: cleanmgr, Enter
echo.
pause
