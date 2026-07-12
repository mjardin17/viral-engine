@echo off
where msedge 2>nul
dir "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" 2>nul
dir "C:\Program Files\Microsoft\Edge\Application\msedge.exe" 2>nul
dir "%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe" 2>nul
pause
