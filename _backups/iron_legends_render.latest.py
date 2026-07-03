#!/usr/bin/env python3
"""
iron_legends_render.py  -  Iron Legends Channel Render Engine v1.0

Channel: Iron Legends — "Roll Out. Transform. Remember Everything."
Audience: Millennials 30-45 (nostalgia) + Kids 6-12 (discovery)
Aesthetic: Cinematic Action / Anime — electric blue, steel gray, orange energy

SCENE TYPE SYSTEM (Iron Legends)
    cold_open       — dark space, electric blue glow
    hero_intro      — steel blue, inspiring
    villain_intro   — deep crimson/black, OVERWHELMING scale
    villain_dominance — pure black, red energy, total domination
    mystery         — gold/crystal, ancient energy
    crisis          — orange/amber, chaos and fire
    darkest_moment  — deep purple/black, all hope lost
    turning_point   — gold eruption, world changing
    hero_reveal     — blinding white/gold, god-level awakening
    cliffhanger     — electric blue, war begins

USAGE:
    python3 iron_legends_render.py --episode IL_EP001
    python3 iron_legends_render.py --episode IL_EP001 --output renders/iron_legends_ep001.mp4
    python3 iron_legends_render.py --test
"""

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import textwrap
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT            = Path(__file__).parent
PROMPTS_DIR     = ROOT / "prompts"
RENDERS_DIR     = ROOT / "renders"
CHAR_DIR        = ROOT / "character_images"
BACKUPS_DIR     = ROOT / "_backups"
IL_RENDERS_DIR  = RENDERS_DIR / "iron_legends"

# ── Video constants ────────────────────────────────────────────────────────────
W, H            = 1920, 1080
FPS             = 24
TITLE_DUR       = 5.0
END_DUR         = 5.0
DEFAULT_DUR     = 10.0
WORDS_PER_SEC   = 2.8   # action pacing — slightly faster than documentary

# ── Fonts ──────────────────────────────────────────────────────────────────────
FONT_BOLD    = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_ITALIC  = "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# ── Iron Legends Color Palette ─────────────────────────────────────────────────
C_BG         = (6,  8,  18)          # deep space black-blue
C_ELECTRIC   = (0,  212, 255)        # electric blue (Axiom Guard)
C_CRIMSON    = (200, 20,  20)        # Ravager red
C_GOLD       = (255, 214, 0)         # Alpha Prime gold
C_STEEL      = (120, 140, 160)       # steel gray
C_WHITE      = (240, 245, 255)       # slightly blue-white
C_ORANGE     = (255, 106, 0)         # fire/crisis orange
C_PURPLE     = (100, 30,  180)       # darkest moment purple

FFMPEG = "/usr/bin/ffmpeg"

# ── Scene type definitions ─────────────────────────────────────────────────────
@dataclass
class ILSceneSpec:
    label:          str
    camera_mode:    str
    grade_rgba:     tuple        # (R,G,B,A) cinematic color overlay
    accent_color:   tuple        # (R,G,B) for subtitle bar and text
    char_position:  str          # left | right | center | none
    vignette:       float        # 0.0 – 1.0
    bar_alpha:      int          # letterbox bar darkness 0-255

IL_SCENE_SPECS = {
    "cold_open":        ILSceneSpec("COLD OPEN",       "pull_back",        (0,  20, 60, 70),   C_ELECTRIC, "none",   0.75, 220),
    "hero_intro":       ILSceneSpec("AXIOM GUARD",     "push_in",          (5,  30, 80, 60),   C_ELECTRIC, "right",  0.60, 210),
    "villain_intro":    ILSceneSpec("THE RAVAGERS",    "pull_back",        (80, 5,  5,  75),   C_CRIMSON,  "center", 0.85, 230),
    "villain_dominance":ILSceneSpec("TOTAL DOMINATION","battlefield_drift",(60, 0,  0,  80),   C_CRIMSON,  "right",  0.90, 240),
    "mystery":          ILSceneSpec("ANCIENT LEGEND",  "orbit",            (30, 25, 5,  65),   C_GOLD,     "center", 0.80, 220),
    "crisis":           ILSceneSpec("UNDER SIEGE",     "battlefield_drift",(80, 35, 0,  70),   C_ORANGE,   "left",   0.75, 225),
    "darkest_moment":   ILSceneSpec("ALL HOPE LOST",   "push_in",          (40, 0,  70, 75),   C_PURPLE,   "center", 0.92, 240),
    "turning_point":    ILSceneSpec("THE GROUND SHAKES","push_in",         (50, 40, 0,  60),   C_GOLD,     "none",   0.65, 210),
    "hero_reveal":      ILSceneSpec("ALPHA PRIME",     "pull_back",        (40, 35, 0,  50),   C_GOLD,     "center", 0.55, 200),
    "cliffhanger":      ILSceneSpec("WAR BEGINS",      "pull_back",        (0,  25, 65, 65),   C_ELECTRIC, "none",   0.70, 215),
    # fallback
    "default":          ILSceneSpec("IRON LEGENDS",    "push_in",          (10, 15, 50, 60),   C_ELECTRIC, "none",   0.70, 215),
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _wrap(text: str, max_chars: int) -> list[str]:
    return textwrap.wrap(text, width=max_chars)


def _run(cmd: list[str], label: str = "", fatal: bool = False) -> bool:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        msg = (e.stderr or "")[-600:]
        print(f"  [ERR] FFmpeg [{label}]: {msg}")
        if fatal:
            raise
        return False


def _probe(path: Path, entry: str = "duration") -> Optional[float]:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", f"format={entry}",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, check=True
        )
        return float(r.stdout.strip())
    except Exception:
        return None


def _backup(src: Path) -> None:
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    ts   = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    stem, ext = src.stem, src.suffix
    shutil.copy2(str(src), str(BACKUPS_DIR / f"{stem}.latest{ext}"))
    shutil.copy2(str(src), str(BACKUPS_DIR / f"{stem}.{ts}{ext}"))


def _fit_canvas(img: Image.Image, w: int = W, h: int = H) -> Image.Image:
    r = img.width / img.height
    if r > w / h:
        img = img.resize((int(h * r), h), Image.LANCZOS)
    else:
        img = img.resize((w, int(w / r)), Image.LANCZOS)
    lx = (img.width  - w) // 2
    ty = (img.height - h) // 2
    return img.crop((lx, ty, lx + w, ty + h))


# ── Mech silhouette generator (Iron Legends aesthetic) ─────────────────────────

def generate_mech_silhouette(role: str, out: Path, accent: tuple = C_ELECTRIC) -> Path:
    """
    Generate an Iron Legends style mech silhouette PNG.
    Hero = blue/electric angular mech
    Villain = massive crimson/black war machine
    Ancient = gold/white titan
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    img  = Image.new("RGBA", (600, 900), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if role in ("protagonist", "hero"):
        color = (*C_ELECTRIC, 220)
        glow  = (*C_ELECTRIC, 40)
        # Mech body — angular, heroic
        draw.ellipse([230, 50, 370, 190],   fill=color)          # head
        draw.polygon([(200, 190), (400, 190), (430, 240), (170, 240)], fill=color)  # neck/collar
        draw.rectangle([180, 240, 420, 500], fill=color)          # torso
        # chest energy core glow
        draw.ellipse([270, 300, 330, 360], fill=(255, 255, 255, 255))
        draw.ellipse([280, 310, 320, 350], fill=(*C_ELECTRIC, 255))
        # arms — angular, weapon-ready
        draw.polygon([(180, 250), (100, 280), (60, 420), (90, 460), (160, 320), (180, 310)], fill=color)
        draw.polygon([(420, 250), (500, 290), (550, 430), (510, 460), (440, 320), (420, 310)], fill=color)
        # legs — powerful stance
        draw.rectangle([210, 500, 290, 760], fill=color)
        draw.rectangle([310, 500, 390, 760], fill=color)
        draw.rectangle([185, 740, 305, 800], fill=color)          # feet
        draw.rectangle([295, 740, 415, 800], fill=color)
        # shoulder pads
        draw.ellipse([140, 230, 200, 310], fill=color)
        draw.ellipse([400, 230, 460, 310], fill=color)
        draw.text((300, 840), "IRON VANGUARD", font=_font(FONT_BOLD, 26), fill=(*C_ELECTRIC[:3], 200), anchor="mm")

    elif role in ("antagonist", "villain"):
        color = (*C_CRIMSON, 230)
        # MASSIVE war machine — 4 arms, crown of wreckage
        # Crown/horns
        draw.polygon([(200, 80), (240, 10), (270, 80)], fill=color)
        draw.polygon([(260, 70), (300, 0),  (330, 70)], fill=color)
        draw.polygon([(320, 80), (360, 10), (390, 80)], fill=color)
        # Head — brutal, imposing
        draw.rectangle([180, 80, 420, 250],  fill=color)
        # Red eyes
        draw.ellipse([215, 130, 270, 175], fill=(255, 0, 0, 255))
        draw.ellipse([330, 130, 385, 175], fill=(255, 0, 0, 255))
        # Massive torso
        draw.rectangle([150, 250, 450, 560], fill=color)
        # 4 arms — each a weapon
        draw.polygon([(150, 260), (60,  290), (10,  450), (60,  500), (140, 340), (150, 300)], fill=color)
        draw.polygon([(450, 260), (540, 300), (590, 460), (540, 510), (460, 350), (450, 300)], fill=color)
        draw.polygon([(150, 380), (50,  420), (0,   580), (60,  610), (140, 470), (150, 420)], fill=color)
        draw.polygon([(450, 380), (550, 430), (600, 590), (540, 620), (460, 490), (450, 430)], fill=color)
        # Legs — tank-like
        draw.rectangle([185, 560, 295, 820], fill=color)
        draw.rectangle([305, 560, 415, 820], fill=color)
        draw.rectangle([155, 800, 325, 870], fill=color)
        draw.rectangle([275, 800, 445, 870], fill=color)
        draw.text((300, 900), "RAVAGER PRIME", font=_font(FONT_BOLD, 26), fill=(*C_CRIMSON[:3], 200), anchor="mm")

    else:  # ancient / alpha prime
        color = (*C_GOLD, 240)
        glow  = (*C_GOLD, 80)
        # Titanic ancient mech covered in sigils
        # Head with halo of energy
        draw.ellipse([200, 40, 400, 220],    fill=color)
        # Halo
        for r_off in [80, 90, 100]:
            draw.arc([300-r_off, 40-r_off//2, 300+r_off, 40+r_off//2], -20, 200, fill=(*C_GOLD[:3], 100), width=3)
        # Body — ancient, massive, sigils
        draw.rectangle([155, 220, 445, 600], fill=color)
        # Sigil marks on chest
        for y_off in [280, 340, 400, 460]:
            draw.line([(200, y_off), (400, y_off)], fill=(255, 255, 255, 180), width=3)
        draw.ellipse([265, 360, 335, 420], fill=(255, 255, 255, 255))
        # Arms — vast
        draw.rectangle([65,  230, 155, 580], fill=color)
        draw.rectangle([445, 230, 535, 580], fill=color)
        # Legs
        draw.rectangle([195, 600, 295, 860], fill=color)
        draw.rectangle([305, 600, 405, 860], fill=color)
        draw.rectangle([165, 840, 325, 900], fill=color)
        draw.rectangle([275, 840, 435, 900], fill=color)
        draw.text((300, 860), "ALPHA PRIME", font=_font(FONT_BOLD, 26), fill=(*C_GOLD[:3], 220), anchor="mm")

    img.save(str(out), "PNG")
    return out


# ── Background builder ─────────────────────────────────────────────────────────

def _make_il_atmospheric_bg(spec: ILSceneSpec) -> Image.Image:
    """
    Procedural atmospheric background for Iron Legends aesthetic.
    Each scene type gets distinct visual treatment.
    """
    img  = Image.new("RGB", (W, H), C_BG)
    draw = ImageDraw.Draw(img)
    gc   = spec.grade_rgba[:3]

    # Base gradient
    for y in range(H):
        t = y / H
        r = min(255, C_BG[0] + int(gc[0] * 0.5 * t))
        g = min(255, C_BG[1] + int(gc[1] * 0.4 * t))
        b = min(255, C_BG[2] + int(gc[2] * 0.6 * (1 - t)))
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Scene-specific atmospheric elements
    scene_type = spec.label

    if "RAVAGER" in scene_type or "DOMINATION" in scene_type or "HOPE LOST" in scene_type:
        # Dark energy cracks across the frame
        for i in range(8):
            x1 = (i * 240) + 100
            draw.line([(x1, 0), (x1 + 60, H)], fill=(*gc[:3], 25), width=2)

    elif "ALPHA" in scene_type or "ANCIENT" in scene_type or "GROUND" in scene_type:
        # Radiating light burst from center
        cx, cy = W // 2, H // 2
        for angle in range(0, 360, 12):
            rad = math.radians(angle)
            ex  = cx + int(math.cos(rad) * W)
            ey  = cy + int(math.sin(rad) * H)
            draw.line([(cx, cy), (ex, ey)], fill=(*C_GOLD[:3], 15), width=1)

    elif "SIEGE" in scene_type or "OPEN" in scene_type:
        # Horizontal speed lines (anime action)
        for i in range(0, H, 40):
            alpha = 10 + (i % 80)
            draw.line([(0, i), (W, i)], fill=(*gc[:3], alpha), width=1)

    # Large dim scene label watermark
    label_font = _font(FONT_BOLD, 160)
    draw.text((W // 2, H // 2), spec.label[:12],
              font=label_font, fill=(*gc[:3], 12), anchor="mm")

    # Horizon line
    hy = int(H * 0.58)
    draw.line([(0, hy), (W, hy)], fill=(*spec.accent_color, 30), width=2)

    return img


def _apply_vignette(img: Image.Image, strength: float = 0.70) -> Image.Image:
    """Radial darkening vignette — heavier than documentary for anime aesthetic."""
    vignette = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw     = ImageDraw.Draw(vignette)
    cx, cy   = W // 2, H // 2
    steps    = 70
    for i in range(steps, 0, -1):
        t     = (steps - i) / steps
        alpha = int(255 * (t ** 1.6) * strength)
        rx    = int(cx * i / steps)
        ry    = int(cy * i / steps)
        draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry],
                     outline=(0, 0, 0, alpha), width=1)
    return Image.alpha_composite(img.convert("RGBA"), vignette).convert("RGB")


def make_scene_background(spec: ILSceneSpec, base_img: Optional[Path] = None) -> Image.Image:
    """Build scene frame: backdrop + cinematic grade + vignette + letterbox."""
    if base_img and base_img.exists():
        bg = Image.open(str(base_img)).convert("RGB")
        bg = _fit_canvas(bg)
    else:
        bg = _make_il_atmospheric_bg(spec)

    # Cinematic color grade overlay
    overlay = Image.new("RGBA", (W, H), spec.grade_rgba)
    bg = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")

    # Vignette
    bg = _apply_vignette(bg, spec.vignette)

    # Letterbox bars — Iron Legends uses wider bars for anime feel
    draw  = ImageDraw.Draw(bg)
    bar_h = 56
    draw.rectangle([0, 0, W, bar_h],     fill=(0, 0, 0, spec.bar_alpha))
    draw.rectangle([0, H - bar_h, W, H], fill=(0, 0, 0, spec.bar_alpha))

    # Subtle accent line on top of bottom bar
    draw.line([(0, H - bar_h - 2), (W, H - bar_h - 2)],
              fill=(*spec.accent_color, 80), width=2)

    return bg


def composite_character(
    bg: Image.Image,
    char_path: Optional[Path],
    position: str,
    opacity: float = 0.90,
    scale: float = 0.70,
) -> Image.Image:
    """Composite a mech character PNG onto background."""
    if position == "none" or not char_path or not char_path.exists():
        return bg

    char = Image.open(str(char_path)).convert("RGBA")
    target_h = int(H * scale)
    target_w = int(char.width * (target_h / char.height))
    char     = char.resize((target_w, target_h), Image.LANCZOS)

    pad = 60
    if position == "left":
        cx = pad
    elif position == "right":
        cx = W - target_w - pad
    else:
        cx = (W - target_w) // 2
    cy = H - target_h - 20

    r, g, b, a = char.split()
    a = a.point(lambda x: int(x * opacity))
    char.putalpha(a)

    bg = bg.convert("RGBA")
    bg.paste(char, (cx, cy), char.getchannel("A"))
    return bg.convert("RGB")


# ── Subtitle system ────────────────────────────────────────────────────────────

@dataclass
class SubEntry:
    start:   float
    end:     float
    text:    str


def text_to_subs(text: str, start: float, duration: float,
                 max_chars: int = 72) -> list[SubEntry]:
    """Split narration into timed subtitle entries."""
    if not text or not text.strip():
        return []
    entries = []
    t       = start
    lines   = _wrap(text.strip(), max_chars)
    for line in lines:
        if not line.strip():
            continue
        word_count   = len(line.split())
        seg_duration = max(1.4, word_count / WORDS_PER_SEC)
        remaining    = duration - (t - start) - 0.2
        if remaining < 0.3:
            break
        seg_duration = min(seg_duration, remaining)
        entries.append(SubEntry(t, t + seg_duration, line))
        t += seg_duration
    return entries


def write_srt(entries: list[SubEntry], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(path), "w", encoding="utf-8") as f:
        for i, e in enumerate(entries, 1):
            f.write(f"{i}\n{_srt_time(e.start)} --> {_srt_time(e.end)}\n{e.text}\n\n")
    return path


def _srt_time(sec: float) -> str:
    h  = int(sec // 3600)
    m  = int((sec % 3600) // 60)
    s  = int(sec % 60)
    ms = int((sec - int(sec)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def render_subtitle_frame(text: str, accent: tuple, width: int = W, height: int = H) -> Image.Image:
    """Render subtitle overlay PNG — Iron Legends style (bold, anime lower-third)."""
    frame = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw  = ImageDraw.Draw(frame)

    if not text or not text.strip():
        return frame

    sub_font = _font(FONT_BOLD, 46)
    pad_x    = 80
    bar_y    = height - 56 - 120      # above letterbox bar
    bar_h    = 90

    # Measure text
    bbox = draw.textbbox((0, 0), text, font=sub_font)
    tw   = bbox[2] - bbox[0]

    # Semi-transparent background strip
    draw.rectangle([0, bar_y, width, bar_y + bar_h],
                   fill=(0, 0, 0, 170))

    # Accent left edge line
    draw.rectangle([0, bar_y, 5, bar_y + bar_h],
                   fill=(*accent[:3], 220))

    # Text centered
    tx = (width - tw) // 2
    ty = bar_y + (bar_h - (bbox[3] - bbox[1])) // 2

    # Shadow
    draw.text((tx + 3, ty + 3), text, font=sub_font, fill=(0, 0, 0, 200))
    # Main text
    draw.text((tx, ty), text, font=sub_font, fill=(255, 255, 255, 255))

    return frame


# ── Camera filter (FFmpeg zoompan) ─────────────────────────────────────────────

def camera_filter(mode: str, duration: float) -> str:
    """Return FFmpeg -vf filter string for camera movement."""
    d = max(1, int(duration * FPS))

    filters = {
        "push_in":          f"zoompan=z='min(zoom+0.0006,1.35)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={d}:s={W}x{H}:fps={FPS}",
        "pull_back":        f"zoompan=z='if(lte(zoom,1.0),1.3,max(zoom-0.0007,1.0))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={d}:s={W}x{H}:fps={FPS}",
        "pan_left":         f"zoompan=z='1.08':x='min(iw*0.10+on*0.7,iw*0.92-(iw/zoom))':y='ih/2-(ih/zoom/2)':d={d}:s={W}x{H}:fps={FPS}",
        "pan_right":        f"zoompan=z='1.08':x='max(iw*0.88-on*0.7,iw/zoom*0)':y='ih/2-(ih/zoom/2)':d={d}:s={W}x{H}:fps={FPS}",
        "battlefield_drift":f"zoompan=z='1.12':x='iw/2-(iw/zoom/2)+{int(W*0.04)}*cos(on*0.05)':y='ih/2-(ih/zoom/2)+{int(H*0.03)}*cos(on*0.07)':d={d}:s={W}x{H}:fps={FPS}",
        "orbit":            f"zoompan=z='1.10':x='iw/2-(iw/zoom/2)+{int(W*0.06)}*cos(on*0.04)':y='ih/2-(ih/zoom/2)+{int(H*0.04)}*cos(on*0.04+1.57)':d={d}:s={W}x{H}:fps={FPS}",
        "parallax":         f"zoompan=z='min(zoom+0.0004,1.20)':x='iw/2-(iw/zoom/2)+{int(W*0.03)}*cos(on*0.03)':y='ih/2-(ih/zoom/2)':d={d}:s={W}x{H}:fps={FPS}",
    }
    return filters.get(mode, filters["push_in"])


def still_to_video(image: Path, out: Path, duration: float, mode: str) -> bool:
    """
    Convert a still image to video clip.
    For clips <= 12s: use zoompan camera movement.
    For longer clips: ultrafast static encode (zoompan is too slow for 45s+ clips).
    """
    if duration <= 12.0:
        vf = camera_filter(mode, duration)
        return _run([
            FFMPEG, "-y", "-loop", "1", "-i", str(image),
            "-t", str(duration),
            "-vf", f"{vf},format=yuv420p",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-pix_fmt", "yuv420p",
            str(out)
        ], f"cam_{mode}")
    else:
        # Long clip — static image, ultrafast encode, no zoompan
        return _run([
            FFMPEG, "-y", "-loop", "1", "-i", str(image),
            "-t", str(duration),
            "-vf", "scale=1920:1080,setsar=1,format=yuv420p",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
            "-pix_fmt", "yuv420p",
            str(out)
        ], f"static_{mode}")


# ── Title / End card builders ──────────────────────────────────────────────────

def make_title_card(title: str, tagline: str, episode_id: str, out: Path) -> Path:
    """Build Iron Legends title card — dark, electric, cinematic."""
    out.parent.mkdir(parents=True, exist_ok=True)
    img  = Image.new("RGB", (W, H), C_BG)
    draw = ImageDraw.Draw(img)

    # Deep space gradient
    for y in range(H):
        t = y / H
        r = int(C_BG[0] + 5 * t)
        g = int(C_BG[1] + 8 * t)
        b = int(C_BG[2] + 30 * (1 - t))
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Electric energy lines (anime title card aesthetic)
    for i in range(5):
        y_off = H // 2 + (i - 2) * 8
        draw.line([(0, y_off), (W, y_off)], fill=(*C_ELECTRIC, 15 - i * 2), width=1)

    # Channel badge
    badge_font = _font(FONT_BOLD, 22)
    draw.text((W // 2, H // 4 - 60), "⚡ IRON LEGENDS ⚡",
              font=badge_font, fill=(*C_ELECTRIC, 200), anchor="mm")

    # Episode ID
    ep_font = _font(FONT_REGULAR, 18)
    draw.text((W // 2, H // 4 - 30), episode_id,
              font=ep_font, fill=(*C_STEEL, 160), anchor="mm")

    # Separator line
    lw = 500
    draw.line([(W // 2 - lw, H // 2 - 80), (W // 2 + lw, H // 2 - 80)],
              fill=(*C_ELECTRIC, 120), width=2)

    # Main title
    title_font = _font(FONT_BOLD, 72)
    words      = title.split()
    mid        = len(words) // 2
    line1      = " ".join(words[:mid])
    line2      = " ".join(words[mid:])
    draw.text((W // 2, H // 2 - 20), line1,
              font=title_font, fill=C_WHITE, anchor="mm")
    draw.text((W // 2, H // 2 + 70), line2,
              font=title_font, fill=C_WHITE, anchor="mm")

    # Separator line (bottom)
    draw.line([(W // 2 - lw, H // 2 + 130), (W // 2 + lw, H // 2 + 130)],
              fill=(*C_ELECTRIC, 120), width=2)

    # Tagline
    tag_font = _font(FONT_ITALIC, 30)
    draw.text((W // 2, H // 2 + 175), tagline,
              font=tag_font, fill=(*C_STEEL, 200), anchor="mm")

    # Letterbox
    draw.rectangle([0, 0, W, 56],     fill=(0, 0, 0))
    draw.rectangle([0, H - 56, W, H], fill=(0, 0, 0))

    img.save(str(out), "PNG")
    return out


def make_end_card(episode_id: str, next_ep: str, out: Path) -> Path:
    """Build Iron Legends end card."""
    out.parent.mkdir(parents=True, exist_ok=True)
    img  = Image.new("RGB", (W, H), C_BG)
    draw = ImageDraw.Draw(img)

    # Gradient
    for y in range(H):
        t = y / H
        draw.line([(0, y), (W, y)], fill=(int(6 + 10 * t), int(8 + 15 * t), int(18 + 40 * (1 - t))))

    # Energy circle
    cx, cy = W // 2, H // 2
    for r in [200, 210, 225]:
        draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                     outline=(*C_ELECTRIC, 40 - r // 10), width=2)

    # Main text
    main_font = _font(FONT_BOLD, 60)
    draw.text((W // 2, H // 2 - 80), "IRON LEGENDS",
              font=main_font, fill=(*C_ELECTRIC, 230), anchor="mm")

    sub_font = _font(FONT_REGULAR, 32)
    draw.text((W // 2, H // 2), "Roll Out. Transform. Remember Everything.",
              font=sub_font, fill=(*C_STEEL, 200), anchor="mm")

    # Next episode
    if next_ep:
        next_font = _font(FONT_BOLD, 26)
        draw.text((W // 2, H // 2 + 80), f"NEXT: {next_ep}",
                  font=next_font, fill=(*C_GOLD, 200), anchor="mm")

    # Subscribe
    cta_font = _font(FONT_BOLD, 28)
    draw.text((W // 2, H * 3 // 4), "SUBSCRIBE · LIKE · ROLL OUT",
              font=cta_font, fill=(*C_ELECTRIC, 180), anchor="mm")

    # Letterbox
    draw.rectangle([0, 0, W, 56],     fill=(0, 0, 0))
    draw.rectangle([0, H - 56, W, H], fill=(0, 0, 0))

    img.save(str(out), "PNG")
    return out


# ── Scene label card ──────────────────────────────────────────────────────────

def make_scene_label(label_text: str, accent: tuple, out: Path) -> Path:
    """Minimal scene label overlay image."""
    out.parent.mkdir(parents=True, exist_ok=True)
    img  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    lf   = _font(FONT_BOLD, 20)
    bbox = draw.textbbox((0, 0), label_text, font=lf)
    tw   = bbox[2] - bbox[0]
    tx   = 80
    ty   = 75

    draw.rectangle([tx - 12, ty - 8, tx + tw + 12, ty + 30], fill=(0, 0, 0, 160))
    draw.rectangle([tx - 12, ty - 8, tx - 8, ty + 30], fill=(*accent[:3], 220))
    draw.text((tx, ty), label_text, font=lf, fill=(255, 255, 255, 220))

    img.save(str(out), "PNG")
    return out


# ── SFX generator (lavfi — no audio files needed) ─────────────────────────────

SFX_CACHE_DIR = ROOT / "assets" / "sfx_cache"

def generate_sfx(sfx_type: str, duration: float, out: Path) -> Optional[Path]:
    SFX_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_key = f"il_{sfx_type}_{int(duration)}.wav"
    cached    = SFX_CACHE_DIR / cache_key
    if cached.exists():
        shutil.copy2(str(cached), str(out))
        return out

    lavfi_map = {
        "space_ambience": f"aevalsrc=0.03*sin(2*PI*60*t)+0.02*sin(2*PI*80*t)+0.015*random(1):s=44100:d={duration}",
        "battle_robots":  f"anoisesrc=color=brown:amplitude=0.12:d={duration},lowpass=f=400",
        "energy_pulse":   f"aevalsrc=0.2*sin(2*PI*120*t)*exp(-t*0.5):s=44100:d={min(duration,2.0)}",
        "mech_march":     f"anoisesrc=color=white:amplitude=0.06:d={duration},bandpass=f=200:w=50",
        "explosion":      f"anoisesrc=color=brown:amplitude=0.25:d={min(duration,3.0)},lowpass=f=300",
        "power_surge":    f"aevalsrc=0.3*sin(2*PI*(80+t*20)*t):s=44100:d={min(duration,3.0)}",
        "victory_rise":   f"aevalsrc=0.2*sin(2*PI*(220+t*30)*t):s=44100:d={min(duration,4.0)}",
    }
    expr = lavfi_map.get(sfx_type, lavfi_map["space_ambience"])
    out.parent.mkdir(parents=True, exist_ok=True)
    ok = _run([
        FFMPEG, "-y", "-f", "lavfi", "-i", expr,
        "-t", str(duration), "-ar", "44100", "-ac", "2", str(out)
    ], f"sfx_{sfx_type}")
    if ok and out.exists():
        shutil.copy2(str(out), str(cached))
        return out
    return None


# ── Synthetic music generator ──────────────────────────────────────────────────

def generate_synth_music(duration: float, music_type: str, out: Path) -> Optional[Path]:
    """
    Generate synthetic Iron Legends music via FFmpeg lavfi.
    action_synth — heavy synth bass + high energy
    ambient_space — sparse, mysterious
    epic_reveal   — swelling orchestral hit
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    dur = duration + 2.0   # slight tail

    if music_type == "action_synth":
        # Heavy 4/4 synth pulse + bass + high arpeggiated lead
        lavfi = (
            f"aevalsrc="
            f"0.15*sin(2*PI*55*t)"                             # bass root
            f"+0.10*sin(2*PI*110*t)"                           # bass octave
            f"+0.08*sin(2*PI*220*(t+0.5*(floor(t*4)/4)))"     # synth arpeggiate
            f"+0.05*sin(2*PI*440*t)*0.3"                       # high shimmer
            f":s=44100:d={dur}"
        )
    elif music_type == "epic_reveal":
        lavfi = (
            f"aevalsrc="
            f"0.20*sin(2*PI*55*t)"
            f"+0.15*sin(2*PI*138.6*t)"
            f"+0.12*sin(2*PI*165*t)"
            f"+0.10*sin(2*PI*220*t)"
            f"+0.08*sin(2*PI*277*t)"
            f":s=44100:d={dur}"
        )
    else:  # ambient_space
        lavfi = (
            f"aevalsrc="
            f"0.06*sin(2*PI*55*t)"
            f"+0.04*sin(2*PI*82.5*t+0.5)"
            f"+0.03*sin(2*PI*110*t+1.0)"
            f":s=44100:d={dur}"
        )

    ok = _run([
        FFMPEG, "-y", "-f", "lavfi", "-i", lavfi,
        "-t", str(dur), "-ar", "44100", "-ac", "2",
        str(out)
    ], f"music_{music_type}")
    return out if ok and out.exists() else None


# ── Silence generator ──────────────────────────────────────────────────────────

def generate_silence(duration: float, out: Path) -> Optional[Path]:
    out.parent.mkdir(parents=True, exist_ok=True)
    ok = _run([
        FFMPEG, "-y", "-f", "lavfi", "-i",
        f"anullsrc=r=44100:cl=stereo",
        "-t", str(duration), "-c:a", "aac", "-b:a", "128k", str(out)
    ], "silence")
    return out if ok and out.exists() else None


# ── Audio mixer ───────────────────────────────────────────────────────────────

def mix_audio(
    out: Path,
    music: Optional[Path] = None,
    sfx: Optional[Path] = None,
    music_vol: float = 0.25,
    sfx_vol:   float = 0.55,
    duration:  float = 10.0,
) -> Optional[Path]:
    """Mix music + SFX into a single audio track."""
    tracks = []
    if music and music.exists():  tracks.append((music, music_vol))
    if sfx   and sfx.exists():    tracks.append((sfx,   sfx_vol))

    if not tracks:
        return generate_silence(duration, out)

    if len(tracks) == 1:
        src, vol = tracks[0]
        ok = _run([
            FFMPEG, "-y", "-i", str(src),
            "-af", f"volume={vol}",
            "-t", str(duration), "-c:a", "aac", "-b:a", "128k", str(out)
        ], "audio_single")
        return out if ok else None

    inputs = []
    for src, _ in tracks:
        inputs += ["-i", str(src)]
    filter_parts = [f"[{i}]volume={v}[a{i}]" for i, (_, v) in enumerate(tracks)]
    mix_inputs   = "".join(f"[a{i}]" for i in range(len(tracks)))
    filter_parts.append(f"{mix_inputs}amix=inputs={len(tracks)}:duration=first[aout]")

    ok = _run([
        FFMPEG, "-y", *inputs,
        "-filter_complex", ";".join(filter_parts),
        "-map", "[aout]",
        "-t", str(duration), "-c:a", "aac", "-b:a", "128k", str(out)
    ], "audio_mix")
    return out if ok else None


# ── Scene renderer ────────────────────────────────────────────────────────────

def render_scene(scene: dict, work_dir: Path, char_paths: dict, episode_id: str) -> Optional[Path]:
    """
    Render a single scene to an MP4 clip.
    Returns path to final scene MP4 or None on failure.
    """
    n        = scene["scene_number"]
    stype    = scene.get("type", "default")
    spec     = IL_SCENE_SPECS.get(stype, IL_SCENE_SPECS["default"])
    duration = float(scene.get("duration_sec", DEFAULT_DUR))
    cam      = scene.get("camera", spec.camera_mode)
    narration = scene.get("narration", "")

    label    = f"[Scene {n:02d}]"
    print(f"\n{label} {scene.get('title', '')} ({stype}, {duration}s)")

    work_dir.mkdir(parents=True, exist_ok=True)

    # ── 1. Background image ───────────────────────────────────────────────────
    bg_file  = CHAR_DIR / scene.get("bg_image", "__none__")
    bg_file  = bg_file if bg_file.exists() else None
    still_bg = work_dir / f"scene_{n:02d}_bg.png"

    if not still_bg.exists():
        print(f"  → Building background...")
        bg = make_scene_background(spec, bg_file)

        # Composite character if available
        char_role = spec.char_position
        if char_role != "none":
            # Try to find an appropriate character image
            if stype in ("villain_intro", "villain_dominance", "darkest_moment"):
                char_img = char_paths.get("antagonist")
            elif stype in ("hero_intro", "crisis", "cliffhanger"):
                char_img = char_paths.get("protagonist")
            elif stype in ("mystery", "turning_point", "hero_reveal"):
                char_img = char_paths.get("ancient")
            else:
                char_img = None

            if char_img and char_img.exists():
                bg = composite_character(bg, char_img, char_role)

        # Subtitle label
        label_still = work_dir / f"scene_{n:02d}_label.png"
        label_img   = make_scene_label(spec.label, spec.accent_color, label_still)

        # Composite label onto background
        label_layer = Image.open(str(label_img)).convert("RGBA")
        bg_rgba     = bg.convert("RGBA")
        bg_rgba.paste(label_layer, (0, 0), label_layer.getchannel("A"))
        bg          = bg_rgba.convert("RGB")

        bg.save(str(still_bg), "PNG")
        print(f"  → Background saved: {still_bg.name}")

    # ── 2. Video motion clip ─────────────────────────────────────────────────
    motion_out = work_dir / f"scene_{n:02d}_motion.mp4"
    if not motion_out.exists():
        print(f"  → Rendering motion clip ({cam})...")
        if not still_to_video(still_bg, motion_out, duration, cam):
            print(f"  [WARN] Motion render failed for scene {n}")
            return None

    # ── 3. Audio ─────────────────────────────────────────────────────────────
    audio_out = work_dir / f"scene_{n:02d}_audio.aac"
    if not audio_out.exists():
        print(f"  → Generating audio...")

        # Music type based on scene
        if stype in ("hero_reveal", "turning_point"):
            mtype = "epic_reveal"
        elif stype in ("cold_open", "mystery"):
            mtype = "ambient_space"
        else:
            mtype = "action_synth"

        music_tmp = work_dir / f"scene_{n:02d}_music.wav"
        sfx_tmp   = work_dir / f"scene_{n:02d}_sfx.wav"

        sfx_map = {
            "cold_open":         "space_ambience",
            "hero_intro":        "mech_march",
            "villain_intro":     "battle_robots",
            "villain_dominance": "explosion",
            "mystery":           "space_ambience",
            "crisis":            "battle_robots",
            "darkest_moment":    "battle_robots",
            "turning_point":     "power_surge",
            "hero_reveal":       "victory_rise",
            "cliffhanger":       "energy_pulse",
        }
        sfx_type = sfx_map.get(stype, "space_ambience")

        generate_synth_music(duration, mtype, music_tmp)
        generate_sfx(sfx_type, duration, sfx_tmp)
        mix_audio(audio_out, music_tmp, sfx_tmp, duration=duration)

    # ── 4. Subtitle burn-in ──────────────────────────────────────────────────
    subbed_out = work_dir / f"scene_{n:02d}_subbed.mp4"
    if not subbed_out.exists() and narration:
        print(f"  → Burning subtitles...")
        subs    = text_to_subs(narration, 0.0, duration)
        sub_imgs = []

        for idx, sub in enumerate(subs):
            sub_img_path = work_dir / f"scene_{n:02d}_sub_{idx:03d}.png"
            if not sub_img_path.exists():
                frame = render_subtitle_frame(sub.text, spec.accent_color)
                frame.save(str(sub_img_path), "PNG")
            sub_imgs.append((sub, sub_img_path))

        if sub_imgs:
            # Use SRT file + ffmpeg subtitles filter approach
            srt_path = work_dir / f"scene_{n:02d}.srt"
            write_srt(subs, srt_path)

            ok = _run([
                FFMPEG, "-y", "-i", str(motion_out),
                "-vf", f"subtitles={str(srt_path)}:force_style='FontName=DejaVu Sans Bold,FontSize=22,PrimaryColour=&Hffffff,BackColour=&H80000000,BorderStyle=4,Outline=0,Shadow=0,Alignment=2'",
                "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                "-an", str(subbed_out)
            ], f"subtitle_burn_{n}")
            if not ok:
                # Fallback: no subtitles
                shutil.copy2(str(motion_out), str(subbed_out))
        else:
            shutil.copy2(str(motion_out), str(subbed_out))
    elif not narration:
        shutil.copy2(str(motion_out), str(subbed_out))

    # ── 5. Mux video + audio ─────────────────────────────────────────────────
    final_out = work_dir / f"scene_{n:02d}_final.mp4"
    if not final_out.exists():
        print(f"  → Muxing audio + video...")
        vid_src = subbed_out if subbed_out.exists() else motion_out
        ok = _run([
            FFMPEG, "-y",
            "-i", str(vid_src),
            "-i", str(audio_out),
            "-c:v", "copy", "-c:a", "copy",
            "-shortest", "-map", "0:v", "-map", "1:a",
            str(final_out)
        ], f"mux_{n}")
        if not ok:
            # Try re-encode if copy fails
            _run([
                FFMPEG, "-y",
                "-i", str(vid_src),
                "-i", str(audio_out),
                "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                "-c:a", "aac", "-b:a", "128k",
                "-shortest", "-map", "0:v:0", "-map", "1:a:0",
                str(final_out)
            ], f"mux_encode_{n}")

    if final_out.exists():
        dur_check = _probe(final_out)
        print(f"  ✓ Scene {n:02d} done: {final_out.name} ({dur_check:.1f}s)")
        return final_out

    print(f"  [FAIL] Scene {n:02d} failed")
    return None


# ── Episode assembler ─────────────────────────────────────────────────────────

def render_episode(episode_id: str, output_path: Optional[Path] = None) -> Optional[Path]:
    """
    Full Iron Legends episode render.
    Loads scene_prompts JSON, renders all scenes, assembles final MP4.
    """
    # Find scene prompts file
    prompts_file = PROMPTS_DIR / f"scene_prompts.{episode_id.lower()}.final.json"
    if not prompts_file.exists():
        print(f"[ERR] Scene prompts not found: {prompts_file}")
        return None

    with open(str(prompts_file), encoding="utf-8") as f:
        ep = json.load(f)

    episode_id   = ep.get("episode_id", episode_id)
    title        = ep.get("title", "Iron Legends Episode")
    tagline      = ep.get("tagline", "Roll Out. Transform. Remember Everything.")
    next_ep      = ep.get("next_episode_preview", "")
    scenes       = ep.get("scenes", [])

    print(f"\n{'='*60}")
    print(f"  IRON LEGENDS — {episode_id}")
    print(f"  {title}")
    print(f"  {len(scenes)} scenes")
    print(f"{'='*60}\n")

    # Work directory
    work_dir = RENDERS_DIR / "iron_legends" / f"_work_{episode_id.lower()}"
    work_dir.mkdir(parents=True, exist_ok=True)
    IL_RENDERS_DIR.mkdir(parents=True, exist_ok=True)

    # ── Generate character silhouettes ────────────────────────────────────────
    print("Building character silhouettes...")
    char_paths = {}

    hero_sil    = work_dir / "char_hero.png"
    villain_sil = work_dir / "char_villain.png"
    ancient_sil = work_dir / "char_ancient.png"

    if not hero_sil.exists():
        generate_mech_silhouette("protagonist", hero_sil, C_ELECTRIC)
    if not villain_sil.exists():
        generate_mech_silhouette("antagonist", villain_sil, C_CRIMSON)
    if not ancient_sil.exists():
        generate_mech_silhouette("ancient", ancient_sil, C_GOLD)

    char_paths["protagonist"] = hero_sil
    char_paths["antagonist"]  = villain_sil
    char_paths["ancient"]     = ancient_sil

    # ── Title card ─────────────────────────────────────────────────────────────
    print("\nBuilding title card...")
    title_still = work_dir / "title_still.png"
    title_vid   = work_dir / "title.mp4"
    title_final = work_dir / "title_final.mp4"
    title_audio = work_dir / "title_audio.aac"

    if not title_still.exists():
        make_title_card(title, tagline, episode_id, title_still)

    if not title_vid.exists():
        still_to_video(title_still, title_vid, TITLE_DUR, "push_in")

    if not title_audio.exists():
        generate_silence(TITLE_DUR, title_audio)

    if not title_final.exists() and title_vid.exists() and title_audio.exists():
        _run([FFMPEG, "-y", "-i", str(title_vid), "-i", str(title_audio),
              "-c:v", "copy", "-c:a", "copy", "-shortest",
              "-map", "0:v", "-map", "1:a", str(title_final)], "title_mux")

    # ── Render all scenes ──────────────────────────────────────────────────────
    scene_clips = []
    for scene in scenes:
        clip = render_scene(scene, work_dir, char_paths, episode_id)
        if clip:
            scene_clips.append(clip)

    # ── End card ───────────────────────────────────────────────────────────────
    print("\nBuilding end card...")
    end_still = work_dir / "end_still.png"
    end_vid   = work_dir / "end.mp4"
    end_final = work_dir / "end_final.mp4"
    end_audio = work_dir / "end_audio.aac"

    if not end_still.exists():
        make_end_card(episode_id, next_ep, end_still)

    if not end_vid.exists():
        still_to_video(end_still, end_vid, END_DUR, "push_in")

    if not end_audio.exists():
        generate_silence(END_DUR, end_audio)

    if not end_final.exists() and end_vid.exists() and end_audio.exists():
        _run([FFMPEG, "-y", "-i", str(end_vid), "-i", str(end_audio),
              "-c:v", "copy", "-c:a", "copy", "-shortest",
              "-map", "0:v", "-map", "1:a", str(end_final)], "end_mux")

    # ── Concat all clips ───────────────────────────────────────────────────────
    print("\nAssembling final episode...")
    all_clips = []
    if title_final.exists():
        all_clips.append(title_final)
    all_clips.extend(scene_clips)
    if end_final.exists():
        all_clips.append(end_final)

    if not all_clips:
        print("[ERR] No clips to assemble")
        return None

    concat_list = work_dir / "concat.txt"
    with open(str(concat_list), "w") as f:
        for clip in all_clips:
            f.write(f"file '{clip}'\n")

    if output_path is None:
        output_path = IL_RENDERS_DIR / f"{episode_id.lower()}.mp4"

    ok = _run([
        FFMPEG, "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy", "-movflags", "+faststart",
        str(output_path)
    ], "final_concat")

    if ok and output_path.exists():
        dur = _probe(output_path)
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"\n{'='*60}")
        print(f"  ✓ EPISODE COMPLETE: {output_path.name}")
        print(f"  Duration: {dur:.1f}s  |  Size: {size_mb:.1f} MB")
        print(f"{'='*60}\n")
        _backup(output_path)
        return output_path
    else:
        print("[ERR] Final concat failed")
        return None


# ── Test render ───────────────────────────────────────────────────────────────

def render_test() -> None:
    """Quick test: render a 5-second scene of each major type."""
    print("\n=== IRON LEGENDS TEST RENDER ===\n")
    work = ROOT / "renders" / "iron_legends" / "_test"
    work.mkdir(parents=True, exist_ok=True)

    test_scene = {
        "scene_number": 0,
        "type": "villain_intro",
        "title": "TEST — Villain Intro",
        "narration": "The Ravagers came from the dark between stars. And they were here to end everything.",
        "duration_sec": 6,
        "camera": "pull_back",
    }

    char_paths = {}
    villain_sil = work / "char_villain.png"
    generate_mech_silhouette("antagonist", villain_sil, C_CRIMSON)
    char_paths["antagonist"] = villain_sil

    result = render_scene(test_scene, work, char_paths, "TEST")
    if result:
        print(f"\n✓ Test render complete: {result}")
    else:
        print("\n✗ Test render failed")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Iron Legends Channel Render Engine