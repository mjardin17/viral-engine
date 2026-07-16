#!/usr/bin/env python3
"""
DIAGNOSE_LO_EP001.py
Tests every component of the LO EP001 assembly pipeline.
Run this to find exactly what's failing before running the full assembly.
"""
import os, json, shutil, sys, urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
WORK_DIR = BASE_DIR / "output" / "LO_EP001_HIGGSFIELD"

PASS = "  [PASS]"
FAIL = "  [FAIL]"
WARN = "  [WARN]"

def hr():
    print("─" * 60)

# ── Load .env ───────────────────────────────────────────────
for line in (BASE_DIR / ".env").read_text(errors="ignore").splitlines():
    if "=" in line and not line.startswith("#"):
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

print()
print("=" * 60)
print("  LO EP001 ASSEMBLY — DIAGNOSTIC")
print("=" * 60)

# ── 1. Check ElevenLabs key ─────────────────────────────────
hr()
print("1. ElevenLabs API Key")
key = os.environ.get("ELEVENLABS_API_KEY", "")
if not key:
    print(f"{FAIL} ELEVENLABS_API_KEY not found in .env")
else:
    print(f"{PASS} Key found ({key[:8]}...)")
    # Test one API call
    print("     Testing ElevenLabs API with a short phrase...")
    try:
        url = "https://api.elevenlabs.io/v1/text-to-speech/EXAVITQu4vr4xnSDxMaL"
        payload = json.dumps({
            "text": "Test.",
            "model_id": "eleven_turbo_v2_5",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
        }).encode()
        req = urllib.request.Request(url, data=payload, headers={
            "xi-api-key": key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg"
        })
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read()
        if len(data) > 1000:
            print(f"{PASS} ElevenLabs responded OK ({len(data)//1024}KB audio)")
        else:
            print(f"{WARN} ElevenLabs returned only {len(data)} bytes — possible error")
    except Exception as e:
        print(f"{FAIL} ElevenLabs API error: {e}")

# ── 2. Check video_urls.json ────────────────────────────────
hr()
print("2. video_urls.json")
urls_file = WORK_DIR / "video_urls.json"
if not urls_file.exists():
    print(f"{FAIL} Not found: {urls_file}")
    print("       Run the URL recovery step first.")
else:
    urls = json.loads(urls_file.read_text())
    print(f"{PASS} Found — {len(urls)} URLs")

    # Test scene 1 CDN URL
    print("     Testing scene 1 CDN URL (download check)...")
    test_url = urls.get("1", "")
    test_file = WORK_DIR / "_test_scene01.mp4"
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    try:
        urllib.request.urlretrieve(test_url, test_file)
        size = test_file.stat().st_size
        test_file.unlink()
        if size > 10000:
            print(f"{PASS} CDN scene 1 downloaded OK ({size//1024}KB)")
        else:
            print(f"{WARN} CDN scene 1 downloaded but only {size} bytes — may be error response")
    except Exception as e:
        print(f"{FAIL} CDN download FAILED: {e}")
        print(f"       URL: {test_url}")
        print(f"       DIAGNOSIS: Higgsfield CDN links may have expired.")
        print(f"       FIX: Need to re-fetch URLs via Higgsfield MCP job_display.")

# ── 3. Check ffmpeg ─────────────────────────────────────────
hr()
print("3. FFmpeg")
ffmpeg = None
for candidate in [
    shutil.which("ffmpeg"),
    r"C:\ffmpeg\bin\ffmpeg.exe",
    str(BASE_DIR / "ffmpeg_bin" / "ffmpeg.exe"),
]:
    if candidate and Path(candidate).exists():
        ffmpeg = candidate
        break

if ffmpeg:
    print(f"{PASS} ffmpeg found: {ffmpeg}")
    # Check ffprobe
    ffprobe = ffmpeg.replace("ffmpeg.exe", "ffprobe.exe")
    if Path(ffprobe).exists():
        print(f"{PASS} ffprobe found: {ffprobe}")
    else:
        # Try the simple replace used in assemble script
        ffprobe2 = ffmpeg.replace("ffmpeg", "ffprobe")
        print(f"{WARN} ffprobe path from script: {ffprobe2}")
        if Path(ffprobe2).exists():
            print(f"{PASS} ffprobe (script path) exists OK")
        else:
            print(f"{WARN} ffprobe not at expected path — duration probe will use script default (OK, non-fatal)")
else:
    print(f"{FAIL} ffmpeg NOT FOUND in PATH or C:\\ffmpeg\\bin or ffmpeg_bin\\")
    print(f"       FIX: Install ffmpeg or copy to C:\\ffmpeg\\bin\\ffmpeg.exe")

# ── 4. Check LO EP001 script JSON ───────────────────────────
hr()
print("4. LO EP001 Script JSON")
script_path = BASE_DIR / "prompts" / "little_olympus" / "scene_prompts.lo_ep001.final.json"
if not script_path.exists():
    print(f"{FAIL} Not found: {script_path}")
else:
    try:
        script = json.loads(script_path.read_text())
        scenes = script.get("scenes", [])
        print(f"{PASS} Loaded — {len(scenes)} scenes")
    except Exception as e:
        print(f"{FAIL} JSON parse error: {e}")

# ── 5. Check renders/ output folder ─────────────────────────
hr()
print("5. Output folders")
renders = BASE_DIR / "renders"
if renders.exists():
    print(f"{PASS} renders/ exists")
else:
    print(f"{WARN} renders/ missing — will be created on run")
final = renders / "LO_EP001_HIGGSFIELD_final.mp4"
if final.exists():
    size_mb = final.stat().st_size / 1024 / 1024
    print(f"{PASS} Final MP4 already exists! {size_mb:.0f}MB — it DID complete")
    print(f"       Path: {final}")
else:
    print(f"  [--] LO_EP001_HIGGSFIELD_final.mp4 does not exist yet")

# ── Summary ─────────────────────────────────────────────────
hr()
print("DIAGNOSIS COMPLETE")
print("Check [FAIL] lines above — those are your blockers.")
print()
