# ================================================================
# EMPIRE OS — Full System Audit & Auto-Repair Script
# Run as: Right-click -> Run with PowerShell
# ================================================================

$ErrorActionPreference = "Continue"
$LOG = "$PSScriptRoot\empire-audit-results.txt"
$PASS = 0; $FAIL = 0; $WARN = 0

function Log($msg) { Write-Host $msg; Add-Content $LOG $msg }
function PASS($label) { $script:PASS++; Log "  ✅ PASS  $label" }
function FAIL($label) { $script:FAIL++; Log "  ❌ FAIL  $label" }
function WARN($label) { $script:WARN++; Log "  ⚠️  WARN  $label" }
function HEAD($title) { Log ""; Log "══════════════════════════════════════════"; Log "  $title"; Log "══════════════════════════════════════════" }

Clear-Content $LOG -ErrorAction SilentlyContinue
$ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Log "EMPIRE OS SYSTEM AUDIT — $ts"
Log "Machine: $env:COMPUTERNAME | User: $env:USERNAME"

# ── PHASE 1: OLLAMA ──────────────────────────────────────────────
HEAD "PHASE 1 — OLLAMA"

# 1a. Is ollama.exe on PATH?
$ollamaExe = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollamaExe) {
    PASS "ollama.exe found: $($ollamaExe.Source)"
} else {
    FAIL "ollama not on PATH — checking common locations..."
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe",
        "C:\Users\$env:USERNAME\AppData\Local\Programs\Ollama\ollama.exe"
    )
    $found = $candidates | Where-Object { Test-Path $_ }
    if ($found) {
        WARN "Found at $($found[0]) — not on PATH. Adding to session PATH."
        $env:PATH = "$env:PATH;$(Split-Path $found[0])"
    } else {
        FAIL "ollama.exe not found on this machine"
    }
}

# 1b. Is Ollama service running?
try {
    $resp = Invoke-RestMethod "http://localhost:11434/api/tags" -TimeoutSec 5 -ErrorAction Stop
    PASS "Ollama service running at localhost:11434"
    $models = $resp.models | ForEach-Object { $_.name }
    if ($models.Count -gt 0) {
        PASS "Models available: $($models -join ', ')"
    } else {
        WARN "Ollama running but NO models installed"
        Log "     → Pulling llama3.2 (3B, lightweight)..."
        Start-Process -FilePath "ollama" -ArgumentList "pull llama3.2" -NoNewWindow -Wait 2>$null
    }
} catch {
    FAIL "Ollama not responding at localhost:11434"
    Log "     → Attempting to start Ollama service..."
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden -ErrorAction SilentlyContinue
    Start-Sleep 5
    try {
        $resp2 = Invoke-RestMethod "http://localhost:11434/api/tags" -TimeoutSec 5
        PASS "Ollama service started successfully"
    } catch {
        FAIL "Ollama still not responding after start attempt"
    }
}

# 1c. Test a prompt if models exist
try {
    $testBody = '{"model":"llama3","prompt":"Say the word OK","stream":false}'
    $testResp = Invoke-RestMethod "http://localhost:11434/api/generate" `
        -Method POST -Body $testBody -ContentType "application/json" -TimeoutSec 30
    if ($testResp.response) {
        PASS "Ollama generate test PASSED — model responded: '$($testResp.response.Substring(0, [Math]::Min(50,$testResp.response.Length)))...'"
    }
} catch {
    WARN "Ollama generate test skipped (no model or timeout)"
}

# ── PHASE 2: OPEN WEBUI / PINOKIO ────────────────────────────────
HEAD "PHASE 2 — OPEN WEBUI / PINOKIO"

$pinokioPaths = @(
    "$env:USERPROFILE\AppData\Local\Programs\Pinokio",
    "C:\Pinokio",
    "$env:USERPROFILE\Pinokio"
)

$pinokioFound = $false
foreach ($p in $pinokioPaths) {
    if (Test-Path $p) {
        PASS "Pinokio found: $p"
        $pinokioFound = $true
        break
    }
}
if (-not $pinokioFound) { WARN "Pinokio directory not found in common locations" }

# Check Open WebUI ports (Pinokio typically uses 8080, but could vary)
$webuiPorts = @(8080, 3000, 7860, 1337, 8000)
$webuiLive = $null
foreach ($port in $webuiPorts) {
    try {
        $r = Invoke-WebRequest "http://localhost:$port" -TimeoutSec 3 -ErrorAction Stop -UseBasicParsing
        if ($r.StatusCode -eq 200) {
            PASS "Open WebUI responding on localhost:$port"
            $webuiLive = $port
            break
        }
    } catch { }
}
if (-not $webuiLive) {
    WARN "Open WebUI not detected on common ports (8080, 3000, 7860, 1337, 8000)"
    Log "     → Open Pinokio and start Open WebUI from there"
}

# ── PHASE 3: EMPIRE OS SERVER ─────────────────────────────────────
HEAD "PHASE 3 — EMPIRE OS SERVER (port 3001)"

try {
    $empireResp = Invoke-RestMethod "http://localhost:3001/health" -TimeoutSec 5 -ErrorAction Stop
    PASS "Empire OS server running at localhost:3001"
    Log "     Modules: $($empireResp.modules | ConvertTo-Json -Depth 1 -Compress)"
} catch {
    WARN "Empire OS server not running on port 3001"
    Log "     → Run LAUNCH_EMPIRE.bat to start it"
}

# ── PHASE 4: PORTS ────────────────────────────────────────────────
HEAD "PHASE 4 — PORT INVENTORY"

$portsToCheck = @(11434, 3001, 3000, 8080, 7860, 1337, 8000, 11435)
foreach ($port in $portsToCheck) {
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($conn) {
        $proc = Get-Process -Id $conn[0].OwningProcess -ErrorAction SilentlyContinue
        PASS "Port $port OPEN — PID $($conn[0].OwningProcess) ($($proc.Name ?? 'unknown'))"
    } else {
        Log "     — Port $port not in use"
    }
}

# ── PHASE 5: PYTHON ───────────────────────────────────────────────
HEAD "PHASE 5 — PYTHON ENVIRONMENT"

$py = Get-Command python -ErrorAction SilentlyContinue
if ($py) {
    $pyVer = (& python --version 2>&1).ToString()
    PASS "Python found: $pyVer at $($py.Source)"
} else {
    FAIL "Python not found on PATH"
}

# Check key packages
$requiredPkgs = @("requests", "fastapi", "uvicorn", "edge-tts", "openai", "google-generativeai")
foreach ($pkg in $requiredPkgs) {
    $check = & python -c "import $($pkg.Replace('-','_')); print('ok')" 2>&1
    if ($check -eq "ok") {
        PASS "Python package: $pkg"
    } else {
        WARN "Python package missing: $pkg"
    }
}

# ── PHASE 6: NODE / NPM ───────────────────────────────────────────
HEAD "PHASE 6 — NODE / NPM"

$node = Get-Command node -ErrorAction SilentlyContinue
$npm  = Get-Command npm  -ErrorAction SilentlyContinue
$npx  = Get-Command npx  -ErrorAction SilentlyContinue

if ($node) { PASS "Node.js: $(& node --version)"; } else { FAIL "node not found" }
if ($npm)  { PASS "npm: $(& npm --version)" }         else { FAIL "npm not found" }
if ($npx)  { PASS "npx available" }                   else { FAIL "npx not found" }

$tsx = & npx tsx --version 2>&1
if ($LASTEXITCODE -eq 0) { PASS "tsx available: $tsx" } else { WARN "tsx not found — run: npm install -g tsx" }

# ── PHASE 7: FIREWALL ────────────────────────────────────────────
HEAD "PHASE 7 — WINDOWS FIREWALL"

$fwProfile = (Get-NetFirewallProfile -Profile Domain,Private,Public | Where-Object { $_.Enabled }).Name
if ($fwProfile) {
    Log "  Firewall enabled on: $($fwProfile -join ', ')"
    # Check if localhost traffic is blocked (it shouldn't be by default)
    $loopbackRules = Get-NetFirewallRule -DisplayName "*localhost*" -ErrorAction SilentlyContinue
    if ($loopbackRules) {
        WARN "Firewall rules for localhost found — may affect local services"
    } else {
        PASS "No localhost-blocking firewall rules detected"
    }
} else {
    PASS "Windows Firewall appears off or not blocking"
}

# ── PHASE 8: ENVIRONMENT VARIABLES ───────────────────────────────
HEAD "PHASE 8 — ENVIRONMENT VARIABLES"

$envFile = "$PSScriptRoot\empire-os-patch\.env.example"
if (Test-Path $envFile) {
    PASS ".env.example found"
}
$dotenv = "$env:USERPROFILE\claude\video-bot-pipeline\.env"
if (Test-Path $dotenv) {
    PASS ".env file found (keys redacted from log)"
} else {
    WARN ".env file not found at expected location"
}

$keyVars = @("ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY", "ELEVENLABS_API_KEY", "OLLAMA_BASE_URL")
foreach ($var in $keyVars) {
    $val = [System.Environment]::GetEnvironmentVariable($var)
    if ($val) { PASS "$var is set" } else { Log "     — $var not set (optional)" }
}

# ── PHASE 9: DISK ────────────────────────────────────────────────
HEAD "PHASE 9 — DISK HEALTH"

$drive = Get-PSDrive C
$freeGB = [math]::Round($drive.Free / 1GB, 1)
$totalGB = [math]::Round(($drive.Used + $drive.Free) / 1GB, 1)
if ($freeGB -gt 20) { PASS "C: drive — ${freeGB}GB free of ${totalGB}GB" }
elseif ($freeGB -gt 5) { WARN "C: drive — only ${freeGB}GB free (renders need space)" }
else { FAIL "C: drive critically low — ${freeGB}GB free" }

# ── PHASE 10: EMPIRE OS WORKSPACE ────────────────────────────────
HEAD "PHASE 10 — EMPIRE OS WORKSPACE"

$workspace = "$PSScriptRoot\EMPIRE_WORKSPACE"
$dirs = @("EmpireOS","BossListers","StoryForge","VideoFactory","Knowledge","Agents","Memory","Automation","Pipelines")
foreach ($d in $dirs) {
    $full = Join-Path $workspace $d
    if (-not (Test-Path $full)) {
        New-Item -ItemType Directory -Force $full | Out-Null
        PASS "Created: EMPIRE_WORKSPACE\$d"
    } else {
        PASS "Exists:  EMPIRE_WORKSPACE\$d"
    }
}

# ── FINAL REPORT ──────────────────────────────────────────────────
HEAD "FINAL HEALTH REPORT"

$total = $PASS + $FAIL + $WARN
$score = if ($total -gt 0) { [math]::Round(($PASS / $total) * 100) } else { 0 }

Log ""
Log "  PASSED:   $PASS"
Log "  WARNINGS: $WARN"
Log "  FAILED:   $FAIL"
Log ""
Log "  SYSTEM HEALTH SCORE: $score / 100"
Log ""

if ($FAIL -eq 0 -and $WARN -le 2) {
    Log "  STATUS: 🟢 OPERATIONAL — Empire OS workstation ready"
} elseif ($FAIL -eq 0) {
    Log "  STATUS: 🟡 MOSTLY OPERATIONAL — review warnings above"
} else {
    Log "  STATUS: 🔴 ISSUES FOUND — review failures above"
}

Log ""
Log "  Full log saved: $LOG"
Log ""
Log "  NEXT COMMANDS:"
Log "  • Start everything:  LAUNCH_EMPIRE.bat"
Log "  • Open dashboard:    EMPIRE_LIVE_DASHBOARD.html (in browser)"
Log "  • Empire OS:         http://localhost:3001"
Log "  • Open WebUI:        http://localhost:8080"
Log "  • Ollama API:        http://localhost:11434"
Log ""

Write-Host ""
Write-Host "══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Health Score: $score/100" -ForegroundColor $(if($score -ge 80){"Green"}elseif($score -ge 50){"Yellow"}else{"Red"})
Write-Host "══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Read-Host "Press Enter to close"
