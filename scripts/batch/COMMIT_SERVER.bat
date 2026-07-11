@echo off
REM ═══════════════════════════════════════════════════════════════
REM  Empire OS — Commit server + EA descriptor fix to empire-os
REM  Works from ANY directory — uses absolute paths throughout
REM ═══════════════════════════════════════════════════════════════

cd /d "%~dp0"
set PIPELINE=%~dp0
set EMPIRE_OS=C:\Users\jjard\empire-os

echo [1/4] Copying server + persistence + workspace files to empire-os...

REM Create server directories
mkdir "%EMPIRE_OS%\apps\empire-os-server\adapters" 2>nul

REM Copy server files
copy /Y "%PIPELINE%empire-os-patch\apps\empire-os-server\server.ts" "%EMPIRE_OS%\apps\empire-os-server\server.ts"
copy /Y "%PIPELINE%empire-os-patch\apps\empire-os-server\package.json" "%EMPIRE_OS%\apps\empire-os-server\package.json"
copy /Y "%PIPELINE%empire-os-patch\apps\empire-os-server\pm2.config.cjs" "%EMPIRE_OS%\apps\empire-os-server\pm2.config.cjs"
copy /Y "%PIPELINE%empire-os-patch\apps\empire-os-server\goose.executor.ts" "%EMPIRE_OS%\apps\empire-os-server\goose.executor.ts"
copy /Y "%PIPELINE%empire-os-patch\apps\empire-os-server\model-manager.module.ts" "%EMPIRE_OS%\apps\empire-os-server\model-manager.module.ts"
copy /Y "%PIPELINE%empire-os-patch\apps\empire-os-server\discovery.module.ts" "%EMPIRE_OS%\apps\empire-os-server\discovery.module.ts"
copy /Y "%PIPELINE%empire-os-patch\apps\empire-os-server\health-monitor.module.ts" "%EMPIRE_OS%\apps\empire-os-server\health-monitor.module.ts"
copy /Y "%PIPELINE%empire-os-patch\apps\empire-os-server\media-engine.module.ts" "%EMPIRE_OS%\apps\empire-os-server\media-engine.module.ts"
copy /Y "%PIPELINE%empire-os-patch\apps\empire-os-server\knowledge-base.module.ts" "%EMPIRE_OS%\apps\empire-os-server\knowledge-base.module.ts"
copy /Y "%PIPELINE%empire-os-patch\apps\empire-os-server\empire-dashboard.module.ts" "%EMPIRE_OS%\apps\empire-os-server\empire-dashboard.module.ts"
copy /Y "%PIPELINE%empire-os-patch\apps\empire-os-server\store.module.ts" "%EMPIRE_OS%\apps\empire-os-server\store.module.ts"
copy /Y "%PIPELINE%empire-os-patch\apps\empire-os-server\installer.module.ts" "%EMPIRE_OS%\apps\empire-os-server\installer.module.ts"
REM Phase 3 backend modules
copy /Y "%PIPELINE%empire-os-patch\apps\empire-os-server\discovery-engine.module.ts" "%EMPIRE_OS%\apps\empire-os-server\discovery-engine.module.ts"
copy /Y "%PIPELINE%empire-os-patch\apps\empire-os-server\benchmark-engine.module.ts" "%EMPIRE_OS%\apps\empire-os-server\benchmark-engine.module.ts"
copy /Y "%PIPELINE%empire-os-patch\apps\empire-os-server\self-improvement.module.ts" "%EMPIRE_OS%\apps\empire-os-server\self-improvement.module.ts"
copy /Y "%PIPELINE%empire-os-patch\apps\empire-os-server\adapters\anthropic.adapter.ts" "%EMPIRE_OS%\apps\empire-os-server\adapters\anthropic.adapter.ts"
copy /Y "%PIPELINE%empire-os-patch\apps\empire-os-server\adapters\gemini.adapter.ts" "%EMPIRE_OS%\apps\empire-os-server\adapters\gemini.adapter.ts"
copy /Y "%PIPELINE%empire-os-patch\apps\empire-os-server\adapters\openai.adapter.ts" "%EMPIRE_OS%\apps\empire-os-server\adapters\openai.adapter.ts"
copy /Y "%PIPELINE%empire-os-patch\apps\empire-os-server\adapters\ollama.adapter.ts" "%EMPIRE_OS%\apps\empire-os-server\adapters\ollama.adapter.ts"

REM CrossPost Enterprise — new Empire OS v3 React panels
set CROSSPOST=%EMPIRE_OS%\apps\crosspost-enterprise\src\components
copy /Y "%PIPELINE%empire-os-patch\apps\crosspost-enterprise\src\components\HealthMonitorPanel.tsx" "%CROSSPOST%\HealthMonitorPanel.tsx"
copy /Y "%PIPELINE%empire-os-patch\apps\crosspost-enterprise\src\components\ModelBenchmarkPanel.tsx" "%CROSSPOST%\ModelBenchmarkPanel.tsx"
copy /Y "%PIPELINE%empire-os-patch\apps\crosspost-enterprise\src\components\DiscoveryFeed.tsx" "%CROSSPOST%\DiscoveryFeed.tsx"
copy /Y "%PIPELINE%empire-os-patch\apps\crosspost-enterprise\src\components\ConnectorManager.tsx" "%CROSSPOST%\ConnectorManager.tsx"
copy /Y "%PIPELINE%empire-os-patch\apps\crosspost-enterprise\src\components\HiggsfieldStatus.tsx" "%CROSSPOST%\HiggsfieldStatus.tsx"
copy /Y "%PIPELINE%empire-os-patch\apps\crosspost-enterprise\src\components\EmpireAIRouterPanel.tsx" "%CROSSPOST%\EmpireAIRouterPanel.tsx"
REM Phase 3 React components
copy /Y "%PIPELINE%empire-os-patch\apps\crosspost-enterprise\src\components\DiscoveryEngine.tsx" "%CROSSPOST%\DiscoveryEngine.tsx"
copy /Y "%PIPELINE%empire-os-patch\apps\crosspost-enterprise\src\components\BenchmarkEngine.tsx" "%CROSSPOST%\BenchmarkEngine.tsx"
copy /Y "%PIPELINE%empire-os-patch\apps\crosspost-enterprise\src\components\SelfImprovementEngine.tsx" "%CROSSPOST%\SelfImprovementEngine.tsx"
copy /Y "%PIPELINE%empire-os-patch\apps\crosspost-enterprise\src\components\DiscoveryDashboard.tsx" "%CROSSPOST%\DiscoveryDashboard.tsx"
copy /Y "%PIPELINE%empire-os-patch\apps\crosspost-enterprise\src\App.tsx" "%EMPIRE_OS%\apps\crosspost-enterprise\src\App.tsx"

REM Updated EA module (descriptor fix)
copy /Y "%PIPELINE%empire-os-patch\apps\empire-assistant\empire-assistant.module.ts" "%EMPIRE_OS%\apps\empire-assistant\empire-assistant.module.ts"

REM Core package.json (exports field — required for @empire-os/core/bootstrap subpath)
copy /Y "%PIPELINE%empire-os-patch\packages\core\package.json" "%EMPIRE_OS%\packages\core\package.json"

REM File-backed persistence implementations
set PKGCORE=%EMPIRE_OS%\packages\core\src\implementations
copy /Y "%PIPELINE%empire-os-patch\packages\core\src\implementations\file-memory-bus.impl.ts" "%PKGCORE%\file-memory-bus.impl.ts"
copy /Y "%PIPELINE%empire-os-patch\packages\core\src\implementations\file-event-bus.impl.ts" "%PKGCORE%\file-event-bus.impl.ts"
copy /Y "%PIPELINE%empire-os-patch\packages\core\src\implementations\file-workflow-engine.impl.ts" "%PKGCORE%\file-workflow-engine.impl.ts"
copy /Y "%PIPELINE%empire-os-patch\packages\core\src\implementations\workflow-engine.impl.ts" "%PKGCORE%\workflow-engine.impl.ts"
copy /Y "%PIPELINE%empire-os-patch\packages\core\src\implementations\ai-router.impl.ts" "%PKGCORE%\ai-router.impl.ts"
copy /Y "%PIPELINE%empire-os-patch\packages\core\src\implementations\index.ts" "%PKGCORE%\index.ts"
copy /Y "%PIPELINE%empire-os-patch\packages\core\src\bootstrap.ts" "%EMPIRE_OS%\packages\core\src\bootstrap.ts"

REM Workspace config (root package.json + pnpm-workspace.yaml)
copy /Y "%PIPELINE%empire-os-patch\package.json" "%EMPIRE_OS%\package.json"
copy /Y "%PIPELINE%empire-os-patch\pnpm-workspace.yaml" "%EMPIRE_OS%\pnpm-workspace.yaml"

REM .env.example (safe — no keys)
copy /Y "%PIPELINE%empire-os-patch\.env.example" "%EMPIRE_OS%\.env.example"

echo [2/4] Updating AGENT_MEMORY.md...
copy /Y "%PIPELINE%empire-os-patch\AGENT_MEMORY.md" "%EMPIRE_OS%\AGENT_MEMORY.md"

echo [3/4] Committing...
cd /d "%EMPIRE_OS%"
git pull origin main
git add -A
git commit -m "[CLAUDE] feat: Empire OS Phase 3 — DiscoveryEngine, BenchmarkEngine, SelfImprovement (3 backend + 4 React components)"
git push origin main

echo [4/4] Done. Empire OS server is committed.
echo.
echo Next step: run START_EMPIRE_OS.bat to launch the server.
pause
