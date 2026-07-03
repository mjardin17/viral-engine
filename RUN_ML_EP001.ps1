$ErrorActionPreference = "Continue"
Set-Location "C:\Users\jjard\claude\video-bot-pipeline"

# Log everything to file AND console
$LogFile = "C:\Users\jjard\claude\video-bot-pipeline\output\run_log.txt"
if (-not (Test-Path "output")) { New-Item -ItemType Directory -Path "output" | Out-Null }
Start-Transcript -Path $LogFile -Append

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CINELAB AUTOPILOT - ML_EP001"           -ForegroundColor Cyan
Write-Host "  The Signal - Mech Legends S1 EP001"     -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. Find Python (skip WindowsApps Store alias) ──────────────────────────
$python = $null

$hardPaths = @(
    "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
    "C:\Program Files\Python314\python.exe",
    "C:\Program Files\Python313\python.exe",
    "C:\Program Files\Python312\python.exe",
    "C:\Program Files\Python311\python.exe",
    "C:\Program Files\Python310\python.exe",
    "C:\Program Files (x86)\Python314\python.exe",
    "C:\Program Files (x86)\Python313\python.exe",
    "$env:USERPROFILE\miniconda3\python.exe",
    "$env:USERPROFILE\anaconda3\python.exe",
    "$env:USERPROFILE\AppData\Local\miniconda3\python.exe"
)

foreach ($p in $hardPaths) {
    if (Test-Path $p) { $python = $p; break }
}

# Registry scan (covers system-wide and user installs)
if (-not $python) {
    foreach ($hive in @("HKLM:\SOFTWARE\Python\PythonCore","HKCU:\SOFTWARE\Python\PythonCore")) {
        try {
            $keys = Get-ChildItem $hive -ErrorAction SilentlyContinue
            foreach ($key in $keys) {
                $ip = (Get-ItemProperty "$($key.PSPath)\InstallPath" -ErrorAction SilentlyContinue)."(default)"
                if ($ip) {
                    $c = Join-Path $ip "python.exe"
                    if (Test-Path $c) { $python = $c; break }
                }
            }
        } catch {}
        if ($python) { break }
    }
}

# PATH scan — skip WindowsApps stub
if (-not $python) {
    foreach ($name in @("python","python3")) {
        try {
            $found = Get-Command $name -ErrorAction SilentlyContinue
            if ($found -and $found.Source -notlike "*WindowsApps*") {
                $python = $found.Source; break
            }
        } catch {}
    }
}

if (-not $python) {
    Write-Host "ERROR: Python not found." -ForegroundColor Red
    Write-Host "Install Python 3.x from https://python.org and re-run." -ForegroundColor Yellow
    exit 1
}

Write-Host "Python : $python" -ForegroundColor Green
$ver = & $python --version 2>&1
Write-Host "Version: $ver" -ForegroundColor Green
Write-Host ""

# ── 2. Install dependencies ─────────────────────────────────────────────────
Write-Host "Checking dependencies..." -ForegroundColor Yellow
& $python -m pip install Pillow numpy --quiet --disable-pip-version-check
# pyttsx3 is optional (voiceover) — install separately, ignore failure
& $python -m pip install pyttsx3 --quiet --disable-pip-version-check 2>$null
Write-Host "Dependencies OK" -ForegroundColor Green
Write-Host ""

# ── 3. Ensure output directory exists ───────────────────────────────────────
if (-not (Test-Path "output")) {
    New-Item -ItemType Directory -Path "output" | Out-Null
    Write-Host "Created output/ directory" -ForegroundColor DarkGray
}

# ── 4. Run local renderer (characters + voiceover) ──────────────────────────
Write-Host "Rendering ML_EP001 locally..." -ForegroundColor Cyan
Write-Host ""

& $python render_ml_ep001_win.py

$code = $LASTEXITCODE
Write-Host ""
if ($code -eq 0) {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  SUCCESS - ML_EP001_final.mp4 is ready" -ForegroundColor Green
    Write-Host "  output\ML_EP001_final.mp4"             -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
} else {
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "  FAILED (exit $code) -- see error above" -ForegroundColor Red
    Write-Host "  Check log: output\run_log.txt"          -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Red
}

Stop-Transcript
