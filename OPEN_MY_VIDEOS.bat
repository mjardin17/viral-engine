@echo off
:: Opens all channel video folders on Desktop — works for every channel
set RENDERS=C:\Users\jjard\claude\video-bot-pipeline\renders

:: GODS AND GLORY
set GG=%USERPROFILE%\Desktop\GODS AND GLORY
if not exist "%GG%" mkdir "%GG%"
copy "%RENDERS%\GG_EP001_final.mp4" "%GG%\EP001 - Thermopylae.mp4" >nul 2>&1
copy "%RENDERS%\GG_EP002_final.mp4" "%GG%\EP002 - Gaugamela.mp4" >nul 2>&1
copy "%RENDERS%\GG_EP003_final.mp4" "%GG%\EP003 - Cannae.mp4" >nul 2>&1
copy "%RENDERS%\GG_EP004_final.mp4" "%GG%\EP004 - Mongols.mp4" >nul 2>&1
copy "%RENDERS%\GG_EP005_final.mp4" "%GG%\EP005 - Constantinople.mp4" >nul 2>&1

:: LITTLE OLYMPUS
set LO=%USERPROFILE%\Desktop\LITTLE OLYMPUS
if not exist "%LO%" mkdir "%LO%"
copy "%RENDERS%\LO_OPENER_final.mp4" "%LO%\LO OPENER.mp4" >nul 2>&1
copy "%RENDERS%\little_olympus\lo_ep001.mp4" "%LO%\EP001 - Little Zeus Gets His Thunderbolt.mp4" >nul 2>&1
copy "%RENDERS%\little_olympus\lo_ep002.mp4" "%LO%\EP002.mp4" >nul 2>&1

:: MACHINE LEARNING
set ML=%USERPROFILE%\Desktop\MACHINE LEARNING
if not exist "%ML%" mkdir "%ML%"
copy "%RENDERS%\ML_EP001_final.mp4" "%ML%\EP001.mp4" >nul 2>&1

echo Done! Opening all channel folders...
explorer "%GG%"
explorer "%LO%"
explorer "%ML%"
