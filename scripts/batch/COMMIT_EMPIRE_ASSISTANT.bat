@echo off
cd /d "C:\Users\jjard\claude\video-bot-pipeline"
echo Copying Empire Assistant V2 to empire-os...

mkdir "C:\Users\jjard\empire-os\apps\empire-assistant" 2>nul
copy /Y "C:\Users\jjard\claude\video-bot-pipeline\empire-os-patch\apps\empire-assistant\empire-assistant.module.ts" "C:\Users\jjard\empire-os\apps\empire-assistant\empire-assistant.module.ts"
copy /Y "C:\Users\jjard\claude\video-bot-pipeline\empire-os-patch\apps\empire-assistant\index.ts" "C:\Users\jjard\empire-os\apps\empire-assistant\index.ts"
copy /Y "C:\Users\jjard\claude\video-bot-pipeline\empire-os-patch\apps\empire-assistant\package.json" "C:\Users\jjard\empire-os\apps\empire-assistant\package.json"
copy /Y "C:\Users\jjard\claude\video-bot-pipeline\empire-os-patch\AGENT_MEMORY.md" "C:\Users\jjard\empire-os\AGENT_MEMORY.md"

echo.
echo Committing to video-bot-pipeline repo...
git add -A
git commit -m "[CLAUDE] feat: build Empire Assistant V2 EmpireModule (apps/empire-assistant/)"
git push origin main
echo.
echo Done! Empire Assistant V2 is live.
pause
