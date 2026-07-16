@echo off
echo Cleaning up intermediate render files...
rmdir /s /q "%~dp0_work_ep005" 2>nul
rmdir /s /q "%~dp0_backups" 2>nul
rmdir /s /q "%~dp0renders\ep006\_work" 2>nul
rmdir /s /q "%~dp0renders\custom\_work" 2>nul
rmdir /s /q "%~dp0renders\iron_legends\_work_il_ep001" 2>nul
rmdir /s /q "%~dp0renders\little_olympus\_work_lo_ep001" 2>nul
rmdir /s /q "%~dp0output" 2>nul
echo Done! Disk space freed.
pause
