@echo off
echo =============================================
echo FORCE COPY TEST FIXES (copy /Y = always overwrite)
echo =============================================

echo.
echo [1/3] event-bus.impl.ts
copy /Y "C:\Users\jjard\claude\video-bot-pipeline\empire-os-patch\packages\core\src\implementations\event-bus.impl.ts" "C:\Users\jjard\empire-os\packages\core\src\implementations\event-bus.impl.ts"

echo.
echo [2/3] workflow-engine.impl.ts
copy /Y "C:\Users\jjard\claude\video-bot-pipeline\empire-os-patch\packages\core\src\implementations\workflow-engine.impl.ts" "C:\Users\jjard\empire-os\packages\core\src\implementations\workflow-engine.impl.ts"

echo.
echo [3/3] workflow-engine.test.ts
copy /Y "C:\Users\jjard\claude\video-bot-pipeline\empire-os-patch\packages\core\src\__tests__\workflow-engine.test.ts" "C:\Users\jjard\empire-os\packages\core\src\__tests__\workflow-engine.test.ts"

echo.
echo =============================================
echo Done. Now run:
echo   cd C:\Users\jjard\empire-os\packages\core
echo   "C:\Users\jjard\AppData\Roaming\npm\pnpm.cmd" test
echo =============================================
pause
