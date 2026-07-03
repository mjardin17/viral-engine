#!/usr/bin/env python3
import argparse
import json
import os
import random
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv
try:
    from elevenlabs.client import ElevenLabs
except Exception:
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
MUSIC_VOLUME = 0.20
TRANSITION_SEC = 0.75
DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
DEFAULT_MODEL_ID = "eleven_v3"
SHOT_PRESETS = {
    "hero_closeup": {"zoom_start": 1.06, "zoom_end": 1.16, "pan_x": 0.00, "pan_y": -0.01},
    "establishing_wide": {"zoom_start": 1.00, "zoom_end": 1.07, "pan_x": 0.00, "pan_y": 0.00},
    "dramatic_push": {"zoom_start": 1.03, "zoom_end": 1.20, "pan_x": 0.00, "pan_y": -0.01},
    "slow_drift": {"zoom_start": 1.03, "zoom_end": 1.11, "pan_x": 0.03, "pan_y": -0.02},
    "orbit_feel": {"zoom_start": 1.04, "zoom_end": 1.10, "pan_x": -0.03, "pan_y": 0.02},
    "tense_static": {"zoom_start": 1.02, "zoom_end": 1.05, "pan_x": 0.00, "pan_y": 0.00},
    "handheld": {"zoom_start": 1.05, "zoom_end": 1.12, "pan_x": 0.01, "pan_y": 0.01},
}
CAMERA_MOVES = {
    "push_in": "dramatic_push",
    "pull_out": "establishing_wide",
    "pan_left": "slow_drift",
    "pan_right": "slow_drift",
    "tilt_up": "slow_drift",
    "tilt_down": "slow_drift",
    "orbit": "orbit_feel",
    "drift": "slow_drift",
    "handheld": "handheld",
    "static": "tense_static",
}
LENS_BOOST = {"24mm": 1.12, "35mm": 1.00, "50mm": 0.92, "85mm": 0.84}
STYLE_FILTERS = {
    "cinematic_dark": "eq=contrast=1.09:saturation=1.12:brightness=-0.01,curves=preset=medium_contrast,vignette=PI/6,unsharp=5:5:0.45:3:3:0.20",
    "clean_high_contrast": "eq=contrast=1.12:saturation=1.05:brightness=0.00,unsharp=5:5:0.35:3:3:0.15",
    "teal_orange": "eq=contrast=1.10:saturation=1.18:brightness=0.00,vignette=PI/7,unsharp=5:5:0.45:3:3:0.20",
    "moody_desaturated": "eq=contrast=1.06:saturation=0.82:brightness=-0.02,vignette=PI/5,unsharp=5:5:0.30:3:3:0.10",
    "default": "eq=contrast=1.07:saturation=1.08:brightness=0.00,vignette=PI/7,unsharp=5:5:0.35:3:3:0.15",
}
TRANSITIONS = {
    "crossfade": "fade",
    "fade": "fade",
    "wipeleft": "wipeleft",
    "wiperight": "wiperight",
    "wipeup": "wipeup",
    "wipedown": "wipedown",
    "slideleft": "slideleft",
    "slideright": "slideright",
    "circlecrop": "circlecrop",
}
@dataclass
class SceneCfg:
    scene_number: int
    narration: str
    visual_prompt: str
    duration_sec: float
    camera_move: str = "push_in"
    motion_strength: str = "medium"
    lens: str = "35mm"
    focal_length: str = "35mm"
    style_preset: str = "cinematic_dark"
    speed_ramp: str = "slow"
    transition: str = "crossfade"
    shot_style: str = "hero_closeup"
def ensure_dirs():
    for p in [PROMPTS_DIR, IMAGES_DIR, AUDIO_DIR, OUTPUT_DIR, WORK_DIR]:
        p.mkdir(parents=True, exist_ok=True)
def run(cmd):
    subprocess.run(cmd, check=True)
def which_or_fail(name):
    if shutil.which(name) is None:
        raise RuntimeError(f"Missing required executable: {name}")
def read_episode(episode_id):
    matches = sorted(PROMPTS_DIR.glob(f"**/{episode_id}.json"))
    if not matches:
        raise FileNotFoundError(f"No JSON found for {episode_id} in {PROMPTS_DIR}")
    return json.loads(matches[0].read_text(encoding="utf-8"))
def scene_image_path(episode_id, num):
    return IMAGES_DIR / episode_id / f"scene_{num:02d}.png"
def scene_audio_path(episode_id, num):
    return AUDIO_DIR / episode_id / f"scene_{num:02d}.mp3"
def scene_segment_path(work_dir, num):
    return work_dir / f"scene_{num:02d}.mp4"
def probe_duration(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ], text=True).strip()
    return float(out)
def tts_client():
    load_dotenv()
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is missing")
    if ElevenLabs is None:
        raise RuntimeError("elevenlabs package is not installed")
    return ElevenLabs(api_key=api_key)
def voice_settings():
    try:
        from elevenlabs import VoiceSettings
        return VoiceSettings(stability=0.18, similarity_boost=0.90, style=0.40, use_speaker_boost=True, speed=1.0)
    except Exception:
        return None
def generate_voiceover(client, text, out_path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    kwargs = dict(
        text=text,
        voice_id=os.getenv("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID),
        model_id=os.getenv("ELEVENLABS_MODEL_ID", DEFAULT_MODEL_ID),
        output_format="mp3_44100_128",
    )
    vs = voice_settings()
    if vs is not None:
        kwargs["voice_settings"] = vs
    audio = client.text_to_speech.convert(**kwargs)
    with open(out_path, "wb") as f:
        if hasattr(audio, "read"):
            f.write(audio.read())
        else:
            for chunk in audio:
                if chunk:
                    f.write(chunk)
def black_frame(tmpdir):
    p = tmpdir / "black.png"
    run([
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=black:s={WIDTH}x{HEIGHT}:r={FPS}",
        "-frames:v", "1",
        str(p),
    ])
    return p
def clamp(v, lo, hi):
    return max(lo, min(hi, v))
def scene_cfg(scene):
    shot_style = str(scene.get("shot_style", "hero_closeup"))
    camera_move = str(scene.get("camera_move", "push_in")).lower()
    move_key = CAMERA_MOVES.get(camera_move, camera_move)
    base = dict(SHOT_PRESETS.get(shot_style, SHOT_PRESETS["hero_closeup"]))
    if move_key in SHOT_PRESETS:
        base = dict(SHOT_PRESETS[move_key])
    strength = str(scene.get("motion_strength", "medium")).lower()
    strength_mul = {"low": 0.78, "medium": 1.0, "high": 1.28}.get(strength, 1.0)
    lens = str(scene.get("lens", "35mm")).lower()
    lens_mul = LENS_BOOST.get(lens, 1.0)
    factor = strength_mul * lens_mul
    base["zoom_end"] = 1.0 + (base["zoom_end"] - 1.0) * factor
    base["pan_x"] *= factor
    base["pan_y"] *= factor
    return {
        "shot_style": shot_style,
        "camera_move": camera_move,
        "motion_strength": strength,
        "lens": lens,
        "focal_length": str(scene.get("focal_length", lens)),
        "style_preset": str(scene.get("style_preset", "cinematic_dark")),
        "speed_ramp": str(scene.get("speed_ramp", "slow")),
        "transition": str(scene.get("transition", "crossfade")),
        **base,
    }
def scene_filter(duration, cfg):
    frames = max(1, int(round(duration * FPS)))
    zoom_start = cfg["zoom_start"]
    zoom_end = cfg["zoom_end"]
    pan_x = cfg["pan_x"]
    pan_y = cfg["pan_y"]
    style = STYLE_FILTERS.get(cfg["style_preset"], STYLE_FILTERS["default"])
    speed_mul = {"slow": 0.85, "normal": 1.0, "fast": 1.18}.get(cfg["speed_ramp"], 0.85)
    zoom_end = 1.0 + (zoom_end - 1.0) * speed_mul
    zoom_expr = f"min({zoom_start}+((on/{frames:.6f})*({zoom_end}-{zoom_start})),{zoom_end})"
    x_expr = f"(iw-ow)/2+((on/{frames:.6f})*({pan_x}*iw))"
    y_expr = f"(ih-oh)/2+((on/{frames:.6f})*({pan_y}*ih))"
    return (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},"
        f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}':d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS},"
        f"format=yuv420p,{style}"
    )
def build_transition_graph(scene_durations, transitions):
    if len(scene_durations) == 1:
        return None, "[v0]"
    parts = []
    current = "[v0]"
    offset = scene_durations[0] - TRANSITION_SEC
    for i in range(1, len(scene_durations)):
        tr = TRANSITIONS.get(transitions[i - 1], "fade")
        nxt = f"[v{i}]"
        out = f"[x{i}]"
        parts.append(f"{current}{nxt}xfade=transition={tr}:duration={TRANSITION_SEC}:offset={offset:.3f}{out}")
        current = out
        offset += scene_durations[i] - TRANSITION_SEC
    return ";".join(parts), current
def scene_video_cmd(img, aud, duration, out_path, cfg):
    vf = scene_filter(duration, cfg)
    return [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(img),
        "-i", str(aud),
        "-t", f"{duration:.3f}",
        "-vf", vf,
        "-r", str(FPS),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        str(out_path),
    ]
def add_music(video_path, music_path, out_path):
    if not music_path:
        shutil.copy2(video_path, out_path)
        return
    run([
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
    ])
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", required=True)
    ap.add_argument("--music", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    ensure_dirs()
    which_or_fail("ffmpeg")
    which_or_fail("ffprobe")
    ep = read_episode(args.episode)
    episode_id = ep["episode_id"]
    scenes = ep["scenes"]
    final_out = OUTPUT_DIR / f"{episode_id}_final.mp4"
    music_path = Path(args.music) if args.music else None
    if music_path and not music_path.is_absolute():
        music_path = BASE_DIR / music_path
    if args.dry_run:
        print(f"Episode: {episode_id}")
        for s in scenes:
            n = int(s["scene_number"])
            print(f"Scene {n:02d}: shot={s.get('shot_style','hero_closeup')} move={s.get('camera_move','push_in')} lens={s.get('lens','35mm')} style={s.get('style_preset','cinematic_dark')} transition={s.get('transition','crossfade')}")
        print(f"Output: {final_out}")
        if music_path:
            print(f"Music: {music_path}")
        return
    client = tts_client()
    ep_audio_dir = AUDIO_DIR / episode_id
    ep_work_dir = WORK_DIR / episode_id
    ep_audio_dir.mkdir(parents=True, exist_ok=True)
    ep_work_dir.mkdir(parents=True, exist_ok=True)
    segment_paths = []
    scene_durations = []
    transitions = []
    with tempfile.TemporaryDirectory(dir=WORK_DIR) as td:
        tmpdir = Path(td)
        placeholder = black_frame(tmpdir)
        for s in scenes:
            n = int(s["scene_number"])
            narration = s["narration"].strip()
            duration = float(s["duration_sec"])
            cfg = scene_cfg(s)
            img = scene_image_path(episode_id, n)
            aud = scene_audio_path(episode_id, n)
            seg = scene_segment_path(ep_work_dir, n)
            print(f"Rendering scene {n:02d}/{len(scenes):02d}")
            generate_voiceover(client, narration, aud)
            if probe_duration(aud) > duration:
                print(f"  note: audio longer than scene budget ({duration:.2f}s)")
            source_img = img if img.exists() else placeholder
            if not img.exists():
                print("  missing image, using black frame")
            run(scene_video_cmd(source_img, aud, duration, seg, cfg))
            segment_paths.append(seg)
            scene_durations.append(duration)
            transitions.append(cfg["transition"])
        if len(segment_paths) == 1:
            stitched = segment_paths[0]
        else:
            filter_graph, last_label = build_transition_graph(scene_durations, transitions)
            if not filter_graph:
                stitched = segment_paths[0]
            else:
                stitched = ep_work_dir / f"{episode_id}_stitched.mp4"
                cmd = ["ffmpeg", "-y"]
                for p in segment_paths:
                    cmd += ["-i", str(p)]
                cmd += ["-filter_complex", filter_graph, "-map", last_label, "-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart", str(stitched)]
                run(cmd)
        if music_path:
            add_music(stitched, music_path, final_out)
        else:
            shutil.copy2(stitched, final_out)
    print(f"Saved: {final_out}")
if __name__ == "__main__":
    main()
