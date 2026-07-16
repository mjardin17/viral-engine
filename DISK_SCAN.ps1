$out = @()
$out += "=" * 60
$out += "  DISK SPACE REPORT"
$out += "=" * 60

$drive = Get-PSDrive C
$used = [math]::Round($drive.Used/1GB, 1)
$free = [math]::Round($drive.Free/1GB, 1)
$total = $used + $free
$out += ""
$out += "C: Drive   Total: ${total}GB   Used: ${used}GB   FREE: ${free}GB"
$out += ""
$out += "=" * 60
$out += "  FOLDER SIZES"
$out += "=" * 60

$folders = @{
    "Downloads"         = "C:\Users\jjard\Downloads"
    "Desktop"           = "C:\Users\jjard\Desktop"
    "Videos"            = "C:\Users\jjard\Videos"
    "Pictures"          = "C:\Users\jjard\Pictures"
    "Documents"         = "C:\Users\jjard\Documents"
    "AppData Local"     = "C:\Users\jjard\AppData\Local"
    "AppData Roaming"   = "C:\Users\jjard\AppData\Roaming"
    "Ollama models"     = "C:\Users\jjard\.ollama"
    "GG renders"        = "C:\Users\jjard\claude\video-bot-pipeline\renders"
    "Windows Temp"      = "C:\Windows\Temp"
}

foreach ($name in $folders.Keys | Sort-Object) {
    $path = $folders[$name]
    if (Test-Path $path) {
        $size = (Get-ChildItem $path -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
        $gb = [math]::Round($size/1GB, 2)
        $mb = [math]::Round($size/1MB, 0)
        if ($gb -ge 1) {
            $out += ("{0,-20} {1,6} GB" -f $name, $gb)
        } else {
            $out += ("{0,-20} {1,6} MB" -f $name, $mb)
        }
    } else {
        $out += ("{0,-20} not found" -f $name)
    }
}

$out += ""
$out += "=" * 60
$out += "  TOP 20 BIGGEST FILES IN DOWNLOADS"
$out += "=" * 60
$files = Get-ChildItem "C:\Users\jjard\Downloads" -Recurse -ErrorAction SilentlyContinue |
    Sort-Object Length -Descending | Select-Object -First 20
foreach ($f in $files) {
    $mb = [math]::Round($f.Length/1MB, 0)
    $out += ("{0,6} MB  {1}" -f $mb, $f.Name)
}

$logPath = "C:\Users\jjard\claude\video-bot-pipeline\DISK_SCAN_RESULTS.txt"
$out | Out-File -FilePath $logPath -Encoding UTF8
Write-Host "Done! Opening results..."
Start-Process notepad $logPath
