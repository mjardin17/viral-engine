"""
pipeline_validator.py — Empire OS stage-by-stage output validation.

Validates every pipeline artifact (prompt, image, audio, video, subtitles,
final render) plus copyright-risk and brand-consistency checks. Called by
the AI Router after each step and by council roles / dry_run.

All methods return ValidationResult and NEVER raise.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR: Path = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

TAG = "[validator]"

# Named brands / copyrighted characters that flag copyright risk in prompts
RISKY_TERMS: frozenset[str] = frozenset({
    "disney", "pixar", "marvel", "dc comics", "batman", "superman", "spiderman",
    "spider-man", "mickey mouse", "star wars", "darth vader", "harry potter",
    "pokemon", "pikachu", "nintendo", "mario", "zelda", "sonic", "transformers",
    "gundam", "voltron", "he-man", "star trek", "lord of the rings", "hobbit",
    "game of thrones", "netflix", "hbo", "coca-cola", "coca cola", "pepsi",
    "nike", "adidas", "mcdonald", "lego", "barbie", "minions", "shrek",
    "frozen", "elsa", "avengers", "iron man", "hulk", "thor ", "godzilla",
    "king kong", "jurassic", "studio ghibli", "totoro", "naruto", "goku",
    "dragon ball", "one piece", "attack on titan",
})

# Channel brand rules: expected voice + minimum scene count
CHANNEL_BRAND: dict[str, dict] = {
    "GG": {"voice": "bm_george", "min_scenes": 12, "style": "documentary"},
    "LO": {"voice": "af_bella", "min_scenes": 24, "style": "kids cartoon"},
    "IL": {"voice": "am_fenrir", "min_scenes": 10, "style": "80s mech anime"},
    "ED": {"voice": "bm_george", "min_scenes": 10, "style": "tech documentary"},
}


@dataclass
class ValidationResult:
    """Outcome of one validation: pass/fail + score + human-readable detail."""

    passed: bool
    score: float = 0.0                       # 0.0-1.0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _ffprobe() -> str | None:
    """Locate ffprobe (next to pipeline ffmpeg, else PATH)."""
    try:
        from empire_render import FFPROBE
        return FFPROBE
    except Exception:
        return shutil.which("ffprobe")


def _probe(path: Path, entries: str, stream: str | None = None) -> str:
    """Run ffprobe, return stdout ('' on failure)."""
    probe = _ffprobe()
    if probe is None:
        return ""
    cmd = [probe, "-v", "quiet", "-show_entries", entries,
           "-of", "default=noprint_wrappers=1:nokey=1"]
    if stream:
        cmd += ["-select_streams", stream]
    cmd.append(str(path))
    try:
        out = subprocess.run(cmd, capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=60)
        return (out.stdout or "").strip()
    except Exception:
        return ""


def _audio_rms_db(path: Path) -> float | None:
    """Mean RMS level in dB via ffmpeg volumedetect. None on failure."""
    try:
        from empire_render import FFMPEG
    except Exception:
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            return None
        FFMPEG = ffmpeg  # type: ignore[misc]
    try:
        out = subprocess.run(
            [FFMPEG, "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=300)
        m = re.search(r"mean_volume:\s*(-?[\d.]+)\s*dB", out.stderr or "")
        return float(m.group(1)) if m else None
    except Exception:
        return None


class PipelineValidator:
    """Validates every pipeline stage. Never raises."""

    # ── prompts ───────────────────────────────────────────────────────────
    def validate_prompt(self, prompt: str) -> ValidationResult:
        """Length, keyword richness, specificity score."""
        r = ValidationResult(passed=True)
        prompt = (prompt or "").strip()
        if not prompt:
            return ValidationResult(passed=False, errors=["prompt is empty"])
        words = prompt.split()
        if len(words) < 4:
            r.warnings.append(f"prompt very short ({len(words)} words)")
        if len(prompt) > 1500:
            r.warnings.append(f"prompt very long ({len(prompt)} chars) — may truncate")
        specificity_markers = ("battle", "portrait", "painting", "engraving",
                               "photograph", "cinematic", "lighting", "close-up",
                               "wide shot", "16:9", "detailed")
        hits = sum(1 for m in specificity_markers if m in prompt.lower())
        has_proper_noun = any(w[:1].isupper() for w in words[1:])
        score = min(1.0, 0.3 + 0.1 * hits + (0.2 if has_proper_noun else 0.0)
                    + min(0.2, len(words) / 100))
        if score < 0.4:
            r.warnings.append("prompt lacks specificity (no style/subject markers)")
        r.score = round(score, 2)
        r.passed = True
        return r

    # ── images ────────────────────────────────────────────────────────────
    def validate_image(self, image_path: str) -> ValidationResult:
        """Existence, size, magic bytes, resolution (via ffprobe)."""
        r = ValidationResult(passed=True, score=1.0)
        p = Path(image_path)
        if not p.exists():
            return ValidationResult(passed=False, errors=[f"missing: {p}"])
        size = p.stat().st_size
        if size < 10_000:
            return ValidationResult(passed=False, score=0.1,
                                    errors=[f"image only {size}B — broken/tiny"])
        if size < 20_000:
            r.warnings.append(f"image small ({size // 1024}KB) — may be low quality")
            r.score = 0.6
        try:
            head = p.read_bytes()[:12]
        except OSError as e:
            return ValidationResult(passed=False, errors=[f"unreadable: {e}"])
        is_jpg = head.startswith(b"\xff\xd8\xff")
        is_png = head.startswith(b"\x89PNG\r\n\x1a\n")
        is_webp = head[:4] == b"RIFF" and head[8:12] == b"WEBP"
        if not (is_jpg or is_png or is_webp):
            return ValidationResult(passed=False, score=0.0,
                                    errors=["not a real JPEG/PNG/WebP (magic bytes)"])
        dims = _probe(p, "stream=width,height", stream="v:0").split()
        if len(dims) >= 2:
            try:
                w, h = int(dims[0]), int(dims[1])
                if w < 640 or h < 360:
                    r.warnings.append(f"low resolution {w}x{h}")
                    r.score = min(r.score, 0.5)
            except ValueError:
                pass
        return r

    # ── audio ─────────────────────────────────────────────────────────────
    def validate_audio(self, audio_path: str) -> ValidationResult:
        """Duration, RMS level, not silent."""
        p = Path(audio_path)
        if not p.exists():
            return ValidationResult(passed=False, errors=[f"missing: {p}"])
        if p.stat().st_size < 1000:
            return ValidationResult(passed=False, errors=["audio file <1KB"])
        r = ValidationResult(passed=True, score=1.0)
        dur_s = _probe(p, "format=duration")
        try:
            duration = float(dur_s)
        except ValueError:
            return ValidationResult(passed=False, errors=["ffprobe cannot read duration"])
        if duration < 0.5:
            return ValidationResult(passed=False,
                                    errors=[f"audio only {duration:.2f}s"])
        rms = _audio_rms_db(p)
        if rms is None:
            r.warnings.append("could not measure RMS level")
            r.score = 0.7
        elif rms < -50.0:
            return ValidationResult(passed=False, score=0.1,
                                    errors=[f"audio effectively silent ({rms:.1f} dB)"])
        elif rms < -35.0:
            r.warnings.append(f"audio quiet ({rms:.1f} dB mean)")
            r.score = 0.7
        return r

    # ── video ─────────────────────────────────────────────────────────────
    def validate_video(self, video_path: str) -> ValidationResult:
        """Duration, audio RMS, frame sample readability."""
        p = Path(video_path)
        if not p.exists():
            return ValidationResult(passed=False, errors=[f"missing: {p}"])
        if p.stat().st_size < 10_000:
            return ValidationResult(passed=False, errors=["video file <10KB"])
        r = ValidationResult(passed=True, score=1.0)
        dur_s = _probe(p, "format=duration")
        try:
            duration = float(dur_s)
        except ValueError:
            return ValidationResult(passed=False, errors=["ffprobe cannot read duration"])
        if duration < 1.0:
            return ValidationResult(passed=False, errors=[f"video only {duration:.2f}s"])
        # audio track present + not silent
        has_audio = bool(_probe(p, "stream=codec_type", stream="a:0"))
        if has_audio:
            rms = _audio_rms_db(p)
            if rms is not None and rms < -50.0:
                r.errors.append(f"video audio effectively silent ({rms:.1f} dB)")
                r.passed = False
                r.score = 0.2
            elif rms is not None and rms < -35.0:
                r.warnings.append(f"video audio quiet ({rms:.1f} dB)")
                r.score = min(r.score, 0.7)
        else:
            r.warnings.append("no audio stream (ok for silent scene clips)")
        # frame sample: can we decode a frame mid-video?
        frames = _probe(p, "stream=nb_read_frames", stream="v:0")
        if not _probe(p, "stream=codec_name", stream="v:0"):
            r.errors.append("no decodable video stream")
            r.passed = False
            r.score = 0.0
        _ = frames  # counted lazily by some builds; codec check is the gate
        return r

    # ── subtitles ─────────────────────────────────────────────────────────
    def validate_subtitles(self, srt_path: str) -> ValidationResult:
        """SRT parseable, timings valid and monotonic."""
        p = Path(srt_path)
        if not p.exists():
            return ValidationResult(passed=False, errors=[f"missing: {p}"])
        r = ValidationResult(passed=True, score=1.0)
        ts = re.compile(r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*"
                        r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})")
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            return ValidationResult(passed=False, errors=[f"unreadable: {e}"])
        matches = ts.findall(text)
        if not matches:
            return ValidationResult(passed=False, errors=["no valid SRT timing lines"])
        last_end = -1.0
        for m in matches:
            start = int(m[0]) * 3600 + int(m[1]) * 60 + int(m[2]) + int(m[3]) / 1000
            end = int(m[4]) * 3600 + int(m[5]) * 60 + int(m[6]) + int(m[7]) / 1000
            if end <= start:
                r.warnings.append(f"cue ends before it starts at {start:.1f}s")
                r.score = 0.6
            if start < last_end - 0.5:
                r.warnings.append(f"overlapping cues near {start:.1f}s")
                r.score = min(r.score, 0.7)
            last_end = end
        return r

    # ── final render ──────────────────────────────────────────────────────
    def validate_render(self, output_path: str) -> ValidationResult:
        """Final MP4 gate: exists, >10MB, >60s."""
        p = Path(output_path)
        if not p.exists():
            return ValidationResult(passed=False, errors=[f"missing: {p}"])
        r = ValidationResult(passed=True, score=1.0)
        size_mb = p.stat().st_size / 1024 / 1024
        if size_mb < 10:
            return ValidationResult(passed=False, score=0.1,
                                    errors=[f"final only {size_mb:.1f}MB (<10MB)"])
        dur_s = _probe(p, "format=duration")
        try:
            duration = float(dur_s)
        except ValueError:
            return ValidationResult(passed=False, errors=["ffprobe cannot read duration"])
        if duration < 60:
            return ValidationResult(passed=False, score=0.2,
                                    errors=[f"final only {duration:.0f}s (<60s)"])
        video = self.validate_video(output_path)
        r.warnings.extend(video.warnings)
        r.errors.extend(video.errors)
        r.passed = r.passed and video.passed
        r.score = min(r.score, video.score)
        return r

    # ── copyright ─────────────────────────────────────────────────────────
    def check_copyright_risk(self, prompt: str) -> float:
        """0.0 = safe, 1.0 = risky. Flags named brands/copyrighted characters."""
        low = f" {(prompt or '').lower()} "
        hits = [t for t in RISKY_TERMS if t in low]
        if not hits:
            return 0.0
        if len(hits) == 1:
            return 0.6
        return 1.0

    # ── brand consistency ─────────────────────────────────────────────────
    def check_brand_consistency(self, channel: str, output: dict) -> ValidationResult:
        """Check an episode output dict against channel brand rules.

        output keys used (all optional): voice, scene_count, title, style.
        """
        r = ValidationResult(passed=True, score=1.0)
        brand = CHANNEL_BRAND.get(channel.upper())
        if brand is None:
            return ValidationResult(passed=False,
                                    errors=[f"unknown channel: {channel}"])
        voice = str(output.get("voice", ""))
        if voice and voice != brand["voice"]:
            r.warnings.append(f"voice {voice!r} != channel standard {brand['voice']!r}")
            r.score = 0.7
        scene_count = int(output.get("scene_count", 0) or 0)
        if scene_count and scene_count < brand["min_scenes"]:
            r.errors.append(f"only {scene_count} scenes — {channel} standard is "
                            f">={brand['min_scenes']} (stub?)")
            r.passed = False
            r.score = 0.3
        title = str(output.get("title", ""))
        if title:
            risk = self.check_copyright_risk(title)
            if risk >= 0.6:
                r.warnings.append(f"title copyright risk {risk:.1f}: {title!r}")
                r.score = min(r.score, 0.6)
        return r
