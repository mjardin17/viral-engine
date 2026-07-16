"""
video_effects.py — Ken Burns pan/zoom + music overlay for Gods & Glory pipeline v3.0

Ken Burns effect: slow pan + zoom on static images using FFmpeg zoompan filter
Music overlay: mix background music under narration at reduced volume

Usage:
    from video_effects import ken_burns_clip, mix_music

    # Create 45-second clip from image with Ken Burns effect
    ken_burns_clip("images/scene_01.jpg", "clips/scene_01.mp4", duration=45)

    # Mix music under narrated video
    mix_music("episode_no_music.mp4", "music/epic_battle.mp3", "episode_final.mp4", music_vol=0.18)
"""

import subprocess
import random
import os
import sys


FFMPEG = "ffmpeg"

# Ken Burns motion presets — variety keeps it visually interesting
MOTION_PRESETS = [
    # Slow zoom in from center
    "zoompan=z='min(zoom+0.0015,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1920x1080:fps=25",
    # Pan left to right
    "zoompan=z='1.2':x='if(lte(on,1),0,x+1.2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1920x1080:fps=25",
    # Pan right to left
    "zoompan=z='1.2':x='if(lte(on,1),iw*0.2,x-1.2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1920x1080:fps=25",
    # Slow zoom out from top
    "zoompan=z='max(zoom-0.0015,1.0)':x='iw/2-(iw/zoom/2)':y='0':d={frames}:s=1920x1080:fps=25",
    # Pan up slowly
    "zoompan=z='1.15':x='iw/2-(iw/zoom/2)':y='if(lte(on,1),ih*0.1,y+0.8)':d={frames}:s=1920x1080:fps=25",
]


def ken_burns_clip(
    image_path: str,
    out_path: str,
    duration: int = 45,
    motion: str = "random",
    fade_in: float = 0.5,
    fade_out: float = 0.5,
) -> bool:
    """
    Create a video clip from a static image with Ken Burns pan/zoom effect.

    Args:
        image_path: Path to source image (jpg/png)
        out_path: Output video path (.mp4)
        duration: Clip duration in seconds
        motion: 'random' or index 0-4 to pick a specific preset
        fade_in: Fade-in duration in seconds
        fade_out: Fade-out duration in seconds

    Returns:
        True if successful
    """
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    frames = duration * 25  # 25fps
    if motion == "random":
        preset = random.choice(MOTION_PRESETS)
    else:
        preset = MOTION_PRESETS[int(motion) % len(MOTION_PRESETS)]

    zoompan_filter = preset.format(frames=frames)

    # Add fade in/out on top of Ken Burns
    vf = (
        f"{zoompan_filter},"
        f"fade=t=in:st=0:d={fade_in},"
        f"fade=t=out:st={duration - fade_out}:d={fade_out}"
    )

    cmd = [
        FFMPEG, "-y",
        "-loop", "1",
        "-i", image_path,
        "-vf", vf,
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-an",
        out_path,
    ]

    print(f"[video_effects] Ken Burns: {image_path} → {out_path} ({duration}s)")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[video_effects] FFmpeg error:\n{result.stderr[-500:]}", file=sys.stderr)
        return False
    print(f"[video_effects] ✅ {out_path}")
    return True


def mix_music(
    video_path: str,
    music_path: str,
    out_path: str,
    music_vol: float = 0.18,
    fade_music_out: float = 3.0,
) -> bool:
    """
    Mix background music under narrated video.

    Args:
        video_path: Input video with narration audio
        music_path: Background music file (mp3/wav)
        out_path: Output video path
        music_vol: Music volume relative to narration (0.0–1.0, default 0.18 = 18%)
        fade_music_out: Fade music out over this many seconds at end

    Returns:
        True if successful
    """
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    # Get video duration for music fade
    probe_cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", video_path
    ]
    probe = subprocess.run(probe_cmd, capture_output=True, text=True)
    duration = 60.0  # fallback
    try:
        import json
        info = json.loads(probe.stdout)
        duration = float(info["format"]["duration"])
    except Exception:
        pass

    fade_start = max(0, duration - fade_music_out)

    # afade music out at end, then mix under narration
    filter_complex = (
        f"[1:a]volume={music_vol},"
        f"afade=t=out:st={fade_start:.2f}:d={fade_music_out},"
        f"aloop=loop=-1:size=2e+09[music];"
        f"[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[aout]"
    )

    cmd = [
        FFMPEG, "-y",
        "-i", video_path,
        "-i", music_path,
        "-filter_complex", filter_complex,
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        out_path,
    ]

    print(f"[video_effects] Music mix: {video_path} + {music_path} → {out_path}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[video_effects] FFmpeg error:\n{result.stderr[-500:]}", file=sys.stderr)
        return False
    print(f"[video_effects] ✅ {out_path}")
    return True


def add_lower_third(
    video_path: str,
    out_path: str,
    title: str,
    subtitle: str = "",
    show_at: float = 1.5,
    hide_at: float = 6.0,
) -> bool:
    """
    Add a lower-third title card (e.g. 'Battle of Thermopylae — 480 BC').

    Args:
        video_path: Input video
        out_path: Output video
        title: Main title text
        subtitle: Optional subtitle (date, location, etc.)
        show_at: When to show (seconds)
        hide_at: When to hide (seconds)

    Returns:
        True if successful
    """
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    # Escape special chars for FFmpeg drawtext
    def esc(s):
        return s.replace("'", "\\'").replace(":", "\\:").replace(",", "\\,")

    duration_show = hide_at - show_at

    vf_parts = [
        # Dark background bar
        f"drawbox=x=0:y=ih-140:w=iw:h=140:color=black@0.65:t=fill"
        f":enable='between(t,{show_at},{hide_at})'",
        # Main title
        f"drawtext=text='{esc(title)}'"
        f":fontcolor=white:fontsize=42:x=60:y=ih-110"
        f":fontfile=/Windows/Fonts/arialbd.ttf"
        f":enable='between(t,{show_at},{hide_at})'",
    ]

    if subtitle:
        vf_parts.append(
            f"drawtext=text='{esc(subtitle)}'"
            f":fontcolor=#FFCC44:fontsize=28:x=60:y=ih-62"
            f":fontfile=/Windows/Fonts/arial.ttf"
            f":enable='between(t,{show_at},{hide_at})'"
        )

    vf = ",".join(vf_parts)

    cmd = [
        FFMPEG, "-y",
        "-i", video_path,
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-c:a", "copy",
        out_path,
    ]

    print(f"[video_effects] Lower third: '{title}' → {out_path}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[video_effects] FFmpeg error:\n{result.stderr[-500:]}", file=sys.stderr)
        return False
    print(f"[video_effects] ✅ {out_path}")
    return True


if __name__ == "__main__":
    # Quick test
    print("video_effects.py — Ken Burns + music overlay module")
    print("Import and use: ken_burns_clip(), mix_music(), add_lower_third()")
