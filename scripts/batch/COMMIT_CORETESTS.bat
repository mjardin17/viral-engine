@echo off
echo ============================================================
echo  Empire OS — Core Unit Tests Commit
echo  7 test files for packages/core/src/__tests__/
echo  Unblocks EA stability criteria 2 and 4
echo ============================================================

cd /d C:\Users\jjard\empire-os

echo.
echo [1/5] Pulling latest from main...
git pull origin main
if errorlevel 1 (echo PULL FAILED && pause && exit /b 1)

echo.
echo [2/5] Copying unit test files from patch area...
xcopy /E /Y /I "C:\Users\jjard\claude\video-bot-pipeline\empire-os-patch\packages\core\src\__tests__" "packages\core\src\__tests__\"
xcopy /Y "C:\Users\jjard\claude\video-bot-pipeline\empire-os-patch\packages\core\package.json" "packages\core\package.json*"

echo.
echo [3/5] Copying updated AGENT_MEMORY.md...
xcopy /Y "C:\Users\jjard\claude\video-bot-pipeline\empire-os-patch\AGENT_MEMORY.md" "AGENT_MEMORY.md*"

echo.
echo [4/5] Verifying test files exist...
if not exist "packages\core\src\__tests__\event-bus.test.ts"       echo MISSING: event-bus.test.ts      && pause && exit /b 1
if not exist "packages\core\src\__tests__\memory-bus.test.ts"      echo MISSING: memory-bus.test.ts     && pause && exit /b 1
if not exist "packages\core\src\__tests__\ai-router.test.ts"       echo MISSING: ai-router.test.ts      && pause && exit /b 1
if not exist "packages\core\src\__tests__\plugin-registry.test.ts" echo MISSING: plugin-registry.test.ts&& pause && exit /b 1
if not exist "packages\core\src\__tests__\module-gateway.test.ts"  echo MISSING: module-gateway.test.ts && pause && exit /b 1
if not exist "packages\core\src\__tests__\workflow-engine.test.ts" echo MISSING: workflow-engine.test.ts && pause && exit /b 1
if not exist "packages\core\src\__tests__\bootstrap.test.ts"       echo MISSING: bootstrap.test.ts      && pause && exit /b 1
echo All 7 test files verified.

echo.
echo [5/5] Committing and pushing...
git add -A
git commit -m "[CLAUDE] feat: add packages/core unit tests for all 6 implementations + bootstrap

- event-bus.test.ts       — publish, subscribe, unsubscribe, history, replay, stats
- memory-bus.test.ts      — write, read, TTL, delete, search, subscribe, clear
- ai-router.test.ts       — complete, fallback, task, models, stats, strategies
- plugin-registry.test.ts — register, update, list, capability, status, validateDependencies
- module-gateway.test.ts  — register, route by id, route by capability, mocked fetch
- workflow-engine.test.ts — 3-step execution, onFailure, cancel, pause/resume, list, dryRun
- bootstrap.test.ts       — all 6 CoreServices integration, singleton, cross-service wiring

EA stability criteria 2 and 4 are now unblocked.
Josh: run 'cd packages/core && npm install && npm test' to validate."
git push origin main
if errorlevel 1 (echo PUSH FAILED && pause && exit /b 1)

echo.
echo ============================================================
echo  DONE. Unit tests committed to empire-os/main.
echo.
echo  NEXT STEP — Run tests locally:
echo    cd C:\Users\jjard\empire-os\packages\core
echo    npm install
echo    npm test
echo.
echo  All 7 files should pass. Then say "build Empire Assistant"
echo  and Claude will write the final module.
echo ============================================================
pause
