@echo off
title DISK AUDIT — Empire OS
set OUT=C:\Users\jjard\disk_audit.txt

echo === DISK AUDIT %DATE% %TIME% === > %OUT%
echo. >> %OUT%

echo --- TOP DISK CONSUMERS --- >> %OUT%
echo. >> %OUT%

echo [Downloads] >> %OUT%
powershell -command "(Get-ChildItem 'C:\Users\jjard\Downloads' -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB | Write-Host -NoNewline" >> %OUT%
echo  MB >> %OUT%

echo [Downloads - JPEG files only] >> %OUT%
powershell -command "(Get-ChildItem 'C:\Users\jjard\Downloads' -Filter '*.jpg' -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB | Write-Host -NoNewline" >> %OUT%
echo  MB >> %OUT%

echo [renders/] >> %OUT%
powershell -command "(Get-ChildItem 'C:\Users\jjard\claude\video-bot-pipeline\renders' -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB | Write-Host -NoNewline" >> %OUT%
echo  MB >> %OUT%

echo [output/] >> %OUT%
powershell -command "(Get-ChildItem 'C:\Users\jjard\claude\video-bot-pipeline\output' -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB | Write-Host -NoNewline" >> %OUT%
echo  MB >> %OUT%

echo [empire-os-hub/node_modules] >> %OUT%
powershell -command "(Get-ChildItem 'C:\Users\jjard\claude\video-bot-pipeline\empire-os-hub\node_modules' -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB | Write-Host -NoNewline" >> %OUT%
echo  MB >> %OUT%

echo [.ollama/] >> %OUT%
powershell -command "(Get-ChildItem 'C:\Users\jjard\.ollama' -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB | Write-Host -NoNewline" >> %OUT%
echo  MB >> %OUT%

echo [.conda/] >> %OUT%
powershell -command "(Get-ChildItem 'C:\Users\jjard\.conda' -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB | Write-Host -NoNewline" >> %OUT%
echo  MB >> %OUT%

echo [.pinokio/] >> %OUT%
powershell -command "(Get-ChildItem 'C:\Users\jjard\.pinokio' -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB | Write-Host -NoNewline" >> %OUT%
echo  MB >> %OUT%

echo [.docker/] >> %OUT%
powershell -command "(Get-ChildItem 'C:\Users\jjard\.docker' -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB | Write-Host -NoNewline" >> %OUT%
echo  MB >> %OUT%

echo [.cursor/] >> %OUT%
powershell -command "(Get-ChildItem 'C:\Users\jjard\.cursor' -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB | Write-Host -NoNewline" >> %OUT%
echo  MB >> %OUT%

echo [AppData/Local/Temp] >> %OUT%
powershell -command "(Get-ChildItem 'C:\Users\jjard\AppData\Local\Temp' -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB | Write-Host -NoNewline" >> %OUT%
echo  MB >> %OUT%

echo [AppData/Local Programs/Python] >> %OUT%
powershell -command "(Get-ChildItem 'C:\Users\jjard\AppData\Local\Programs\Python' -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB | Write-Host -NoNewline" >> %OUT%
echo  MB >> %OUT%

echo. >> %OUT%
echo --- renders/ FILES (MP4s) --- >> %OUT%
dir /s /b "C:\Users\jjard\claude\video-bot-pipeline\renders\*.mp4" >> %OUT% 2>nul

echo. >> %OUT%
echo --- DONE --- >> %OUT%

echo.
echo Audit complete! Results saved to: %OUT%
echo Opening results...
notepad %OUT%
pause
