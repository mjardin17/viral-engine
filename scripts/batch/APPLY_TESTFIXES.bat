@echo off
echo =============================================
echo APPLY TEST FIXES — 3 files
echo =============================================

echo.
echo [1/3] event-bus.impl.ts (fixes history+stats field/method naming collision)
robocopy "C:\Users\jjard\claude\video-bot-pipeline\empire-os-patch\packages\core\src\implementations" "C:\Users\jjard\empire-os\packages\core\src\implementations" event-bus.impl.ts
echo.

echo [2/3] workflow-engine.impl.ts (fixes runInstance overwriting rejected/cancelled status)
robocopy "C:\Users\jjard\claude\video-bot-pipeline\empire-os-patch\packages\core\src\implementations" "C:\Users\jjard\empire-os\packages\core\src\implementations" workflow-engine.impl.ts
echo.

echo [3/3] workflow-engine.test.ts (fixes topic string + reject test)
robocopy "C:\Users\jjard\claude\video-bot-pipeline\empire-os-patch\packages\core\src\__tests__" "C:\Users\jjard\empire-os\packages\core\src\__tests__" workflow-engine.test.ts
echo.

echo =============================================
echo Files copied. Now run:
echo   cd C:\Users\jjard\empire-os\packages\core
echo   "C:\Users\jjard\AppData\Roaming\npm\pnpm.cmd" test
echo =============================================
pause
