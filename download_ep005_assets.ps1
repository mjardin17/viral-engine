# Empire Decoded Episode 5 — Asset Downloader
# Run this ONCE on your Windows machine to download all Higgsfield assets.
# After running, re-run: python3 ep005_final_render.py
# This upgrades from synthetic audio to REAL Hades voice + Hans Zimmer music.

$base = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Host "Empire Decoded Ep005 — Downloading assets..." -ForegroundColor Cyan
Write-Host "Base: $base"

# Create folders
$narr  = Join-Path $base "assets\narration"
$sfx   = Join-Path $base "assets\sfx"
$music = Join-Path $base "assets\music"
$chars = Join-Path $base "character_images"
$clips = Join-Path $base "assets\video_clips"

foreach ($dir in @($narr, $sfx, $music, $chars, $clips)) {
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
}

function Download-Asset {
    param([string]$Url, [string]$OutFile, [string]$Label)
    if (Test-Path $OutFile) {
        $size = (Get-Item $OutFile).Length
        if ($size -gt 1000) {
            Write-Host "  SKIP  $Label (already downloaded, $([math]::Round($size/1024))KB)" -ForegroundColor DarkGray
            return
        }
    }
    Write-Host "  GET   $Label..." -NoNewline
    try {
        Invoke-WebRequest -Uri $Url -OutFile $OutFile -UseBasicParsing -TimeoutSec 120
        $size = (Get-Item $OutFile).Length
        Write-Host " OK ($([math]::Round($size/1024))KB)" -ForegroundColor Green
    } catch {
        Write-Host " FAILED: $_" -ForegroundColor Red
    }
}

Write-Host "`n[NARRATION — Hades voice]" -ForegroundColor Yellow
Download-Asset `
    "https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260614_173745_25c20571-07a8-4b8d-a8a7-971bb0a6ef57.wav" `
    "$narr\01_cold_open_final.wav" "01_cold_open_final"

Download-Asset `
    "https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260614_171016_c6a638ad-98a1-4438-ab70-34466c1d9ffe.wav" `
    "$narr\02_agoge.wav" "02_agoge"

Download-Asset `
    "https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260614_171102_a71d1d80-1fee-48db-97ef-9d24422d7768.wav" `
    "$narr\03_phalanx.wav" "03_phalanx"

Download-Asset `
    "https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260614_171103_a8b35f30-9be4-4f66-9779-ddfebee83458.wav" `
    "$narr\04_prophecy.wav" "04_prophecy"

Download-Asset `
    "https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260614_171130_9982e842-57ff-453e-ad70-1e859ba459b9.wav" `
    "$narr\05_persian_invasion.wav" "05_persian_invasion"

Download-Asset `
    "https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260614_171131_7461946f-b13e-4983-89bf-8368fe1aee8d.wav" `
    "$narr\06_the_immortals.wav" "06_the_immortals"

Download-Asset `
    "https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260614_171157_f1893ac3-9db5-4b94-b862-a3ee90b2cad3.wav" `
    "$narr\07_the_stand_begins.wav" "07_the_stand_begins"

Download-Asset `
    "https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260614_171158_f61fd67b-da01-4385-bf1c-f9554bc3e82b.wav" `
    "$narr\08_the_betrayal_turn.wav" "08_the_betrayal_turn"

Download-Asset `
    "https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260614_171223_dbf6d813-bbdb-4de0-8fee-74b100358d5e.wav" `
    "$narr\09_aftermath.wav" "09_aftermath"

Download-Asset `
    "https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260614_171224_b3477324-f751-49b2-9289-8ded8f281bc9.wav" `
    "$narr\10_legacy_outro.wav" "10_legacy_outro"

Write-Host "`n[MUSIC — 300s Hans Zimmer-style orchestral]" -ForegroundColor Yellow
Download-Asset `
    "https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260614_171253_a3b190c6-75f6-42da-a96f-70a4891fde53.m4a" `
    "$music\music.m4a" "music (300s orchestral)"

Write-Host "`n[SFX — 10 tracks]" -ForegroundColor Yellow
Download-Asset `
    "https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260614_173449_e42d097d-3b55-498a-bed9-2b13d57e9ba6.mp3" `
    "$sfx\tension_drone.mp3" "tension_drone"

Download-Asset `
    "https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260614_173450_d3b6a9f7-69a4-41a0-b446-9a8d14b6b6e8.mp3" `
    "$sfx\agoge_training.mp3" "agoge_training"

Download-Asset `
    "https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260614_173518_ffcc9ff2-27b4-4d0e-829d-aad84616a68e.mp3" `
    "$sfx\forge.mp3" "forge"

Download-Asset `
    "https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260614_173519_6875d8e1-8620-4387-8037-9b0bb9577dc4.mp3" `
    "$sfx\oracle_temple.mp3" "oracle_temple"

Download-Asset `
    "https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260614_173546_e5e9c81f-a805-4198-9ff4-c70a19b9fa87.mp3" `
    "$sfx\persian_army_march.mp3" "persian_army_march"

Download-Asset `
    "https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260614_173548_4b072c01-8495-4a57-ae6f-4b0d5fd26c13.mp3" `
    "$sfx\immortals_march.mp3" "immortals_march"

Download-Asset `
    "https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260614_173617_2e2265b6-a00e-404e-aaa3-13e496bc190c.mp3" `
    "$sfx\storm_battle.mp3" "storm_battle"

Download-Asset `
    "https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260614_173618_1979719b-03fa-4677-b003-22f4b70a60fe.mp3" `
    "$sfx\last_stand_chaos.mp3" "last_stand_chaos"

Download-Asset `
    "https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260614_173647_34e2f7ac-8d8a-45f9-93c9-989c0b6d8b59.mp3" `
    "$sfx\aftermath_ambience.mp3" "aftermath_ambience"

Download-Asset `
    "https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260614_173648_7c002741-6379-4950-b74c-880100be64c3.mp3" `
    "$sfx\triumphant_resolution.mp3" "triumphant_resolution"

Write-Host "`n[CHARACTER IMAGE — Spartan hoplite]" -ForegroundColor Yellow
Download-Asset `
    "https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260614_164125_2abbd8d0-a186-4f40-a307-d0240741f7df.png" `
    "$chars\spartan_hoplite_reference.png" "spartan_hoplite_reference"

Write-Host "`n[VIDEO CLIP — Scene 1]" -ForegroundColor Yellow
Download-Asset `
    "https://d8j0ntlcm91z4.cloudfront.net/user_3D9eVQycjqBmIClt0W6gUnVzpEA/hf_20260614_233334_05427a01-7ca8-4c14-b6e9-377805007fce.mp4" `
    "$clips\scene_01.mp4" "scene_01_grok_video"

Write-Host "`n[DONE]" -ForegroundColor Green
Write-Host "Now re-run the render:"
Write-Host "  cd $base"
Write-Host "  python3 ep005_final_render.py"
Write-Host ""
Write-Host "The script auto-detects real assets and uses them instead of synthetics."
