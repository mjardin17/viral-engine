"""
render_commercial.py — Product commercial renderer (Boss Listers → social)
===========================================================================
Turns a commercial script JSON (produced by lib/commercial_generator.py) into
a real vertical MP4: title card → product showcase → description → price/CTA
→ product loop, narrated with Kokoro, output at 1080x1920 for Reels/TikTok/
Shorts.

WHY THIS FILE EXISTS (2026-08-12): commercial rendering never worked. Four
missions sat in MISSION_BOARD.json for 60-83 hours because
video_pipeline_agent.py called `empire_render.py --script <path>` — but
--channel/--episode are required there, so it died at argparse before any
frame rendered, and the commercial scene types (product_showcase,
price_and_cta, product_loop) don't exist in that file anyway — it renders
documentary episodes, not product ads. Rather than bend empire_render.py's
episode-shaped CLI/dispatch to fit a fundamentally different job, this is a
dedicated, honestly-scoped entrypoint: `--script` in, MP4 out, no channel or
episode concept because a commercial has neither.

Reuses the PROVEN low-level primitives from video_effects.py (ken_burns_clip,
mix_music, add_title_card, add_price_card, add_lower_third) rather than
reimplementing FFmpeg filter graphs — that module already renders real
episodes correctly. Everything below this is orchestration: scene dispatch,
TTS, image resolution, concat.

Usage:
    python render_commercial.py --script .temp_commercial_<id>.json --out output/<id>.mp4
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from video_effects import (  # noqa: E402
    FFMPEG,
    FFPROBE,
    add_price_card,
    add_title_card,
    ken_burns_clip,
    mix_music,
)

TAG = "[render_commercial]"

PYTHON_MAIN = Path(r"C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe")
KOKORO_VENV_PYTHON = BASE_DIR / "voice-music-factory" / "venv" / "Scripts" / "python.exe"
TTS_CLI = BASE_DIR / "voice-music-factory" / "tts_cli.py"

DEFAULT_SIZE = "1080x1920"  # vertical — Reels/TikTok/Shorts

# The commercial JSON's "voice" field is a mood descriptor, not a real Kokoro
# voice ID (confirmed against voice-music-factory/run_factory_v2.py's actual
# list). af_bella is reserved for LO's kids-storyteller tone elsewhere in this
# pipeline, so a commercial gets a distinct voice rather than sounding like a
# children's episode.
VOICE_MAP = {
    "professional_female": "af_sarah",
    "professional_male": "am_michael",
    "warm_female": "af_bella",
    "warm_male": "am_adam",
}
DEFAULT_VOICE = "af_sarah"

MIN_IMAGE_BYTES = 5_000  # guards against empty/broken downloads — see resolve_image()


def run_ffmpeg(args: list[str], label: str) -> bool:
    result = subprocess.run([FFMPEG, "-y", *args], capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if result.returncode != 0:
        print(f"{TAG} ❌ ffmpeg failed ({label}):\n{(result.stderr or '')[-500:]}", file=sys.stderr)
        return False
    return True


def probe_duration(media_path: Path) -> float | None:
    result = subprocess.run(
        [FFPROBE, "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(media_path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    try:
        return float(result.stdout.strip())
    except (ValueError, AttributeError):
        return None


def tts_narrate(text: str, out_wav: Path, voice: str, speed: float = 1.0) -> bool:
    """Generate Kokoro TTS narration — same invocation empire_render.py uses."""
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    python = KOKORO_VENV_PYTHON if KOKORO_VENV_PYTHON.exists() else PYTHON_MAIN
    cmd = [str(python), str(TTS_CLI),
           "--text", text, "--voice", voice, "--speed", str(speed), "--out", str(out_wav)]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0 or not out_wav.exists() or out_wav.stat().st_size < 1000:
        print(f"{TAG} ❌ TTS failed: {(result.stderr or '')[-300:]}", file=sys.stderr)
        return False
    return True


# ── Image resolution ──────────────────────────────────────────────────────────
def resolve_image(ref: str, work_dir: Path, tag: str) -> Path | None:
    """
    Resolve a product_images entry to a local file: download if it's a URL,
    use directly if it's already a local path. Validates the result is a real,
    non-trivial image — not a 0-byte or placeholder-sized file. This is the
    exact failure mode that made LO_EP001 pass QA while showing broken visuals
    (CLAUDE.md Lessons); refusing bad images here is cheaper than discovering
    it in a finished render.
    """
    if ref.startswith(("http://", "https://")):
        dest = work_dir / f"{tag}_{Path(ref.split('?')[0]).name or 'img.jpg'}"
        try:
            req = urllib.request.Request(ref, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                dest.write_bytes(resp.read())
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            print(f"{TAG} ❌ could not download {ref}: {e}", file=sys.stderr)
            return None
    else:
        dest = Path(ref)
        if not dest.is_absolute():
            dest = BASE_DIR / ref

    if not dest.exists():
        print(f"{TAG} ❌ image not found: {dest}", file=sys.stderr)
        return None
    if dest.stat().st_size < MIN_IMAGE_BYTES:
        print(f"{TAG} ❌ image too small to be real ({dest.stat().st_size}B): {dest}", file=sys.stderr)
        return None
    # ffprobe confirms it's actually decodable, not just a file that exists.
    probe = subprocess.run(
        [FFPROBE, "-v", "quiet", "-show_entries", "stream=width,height",
         "-of", "csv=p=0", str(dest)],
        capture_output=True, text=True,
    )
    if not probe.stdout.strip():
        print(f"{TAG} ❌ not a decodable image: {dest}", file=sys.stderr)
        return None
    return dest


# ── Building blocks ────────────────────────────────────────────────────────────
def slideshow(images: list[Path], out: Path, work_dir: Path, tag: str,
             duration: float, size: str) -> bool:
    """Equal-share Ken Burns across N images, concatenated — mirrors
    empire_render.py's make_ken_burns_slideshow(), reusing ken_burns_clip()."""
    per_image = duration / len(images)
    segments: list[Path] = []
    for i, img in enumerate(images):
        seg = work_dir / f"{tag}_kb{i + 1}.mp4"
        if not ken_burns_clip(str(img), str(seg), duration=max(1.0, per_image),
                              motion=str(i % 5), size=size):
            return False
        segments.append(seg)
    if len(segments) == 1:
        shutil.copy2(segments[0], out)
        return True
    return concat_clips(segments, out)


def concat_clips(clips: list[Path], out: Path) -> bool:
    list_file = out.with_suffix(".concat.txt")
    list_file.write_text(
        "\n".join(f"file '{c.resolve().as_posix()}'" for c in clips), encoding="utf-8"
    )
    ok = run_ffmpeg(["-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(out)],
                    f"concat {out.name}")
    list_file.unlink(missing_ok=True)
    return ok


def solid_background(out: Path, duration: float, size: str, color: str = "#1a1410") -> bool:
    """
    Plain solid-color background for scenes with no product image (e.g. a
    title card before any photo is shown). "gradient_dark_gold" in the JSON
    is a mood keyword, not an asset this pipeline has — a flat dark-gold-ish
    solid is an honest stand-in, not a fake gradient system pretending to
    exist. Swap for a real gradient asset later if the look needs it.
    """
    w, h = size.split("x")
    return run_ffmpeg(
        ["-f", "lavfi", "-i", f"color=c={color}:s={w}x{h}:d={duration:.3f}:r=25",
         "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p", str(out)],
        f"solid bg {out.name}",
    )


def add_silent_audio(video: Path, out: Path, duration: float) -> bool:
    """
    Attach a silent AAC track to a video-only clip.

    Required so concat_clips()'s concat-demuxer `-c copy` sees a CONSISTENT
    stream layout across every segment. Found by direct verification, not
    assumption: mixing video-only clips (title/showcase/loop — ken_burns_clip
    uses -an) with video+audio clips (narrated description/price_and_cta) in
    the same concat silently dropped ALL audio in the final output — the
    demuxer took its stream template from the first (audio-less) file. The
    render reported success; ffprobe on the actual output showed zero audio
    streams. Every scene now gets an audio track, silent or real, before concat.
    """
    return run_ffmpeg(
        ["-i", str(video), "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
         "-map", "0:v", "-map", "1:a", "-t", f"{duration:.3f}",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(out)],
        f"silent audio {out.name}",
    )


def combine_with_narration(video: Path, audio: Path, out: Path, min_duration: float) -> bool:
    """
    Merge silent video with narration audio. Unlike episode scenes (which
    trim video to EXACTLY the narration length), a commercial scene's video
    is built to `min_duration` already — if narration runs longer, extend the
    last frame instead of cutting speech off mid-word.
    """
    narration_dur = probe_duration(audio) or min_duration
    if narration_dur <= min_duration:
        return run_ffmpeg(
            ["-i", str(video), "-i", str(audio), "-map", "0:v", "-map", "1:a",
             "-t", f"{min_duration:.3f}",
             "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", str(out)],
            f"combine {out.name}",
        )
    # Narration is longer than the visual — hold the last frame to cover it.
    hold = narration_dur - min_duration
    return run_ffmpeg(
        ["-i", str(video), "-i", str(audio),
         "-filter_complex", f"[0:v]tpad=stop_mode=clone:stop_duration={hold:.3f}[v]",
         "-map", "[v]", "-map", "1:a", "-t", f"{narration_dur:.3f}",
         "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", str(out)],
        f"combine+hold {out.name}",
    )


# ── Scene dispatch ─────────────────────────────────────────────────────────────
@dataclass
class RenderContext:
    work_dir: Path
    size: str
    voice: str
    last_product_images: list[Path]  # carried forward so a caption-only scene
                                      # (e.g. price_and_cta) still has a visual


def render_scene(scene: dict, index: int, ctx: RenderContext) -> Path | None:
    stype = scene.get("type", "")
    duration = float(scene.get("duration", 4))
    out = ctx.work_dir / f"scene_{index:02d}_{stype}.mp4"

    images: list[Path] = []
    for ref in scene.get("product_images", []) or []:
        img = resolve_image(ref, ctx.work_dir, f"s{index}")
        if img:
            images.append(img)
    if images:
        ctx.last_product_images = images
    elif ctx.last_product_images:
        images = ctx.last_product_images

    audio_field = (scene.get("audio") or "").strip()
    narration_wav: Path | None = None
    if audio_field.startswith("tts:"):
        narration_wav = ctx.work_dir / f"scene_{index:02d}_narration.wav"
        if not tts_narrate(audio_field[4:].strip(), narration_wav, ctx.voice):
            print(f"{TAG} ⚠ narration failed for scene {index} — continuing without it")
            narration_wav = None

    # Build the silent visual first, then layer narration (if any) on top.
    silent = ctx.work_dir / f"scene_{index:02d}_visual.mp4"

    if stype == "title":
        if images:
            if not ken_burns_clip(str(images[0]), str(silent), duration=duration,
                                  motion="0", size=ctx.size):
                return None
        elif not solid_background(silent, duration, ctx.size):
            return None
        titled = ctx.work_dir / f"scene_{index:02d}_titled.mp4"
        if not add_title_card(str(silent), str(titled), scene.get("text", "")):
            return None
        silent = titled

    elif stype in ("product_showcase", "product_loop"):
        if not images:
            print(f"{TAG} ❌ scene {index} ({stype}): no usable product images", file=sys.stderr)
            return None
        if not slideshow(images, silent, ctx.work_dir, f"s{index}", duration, ctx.size):
            return None
        caption = scene.get("caption") or scene.get("text")
        if caption:
            captioned = ctx.work_dir / f"scene_{index:02d}_captioned.mp4"
            if not add_title_card(str(silent), str(captioned), caption,
                                  show_at=duration - 2.5 if duration > 2.5 else 0.0,
                                  hide_at=duration, bg_color="black@0.35"):
                return None
            silent = captioned

    elif stype == "description":
        if images:
            if not slideshow(images, silent, ctx.work_dir, f"s{index}", duration, ctx.size):
                return None
        elif not solid_background(silent, duration, ctx.size):
            return None

    elif stype == "price_and_cta":
        if images:
            if not ken_burns_clip(str(images[0]), str(silent), duration=duration,
                                  motion="3", size=ctx.size):
                return None
        elif not solid_background(silent, duration, ctx.size, color="#0d0d0d"):
            return None
        carded = ctx.work_dir / f"scene_{index:02d}_priced.mp4"
        if not add_price_card(str(silent), str(carded), scene.get("price", ""),
                              scene.get("cta_button", "")):
            return None
        silent = carded

    else:
        print(f"{TAG} ⚠ unknown scene type '{stype}' at index {index} — skipping", file=sys.stderr)
        return None

    if narration_wav:
        if not combine_with_narration(silent, narration_wav, out, duration):
            return None
        return out

    # No narration: still needs an audio track (silent) so this segment's
    # stream layout matches narrated segments — see add_silent_audio().
    if not add_silent_audio(silent, out, duration):
        return None
    return out


# ── Top-level render ───────────────────────────────────────────────────────────
def render_commercial(script_path: Path, out_path: Path,
                      size: str = DEFAULT_SIZE, music_path: Path | None = None) -> bool:
    if not script_path.exists():
        print(f"{TAG} ❌ script not found: {script_path}", file=sys.stderr)
        return False

    script = json.loads(script_path.read_text(encoding="utf-8"))
    scenes = script.get("scenes", [])
    if not scenes:
        print(f"{TAG} ❌ script has no scenes: {script_path}", file=sys.stderr)
        return False

    voice_key = (script.get("audio") or {}).get("voice", "")
    voice = VOICE_MAP.get(voice_key, DEFAULT_VOICE)

    with tempfile.TemporaryDirectory(prefix="commercial_") as tmp:
        work_dir = Path(tmp)
        ctx = RenderContext(work_dir=work_dir, size=size, voice=voice, last_product_images=[])

        clips: list[Path] = []
        for i, scene in enumerate(scenes, start=1):
            print(f"{TAG} scene {i}/{len(scenes)}: {scene.get('type', '?')}")
            clip = render_scene(scene, i, ctx)
            if clip is None:
                print(f"{TAG} ❌ scene {i} failed — aborting render "
                      f"(no faking a partial commercial)", file=sys.stderr)
                return False
            clips.append(clip)

        assembled = work_dir / "assembled.mp4"
        if not concat_clips(clips, assembled):
            return False

        out_path.parent.mkdir(parents=True, exist_ok=True)

        if music_path and music_path.exists():
            music_vol = (script.get("audio") or {}).get("volume_levels", {}).get("music", 0.5)
            print(f"{TAG} mixing music: {music_path} at {music_vol:.0%}")
            if not mix_music(str(assembled), str(music_path), str(out_path), music_vol=music_vol):
                return False
        else:
            if music_path:
                print(f"{TAG} ⚠ music file not found: {music_path} — rendering without music")
            else:
                print(f"{TAG} no music specified — rendering without it "
                      f"(no matching royalty-free track in this repo yet, see CLAUDE.md)")
            shutil.copy2(assembled, out_path)

    dur = probe_duration(out_path)
    print(f"{TAG} ✅ {out_path} ({dur:.1f}s)" if dur else f"{TAG} ✅ {out_path}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render a product commercial script to MP4. "
                    "No --channel/--episode — a commercial has neither.")
    parser.add_argument("--script", required=True, help="Path to commercial JSON")
    parser.add_argument("--out", required=True, help="Output MP4 path")
    parser.add_argument("--size", default=DEFAULT_SIZE, help="WxH, default 1080x1920 (vertical)")
    parser.add_argument("--music", default=None, help="Optional background music file")
    args = parser.parse_args()

    ok = render_commercial(
        Path(args.script), Path(args.out), size=args.size,
        music_path=Path(args.music) if args.music else None,
    )
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
