#!/usr/bin/env python3
"""
assemble_lo_ep001_higgsfield.py
Downloads Higgsfield video clips + generates ElevenLabs TTS, assembles LO EP001.
Run after all 24 Higgsfield video jobs complete.
"""
import os, json, shutil, subprocess, urllib.request
from pathlib import Path

BASE_DIR   = Path(__file__).resolve().parent
WORK_DIR   = BASE_DIR / "output" / "LO_EP001_HIGGSFIELD"
RENDERS    = BASE_DIR / "renders"
WORK_DIR.mkdir(parents=True, exist_ok=True)
RENDERS.mkdir(exist_ok=True)

# Load .env
for line in (BASE_DIR / ".env").read_text(errors="ignore").splitlines():
    if "=" in line and not line.startswith("#"):
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

ELEVEN_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
VOICE_ID   = "JBFqnCBsd6RMkjVDRZzb"   # George — deep cinematic male
# LO uses warm playful storyteller — swap to a female voice if preferred
LO_VOICE   = "EXAVITQu4vr4xnSDxMaL"   # Bella — warm female (ElevenLabs preset)

# ── Scene data ─────────────────────────────────────────────────────────────────
SCRIPT = json.load(open(BASE_DIR / "prompts" / "little_olympus" / "scene_prompts.lo_ep001.final.json"))
SCENES = SCRIPT["scenes"]

# Higgsfield CDN video URLs — filled in once all jobs complete
# Format: scene_number -> CDN URL (filled by fill_urls step)
VIDEO_URLS_FILE = WORK_DIR / "video_urls.json"

# Job IDs in scene order (for polling)
JOB_IDS = {
    1:  "eeefd769-1bbc-4323-9744-f8cea44e07ae",
    2:  "6f1ee452-e9d2-4567-ba22-701ca56de71e",
    3:  "7c2006a7-4f6e-4a4d-b222-cac46b3d09ce",
    4:  "01ce06be-a9e7-4866-b375-814f8bc05916",
    5:  "dcfb0477-7b05-4b54-a85a-e9a7cfd4c5a2",
    6:  "835c717d-1e48-486b-a7e7-ca6fb0e1b36f",
    7:  "553f9b82-1341-47f8-b404-93d6e4bc1910",
    8:  "10d1e448-2edc-4c66-bb58-168eb260c858",
    9:  "e557f9ad-f2b2-4086-a127-ce24fce7fea9",
    10: "e1663a54-9692-4141-8e53-fb26851ff012",
    11: "514c108d-1920-49dd-ba2c-2fca01a804fa",
    12: "7b13a14e-a9d4-42fa-bedf-f5fb9269e749",
    13: "7c867874-b146-47f3-b7c9-2724e79f4196",
    14: "325105aa-ab32-435d-aab4-d2c5177128ca",
    15: "ff3a53e4-6cff-4070-aafd-3bbb64b13ab0",
    16: "066d0de0-4205-4d03-b8fc-e7eacb6af0a8",
    17: "2dad8e6a-2abb-4a54-a36a-bfafa8f9baba",
    18: "0a1e0127-265c-4c2a-931a-24d112d49405",
    19: "0e99c93b-17e7-45e4-8b6d-ed294f2b8caa",
    20: "6652e3da-c952-401b-85c0-a49db0767687",
    21: "849da7c9-5156-4f19-90bd-2448b0048338",
    22: "bd1f6aaa-e4a7-44a4-8276-7aa32c13333b",
    23: "681e8942-ced0-4df8-8298-9638f8dd7afc",
    24: "5a88d739-df7b-4642-9eeb-80c0a797856b",
}


def find_ffmpeg():
    f = shutil.which("ffmpeg")
    if f: return f
    for c in [r"C:\ffmpeg\bin\ffmpeg.exe", str(BASE_DIR / "ffmpeg_bin" / "ffmpeg.exe")]:
        if Path(c).exists(): return c
    raise RuntimeError("ffmpeg not found")


def download(url: str, dest: Path):
    if dest.exists() and dest.stat().st_size > 1000:
        print(f"  [skip] {dest.name} already downloaded")
        return
    print(f"  [dl] {dest.name}")
    urllib.request.urlretrieve(url, dest)


def tts_elevenlabs(text: str, out_path: Path):
    """Generate TTS via ElevenLabs API."""
    if out_path.exists() and out_path.stat().st_size > 1000:
        print(f"  [skip] {out_path.name} already generated")
        return
    if not ELEVEN_KEY:
        raise RuntimeError("ELEVENLABS_API_KEY not set in .env")
    import urllib.request as req, json
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{LO_VOICE}"
    payload = json.dumps({
        "text": text,
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "speed": 0.9}
    }).encode()
    r = req.Request(url, data=payload, headers={
        "xi-api-key": ELEVEN_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg"
    })
    with req.urlopen(r) as resp:
        out_path.write_bytes(resp.read())
    print(f"  [tts] {out_path.name}")


def assemble_scene(ffmpeg: str, video: Path, audio: Path, out: Path, target_dur: float):
    """Overlay TTS audio on video clip, loop video if audio is longer."""
    if out.exists() and out.stat().st_size > 10000:
        print(f"  [skip] {out.name}")
        return
    # Get audio duration — use ffprobe at same bin dir as ffmpeg
    ffprobe = ffmpeg.replace("ffmpeg.exe", "ffprobe.exe")
    probe = subprocess.run(
        [ffprobe, "-v", "quiet",
         "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
         str(audio)], capture_output=True
    )
    audio_dur = float(probe.stdout.strip() or target_dur)
    # Stream loop video to match audio length, overlay audio
    subprocess.run([
        ffmpeg, "-y",
        "-stream_loop", "-1", "-i", str(video),
        "-i", str(audio),
        "-map", "0:v", "-map", "1:a",
        "-shortest", "-t", str(max(audio_dur, 3)),
        "-c:v", "libx264", "-crf", "20", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        str(out)
    ], check=True)
    print(f"  [ok] {out.name}")


def main():
    ffmpeg = find_ffmpeg()

    # Load video URLs (must be filled in first)
    if not VIDEO_URLS_FILE.exists():
        print("\nERROR: video_urls.json not found.")
        print("Run POLL_HIGGSFIELD_URLS.bat first to fetch completed video URLs.\n")
        return

    urls = json.loads(VIDEO_URLS_FILE.read_text())

    scene_clips = []
    for scene in SCENES:
        n   = scene["scene_number"]
        dur = float(scene.get("duration_sec", 30))
        narr = scene.get("narration", "")

        video_path = WORK_DIR / f"scene_{n:02d}_video.mp4"
        audio_path = WORK_DIR / f"scene_{n:02d}_audio.mp3"
        clip_path  = WORK_DIR / f"scene_{n:02d}_clip.mp4"

        url = urls.get(str(n))
        if not url:
            print(f"  [WARN] No URL for scene {n} — skipping")
            continue

        print(f"\n── Scene {n} ──")
        download(url, video_path)
        if narr.strip():
            tts_elevenlabs(narr, audio_path)
            assemble_scene(ffmpeg, video_path, audio_path, clip_path, dur)
        else:
            # No narration — use video as-is
            shutil.copy(video_path, clip_path)

        scene_clips.append(clip_path)

    if not scene_clips:
        print("No clips assembled — check video_urls.json")
        return

    # Concatenate all scene clips
    concat_file = WORK_DIR / "concat.txt"
    concat_file.write_text("\n".join(f"file '{p}'" for p in scene_clips))

    final = RENDERS / "LO_EP001_HIGGSFIELD_final.mp4"
    print(f"\n── Concatenating {len(scene_clips)} clips → {final.name} ──")
    subprocess.run([
        ffmpeg, "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        str(final)
    ], check=True)

    size_mb = final.stat().st_size / 1024 / 1024
    print(f"\n✅  Done! {final.name} ({size_mb:.0f}MB)")
    print(f"    Path: {final}")


if __name__ == "__main__":
    main()
