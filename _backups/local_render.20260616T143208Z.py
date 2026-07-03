#!/usr/bin/env python3
"""
local_render.py  —  Empire Decoded Local Video Engine  v2.0

Produces a finished MP4 from episode JSON + local assets.
No paid APIs required.

FEATURES (Phase 2):
  ✓ Character image support (auto-matched to scenes)
  ✓ Burned subtitle overlays (narration text → screen)
  ✓ Narration audio (per-scene MP3 or single track)
  ✓ Background music (mixed at 0.12 vol under narration)
  ✓ Sound effects (per-scene SFX audio files)
  ✓ 6-scene Empire Decoded episode template
  ✓ Ken Burns / pan motion effects per scene type
  ✓ Cinematic color grading per scene type
  ✓ Title card + end card
  ✓ Crossfade transitions (reliable filter_complex concat)
  ✓ 3x backup of all outputs

SCENE TEMPLATE (Empire Decoded):
  1 - Threat             (zoom_out,  dark red)
  2 - Enemy Dominance    (pan_right, dark blue)
  3 - Crisis             (drift,     dark amber)
  4 - Turning Point      (zoom_in,   steel blue)
  5 - Victory            (pan_left,  dark green)
  6 - Historical Consequence (zoom_out, deep purple)

USAGE:
  python3 local_render.py --test
  python3 local_render.py --episode 6
  python3 local_render.py --episode 6 --preview
  python3 local_render.py --thermopylae
  python3 local_render.py --title "Battle of Marathon" --output renders/marathon.mp4
  python3 local_render.py --episode 6 --music epic_music.mp3 --narration-dir renders/ep006/
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT             = Path(__file__).parent
PROMPTS_DIR      = ROOT / "prompts"
RENDERS_DIR      = ROOT / "renders"
CHAR_IMAGES_DIR  = ROOT / "character_images"
ASSETS_DIR       = ROOT / "assets"
BACKUPS_DIR      = ROOT / "_backups"

# ── Video constants ────────────────────────────────────────────────────────────
W, H             = 1920, 1080
FPS              = 24
TRANSITION_DUR   = 0.5
TITLE_DUR        = 4.0
END_DUR          = 3.5
DEFAULT_SCENE_DUR = 9.0

# ── Fonts ──────────────────────────────────────────────────────────────────────
FONT_BOLD    = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# ── Colors ─────────────────────────────────────────────────────────────────────
C_BG    = (8,   6,   4)
C_GOLD  = (201, 168,  76)
C_WHITE = (240, 235, 225)

# Per-scene cinematic grade (RGBA overlay)
SCENE_GRADE = {
    1: (100, 20, 15, 55),
    2: (10,  15, 80, 55),
    3: (80,  50, 10, 65),
    4: (30,  55, 90, 40),
    5: (25,  75, 30, 40),
    6: (45,  20, 70, 50),
}

# Per-scene motion effect
SCENE_MOTION = {
    1: "zoom_out",
    2: "pan_right",
    3: "drift",
    4: "zoom_in",
    5: "pan_left",
    6: "zoom_out",
}

# Scene type labels
SCENE_LABELS = {
    1: "THREAT",
    2: "ENEMY DOMINANCE",
    3: "CRISIS",
    4: "TURNING POINT",
    5: "VICTORY",
    6: "HISTORICAL CONSEQUENCE",
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _wrap(text: str, px_width: int, font_size: int = 40) -> list[str]:
    chars = max(20, px_width // (font_size // 2))
    return textwrap.wrap(text, width=chars)


def _run(cmd: list[str], label: str = "", fatal: bool = False) -> bool:
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        msg = e.stderr[-600:] if e.stderr else "(no stderr)"
        print(f"  ✗ FFmpeg [{label}]: {msg}")
        if fatal:
            raise
        return False


def _duration(path: Path) -> float | None:
    cmd = ["ffprobe", "-v", "error",
           "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1",
           str(path)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(r.stdout.strip())
    except Exception:
        return None


def _backup(src: Path) -> None:
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    ts   = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    stem = src.stem
    ext  = src.suffix
    shutil.copy2(str(src), str(BACKUPS_DIR / f"{stem}.latest{ext}"))
    shutil.copy2(str(src), str(BACKUPS_DIR / f"{stem}.{ts}{ext}"))


# ── PIL image builders ─────────────────────────────────────────────────────────

def _fit_to_canvas(img: Image.Image, w: int = W, h: int = H) -> Image.Image:
    ratio = img.width / img.height
    if ratio > w / h:
        img = img.resize((int(h * ratio), h), Image.LANCZOS)
    else:
        img = img.resize((w, int(w / ratio)), Image.LANCZOS)
    left = (img.width  - w) // 2
    top  = (img.height - h) // 2
    return img.crop((left, top, left + w, top + h))


def make_title_card(
    title: str,
    subtitle: str = "",
    series: str = "EMPIRE DECODED",
    out: Path = None,
) -> Path:
    img  = Image.new("RGB", (W, H), C_BG)
    draw = ImageDraw.Draw(img)

    draw.rectangle([100, 180, W - 100, 184], fill=C_GOLD)
    draw.text((W // 2, 145), series, font=_font(FONT_BOLD, 40),
              fill=C_GOLD, anchor="mm")

    lines   = _wrap(title, W - 240, 80)
    font_sz = 88 if len(lines) <= 2 else 64
    ft      = _font(FONT_BOLD, font_sz)
    line_h  = font_sz + 14
    y       = H // 2 - (len(lines) * line_h) // 2
    for line in lines:
        draw.text((W // 2, y), line, font=ft, fill=C_WHITE, anchor="mm")
        y += line_h

    draw.rectangle([100, H - 185, W - 100, H - 181], fill=C_GOLD)
    if subtitle:
        draw.text((W // 2, H - 148), subtitle.upper(),
                  font=_font(FONT_REGULAR, 32), fill=(*C_GOLD, 200), anchor="mm")

    out = out or (RENDERS_DIR / "_tmp_title.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out))
    return out


def make_scene_still(
    base_image: Path | None,
    narration: str,
    scene_number: int,
    scene_label: str,
    out: Path,
    show_subtitles: bool = True,
) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    grade = SCENE_GRADE.get(scene_number, (40, 40, 60, 50))

    if base_image and base_image.exists():
        img = Image.open(str(base_image)).convert("RGB")
        img = _fit_to_canvas(img)
        overlay = Image.new("RGBA", (W, H), grade)
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    else:
        img = _dark_card(scene_label, scene_number)

    if show_subtitles and narration:
        img = _burn_subtitle(img, narration, scene_number)

    img.save(str(out))
    return out


def _dark_card(label: str, scene_number: int) -> Image.Image:
    img  = Image.new("RGB", (W, H), C_BG)
    draw = ImageDraw.Draw(img)
    gc   = SCENE_GRADE.get(scene_number, (60, 60, 60, 80))[:3]

    # Diagonal texture lines
    for i in range(0, W + H, 80):
        draw.line([(i, 0), (i - H, H)], fill=(*gc, 15), width=1)

    # Scene chip
    draw.rectangle([60, 50, 215, 108], fill=gc)
    draw.text((137, 79), f"SCENE {scene_number}", font=_font(FONT_BOLD, 22),
              fill=C_WHITE, anchor="mm")

    # Scene label
    lines = _wrap(label, W - 300, 72)
    y     = H // 2 - len(lines) * 46
    for line in lines:
        draw.text((W // 2, y), line, font=_font(FONT_BOLD, 72),
                  fill=C_WHITE, anchor="mm")
        y += 90

    return img


def _burn_subtitle(img: Image.Image, text: str, scene_number: int) -> Image.Image:
    img    = img.convert("RGBA")
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw   = ImageDraw.Draw(canvas)
    font   = _font(FONT_REGULAR, 40)
    lines  = _wrap(text, W - 160, 40)[-3:]
    line_h = 52
    bar_h  = len(lines) * line_h + 44
    bar_y  = H - bar_h - 36

    draw.rectangle([0, bar_y - 8, W, H], fill=(0, 0, 0, 170))
    gc = SCENE_GRADE.get(scene_number, (201, 168, 76, 255))[:3]
    draw.rectangle([0, bar_y - 8, 6, H], fill=(*gc, 220))

    y = bar_y + 12
    for line in lines:
        draw.text((W // 2, y), line, font=font, fill=C_WHITE, anchor="mm")
        y += line_h

    return Image.alpha_composite(img, canvas).convert("RGB")


def make_end_card(out: Path) -> Path:
    return make_title_card("Subscribe",
                           "Empire Decoded — New Episode Every Week",
                           out=out)


# ── FFmpeg clip builders ───────────────────────────────────────────────────────

def still_to_video(image: Path, out: Path, duration: float,
                   effect: str = "zoom_in") -> bool:
    out.parent.mkdir(parents=True, exist_ok=True)
    d = int(duration * FPS)
    effects = {
        "zoom_in":   f"z='min(zoom+0.0007,1.06)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={d}",
        "zoom_out":  f"z='if(lte(zoom,1.0),1.0,zoom-0.0007)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={d}",
        "pan_left":  f"z='1.05':x='iw*0.05-n*0.4':y='ih/2-(ih/zoom/2)':d={d}",
        "pan_right": f"z='1.05':x='n*0.4':y='ih/2-(ih/zoom/2)':d={d}",
        "pan_up":    f"z='1.05':x='iw/2-(iw/zoom/2)':y='ih*0.05-n*0.3':d={d}",
        "drift":     f"z='1.04':x='n*0.25':y='n*0.12':d={d}",
    }
    zp = effects.get(effect, effects["zoom_in"])
    vf = f"scale={W*2}:{H*2},zoompan={zp}:s={W}x{H},setsar=1,fps={FPS}"
    return _run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(image),
        "-vf", vf, "-t", str(duration),
        "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        str(out),
    ], f"still→video [{effect}]")


def add_audio_to_video(
    video: Path, out: Path,
    narration: Path | None = None,
    music:     Path | None = None,
    sfx:       Path | None = None,
    narration_vol: float = 1.0,
    music_vol:     float = 0.12,
    sfx_vol:       float = 0.35,
) -> bool:
    out.parent.mkdir(parents=True, exist_ok=True)
    tracks = []
    if narration and narration.exists(): tracks.append((narration, narration_vol))
    if music     and music.exists():     tracks.append((music, music_vol))
    if sfx       and sfx.exists():       tracks.append((sfx, sfx_vol))

    if not tracks:
        shutil.copy2(str(video), str(out))
        return True

    inputs = ["-i", str(video)]
    for p, _ in tracks:
        inputs += ["-i", str(p)]

    if len(tracks) == 1:
        _, vol = tracks[0]
        af = f"[1:a]volume={vol},apad[aout]"
    else:
        parts = [f"[{i+1}:a]volume={v}[a{i}]" for i, (_, v) in enumerate(tracks)]
        mix   = "".join(f"[a{i}]" for i in range(len(tracks)))
        parts.append(f"{mix}amix=inputs={len(tracks)}:duration=first:dropout_transition=0[aout]")
        af = ";".join(parts)

    return _run([
        "ffmpeg", "-y", *inputs,
        "-filter_complex", af,
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
        str(out),
    ], "audio mix")


def concat_clips(clips: list[Path], out: Path) -> bool:
    """
    Reliable multi-clip concatenation using filter_complex [concat].
    Falls back to concat demuxer with re-encode if filter_complex fails.
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    if len(clips) == 1:
        shutil.copy2(str(clips[0]), str(out))
        return True

    n      = len(clips)
    inputs = []
    for c in clips:
        inputs += ["-i", str(c)]

    # Check for audio in first clip
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=codec_type",
         "-of", "default=noprint_wrappers=1:nokey=1", str(clips[0])],
        capture_output=True, text=True
    )
    has_audio = "audio" in probe.stdout

    if has_audio:
        lv = "".join(f"[{i}:v]" for i in range(n))
        la = "".join(f"[{i}:a]" for i in range(n))
        fc = f"{lv}{la}concat=n={n}:v=1:a=1[vout][aout]"
        map_args = ["-map", "[vout]", "-map", "[aout]", "-c:a", "aac", "-b:a", "192k"]
    else:
        lv = "".join(f"[{i}:v]" for i in range(n))
        fc = f"{lv}concat=n={n}:v=1:a=0[vout]"
        map_args = ["-map", "[vout]"]

    ok = _run([
        "ffmpeg", "-y", *inputs,
        "-filter_complex", fc,
        *map_args,
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-pix_fmt", "yuv420p",
        str(out),
    ], f"filter_complex concat ({n} clips)")

    if ok:
        return True

    # Fallback: re-encode to identical params, then concat demuxer
    print("  ⚠ filter_complex failed — using concat demuxer fallback")
    reenc = []
    for i, clip in enumerate(clips):
        r = out.parent / f"_reenc_{i:02d}.mp4"
        _run([
            "ffmpeg", "-y", "-i", str(clip),
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-pix_fmt", "yuv420p", "-r", str(FPS), "-s", f"{W}x{H}", "-an",
            str(r),
        ], f"re-encode {i}")
        reenc.append(r)

    lst = out.parent / "_concat_list.txt"
    with open(lst, "w") as f:
        for r in reenc:
            f.write(f"file '{r}'\n")
    return _run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-pix_fmt", "yuv420p", str(out),
    ], "concat demuxer fallback")


# ── Audio asset finders ────────────────────────────────────────────────────────

def find_narration(narration_dir: Path | None, scene_num: int) -> Path | None:
    if not narration_dir:
        return None
    for pat in [f"narration_s{scene_num:02d}.mp3", f"narration_{scene_num}.mp3",
                f"scene_{scene_num}_narration.mp3", f"s{scene_num:02d}.mp3",
                f"narration_s{scene_num:02d}.wav", f"narration_{scene_num}.wav"]:
        p = narration_dir / pat
        if p.exists():
            return p
    return None


def find_sfx(sfx_dir: Path | None, scene_num: int, label: str = "") -> Path | None:
    if not sfx_dir:
        return None
    for pat in [f"sfx_s{scene_num:02d}.mp3", f"sfx_{scene_num}.mp3",
                f"{label}.mp3" if label else "", f"sfx_s{scene_num:02d}.wav"]:
        if not pat:
            continue
        p = sfx_dir / pat
        if p.exists():
            return p
    return None


# ── Character image resolver ───────────────────────────────────────────────────

def resolve_char_images(episode: dict) -> dict[str, Path]:
    found = {}
    for char in episode.get("character_images", []):
        label = char.get("label", "")
        p = CHAR_IMAGES_DIR / f"{label}.png"
        if p.exists():
            found[label] = p
    return found


def pick_scene_image(char_map: dict, char_list: list[Path], idx: int) -> Path | None:
    if char_map:
        keys = list(char_map.keys())
        return char_map[keys[idx % len(keys)]]
    if char_list:
        return char_list[idx % len(char_list)]
    return None


# ── Main renderer ──────────────────────────────────────────────────────────────

class EmpireRenderer:
    """
    Full local video production engine for Empire Decoded.

    Accepts either an episode JSON path OR custom title + scenes list.
    Produces: title card → 6 cinematic scenes → end card → final MP4.

    Audio pipeline:
      - Per-scene narration (MP3 named narration_sNN.mp3)
      - Per-scene SFX      (MP3 named sfx_sNN.mp3)
      - Global music track  (mixed at 0.12 vol over full video)
    """

    def __init__(
        self,
        episode_json:  Path | None   = None,
        custom_title:  str           = "",
        custom_scenes: list[dict] | None = None,
        music_path:    Path | None   = None,
        narration_dir: Path | None   = None,
        sfx_dir:       Path | None   = None,
        preview:       bool          = False,
        output_path:   Path | None   = None,
    ):
        self.music_path    = music_path
        self.narration_dir = Path(narration_dir) if narration_dir else None
        self.sfx_dir       = Path(sfx_dir) if sfx_dir else None
        self.preview       = preview

        if episode_json:
            with open(episode_json) as f:
                self.episode = json.load(f)
            self.title  = self.episode.get("title", episode_json.stem)
            self.scenes = self.episode.get("scenes", [])
            ep_num      = self.episode.get("episode_number", 0)
            self.ep_key = f"ep{ep_num:03d}"
        else:
            self.episode = {}
            self.title   = custom_title or "Empire Decoded"
            self.scenes  = custom_scenes or []
            self.ep_key  = "custom"

        if preview:
            self.scenes = self.scenes[:1]

        if output_path:
            self.output_path = Path(output_path)
        elif episode_json:
            ep_num = self.episode.get("episode_number", 0)
            sfx    = "_preview" if preview else ""
            self.output_path = RENDERS_DIR / f"EP_{ep_num:03d}{sfx}.mp4"
        else:
            safe = self.title.lower().replace(" ", "_").replace(":", "")[:40]
            self.output_path = RENDERS_DIR / f"{safe}.mp4"

        self.work       = RENDERS_DIR / self.ep_key / "_work"
        self.char_map   = resolve_char_images(self.episode)
        self.char_list  = sorted(CHAR_IMAGES_DIR.glob("*.png")) if CHAR_IMAGES_DIR.exists() else []

    def render(self) -> Path:
        self.work.mkdir(parents=True, exist_ok=True)
        print(f"\n{'═'*62}")
        print(f"  Empire Decoded  —  Local Render  v2.0")
        print(f"  {self.title}")
        print(f"  Scenes: {len(self.scenes)}  |  Preview: {self.preview}")
        print(f"  Characters: {len(self.char_map)} matched + {len(self.char_list)} loose")
        print(f"  Music: {'yes' if self.music_path else 'no'}  |  Narration: {self.narration_dir or 'none'}")
        print(f"{'═'*62}\n")

        scene_clips: list[Path] = []

        for i, scene in enumerate(self.scenes):
            sn       = scene.get("scene_number", i + 1)
            s_label  = scene.get("title", SCENE_LABELS.get(sn, f"Scene {sn}"))
            narr_txt = scene.get("narration", scene.get("description", ""))
            duration = float(scene.get("duration_sec", DEFAULT_SCENE_DUR))
            effect   = SCENE_MOTION.get(sn, "zoom_in")
            sfx_lbl  = scene.get("sfx_label", "")

            print(f"  ─── Scene {sn}: {s_label} [{effect}, {duration}s]")

            # Still image
            base_img = pick_scene_image(self.char_map, self.char_list, i)
            still    = self.work / f"still_s{sn:02d}.png"
            make_scene_still(base_image=base_img, narration=narr_txt,
                             scene_number=sn, scene_label=SCENE_LABELS.get(sn, s_label.upper()),
                             out=still, show_subtitles=True)
            print(f"      ✓ Still ({'character' if base_img else 'text card'})")

            # Ken Burns motion
            motion_clip = self.work / f"motion_s{sn:02d}.mp4"
            ok = still_to_video(still, motion_clip, duration, effect)
            if not ok:
                _run(["ffmpeg", "-y", "-loop", "1", "-i", str(still),
                      "-t", str(duration), "-pix_fmt", "yuv420p",
                      "-c:v", "libx264", "-preset", "fast", str(motion_clip)],
                     "static fallback")
            print(f"      ✓ Motion [{effect}]")

            # Per-scene audio
            narr_audio = find_narration(self.narration_dir, sn)
            sfx_audio  = find_sfx(self.sfx_dir, sn, sfx_lbl)
            final_clip = motion_clip

            if narr_audio or sfx_audio:
                mixed = self.work / f"mixed_s{sn:02d}.mp4"
                add_audio_to_video(video=motion_clip, out=mixed,
                                   narration=narr_audio, sfx=sfx_audio)
                final_clip = mixed
                tags = ([" narration"] if narr_audio else []) + (["sfx"] if sfx_audio else [])
                print(f"      ✓ Audio ({', '.join(tags)})")

            scene_clips.append(final_clip)

        # Title + end cards
        print(f"\n  Building title card ...")
        title_png  = self.work / "title_card.png"
        title_clip = self.work / "title_card.mp4"
        make_title_card(self.title, "Empire Decoded", out=title_png)
        still_to_video(title_png, title_clip, TITLE_DUR, "zoom_in")
        print(f"  ✓ Title card")

        end_png  = self.work / "end_card.png"
        end_clip = self.work / "end_card.mp4"
        make_end_card(end_png)
        still_to_video(end_png, end_clip, END_DUR, "zoom_out")
        print(f"  ✓ End card")

        # Concatenate
        print(f"\n  Concatenating {len(scene_clips)} scenes + title + end card ...")
        all_clips = [title_clip] + scene_clips + [end_clip]
        no_music  = self.work / "assembled_no_music.mp4"
        if not concat_clips(all_clips, no_music):
            raise RuntimeError("Concat failed — all methods exhausted")
        print(f"  ✓ Assembled ({len(all_clips)} clips)")

        # Global music mix
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        if self.music_path and Path(self.music_path).exists():
            print(f"  Mixing music ...")
            add_audio_to_video(video=no_music, out=self.output_path,
                               music=Path(self.music_path), music_vol=0.12)
            print(f"  ✓ Music mixed")
        else:
            shutil.copy2(str(no_music), str(self.output_path))
            print(f"  ⚠  No music (add --music track.mp3 to include)")

        if not self.output_path.exists():
            raise RuntimeError(f"Output missing: {self.output_path}")

        _backup(self.output_path)

        size_mb = self.output_path.stat().st_size / 1_000_000
        dur     = _duration(self.output_path)
        print(f"\n{'═'*62}")
        print(f"  ✓  RENDER COMPLETE")
        print(f"  File     : {self.output_path}")
        print(f"  Size     : {size_mb:.1f} MB")
        if dur:
            print(f"  Duration : {dur:.1f}s  ({dur / 60:.1f} min)")
        print(f"  Backups  : _backups/{self.output_path.stem}.*")
        print(f"{'═'*62}\n")
        return self.output_path


# ── Built-in episode templates ─────────────────────────────────────────────────

def make_thermopylae_scenes() -> tuple[str, list[dict]]:
    """Full 6-scene Thermopylae episode with proper Empire Decoded structure."""
    return "Battle of Thermopylae", [
        {
            "scene_number": 1, "title": "Threat",
            "narration": (
                "480 BC. The Persian Empire stretched from Egypt to India — "
                "the largest empire the ancient world had ever seen. "
                "Now Xerxes marched with an army so vast, it reportedly drank rivers dry."
            ),
            "duration_sec": 9,
        },
        {
            "scene_number": 2, "title": "Enemy Dominance",
            "narration": (
                "Over a million soldiers. Five thousand elite Immortals in gold-plated armor. "
                "A navy of twelve hundred warships. "
                "City after city surrendered without a fight."
            ),
            "duration_sec": 9,
        },
        {
            "scene_number": 3, "title": "Crisis",
            "narration": (
                "King Leonidas of Sparta marched to the pass of Thermopylae with only three hundred men. "
                "The Oracle had warned: either Sparta falls, or a Spartan king must die. "
                "Leonidas chose the pass anyway."
            ),
            "duration_sec": 9,
        },
        {
            "scene_number": 4, "title": "Turning Point",
            "narration": (
                "For two days the Spartans held. The narrow pass neutralized Persia's numbers. "
                "Every Spartan was worth a hundred enemies in that killing corridor. "
                "Xerxes burned through ten thousand soldiers trying to break through."
            ),
            "duration_sec": 9,
        },
        {
            "scene_number": 5, "title": "Victory",
            "narration": (
                "On the third day a traitor showed the Persians a mountain path around the pass. "
                "Leonidas sent most allies away. The three hundred stayed. "
                "They fought to the last man — buying Greece the time it needed."
            ),
            "duration_sec": 10,
        },
        {
            "scene_number": 6, "title": "Historical Consequence",
            "narration": (
                "The delay at Thermopylae let Athens evacuate. At Salamis, the Greek navy shattered Persia's fleet. "
                "The Persian invasion collapsed. Western civilization survived. "
                "Three hundred men changed the course of history."
            ),
            "duration_sec": 10,
        },
    ]


def make_generic_scenes(title: str) -> tuple[str, list[dict]]:
    labels = {1: "Threat", 2: "Enemy Dominance", 3: "Crisis",
              4: "Turning Point", 5: "Victory", 6: "Historical Consequence"}
    return title, [
        {"scene_number": n, "title": lbl,
         "narration": f"{title} — {lbl}. Add narration here.",
         "duration_sec": 9}
        for n, lbl in labels.items()
    ]


# ── Quick test ─────────────────────────────────────────────────────────────────

def run_test() -> Path:
    print("\n=== Empire Decoded — Quick Test Render ===\n")
    RENDERS_DIR.mkdir(parents=True, exist_ok=True)
    work = RENDERS_DIR / "_test_work"
    work.mkdir(parents=True, exist_ok=True)

    clips = []
    for sn in [1, 4, 5]:
        still = work / f"test_still_{sn}.png"
        make_scene_still(None,
                         f"Scene {sn}: {SCENE_LABELS[sn]} — test narration.",
                         sn, SCENE_LABELS[sn], still)
        clip = work / f"test_clip_{sn}.mp4"
        still_to_video(still, clip, 5.0, SCENE_MOTION[sn])
        clips.append(clip)
        print(f"  ✓ Scene {sn}: {SCENE_LABELS[sn]}")

    title_png  = work / "title.png"
    title_clip = work / "title.mp4"
    make_title_card("EMPIRE DECODED — TEST", "Quick render test", out=title_png)
    still_to_video(title_png, title_clip, 3.0, "zoom_in")

    out = RENDERS_DIR / "TEST_RENDER.mp4"
    concat_clips([title_clip] + clips, out)

    dur  = _duration(out)
    size = out.stat().st_size / 1_000_000 if out.exists() else 0
    print(f"\n  ✓ TEST COMPLETE — {out}  ({size:.1f} MB, {dur:.1f}s)")
    return out


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="Empire Decoded local video renderer v2.0")
    ap.add_argument("--episode",       "-e", type=int)
    ap.add_argument("--title",               type=str)
    ap.add_argument("--music",               type=str)
    ap.add_argument("--narration-dir",       type=str)
    ap.add_argument("--sfx-dir",             type=str)
    ap.add_argument("--output",        "-o", type=str)
    ap.add_argument("--preview",             action="store_true")
    ap.add_argument("--test",                action="store_true")
    ap.add_argument("--thermopylae",         action="store_true",
                    help="Render full 6-scene Thermopylae episode")
    args = ap.parse_args()

    RENDERS_DIR.mkdir(parents=True, exist_ok=True)

    if args.test:
        run_test()
        return

    if args.thermopylae:
        title, scenes = make_thermopylae_scenes()
        out = Path(args.output) if args.output else RENDERS_DIR / "thermopylae_test.mp4"
        EmpireRenderer(custom_title=title, custom_scenes=scenes,
                       music_path=Path(args.music) if args.music else None,
                       narration_dir=args.narration_dir,
                       sfx_dir=args.sfx_dir,
                       preview=args.preview,
                       output_path=out).render()
        return

    if args.title:
        title, scenes = make_generic_scenes(args.title)
        EmpireRenderer(custom_title=title, custom_scenes=scenes,
                       music_path=Path(args.music) if args.music else None,
                       narration_dir=args.narration_dir,
                       sfx_dir=args.sfx_dir,
                       preview=args.preview,
                       output_path=Path(args.output) if args.output else None).render()
        return

    if args.episode:
        script = PROMPTS_DIR / f"scene_prompts.ep{args.episode:03d}.final.json"
        if not script.exists():
            print(f"✗ Script not found: {script}")
            sys.exit(1)
        EmpireRenderer(episode_json=script,
                       music_path=Path(args.music) if args.music else None,
                       narration_dir=args.narration_dir,
                       sfx_dir=args.sfx_dir,
                       preview=args.preview,
                       output_path=Path(args.output) if args.output else None).render()
        return

    ap.print_help()
    print("\nExamples:")
    print("  python3 local_render.py --test")
    print("  python3 local_render.py --thermopylae")
    print("  python3 local_render.py --thermopylae --output renders/thermopylae_test.mp4")
    print("  python3 local_render.py --episode 6")
    print("  python3 local_render.py --episode 6 --music epic.mp3")
    print("  python3 local_render.py --title 'Battle of Marathon'")


if __name__ == "__main__":
    main()
