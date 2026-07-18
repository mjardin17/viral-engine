# Empire OS - Commit + Push (PowerShell)
# Right-click -> "Run with PowerShell"   OR   open PowerShell and run: .\COMMIT_SERVER.ps1

$ErrorActionPreference = "Stop"

$PIPELINE  = $PSScriptRoot
$EMPIRE_OS = "C:\Users\jjard\empire-os"
$CROSSPOST = "$EMPIRE_OS\apps\crosspost-enterprise\src\components"
$PKGCORE   = "$EMPIRE_OS\packages\core\src\implementations"

Write-Host "[1/4] Copying files to empire-os..." -ForegroundColor Cyan

New-Item -ItemType Directory -Force "$EMPIRE_OS\apps\empire-os-server\adapters" | Out-Null

Copy-Item -Force "$PIPELINE\empire-os-patch\apps\empire-os-server\server.ts"                  "$EMPIRE_OS\apps\empire-os-server\server.ts"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\empire-os-server\package.json"               "$EMPIRE_OS\apps\empire-os-server\package.json"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\empire-os-server\pm2.config.cjs"             "$EMPIRE_OS\apps\empire-os-server\pm2.config.cjs"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\empire-os-server\goose.executor.ts"          "$EMPIRE_OS\apps\empire-os-server\goose.executor.ts"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\empire-os-server\model-manager.module.ts"    "$EMPIRE_OS\apps\empire-os-server\model-manager.module.ts"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\empire-os-server\discovery.module.ts"        "$EMPIRE_OS\apps\empire-os-server\discovery.module.ts"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\empire-os-server\health-monitor.module.ts"   "$EMPIRE_OS\apps\empire-os-server\health-monitor.module.ts"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\empire-os-server\media-engine.module.ts"     "$EMPIRE_OS\apps\empire-os-server\media-engine.module.ts"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\empire-os-server\knowledge-base.module.ts"   "$EMPIRE_OS\apps\empire-os-server\knowledge-base.module.ts"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\empire-os-server\empire-dashboard.module.ts" "$EMPIRE_OS\apps\empire-os-server\empire-dashboard.module.ts"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\empire-os-server\store.module.ts"            "$EMPIRE_OS\apps\empire-os-server\store.module.ts"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\empire-os-server\installer.module.ts"        "$EMPIRE_OS\apps\empire-os-server\installer.module.ts"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\empire-os-server\tsconfig.json"               "$EMPIRE_OS\apps\empire-os-server\tsconfig.json"

Copy-Item -Force "$PIPELINE\empire-os-patch\apps\empire-os-server\discovery-engine.module.ts" "$EMPIRE_OS\apps\empire-os-server\discovery-engine.module.ts"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\empire-os-server\benchmark-engine.module.ts" "$EMPIRE_OS\apps\empire-os-server\benchmark-engine.module.ts"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\empire-os-server\self-improvement.module.ts" "$EMPIRE_OS\apps\empire-os-server\self-improvement.module.ts"

# Phase 4 — Video Factory (19 departments)
New-Item -ItemType Directory -Force "$EMPIRE_OS\apps\empire-os-server\video-factory" | Out-Null
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\empire-os-server\video-factory\video-factory.departments.ts" "$EMPIRE_OS\apps\empire-os-server\video-factory\video-factory.departments.ts"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\empire-os-server\video-factory\video-factory.pipeline.ts"    "$EMPIRE_OS\apps\empire-os-server\video-factory\video-factory.pipeline.ts"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\empire-os-server\video-factory\video-factory.memory.ts"      "$EMPIRE_OS\apps\empire-os-server\video-factory\video-factory.memory.ts"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\empire-os-server\video-factory\video-factory.providers.ts"   "$EMPIRE_OS\apps\empire-os-server\video-factory\video-factory.providers.ts"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\empire-os-server\video-factory\video-factory.module.ts"      "$EMPIRE_OS\apps\empire-os-server\video-factory\video-factory.module.ts"

# Phase 4 — Autonomous Executive (10 workers + Master Queue)
New-Item -ItemType Directory -Force "$EMPIRE_OS\apps\empire-os-server\executive" | Out-Null
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\empire-os-server\executive\executive.workers.ts"  "$EMPIRE_OS\apps\empire-os-server\executive\executive.workers.ts"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\empire-os-server\executive\executive.queue.ts"    "$EMPIRE_OS\apps\empire-os-server\executive\executive.queue.ts"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\empire-os-server\executive\executive.briefing.ts" "$EMPIRE_OS\apps\empire-os-server\executive\executive.briefing.ts"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\empire-os-server\executive\executive.module.ts"   "$EMPIRE_OS\apps\empire-os-server\executive\executive.module.ts"

Copy-Item -Force "$PIPELINE\empire-os-patch\apps\empire-os-server\adapters\anthropic.adapter.ts" "$EMPIRE_OS\apps\empire-os-server\adapters\anthropic.adapter.ts"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\empire-os-server\adapters\gemini.adapter.ts"    "$EMPIRE_OS\apps\empire-os-server\adapters\gemini.adapter.ts"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\empire-os-server\adapters\openai.adapter.ts"    "$EMPIRE_OS\apps\empire-os-server\adapters\openai.adapter.ts"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\empire-os-server\adapters\ollama.adapter.ts"    "$EMPIRE_OS\apps\empire-os-server\adapters\ollama.adapter.ts"

New-Item -ItemType Directory -Force $CROSSPOST | Out-Null
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\crosspost-enterprise\src\components\HealthMonitorPanel.tsx"    "$CROSSPOST\HealthMonitorPanel.tsx"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\crosspost-enterprise\src\components\ModelBenchmarkPanel.tsx"   "$CROSSPOST\ModelBenchmarkPanel.tsx"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\crosspost-enterprise\src\components\DiscoveryFeed.tsx"         "$CROSSPOST\DiscoveryFeed.tsx"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\crosspost-enterprise\src\components\ConnectorManager.tsx"      "$CROSSPOST\ConnectorManager.tsx"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\crosspost-enterprise\src\components\HiggsfieldStatus.tsx"      "$CROSSPOST\HiggsfieldStatus.tsx"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\crosspost-enterprise\src\components\EmpireAIRouterPanel.tsx"   "$CROSSPOST\EmpireAIRouterPanel.tsx"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\crosspost-enterprise\src\components\DiscoveryEngine.tsx"       "$CROSSPOST\DiscoveryEngine.tsx"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\crosspost-enterprise\src\components\BenchmarkEngine.tsx"       "$CROSSPOST\BenchmarkEngine.tsx"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\crosspost-enterprise\src\components\SelfImprovementEngine.tsx" "$CROSSPOST\SelfImprovementEngine.tsx"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\crosspost-enterprise\src\components\DiscoveryDashboard.tsx"    "$CROSSPOST\DiscoveryDashboard.tsx"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\crosspost-enterprise\src\App.tsx"                              "$EMPIRE_OS\apps\crosspost-enterprise\src\App.tsx"

New-Item -ItemType Directory -Force "$EMPIRE_OS\apps\empire-assistant" | Out-Null

Copy-Item -Force "$PIPELINE\empire-os-patch\apps\empire-assistant\empire-assistant.module.ts" "$EMPIRE_OS\apps\empire-assistant\empire-assistant.module.ts"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\empire-assistant\package.json"               "$EMPIRE_OS\apps\empire-assistant\package.json"
Copy-Item -Force "$PIPELINE\empire-os-patch\apps\empire-assistant\index.ts"                   "$EMPIRE_OS\apps\empire-assistant\index.ts"

Copy-Item -Force "$PIPELINE\empire-os-patch\packages\core\package.json" "$EMPIRE_OS\packages\core\package.json"
New-Item -ItemType Directory -Force $PKGCORE | Out-Null
Copy-Item -Force "$PIPELINE\empire-os-patch\packages\core\src\implementations\file-memory-bus.impl.ts"      "$PKGCORE\file-memory-bus.impl.ts"
Copy-Item -Force "$PIPELINE\empire-os-patch\packages\core\src\implementations\file-event-bus.impl.ts"       "$PKGCORE\file-event-bus.impl.ts"
Copy-Item -Force "$PIPELINE\empire-os-patch\packages\core\src\implementations\file-workflow-engine.impl.ts" "$PKGCORE\file-workflow-engine.impl.ts"
Copy-Item -Force "$PIPELINE\empire-os-patch\packages\core\src\implementations\workflow-engine.impl.ts"      "$PKGCORE\workflow-engine.impl.ts"
Copy-Item -Force "$PIPELINE\empire-os-patch\packages\core\src\implementations\ai-router.impl.ts"            "$PKGCORE\ai-router.impl.ts"
Copy-Item -Force "$PIPELINE\empire-os-patch\packages\core\src\implementations\index.ts"                     "$PKGCORE\index.ts"
Copy-Item -Force "$PIPELINE\empire-os-patch\packages\core\src\bootstrap.ts"                                 "$EMPIRE_OS\packages\core\src\bootstrap.ts"

Copy-Item -Force "$PIPELINE\empire-os-patch\package.json"        "$EMPIRE_OS\package.json"
Copy-Item -Force "$PIPELINE\empire-os-patch\pnpm-workspace.yaml" "$EMPIRE_OS\pnpm-workspace.yaml"
Copy-Item -Force "$PIPELINE\empire-os-patch\.env.example"        "$EMPIRE_OS\.env.example"

$ELECTRON_SRC = "$PIPELINE\empire-os-patch\apps\electron"
$ELECTRON_DST = "$EMPIRE_OS\apps\electron"
New-Item -ItemType Directory -Force "$ELECTRON_DST\assets" | Out-Null
Copy-Item -Force "$ELECTRON_SRC\main.ts"         "$ELECTRON_DST\main.ts"
Copy-Item -Force "$ELECTRON_SRC\preload.ts"      "$ELECTRON_DST\preload.ts"
Copy-Item -Force "$ELECTRON_SRC\tsconfig.json"   "$ELECTRON_DST\tsconfig.json"
Copy-Item -Force "$ELECTRON_SRC\package.json"    "$ELECTRON_DST\package.json"
Copy-Item -Force "$ELECTRON_SRC\assets\icon.png" "$ELECTRON_DST\assets\icon.png"

Write-Host "[2/4] Copying AGENT_MEMORY.md..." -ForegroundColor Cyan
Copy-Item -Force "$PIPELINE\empire-os-patch\AGENT_MEMORY.md" "$EMPIRE_OS\AGENT_MEMORY.md"

Write-Host "[3/4] Committing and pushing to GitHub..." -ForegroundColor Cyan
Set-Location $EMPIRE_OS

git pull origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "git pull failed - check your connection and credentials" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

git add -A
git status --short

$msg = "[CLAUDE] feat: Empire OS Phase 4 - VideoFactory (19 depts, 20-stage pipeline) + AutonomousExecutive (10 workers, Master Queue, Daily Briefing)"
git commit -m $msg
if ($LASTEXITCODE -ne 0) {
    Write-Host "Nothing new to commit (or commit failed)." -ForegroundColor Yellow
}

git push origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Push failed. To save credentials permanently, run:" -ForegroundColor Yellow
    Write-Host "  git config --global credential.helper store" -ForegroundColor White
    Write-Host "Then push once manually - git will save your token." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "[4/4] Done. Empire OS Phase 4 — Video Factory + Autonomous Executive pushed to GitHub." -ForegroundColor Green
Write-Host ""
Write-Host "Next step: restart Empire OS server (run START_EMPIRE_OS.bat)" -ForegroundColor Cyan
Read-Host "Press Enter to close"
