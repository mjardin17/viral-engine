@echo off
set DEST=%USERPROFILE%\Desktop\LITTLE OLYMPUS - FULL EPISODES

if not exist "%DEST%" mkdir "%DEST%"

echo Copying Little Olympus episodes to Desktop...

copy "C:\Users\jjard\claude\video-bot-pipeline\renders\little_olympus\lo_ep001.mp4" "%DEST%\LO EP001 - Little Zeus Gets His Thunderbolt.mp4"
copy "C:\Users\jjard\claude\video-bot-pipeline\renders\little_olympus\lo_ep002.mp4" "%DEST%\LO EP002.mp4"
copy "C:\Users\jjard\claude\video-bot-pipeline\renders\LO_OPENER_final.mp4" "%DEST%\LO OPENER.mp4"

echo Done! Opening folder...
explorer "%DEST%"
