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
import shutil
import sys
from pathlib import Path


def _find_ffmpeg() -> str:
    """Locate ffmpeg: PATH first, then known Windows install locations.

    Bare "ffmpeg" fails with WinError 2 in subprocesses when ffmpeg is not
    on PATH — always resolve the full executable path up front.
    """
    if f := shutil.which("ffmpeg"):
        return f
    for candidate in (
        Path(r"C:\ffmpeg\ffmpeg-8.1.2-essentials_build\bin\ffmpeg.exe"),
        Path(r"C:\ffmpeg\bin\ffmpeg.exe"),
        Path(__file__).resolve().parent / "ffmpeg_bin" / "ffmpeg.exe",
    ):
        if candidate.exists():
            return str(candidate)
    raise RuntimeError("ffmpeg not found — install it or add to PATH")


def _find_ffprobe(ffmpeg: str) -> str:
    """Locate ffprobe next to ffmpeg (or on PATH)."""
    if ffmpeg.lower().endswith("ffmpeg.exe"):
        probe = ffmpeg[: -len("ffmpeg.exe")] + "ffprobe.exe"
        if Path(probe).exists():
            return probe
    return shutil.which("ffprobe") or "ffprobe"


FFMPEG = _find_ffmpeg()
FFPROBE = _find_ffprobe(FFMPEG)

# Ken Burns motion presets — variety keeps it visually interesting.
# {size} is filled in at call time so the same presets serve landscape
# (1920x1080, documentary episodes) and vertical (1080x1920, Reels/TikTok/
# Shorts commercials) output without duplicating the five zoompan formulas.
MOTION_PRESETS = [
    # Slow zoom in from center
    "zoompan=z='min(zoom+0.0015,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={size}:fps=25",
    # Pan left to right
    "zoompan=z='1.2':x='if(lte(on,1),0,x+1.2)':y='ih/2-(ih/zoom/2)':d={frames}:s={size}:fps=25",
    # Pan right to left
    "zoompan=z='1.2':x='if(lte(on,1),iw*0.2,x-1.2)':y='ih/2-(ih/zoom/2)':d={frames}:s={size}:fps=25",
    # Slow zoom out from top
    "zoompan=z='max(zoom-0.0015,1.0)':x='iw/2-(iw/zoom/2)':y='0':d={frames}:s={size}:fps=25",
    # Pan up slowly
    "zoompan=z='1.15':x='iw/2-(iw/zoom/2)':y='if(lte(on,1),ih*0.1,y+0.8)':d={frames}:s={size}:fps=25",
]


def ken_burns_clip(
    image_path: str,
    out_path: str,
    duration: float = 45,
    motion: str = "random",
    fade_in: float = 0.5,
    fade_out: float = 0.5,
    size: str = "1920x1080",
) -> bool:
    """
    Create a video clip from a static image with Ken Burns pan/zoom effect.

    Args:
        image_path: Path to source image (jpg/png)
        out_path: Output video path (.mp4)
        duration: Clip duration in seconds (float — exact durations supported
            so multi-image scenes can split narration time equally)
        motion: 'random' or index 0-4 to pick a specific preset
        fade_in: Fade-in duration in seconds
        fade_out: Fade-out duration in seconds
        size: Output resolution as "WxH". Default matches existing GG/LO/IL
            episode renders (1920x1080); pass "1080x1920" for vertical
            Reels/TikTok/Shorts output.

    Returns:
        True if successful
    """
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    frames = max(1, int(round(duration * 25)))  # 25fps
    if motion == "random":
        preset = random.choice(MOTION_PRESETS)
    else:
        preset = MOTION_PRESETS[int(motion) % len(MOTION_PRESETS)]

    zoompan_filter = preset.format(frames=frames, size=size)

    # Add fade in/out on top of Ken Burns
    fade_out_start = max(0.0, duration - fade_out)
    vf = (
        f"{zoompan_filter},"
        f"fade=t=in:st=0:d={fade_in},"
        f"fade=t=out:st={fade_out_start:.3f}:d={fade_out}"
    )

    cmd = [
        FFMPEG, "-y",
        "-loop", "1",
        "-i", image_path,
        "-vf", vf,
        "-t", f"{duration:.3f}",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-an",
        out_path,
    ]

    print(f"[video_effects] Ken Burns: {image_path} → {out_path} ({duration:.1f}s)")
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
        FFPROBE, "-v", "quiet", "-print_format", "json",
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
        # NOTE 2026-08-12: y uses `h` (drawtext's frame-height constant), not
        # `ih` — `ih` is undefined inside drawtext's own expression evaluator
        # (it belongs to filters like scale/crop/drawbox) and fails with
        # "Undefined constant ... in 'ih-110'" the moment this actually runs.
        # Confirmed live: this function had never been exercised by any
        # rendered episode (only gg_ep012_v3.json sets lower_third, and S3
        # scripts were written but not yet rendered) — caught before it broke
        # a real render.
        f"drawtext=text='{esc(title)}'"
        f":fontcolor=white:fontsize=42:x=60:y=h-110"
        f":fontfile=/Windows/Fonts/arialbd.ttf"
        f":enable='between(t,{show_at},{hide_at})'",
    ]

    if subtitle:
        vf_parts.append(
            f"drawtext=text='{esc(subtitle)}'"
            f":fontcolor=#FFCC44:fontsize=28:x=60:y=h-62"
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


def _esc(s: str) -> str:
    """Escape text for FFmpeg drawtext (shared by every card function below)."""
    return s.replace("\\", "\\\\").replace("'", "\\'").replace(":", "\\:").replace(",", "\\,")


def add_title_card(
    video_path: str,
    out_path: str,
    title: str,
    subtitle: str = "",
    show_at: float = 0.0,
    hide_at: float | None = None,
    bg_color: str = "black@0.55",
) -> bool:
    """
    Full-frame title card — distinct from add_lower_third(), which only
    darkens a bottom bar. Used for a commercial's opening scene, where the
    title needs to read clearly over the whole frame, not just a strip of it.

    Args:
        video_path: Input video (typically a Ken Burns background clip)
        out_path: Output video
        title: Main title text (e.g. product name)
        subtitle: Optional secondary line
        show_at / hide_at: Visibility window in seconds. hide_at=None means
            "for the whole clip" (probes duration to find the end).
        bg_color: FFmpeg color+alpha for the full-frame dark overlay, so text
            stays readable over a busy product photo.

    Returns:
        True if successful
    """
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    if hide_at is None:
        hide_at = _probe_duration(video_path) or 999.0

    vf_parts = [
        f"drawbox=x=0:y=0:w=iw:h=ih:color={bg_color}:t=fill"
        f":enable='between(t,{show_at},{hide_at})'",
        f"drawtext=text='{_esc(title)}'"
        f":fontcolor=white:fontsize=72:x=(w-text_w)/2:y=(h-text_h)/2"
        f":fontfile=/Windows/Fonts/arialbd.ttf"
        f":enable='between(t,{show_at},{hide_at})'",
    ]
    if subtitle:
        vf_parts.append(
            f"drawtext=text='{_esc(subtitle)}'"
            f":fontcolor=#FFCC44:fontsize=36:x=(w-text_w)/2:y=(h/2)+60"
            f":fontfile=/Windows/Fonts/arial.ttf"
            f":enable='between(t,{show_at},{hide_at})'"
        )

    cmd = [
        FFMPEG, "-y", "-i", video_path, "-vf", ",".join(vf_parts),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-c:a", "copy",
        out_path,
    ]
    print(f"[video_effects] Title card: '{title}' → {out_path}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[video_effects] FFmpeg error:\n{result.stderr[-500:]}", file=sys.stderr)
        return False
    print(f"[video_effects] ✅ {out_path}")
    return True


def add_price_card(
    video_path: str,
    out_path: str,
    price: str,
    cta_text: str = "",
    show_at: float = 0.0,
    hide_at: float | None = None,
) -> bool:
    """
    Price + call-to-action card for a commercial's closing scenes
    (e.g. "$49.99" + "Available now — link in bio"). Same drawbox+drawtext
    primitives as add_lower_third()/add_title_card(), different layout: price
    is large and centered, CTA sits below it in a solid accent bar so it
    reads as a clickable button even in a static frame.

    Returns:
        True if successful
    """
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    if hide_at is None:
        hide_at = _probe_duration(video_path) or 999.0

    vf_parts = [
        # Dark band across the lower third so price/CTA stay legible.
        f"drawbox=x=0:y=ih-260:w=iw:h=260:color=black@0.72:t=fill"
        f":enable='between(t,{show_at},{hide_at})'",
        f"drawtext=text='{_esc(price)}'"
        f":fontcolor=#FFCC44:fontsize=64:x=(w-text_w)/2:y=h-220"
        f":fontfile=/Windows/Fonts/arialbd.ttf"
        f":enable='between(t,{show_at},{hide_at})'",
    ]
    if cta_text:
        vf_parts.append(
            f"drawbox=x=(iw-420)/2:y=ih-120:w=420:h=64:color=#D4A017:t=fill"
            f":enable='between(t,{show_at},{hide_at})'"
        )
        vf_parts.append(
            f"drawtext=text='{_esc(cta_text)}'"
            f":fontcolor=black:fontsize=32:x=(w-text_w)/2:y=h-104"
            f":fontfile=/Windows/Fonts/arialbd.ttf"
            f":enable='between(t,{show_at},{hide_at})'"
        )

    cmd = [
        FFMPEG, "-y", "-i", video_path, "-vf", ",".join(vf_parts),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-c:a", "copy",
        out_path,
    ]
    print(f"[video_effects] Price card: '{price}' → {out_path}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[video_effects] FFmpeg error:\n{result.stderr[-500:]}", file=sys.stderr)
        return False
    print(f"[video_effects] ✅ {out_path}")
    return True


def _probe_duration(media_path: str) -> float | None:
    """Return media duration in seconds via ffprobe, or None on failure."""
    result = subprocess.run(
        [FFPROBE, "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", media_path],
        capture_output=True, text=True,
    )
    try:
        return float(result.stdout.strip())
    except (ValueError, AttributeError):
        return None


if __name__ == "__main__":
    # Quick test
    print("video_effects.py — Ken Burns + music overlay module")
    print("Import and use: ken_burns_clip(), mix_music(), add_lower_third(), "
          "add_title_card(), add_price_card()")
