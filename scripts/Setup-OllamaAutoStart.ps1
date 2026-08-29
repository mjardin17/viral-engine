# Setup-OllamaAutoStart.ps1 — Configure Task Scheduler to start Ollama on Windows login
# Run as Administrator:
#   powershell -ExecutionPolicy Bypass -File Setup-OllamaAutoStart.ps1

$TaskName = "Ollama Auto-Start"
$TaskPath = "\Ollama\"
$ScriptPath = "C:\Users\jjard\claude\video-bot-pipeline\scripts\ollama-autostart.bat"

# Check if running as admin
$CurrentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
$Principal = New-Object Security.Principal.WindowsPrincipal($CurrentUser)
if (-not $Principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "This script must run as Administrator"
    exit 1
}

# Remove existing task if it exists
$ExistingTask = Get-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath -ErrorAction SilentlyContinue
if ($ExistingTask) {
    Write-Host "Removing existing task '$TaskName'..."
    Unregister-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath -Confirm:$false
}

# Create task action
$Action = New-ScheduledTaskAction -Execute $ScriptPath

# Create task trigger (at user logon)
$Trigger = New-ScheduledTaskTrigger -AtLogOn

# Create task settings
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -DontStopOnIdleEnd `
    -RunOnlyIfNetworkAvailable `
    -MultipleInstances IgnoreNew

# Register the task
$Task = Register-ScheduledTask `
    -TaskName $TaskName `
    -TaskPath $TaskPath `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Start Ollama server automatically on Windows login for Book Factory fallback" `
    -RunLevel Highest

Write-Host "✓ Task registered: $($Task.TaskName)"
Write-Host "✓ Path: $($Task.TaskPath)"
Write-Host "✓ Trigger: At user logon"
Write-Host ""
Write-Host "To verify it works:"
Write-Host "  1. Restart your computer"
Write-Host "  2. Check Task Scheduler: Computer Management > Task Scheduler > Ollama"
Write-Host "  3. Verify Ollama is running: tasklist | findstr ollama.exe"
Write-Host "  4. Test Ollama API: curl http://localhost:11434/api/tags"
