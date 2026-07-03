#!/usr/bin/env python3
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from dotenv import load_dotenv
try:
    from elevenlabs.client import ElevenLabs
except Exception as e:
    ElevenLabs = None
BASE_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = BASE_DIR / "prompts"
IMAGES_DIR = BASE_DIR / "images"
AUDIO_DIR = BASE_DIR / "audio"
OUTPUT_DIR = BASE_DIR / "output"
WORK_DIR = BASE_DIR / "work"
WIDTH = 1080
HEIGHT = 1920
FPS = 30
ZOOM_RATE = 0.0009
CROSSFADE_SEC = 0.75
MUSIC_VOLUME = 0.20
VOICE_MODEL_ID = "eleven_v3"
def ensure_dirs():
    for p in [PROMPTS_DIR, IMAGES_DIR, AUDIO_DIR, OUTPUT_DIR, WORK_DIR]:
        p.mkdir(parents=True, exist_ok=True)
def run(cmd):
    subprocess.run(cmd, check=True)
def which_or_fail(name):
    if shutil.which(name) is None:
        raise RuntimeError(f"Required executable not found on PATH: {name}")
def read_episode(episode_id):
    matches = sorted(PROMPTS_DIR.glob(f"**/{episode_id}.json"))
    if not matches:
        raise FileNotFoundError(f"Episode JSON not found for {episode_id} in {PROMPTS_DIR}")
    with open(matches[0], "r", encoding="utf-8") as f:
        return json.load(f)
def scene_image_path(episode_id, scene_number):
    return IMAGES_DIR / episode_id / f"scene_{scene_number:02d}.png"
def scene_audio_path(episode_id, scene_number):
    return AUDIO_DIR / episode_id / f"scene_{scene_number:02d}.mp3"
def placeholder_image_path(tmpdir):
    p = tmpdir / "black.png"
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=black:s={WIDTH}x{HEIGHT}:r={FPS}",
        "-frames:v", "1",
        str(p),
    ]
    run(cmd)
    return p
def probe_duration(path):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    out = subprocess.check_output(cmd, text=True).strip()
    return float(out)
def estimate_audio_duration_seconds(text):
    words = len(text.split())
    return max(1.5, (words / 2.2))
def tts_client():
    load_dotenv()
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is missing")
    if ElevenLabs is None:
        raise RuntimeError("elevenlabs package is not installed")
    return ElevenLabs(api_key=api_key)
def generate_voiceover(client, text, out_path, dry_run=False):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if dry_run:
        print(f"[dry-run] Would generate voiceover: {out_path}")
        return
    audio = client.text_to_speech.convert(
        text=text,
        voice_id=os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb"),
        model_id=VOICE_MODEL_ID,
        output_format="mp3_44100_128",
    )
    if isinstance(audio, (bytes, bytearray)):
        out_path.write_bytes(audio)
    elif hasattr(audio, "read"):
        out_path.write_bytes(audio.read())
    else:
        with open(out_path, "wb") as f:
            for chunk in audio:
                f.write(chunk)
    print(f"Generated audio: {out_path}")
def make_scene_video(scene_idx, img_path, audio_path, duration, out_path, placeholder=False):
    zoom_expr = f"zoom='min(zoom+{ZOOM_RATE},1.10)':d={int(duration*FPS)}"
    vf = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},"
        f"zoompan={zoom_expr}:s={WIDTH}x{HEIGHT}:fps={FPS},"
        f"format=yuv420p"
    )
    if placeholder:
        img_input = [
            "-f", "lavfi",
            "-i", f"color=c=black:s={WIDTH}x{HEIGHT}:r={FPS}",
        ]
    else:
        img_input = ["-loop", "1", "-i", str(img_path)]
    cmd = [
        "ffmpeg", "-y",
        *img_input,
        "-i", str(audio_path),
        "-t", f"{duration:.3f}",
        "-r", str(FPS),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        str(out_path),
    ]
    run(cmd)
def concat_video_segments(segment_paths, out_path):
    list_file = out_path.parent / "segments.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for p in segment_paths:
            f.write(f"file '{p.as_posix()}'\n")
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(out_path),
    ]
    run(cmd)
def add_music_and_normalize(video_path, music_path, out_path):
    if not music_path:
        shutil.copy2(video_path, out_path)
        return
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-stream_loop", "-1",
        "-i", str(music_path),
        "-filter_complex",
        f"[1:a]volume={MUSIC_VOLUME}[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[a]",
        "-map", "0:v:0",
        "-map", "[a]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        str(out_path),
    ]
    run(cmd)
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode", required=True)
    parser.add_argument("--music", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    ensure_dirs()
    which_or_fail("ffmpeg")
    which_or_fail("ffprobe")
    episode = read_episode(args.episode)
    episode_id = episode["episode_id"]
    scenes = episode["scenes"]
    ep_audio_dir = AUDIO_DIR / episode_id
    ep_audio_dir.mkdir(parents=True, exist_ok=True)
    ep_video_dir = WORK_DIR / episode_id
    ep_video_dir.mkdir(parents=True, exist_ok=True)
    ep_output = OUTPUT_DIR / f"{episode_id}_final.mp4"
    music_path = Path(args.music) if args.music else None
    if music_path and not music_path.is_absolute():
        music_path = BASE_DIR / music_path
    client = None
    if not args.dry_run:
        client = tts_client()
    print(f"Episode: {episode_id} | Title: {episode.get('title', '')}")
    print(f"Scenes: {len(scenes)}")
    if args.dry_run:
        for s in scenes:
            n = int(s["scene_number"])
            ap = scene_audio_path(episode_id, n)
            ip = scene_image_path(episode_id, n)
            print(f"Scene {n:02d}:")
            print(f"  audio -> {ap}")
            print(f"  image -> {ip} {'(missing, black frame used)' if not ip.exists() else ''}")
        print(f"Output -> {ep_output}")
        if music_path:
            print(f"Music  -> {music_path}")
        return
    placeholder = None
    with tempfile.TemporaryDirectory(dir=WORK_DIR) as td:
        tmpdir = Path(td)
        placeholder = placeholder_image_path(tmpdir)
        segment_paths = []
        for idx, scene in enumerate(scenes, start=1):
            scene_number = int(scene["scene_number"])
            narration = scene["narration"].strip()
            duration = float(scene["duration_sec"])
            img_path = scene_image_path(episode_id, scene_number)
            audio_path = scene_audio_path(episode_id, scene_number)
            seg_path = ep_video_dir / f"scene_{scene_number:02d}_segment.mp4"
            print(f"Processing scene {scene_number:02d}/{len(scenes):02d}")
            generate_voiceover(client, narration, audio_path, dry_run=False)
            actual_audio_dur = probe_duration(audio_path)
            if actual_audio_dur > duration:
                print(f"  warning: audio is {actual_audio_dur:.2f}s, scene budget is {duration:.2f}s")
            use_placeholder = not img_path.exists()
            source_img = placeholder if use_placeholder else img_path
            make_scene_video(
                idx,
                source_img,
                audio_path,
                duration,
                seg_path,
                placeholder=use_placeholder,
            )
            segment_paths.append(seg_path)
        stitched = ep_video_dir / f"{episode_id}_stitched.mp4"
        concat_video_segments(segment_paths, stitched)
        if music_path:
            add_music_and_normalize(stitched, music_path, ep_output)
        else:
            shutil.copy2(stitched, ep_output)
    print(f"Done: {ep_output}")
if __name__ == "__main__":
    main()
