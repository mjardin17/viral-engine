"""
empire_render.py — Empire OS Boss Tool (unified renderer for all channels)

One renderer for every Empire OS channel:

  GG (Gods & Glory)   — Wikimedia/Pollinations images + Ken Burns + Kokoro + music (18%)
  LO (Little Olympus) — Pre-generated Higgsfield clips + Kokoro narration + music (12%)
  IL (Iron Legends)   — Same pipeline as LO (Higgsfield clips)

CRITICAL RULE (LO/IL): each Higgsfield clip plays ONCE per scene.
  - Clip longer than narration  → trim clip to narration length
  - Clip shorter than narration → freeze last frame (tpad clone) — NEVER loop
  - Scenes always render and concat in scene_number order

Usage:
    python empire_render.py --channel GG --episode GG_EP012
    python empire_render.py --channel GG --episode GG_EP012 --music music/gg_battle_theme.mp3
    python empire_render.py --channel LO --episode LO_EP001 --clips-dir higgsfield_clips/LO_EP001/
    python empire_render.py --channel IL --episode IL_EP001 --clips-dir higgsfield_clips/IL_EP001/
    python empire_render.py --channel LO --episode LO_EP002   # no clips dir → provider waterfall
                                                              # (free APIs first, Higgsfield last)

Output:
    renders/gods_glory/GG_EP012_final.mp4
    renders/little_olympus/LO_EP001_final.mp4
    renders/iron_legends/IL_EP001_final.mp4
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

# ── Console safety (Windows cp1252 can't print ✅) ────────────────────────────
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:
        pass

BASE_DIR: Path = Path(__file__).resolve().parent

# Local pipeline modules (live in repo root)
sys.path.insert(0, str(BASE_DIR))
from wikimedia_fetch import search_wikimedia  # noqa: E402

TAG = "[empire_render]"

# ── Executables ────────────────────────────────────────────────────────────────
PYTHON_MAIN: Path = Path(r"C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe")
KOKORO_VENV_PYTHON: Path = BASE_DIR / "voice-music-factory" / "venv" / "Scripts" / "python.exe"
TTS_CLI: Path = BASE_DIR / "voice-music-factory" / "tts_cli.py"


def find_ffmpeg() -> str:
    """Locate ffmpeg: PATH first, then known Windows install locations."""
    if f := shutil.which("ffmpeg"):
        return f
    for candidate in (
        Path(r"C:\ffmpeg\ffmpeg-8.1.2-essentials_build\bin\ffmpeg.exe"),
        Path(r"C:\ffmpeg\bin\ffmpeg.exe"),
        BASE_DIR / "ffmpeg_bin" / "ffmpeg.exe",
    ):
        if candidate.exists():
            return str(candidate)
    raise RuntimeError("ffmpeg not found — install it or add to PATH")


def find_ffprobe(ffmpeg: str) -> str:
    """Locate ffprobe next to ffmpeg (or on PATH)."""
    if ffmpeg.lower().endswith("ffmpeg.exe"):
        probe = ffmpeg[: -len("ffmpeg.exe")] + "ffprobe.exe"
        if Path(probe).exists():
            return probe
    return shutil.which("ffprobe") or "ffprobe"


FFMPEG: str = find_ffmpeg()
FFPROBE: str = find_ffprobe(FFMPEG)

# ── Channel configuration ──────────────────────────────────────────────────────
CHANNEL_OUTPUT_DIR: dict[str, str] = {
    "GG": "gods_glory",
    "LO": "little_olympus",
    "IL": "iron_legends",
}
CHANNEL_PROMPT_DIR: dict[str, str] = {
    "GG": "gods_glory",
    "LO": "little_olympus",
    "IL": "iron_legends",
}
CHANNEL_VOICE: dict[str, str] = {
    "GG": "bm_george",   # British male — documentary authority
    "LO": "af_bella",    # Warm female — kids storyteller
    "IL": "am_fenrir",   # Dramatic male — Saturday-morning cartoon energy
}
CHANNEL_SPEED: dict[str, float] = {
    "GG": 0.95,  # v3.0 short punchy format — near-normal pace (old 0.65 was 45-min format)
    "LO": 0.90,  # Kids need time to follow
    "IL": 1.08,  # Fast and punchy
}
CHANNEL_MUSIC_VOL: dict[str, float] = {
    "GG": 0.18,
    "LO": 0.12,
    "IL": 0.12,
}
DEFAULT_GG_MUSIC: Path = BASE_DIR / "music" / "gg_battle_theme.mp3"

# Ken Burns presets rotate in this fixed order per scene (indexes into
# video_effects.MOTION_PRESETS): zoom_in, pan_left, pan_right, zoom_out, pan_up
KEN_BURNS_ROTATION: tuple[int, ...] = (0, 1, 2, 3, 4)

MIN_IMAGE_BYTES = 50 * 1024  # Wikimedia image must be >50KB to count as real

MAX_PARALLEL_SCENES = 2  # scenes rendered concurrently — keep low: Pollinations rate-limits ~1 req/s

# ── Quality feature flags (Josh can set to False to disable) ───────────────────
SMART_IMAGE_PROMPTS = True  # Use Gemini to match images to narration
ACTION_VIDEO_CLIPS = True   # Try FAL/Replicate for action scenes

# Gemini text models tried in order for narration → image-prompt generation
GEMINI_TEXT_MODELS: tuple[str, ...] = ("gemini-2.5-flash", "gemini-2.0-flash")

# Words that mark a scene as an ACTION scene (checked in narration.lower())
ACTION_WORDS: frozenset[str] = frozenset({
    "charge", "battle", "attack", "cavalry", "siege", "march", "fire",
    "explosion", "clash", "assault", "overwhelm", "surrounded", "encircle",
})


# ── Result tracking ────────────────────────────────────────────────────────────
@dataclass
class RenderStats:
    """Tracks per-episode render progress for the final summary."""

    total: int = 0
    rendered: int = 0
    skipped: list[int] = field(default_factory=list)

    def skip(self, scene_number: int) -> None:
        """Record a scene as skipped."""
        self.skipped.append(scene_number)


# ── Subprocess helpers ─────────────────────────────────────────────────────────
def run_ffmpeg(args: list[str], label: str) -> bool:
    """Run an ffmpeg command; log the error tail on failure. Returns success."""
    result = subprocess.run([FFMPEG, "-y", *args], capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if result.returncode != 0:
        print(f"{TAG} ❌ ffmpeg failed ({label}):\n{(result.stderr or '')[-500:]}", file=sys.stderr)
        return False
    return True


def probe_duration(media_path: Path) -> float | None:
    """Return media duration in seconds via ffprobe, or None on failure."""
    result = subprocess.run(
        [FFPROBE, "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(media_path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    try:
        return float(result.stdout.strip())
    except (ValueError, AttributeError):
        print(f"{TAG} ❌ ffprobe could not read duration: {media_path}", file=sys.stderr)
        return None


# ── Script loading ─────────────────────────────────────────────────────────────
def find_episode_script(channel: str, episode_id: str) -> Path | None:
    """Locate the episode JSON in prompts/<channel_dir>/ by episode id (case-insensitive)."""
    prompt_dir = BASE_DIR / "prompts" / CHANNEL_PROMPT_DIR[channel]
    if not prompt_dir.exists():
        return None
    ep_lower = episode_id.lower()
    candidates: list[Path] = []
    for p in sorted(prompt_dir.glob("*.json")):
        name = p.name.lower()
        if ep_lower in name:
            candidates.append(p)
    if not candidates:
        return None
    # Prefer files whose name STARTS with the episode id (e.g. GG_EP002_cannae.json)
    # over files that merely contain it (e.g. scene_prompts.gg_ep002.final.json),
    # then "final" scripts, then v3, then shortest name (most canonical)
    candidates.sort(key=lambda p: (
        (not p.name.lower().startswith(ep_lower)),
        ("final" not in p.name.lower()),
        ("v3" not in p.name.lower()),
        len(p.name),
    ))
    return candidates[0]


def load_script(script_path: Path) -> dict:
    """Load and return the episode JSON."""
    with open(script_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── TTS ────────────────────────────────────────────────────────────────────────
def tts_narrate(text: str, out_wav: Path, voice: str, speed: float) -> bool:
    """Generate Kokoro TTS narration via voice-music-factory/tts_cli.py."""
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    python = KOKORO_VENV_PYTHON if KOKORO_VENV_PYTHON.exists() else PYTHON_MAIN
    cmd = [str(python), str(TTS_CLI),
           "--text", text, "--voice", voice, "--speed", str(speed), "--out", str(out_wav)]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0 or not out_wav.exists() or out_wav.stat().st_size < 1000:
        print(f"{TAG} ❌ TTS failed: {(result.stderr or '')[-300:]}", file=sys.stderr)
        return False
    return True


# ── Smart image prompts (Gemini: narration chunk → specific visual) ────────────
def _gemini_generate_text(prompt: str) -> str | None:
    """
    One synchronous Gemini text completion (generateContent, x-goog-api-key).
    Tries GEMINI_TEXT_MODELS in order. Returns stripped text or None. Never raises.
    """
    from providers.gemini_image import _load_env  # reuse .env loader
    _load_env()
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return None
    payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    for model in GEMINI_TEXT_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        try:
            req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            for candidate in result.get("candidates", []):
                for part in (candidate.get("content") or {}).get("parts", []):
                    text = (part.get("text") or "").strip()
                    if text:
                        return text
        except Exception as e:
            print(f"{TAG} Gemini text ({model}) failed: {e}", file=sys.stderr)
    return None


def split_narration_to_image_prompts(narration: str, n: int = 4,
                                     fallback: list[str] | None = None) -> list[str]:
    """
    Split narration into n equal word-count chunks and ask Gemini for the
    single most powerful specific historical image for EACH chunk — so every
    on-screen visual matches exactly what the narrator is saying right then.

    Fallbacks (never fails):
      - GEMINI_API_KEY not set → return `fallback` (script image_prompts)
      - One chunk's Gemini call fails → that slot uses fallback[i], else the
        raw chunk text as the search prompt
    """
    clean_fallback: list[str] = [
        p.strip() for p in (fallback or []) if isinstance(p, str) and p.strip()
    ]
    words = narration.split()
    if not words:
        return clean_fallback
    chunk_size = max(1, math.ceil(len(words) / n))
    chunks = [" ".join(words[i:i + chunk_size])
              for i in range(0, len(words), chunk_size)][:n]

    if not os.environ.get("GEMINI_API_KEY"):
        from providers.gemini_image import _load_env
        _load_env()
    if not os.environ.get("GEMINI_API_KEY"):
        if clean_fallback:
            print(f"{TAG} GEMINI_API_KEY not set — using script image_prompts")
            return clean_fallback
        return chunks

    prompts: list[str] = []
    for i, chunk in enumerate(chunks):
        ask = (
            "You are creating visuals for a history documentary. "
            f"The narrator is saying: '{chunk}'. "
            "Describe in one sentence the single most powerful, specific "
            "historical image that would appear on screen right now. "
            "Be specific — name the person, location, and action. "
            "Style: historical oil painting or period engraving."
        )
        text = _gemini_generate_text(ask)
        if text:
            prompts.append(" ".join(text.split())[:300])  # one clean line, capped
        elif i < len(clean_fallback):
            prompts.append(clean_fallback[i])
        else:
            prompts.append(chunk)
    return prompts


# ── Image fetching (GG) ────────────────────────────────────────────────────────
def _looks_like_image(path: Path) -> bool:
    """Check magic bytes: real JPEG or PNG file."""
    try:
        head = path.read_bytes()[:8]
    except OSError:
        return False
    return head.startswith(b"\xff\xd8\xff") or head.startswith(b"\x89PNG\r\n\x1a\n")


def fetch_wikimedia_image(query: str, dest: Path, max_results: int = 5) -> bool:
    """
    Fetch a validated historical image from Wikimedia Commons.
    Tries up to max_results search results; each download must be >50KB
    and a real JPEG/PNG (magic-byte check) to be accepted.
    """
    results = search_wikimedia(query, count=max_results)
    ua = {"User-Agent": "EmpireOS/1.0 (Gods&Glory pipeline; contact@empireos.ai)"}
    for r in results[:max_results]:
        try:
            req = urllib.request.Request(r["url"], headers=ua)
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
            if len(data) <= MIN_IMAGE_BYTES:
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            if _looks_like_image(dest):
                print(f"{TAG} Wikimedia ✅ {r['title']} ({len(data) // 1024}KB)")
                return True
            dest.unlink(missing_ok=True)
        except Exception as e:
            print(f"{TAG} Wikimedia candidate failed: {e}", file=sys.stderr)
    return False


def fetch_pollinations_image(prompt: str, dest: Path) -> bool:
    """
    Fallback: generate an image via Pollinations AI.
    Pollinations rate-limits at ~1 req/s — on HTTP 429 we wait 3s and
    retry once before giving up.
    """
    encoded = urllib.parse.quote(prompt[:200])
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1920&height=1080&nologo=true"
    for attempt in (1, 2):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "EmpireOS/1.0"})
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = resp.read()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            if len(data) > 10_000 and _looks_like_image(dest):
                print(f"{TAG} Pollinations fallback ✅ ({len(data) // 1024}KB)")
                return True
            dest.unlink(missing_ok=True)
            return False
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt == 1:
                print(f"{TAG} Pollinations 429 (rate limited) — waiting 3s and retrying once",
                      file=sys.stderr)
                time.sleep(3)
                continue
            print(f"{TAG} Pollinations failed: HTTP {e.code} {e.reason}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"{TAG} Pollinations failed: {e}", file=sys.stderr)
            return False
    return False


def fetch_one_scene_image(prompt: str, work_dir: Path, tag: str, dest: Path) -> bool:
    """
    Fetch ONE image for a prompt via the image_scout waterfall:
    Wikimedia (real historical) → Gemini image gen → Pollinations.
    Copies the winning image to `dest`. Falls back to the direct
    Wikimedia→Pollinations flow if image_scout itself errors. Never raises.
    """
    try:
        # Lazy import — image_scout imports back from this module (no cycle at import time)
        from orchestrator.agents.image_scout import scout_image_source_first
        result = scout_image_source_first(prompt, work_dir, tag)
        if result is not None:
            if result.path != dest:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(result.path, dest)
            return True
    except Exception as e:
        print(f"{TAG} image_scout failed ({e}) — direct fetch fallback", file=sys.stderr)
    if fetch_wikimedia_image(prompt, dest):
        return True
    print(f"{TAG} Wikimedia exhausted for '{prompt}' — falling back to Pollinations")
    return fetch_pollinations_image(prompt, dest)


def fetch_scene_images(prompts: list[str], work_dir: Path, scene_number: int,
                       episode_title: str) -> list[Path]:
    """
    Fetch ALL images for a scene — one per prompt (4 per scene is the GG
    standard). EACH prompt runs the image_scout waterfall: Wikimedia first,
    then Gemini image generation, then Pollinations. Returns every image
    that succeeded (order preserved); failed prompts are logged and skipped.
    """
    clean: list[str] = [p.strip() for p in (prompts or [])
                        if isinstance(p, str) and p.strip()]
    if not clean:
        clean = [episode_title]

    images: list[Path] = []
    for i, prompt in enumerate(clean, start=1):
        dest = work_dir / f"scene_{scene_number:02d}_img{i}.jpg"
        if dest.exists() and dest.stat().st_size > 10_000:
            images.append(dest)
            continue
        if i > 1:
            time.sleep(1.0)  # pace image fetches — Pollinations rate-limits ~1 req/s
        if fetch_one_scene_image(prompt, work_dir, f"scene_{scene_number:02d}_img{i}", dest):
            images.append(dest)
        else:
            print(f"{TAG} ⚠ Scene {scene_number:02d} image {i}/{len(clean)} "
                  f"failed on all sources — continuing with remaining images", file=sys.stderr)
    return images


# ── Video building blocks ──────────────────────────────────────────────────────
def make_ken_burns_clip(image: Path, out: Path, duration: float, preset_index: int) -> bool:
    """
    Build a silent Ken Burns clip from a still image using one of the 5
    rotating motion presets. Duration is exact (float) so multi-image scenes
    split narration time equally; final trim to narration happens at combine.
    """
    from video_effects import ken_burns_clip  # local module, imported lazily
    return ken_burns_clip(
        str(image), str(out),
        duration=max(1.0, duration),
        motion=str(preset_index % len(KEN_BURNS_ROTATION)),
    )


def make_ken_burns_slideshow(images: list[Path], out: Path, work_dir: Path,
                             scene_number: int, total_duration: float,
                             preset_index: int) -> bool:
    """
    Build one silent scene video from ALL scene images: each image gets an
    equal share of the narration duration with its own Ken Burns motion
    (presets rotate per image), then the segments are concatenated.
    A 48s scene with 4 images → 4 × 12s Ken Burns segments.
    """
    per_image = total_duration / len(images)
    segments: list[Path] = []
    for i, image in enumerate(images):
        seg = work_dir / f"scene_{scene_number:02d}_kb{i + 1}.mp4"
        if not seg.exists():
            if not make_ken_burns_clip(image, seg, per_image, preset_index=preset_index + i):
                return False
        segments.append(seg)
    if len(segments) == 1:
        shutil.copy2(segments[0], out)
        return True
    return concat_scenes(segments, out)


def combine_clip_and_narration(video: Path, audio: Path, out: Path, exact_duration: float) -> bool:
    """
    Merge a silent video with narration audio, trimming output to exactly
    the narration duration. Re-encodes video for frame-accurate cut.
    """
    return run_ffmpeg(
        ["-i", str(video), "-i", str(audio),
         "-map", "0:v", "-map", "1:a",
         "-t", f"{exact_duration:.3f}",
         "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "25",
         "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
         str(out)],
        f"combine {out.name}",
    )


def fit_clip_to_narration(clip: Path, narration_dur: float, clip_dur: float, out: Path) -> bool:
    """
    LO/IL core fix — play the Higgsfield clip ONCE, never loop:
      clip > narration → trim to narration length
      clip < narration → freeze last frame (tpad clone) to fill remaining time
    Also normalizes to 1920x1080 @ 25fps so scenes concat cleanly.
    """
    scale = ("scale=1920:1080:force_original_aspect_ratio=decrease,"
             "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=25")
    if clip_dur >= narration_dur:
        vf = scale
    else:
        hold = narration_dur - clip_dur
        zoom_max = 1.12
        kenburns = (
            f"scale=trunc(iw*{zoom_max}/2)*2:trunc(ih*{zoom_max}/2)*2,"
            f"crop=w=1920:h=1080:"
            f"x='(iw-1920)*t/{narration_dur:.3f}':"
            f"y='(ih-1080)*t/{narration_dur:.3f}'"
        )
        vf = f"{scale},tpad=stop_mode=clone:stop_duration={hold:.3f},{kenburns}"
    return run_ffmpeg(
        ["-i", str(clip),
         "-vf", vf,
         "-t", f"{narration_dur:.3f}",
         "-an",
         "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
         str(out)],
        f"fit {out.name}",
    )


def apply_lower_third(video: Path, out: Path, lower_third: str) -> bool:
    """
    Burn a lower-third onto a scene ('Title | Subtitle' format):
    dark semi-transparent bar, white bold title, gold subtitle,
    shown from 1.5s to 6s.
    """
    from video_effects import add_lower_third  # local module
    parts = lower_third.split("|")
    title = parts[0].strip()
    subtitle = parts[1].strip() if len(parts) > 1 else ""
    return add_lower_third(str(video), str(out), title, subtitle, show_at=1.5, hide_at=6.0)


def concat_scenes(clips: list[Path], out: Path) -> bool:
    """Concatenate scene clips (identical encode params) via the concat demuxer."""
    list_file = out.with_suffix(".concat.txt")
    list_file.write_text(
        "\n".join(f"file '{c.resolve().as_posix()}'" for c in clips), encoding="utf-8"
    )
    ok = run_ffmpeg(
        ["-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(out)],
        f"concat {out.name}",
    )
    list_file.unlink(missing_ok=True)
    return ok


def mix_music(video: Path, music: Path, out: Path, music_vol: float, fade: float = 3.0) -> bool:
    """
    Mix background music under narration:
    loops music to cover the episode, fades in over `fade`s at the start,
    fades out over `fade`s at the end, at `music_vol` relative volume.
    """
    total = probe_duration(video) or 60.0
    fade_out_start = max(0.0, total - fade)
    filter_complex = (
        f"[1:a]aloop=loop=-1:size=2e+09,"
        f"volume={music_vol},"
        f"afade=t=in:st=0:d={fade},"
        f"afade=t=out:st={fade_out_start:.2f}:d={fade}[music];"
        f"[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[aout]"
    )
    return run_ffmpeg(
        ["-i", str(video), "-i", str(music),
         "-filter_complex", filter_complex,
         "-map", "0:v", "-map", "[aout]",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         str(out)],
        f"music mix {out.name}",
    )


# ── Higgsfield clip discovery (LO/IL) ──────────────────────────────────────────
def find_higgsfield_clip(clips_dir: Path, scene_number: int) -> Path | None:
    """Find a scene's Higgsfield clip: scene_{N:02d}.mp4 preferred, scene_{N}.mp4 accepted."""
    for name in (f"scene_{scene_number:02d}.mp4", f"scene_{scene_number}.mp4"):
        candidate = clips_dir / name
        if candidate.exists() and candidate.stat().st_size > 10_000:
            return candidate
    return None


# ── Action video clips (GG battle scenes) ──────────────────────────────────────
def is_action_scene(narration: str) -> bool:
    """True if the narration contains any ACTION_WORDS (battle/charge/siege...)."""
    low = narration.lower()
    return any(word in low for word in ACTION_WORDS)


def generate_action_clip(scene: dict, work_dir: Path, scene_number: int,
                         episode_title: str) -> Path | None:
    """
    Try to generate a ~5s real video clip for an action scene via connected
    video providers (FAL, then Replicate). Returns clip path or None — every
    failure is a silent fallback to the images-only path. Never raises.
    """
    try:
        from providers.fal_video import FalVideoProvider
        from providers.replicate_video import ReplicateVideoProvider
        from providers.waterfall import _run_video_provider
    except Exception as e:
        print(f"{TAG} action clip providers unavailable: {e}", file=sys.stderr)
        return None

    title = (scene.get("title") or episode_title).strip()
    prompt = (f"Cinematic live-action historical battle footage: {title}. "
              f"Epic action, realistic, dramatic lighting, film grain, no text.")
    for name, factory in (("fal_video", FalVideoProvider),
                          ("replicate", ReplicateVideoProvider)):
        try:
            provider = factory()
            if not provider.is_connected():
                continue  # silent skip — key not set
            dest = work_dir / f"scene_{scene_number:02d}_action_{name}.mp4"
            if dest.exists() and dest.stat().st_size > 10_000:
                return dest
            clip = _run_video_provider(provider, name, prompt, 5, "16:9", dest)
            if clip is not None:
                print(f"{TAG} Scene {scene_number:02d} action clip via {name} ✅")
                return clip
        except Exception as e:
            print(f"{TAG} action clip ({name}) failed: {e}", file=sys.stderr)
    return None


def normalize_action_clip(clip: Path, out: Path, max_duration: float) -> bool:
    """Normalize an action clip to 1920x1080 @ 25fps, silent, capped at max_duration."""
    vf = ("scale=1920:1080:force_original_aspect_ratio=decrease,"
          "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=25")
    return run_ffmpeg(
        ["-i", str(clip), "-vf", vf, "-t", f"{max_duration:.3f}", "-an",
         "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
         str(out)],
        f"normalize {out.name}",
    )


def build_action_scene_video(action_clip: Path, images: list[Path], out: Path,
                             work_dir: Path, scene_number: int, narr_dur: float,
                             preset_index: int) -> bool:
    """
    Build the scene's silent video with the action clip FIRST, then Ken Burns
    images covering the remaining narration time. Returns False on any failure
    so the caller silently falls back to the images-only slideshow.
    """
    try:
        norm = work_dir / f"scene_{scene_number:02d}_action_norm.mp4"
        if not norm.exists():
            if not normalize_action_clip(action_clip, norm, narr_dur):
                return False
        clip_dur = probe_duration(norm)
        if not clip_dur:
            return False
        remaining = narr_dur - clip_dur
        if remaining < 1.0:
            return False  # no room for Ken Burns — images-only path is safer
        rest_dir = work_dir / f"scene_{scene_number:02d}_action_rest"
        rest_dir.mkdir(parents=True, exist_ok=True)
        kb_rest = rest_dir / f"scene_{scene_number:02d}_kb_rest.mp4"
        if not kb_rest.exists():
            if not make_ken_burns_slideshow(images, kb_rest, rest_dir, scene_number,
                                            remaining, preset_index=preset_index):
                return False
        return concat_scenes([norm, kb_rest], out)
    except Exception as e:
        print(f"{TAG} action scene build failed: {e}", file=sys.stderr)
        return False


# ── Scene renderers ────────────────────────────────────────────────────────────
def render_scene_gg(scene: dict, index: int, total: int, work_dir: Path,
                    episode_title: str, voice: str, speed: float) -> Path | None:
    """
    Render one GG scene: narration-matched images → (optional action clip) →
    Ken Burns → TTS → combine → lower third.
    Returns the finished scene clip path, or None if the scene failed.
    """
    n = int(scene.get("scene_number", index + 1))
    kb = work_dir / f"scene_{n:02d}_kb.mp4"
    wav = work_dir / f"scene_{n:02d}.wav"
    narrated = work_dir / f"scene_{n:02d}_narrated.mp4"
    final = work_dir / f"scene_{n:02d}_final.mp4"

    narration = (scene.get("narration") or "").strip()
    if not narration:
        print(f"{TAG} Scene {n:02d}/{total} ❌ no narration text — skipping")
        return None

    # 1. TTS first — its duration drives everything else
    if not wav.exists():
        if not tts_narrate(narration, wav, voice, speed):
            return None
    narr_dur = probe_duration(wav)
    if not narr_dur:
        return None

    # 2. Image prompts: Gemini matches each visual to its exact narration chunk
    #    (SMART_IMAGE_PROMPTS); script image_prompts are the fallback
    script_prompts: list[str] = [
        p.strip() for p in (scene.get("image_prompts") or [])
        if isinstance(p, str) and p.strip()
    ]
    if not script_prompts:
        legacy = (scene.get("wikimedia_query") or scene.get("visual_prompt")
                  or scene.get("title") or episode_title)
        script_prompts = [legacy]
    if SMART_IMAGE_PROMPTS:
        smart_prompts = split_narration_to_image_prompts(narration, fallback=script_prompts)
    else:
        smart_prompts = script_prompts

    # Images: EACH prompt runs Wikimedia → Gemini image gen → Pollinations
    images = fetch_scene_images(smart_prompts, work_dir, n, episode_title)
    if not images:
        print(f"{TAG} Scene {n:02d}/{total} ❌ no images fetched", file=sys.stderr)
        return None

    # 3. Silent video track. Action scenes try a real 5s video clip first
    #    (FAL/Replicate), then Ken Burns images fill the remaining narration
    #    time. Any clip failure silently falls back to the images-only path.
    if not kb.exists():
        built = False
        if ACTION_VIDEO_CLIPS and is_action_scene(narration):
            action_clip = generate_action_clip(scene, work_dir, n, episode_title)
            if action_clip is not None:
                built = build_action_scene_video(action_clip, images, kb, work_dir,
                                                 n, narr_dur, preset_index=index)
                if built:
                    print(f"{TAG} Scene {n:02d}/{total} — action clip lead-in ✅")
        if not built:
            if not make_ken_burns_slideshow(images, kb, work_dir, n, narr_dur,
                                            preset_index=index):
                return None

    # 4-5. Combine + trim exactly to narration
    if not narrated.exists():
        if not combine_clip_and_narration(kb, wav, narrated, narr_dur):
            return None

    # 6. Lower third
    lower_third = (scene.get("lower_third") or "").strip()
    if not final.exists():
        if lower_third:
            if not apply_lower_third(narrated, final, lower_third):
                shutil.copy2(narrated, final)  # lower third is cosmetic — don't kill the scene
        else:
            shutil.copy2(narrated, final)

    print(f"{TAG} Scene {n:02d}/{total} ✅ narration:{narr_dur:.1f}s images:{len(images)}")
    return final


def generate_scene_clip_waterfall(scene: dict, n: int, total: int, work_dir: Path,
                                  narr_dur: float, preset_index: int) -> Path | None:
    """
    Auto-generate a scene clip via the free-first provider waterfall
    (providers/waterfall.py). Video providers return a clip directly;
    image providers (Gemini/Pollinations) return a still that gets Ken
    Burns motion applied here. Returns a silent video clip path or None.
    """
    from providers.waterfall import generate_scene_asset  # lazy — keeps GG path light

    prompt = (scene.get("visual_prompt") or scene.get("higgsfield_prompt")
              or scene.get("title") or scene.get("narration") or "").strip()
    if not prompt:
        return None

    duration = max(3, min(10, math.ceil(narr_dur)))
    asset = generate_scene_asset(prompt, duration, "16:9", work_dir, f"scene_{n:02d}")
    if asset is None:
        return None

    print(f"{TAG} Scene {n:02d}/{total} — provider: {asset.provider} ✅ ({asset.kind})")
    if asset.kind == "video":
        return asset.path

    # Image asset → Ken Burns motion clip
    kb = work_dir / f"scene_{n:02d}_kb.mp4"
    if kb.exists() or make_ken_burns_clip(asset.path, kb, narr_dur, preset_index=preset_index):
        return kb
    return None


def render_scene_clip(scene: dict, index: int, total: int, work_dir: Path,
                      clips_dir: Path | None, voice: str, speed: float) -> Path | None:
    """
    Render one LO/IL scene. Clip source:
      - clips_dir set  → pre-generated Higgsfield clip (original flow)
      - clips_dir None → auto-generate via the free-first provider waterfall
    Clip plays ONCE: trimmed if longer than narration, last-frame-frozen if
    shorter. Never looped. Returns finished scene clip path or None.
    """
    n = int(scene.get("scene_number", index + 1))
    wav = work_dir / f"scene_{n:02d}.wav"
    fitted = work_dir / f"scene_{n:02d}_fitted.mp4"
    final = work_dir / f"scene_{n:02d}_final.mp4"

    narration = (scene.get("narration") or "").strip()
    if not narration:
        print(f"{TAG} Scene {n:02d}/{total} ❌ no narration text — skipping")
        return None

    # TTS first — its duration drives clip generation and fitting
    if not wav.exists():
        if not tts_narrate(narration, wav, voice, speed):
            return None
    narr_dur = probe_duration(wav)
    if not narr_dur:
        return None

    # Clip source: pre-made Higgsfield clip, or provider waterfall
    clip: Path | None
    if clips_dir is not None:
        clip = find_higgsfield_clip(clips_dir, n)
        if clip is None:
            print(f"{TAG} Scene {n:02d}/{total} ⚠ Higgsfield clip missing "
                  f"({clips_dir / f'scene_{n:02d}.mp4'}) — trying provider waterfall")
            clip = generate_scene_clip_waterfall(scene, n, total, work_dir, narr_dur, index)
    else:
        clip = generate_scene_clip_waterfall(scene, n, total, work_dir, narr_dur, index)
    if clip is None:
        print(f"{TAG} Scene {n:02d}/{total} ❌ no clip from any source", file=sys.stderr)
        return None

    clip_dur = probe_duration(clip)
    if not clip_dur:
        return None

    action = "trim" if clip_dur >= narr_dur else "pad"
    print(f"{TAG} Scene {n}/{total} | clip: {clip_dur:.1f}s | narration: {narr_dur:.1f}s | action: {action}")

    # Fit clip (play once, trim or freeze-pad) then attach narration
    if not fitted.exists():
        if not fit_clip_to_narration(clip, narr_dur, clip_dur, fitted):
            return None
    if not final.exists():
        if not combine_clip_and_narration(fitted, wav, final, narr_dur):
            return None

    print(f"{TAG} Scene {n:02d}/{total} ✅ clip:{clip_dur:.1f}s narration:{narr_dur:.1f}s action:{action}")
    return final


# ── Episode renderer ───────────────────────────────────────────────────────────
def render_episode(channel: str, episode_id: str, script_path: Path,
                   music_path: Path | None, clips_dir: Path | None,
                   multi_agent: bool = False) -> Path | None:
    """
    Render a full episode for any channel. Returns final MP4 path or None.
    Never crashes mid-render: per-scene failures are logged and skipped.

    multi_agent=True (GG): each scene is built by the orchestrator's
    scene_builder agent — parallel multi-source image scouting, video_agent
    for action scenes, and 3-round council evaluation with per-step retries.
    """
    script = load_script(script_path)
    ep_id = script.get("episode_id", episode_id)
    title = script.get("title", ep_id)
    scenes: list[dict] = script.get("scenes", [])
    scenes.sort(key=lambda s: int(s.get("scene_number", 0)))  # always in scene order

    voice = CHANNEL_VOICE[channel]
    speed = CHANNEL_SPEED[channel]
    stats = RenderStats(total=len(scenes))

    work_dir = BASE_DIR / "output" / "empire_render" / ep_id
    work_dir.mkdir(parents=True, exist_ok=True)
    out_dir = BASE_DIR / "renders" / CHANNEL_OUTPUT_DIR[channel]
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{TAG} === {ep_id}: {title} ===")
    print(f"{TAG} Channel: {channel} | Scenes: {len(scenes)} | Script: {script_path}")
    if channel in ("LO", "IL"):
        if clips_dir is not None:
            print(f"{TAG} Higgsfield clips dir: {clips_dir}")
        else:
            print(f"{TAG} No clips dir — auto-generating clips via provider waterfall "
                  f"(free APIs first, Higgsfield last)")

    def render_one_scene(index: int, scene: dict) -> Path | None:
        """Render a single scene via the right per-channel path. Never raises."""
        if channel == "GG" and multi_agent:
            from orchestrator.agents.scene_builder import build_scene  # lazy
            return build_scene(scene, index, len(scenes), work_dir, title, voice, speed)
        if channel == "GG":
            return render_scene_gg(scene, index, len(scenes), work_dir, title, voice, speed)
        return render_scene_clip(scene, index, len(scenes), work_dir, clips_dir, voice, speed)

    # Render ALL scenes in parallel (4 workers); assembly waits for everything.
    print(f"{TAG} Rendering {len(scenes)} scenes in parallel "
          f"({MAX_PARALLEL_SCENES} workers)...")
    results: dict[int, Path | None] = {}
    progress_lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_SCENES) as pool:
        futures = {pool.submit(render_one_scene, i, s): i for i, s in enumerate(scenes)}
        for future in as_completed(futures):
            i = futures[future]
            n = int(scenes[i].get("scene_number", i + 1))
            try:
                clip = future.result()
            except Exception as e:  # never crash mid-render
                print(f"{TAG} Scene {n:02d} ❌ unexpected error: {e}", file=sys.stderr)
                clip = None
            with progress_lock:
                results[i] = clip
                if clip is not None:
                    print(f"{TAG} Scene {n:02d}/{len(scenes)} complete ✅")
                else:
                    print(f"{TAG} Scene {n:02d}/{len(scenes)} FAILED ❌", file=sys.stderr)

    # Collect in strict scene order — concat must never shuffle scenes
    scene_clips: list[Path] = []
    for i in sorted(results):
        n = int(scenes[i].get("scene_number", i + 1))
        if results[i] is not None:
            scene_clips.append(results[i])  # type: ignore[arg-type]
            stats.rendered += 1
        else:
            stats.skip(n)

    if not scene_clips:
        print(f"{TAG} ❌ No scenes rendered — aborting", file=sys.stderr)
        return None

    # Concat all scenes
    assembled = work_dir / f"{ep_id}_assembled.mp4"
    print(f"\n{TAG} Assembling {len(scene_clips)} scenes...")
    if not concat_scenes(scene_clips, assembled):
        return None

    # Music mix
    final_path = out_dir / f"{ep_id}_final.mp4"
    if music_path and music_path.exists():
        print(f"{TAG} Mixing music: {music_path} at {CHANNEL_MUSIC_VOL[channel]:.0%}")
        if not mix_music(assembled, music_path, final_path, CHANNEL_MUSIC_VOL[channel]):
            print(f"{TAG} ⚠ Music mix failed — shipping without music")
            shutil.copy2(assembled, final_path)
    else:
        if music_path:
            print(f"{TAG} ⚠ Music file not found: {music_path} — rendering without music")
        shutil.copy2(assembled, final_path)

    # Mandatory council QC on the finished episode (3 rounds: duration/audio/frames).
    # Expected duration = sum of all scene clip durations (probe BEFORE cleanup).
    expected_dur = sum(probe_duration(c) or 0.0 for c in scene_clips)
    from orchestrator.agents import council_evaluator  # lazy
    verdict = council_evaluator.evaluate(final_path, expected_dur, tag=ep_id)
    if not verdict.passed:
        print(f"{TAG} ❌ COUNCIL REJECTED — round {verdict.round_failed} failed: "
              f"{verdict.reason}", file=sys.stderr)
        print(f"{TAG} ❌ {final_path} is NOT upload-ready — "
              f"work files kept in {work_dir} for re-run", file=sys.stderr)
        return None
    print(f"{TAG} ✅ COUNCIL APPROVED — ready to upload")

    # Post-render hook: upload mission + UPLOAD bat + website feed + social
    # clip staging. Best-effort — a hook failure never kills a finished render.
    try:
        from social_clips.post_render import on_council_approved  # lazy
        on_council_approved(channel, ep_id, final_path, title)
    except Exception as e:
        print(f"{TAG} ⚠ post-render hook failed (non-fatal): {e}", file=sys.stderr)

    # Clean work files only after a fully successful, council-approved render
    # (keep them if scenes were skipped, so a re-run can resume and fill the gaps)
    if not stats.skipped:
        shutil.rmtree(work_dir, ignore_errors=True)

    size_mb = final_path.stat().st_size / 1024 / 1024
    print(f"\n{TAG} === DONE ===")
    print(f"{TAG} Scenes: {stats.rendered}/{stats.total} rendered, {len(stats.skipped)} skipped"
          + (f" (skipped: {stats.skipped})" if stats.skipped else ""))
    print(f"{TAG} Output: {final_path} ({size_mb:.1f}MB)")
    return final_path


# ── CLI ────────────────────────────────────────────────────────────────────────
def main() -> None:
    """Parse arguments and render the requested episode."""
    parser = argparse.ArgumentParser(description="Empire OS unified renderer (GG/LO/IL)")
    parser.add_argument("--channel", required=True, choices=sorted(CHANNEL_OUTPUT_DIR),
                        help="Channel code: GG, LO, or IL")
    parser.add_argument("--episode", required=True, help="Episode ID, e.g. GG_EP012")
    parser.add_argument("--script", default=None,
                        help="Explicit episode JSON path (auto-located in prompts/ if omitted)")
    parser.add_argument("--music", default=None,
                        help="Background music file (GG defaults to music/gg_battle_theme.mp3)")
    parser.add_argument("--clips-dir", default=None,
                        help="Higgsfield clips directory (LO/IL; default higgsfield_clips/{episode}/)")
    parser.add_argument("--multi-agent", action="store_true",
                        help="GG: build each scene via orchestrator scene_builder "
                             "(parallel image scout + video agent + 3-round council QC)")
    args = parser.parse_args()

    channel: str = args.channel.upper()
    episode_id: str = args.episode.upper()

    # Resolve script
    script_path = Path(args.script) if args.script else find_episode_script(channel, episode_id)
    if not script_path or not script_path.exists():
        print(f"{TAG} ❌ Episode script not found for {episode_id} "
              f"(looked in prompts/{CHANNEL_PROMPT_DIR[channel]}/)", file=sys.stderr)
        sys.exit(1)

    # Resolve music
    music_path: Path | None = Path(args.music) if args.music else None
    if music_path is None and channel == "GG" and DEFAULT_GG_MUSIC.exists():
        music_path = DEFAULT_GG_MUSIC

    # Resolve clips dir for LO/IL.
    # --clips-dir given        → must exist (original Higgsfield flow)
    # not given, default exists → use it
    # not given, no default    → auto-generate via provider waterfall
    clips_dir: Path | None = None
    if channel in ("LO", "IL"):
        if args.clips_dir:
            clips_dir = Path(args.clips_dir)
            if not clips_dir.exists():
                print(f"{TAG} ❌ --clips-dir not found: {clips_dir}", file=sys.stderr)
                sys.exit(1)
        else:
            default_dir = BASE_DIR / "higgsfield_clips" / episode_id
            if default_dir.exists():
                clips_dir = default_dir
            else:
                print(f"{TAG} No pre-made clips at {default_dir} — "
                      f"clips will be auto-generated via the provider waterfall.")

    result = render_episode(channel, episode_id, script_path, music_path, clips_dir,
                            multi_agent=args.multi_agent)
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
