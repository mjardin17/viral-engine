Set-Location $PSScriptRoot
Remove-Item -Force ".git\index.lock" -ErrorAction SilentlyContinue
Remove-Item -Force ".git\index_tmp.lock" -ErrorAction SilentlyContinue
git add -A
git commit -m "[CLAUDE] feat: wire Kokoro TTS into auto_render.py, replace edge-tts"
git push origin main
Write-Host "`nDone! Press Enter to close." -ForegroundColor Green
Read-Host
