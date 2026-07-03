#!/usr/bin/env python3
"""
Empire Decoded — Episode 5: The Battle of Thermopylae
ep005_final_render.py — Full episode assembly

Uses real Higgsfield assets if downloaded; synthetic fallbacks otherwise.
Run download_ep005_assets.ps1 first to enable Hades voice + real music.

Output: renders/thermopylae_final.mp4
"""

import os, sys, math, shutil, subprocess, textwrap, time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE     = Path(__file__).parent
WORK     = BASE / "_work_ep005"
RENDERS  = BASE / "renders"
ASSETS   = BASE / "assets"
NARR     = ASSETS / "narration"
SFX_DIR  = ASSETS / "sfx"
MUSIC    = ASSETS / "music" / "music.m4a"
CHAR_IMG = BASE / "character_images" / "spartan_hoplite_reference.png"
SFX_CACHE = ASSETS / "sfx_cache"

CHAR_DIR = BASE / "character_images"
FFMPEG = "ffmpeg"
W, H   = 1920, 1080
FPS    = 24
CRF    = 20

FONT_BOLD  = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG   = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"

# ── EPISODE SCRIPT ─────────────────────────────────────────────────────────────

SEGMENTS = [
    {
        "n": 1,
        "id":      "01_cold_open_final",
        "chapter": "THE BATTLE OF THERMOPYLAE",
        "sub_text": (
            "What does it take to stop an empire of a million men?\n"
            "In 480 B.C., three hundred Spartans found out.\n"
            "This is Empire Decoded. This is the Battle of Thermopylae."
        ),
        "narr_file": "01_cold_open_final.wav",
        "est_dur":   24,
        "sfx_type":  "tension_drone",
        "sfx_file":  "tension_drone.mp3",
        "camera":    "push_in",
        "bg_top":    (2,  0,  0),
        "bg_mid":    (15, 0,  0),
        "bg_bot":    (40, 5,  5),
        "accent":    (180, 20, 20),
        "show_char": False,
        "bg_image":  "lucid-origin_Massive_naval_fleet_of_ancient_Persia_crossing_the_sea_toward_Greece_giant_warsh-1.jpg",
    },
    {
        "n": 2,
        "id":      "02_agoge",
        "chapter": "THE SPARTAN AGOGE",
        "sub_text": (
            "In Sparta, a boy did not belong to his family.\n"
            "At age seven he entered the agoge — a brutal training system\n"
            "with one purpose: the perfect soldier."
        ),
        "narr_file": "02_agoge.wav",
        "est_dur":   28,
        "sfx_type":  "marching",
        "sfx_file":  "agoge_training.mp3",
        "camera":    "pull_back",
        "bg_top":    (8,  8,  12),
        "bg_mid":    (30, 28, 22),
        "bg_bot":    (55, 50, 35),
        "accent":    (170, 130, 50),
        "show_char": True,
        "bg_image":  "lucid-origin_Ancient_Spartan_soldiers_training_as_children_harsh_military_camp_bronze_weapons-0.jpg",
    },
    {
        "n": 3,
        "id":      "03_phalanx",
        "chapter": "THE PHALANX",
        "sub_text": (
            "Every Spartan hoplite fought shoulder to shoulder,\n"
            "shields overlapping, spears forward.\n"
            "The phalanx made Sparta's army the most feared in the world."
        ),
        "narr_file": "03_phalanx.wav",
        "est_dur":   24,
        "sfx_type":  "battle_ambience",
        "sfx_file":  "forge.mp3",
        "camera":    "push_in",
        "bg_top":    (10, 7,  2),
        "bg_mid":    (50, 35, 10),
        "bg_bot":    (90, 65, 20),
        "accent":    (200, 150, 40),
        "show_char": True,
        "bg_image":  "lucid-origin_Ancient_Spartan_warriors_standing_in_heavy_rain_before_battle_shields_locked_tog-0.jpg",
    },
    {
        "n": 4,
        "id":      "04_prophecy",
        "chapter": "THE ORACLE'S WARNING",
        "sub_text": (
            "The Oracle of Delphi delivered a grim prophecy:\n"
            "either Sparta would be destroyed —\n"
            "or one of her kings must die. Leonidas chose."
        ),
        "narr_file": "04_prophecy.wav",
        "est_dur":   26,
        "sfx_type":  "crowd_reaction",
        "sfx_file":  "oracle_temple.mp3",
        "camera":    "pull_back",
        "bg_top":    (5,  3,  12),
        "bg_mid":    (25, 18, 50),
        "bg_bot":    (60, 45, 20),
        "accent":    (220, 190, 100),
        "show_char": False,
        "bg_image":  "lucid-origin_Ancient_Greek_oracle_temple_with_mysterious_atmosphere_priests_and_torches_giant-0.jpg",
    },
    {
        "n": 5,
        "id":      "05_persian_invasion",
        "chapter": "THE MILLION-MAN ARMY",
        "sub_text": (
            "King Xerxes assembled the largest invasion force\n"
            "the ancient world had ever seen — over a million soldiers.\n"
            "His engineers built a bridge of boats across the Hellespont."
        ),
        "narr_file": "05_persian_invasion.wav",
        "est_dur":   28,
        "sfx_type":  "marching",
        "sfx_file":  "persian_army_march.mp3",
        "camera":    "pull_back",
        "bg_top":    (8,  4,  0),
        "bg_mid":    (45, 20, 0),
        "bg_bot":    (90, 40, 5),
        "accent":    (200, 80, 10),
        "show_char": False,
        "bg_image":  "lucid-origin_Huge_Persian_army_crossing_mountains_toward_Greece_thousands_of_ancient_soldiers-1.jpg",
    },
    {
        "n": 6,
        "id":      "06_the_immortals",
        "chapter": "THE IMMORTALS",
        "sub_text": (
            "At the heart of that army marched the Immortals —\n"
            "ten thousand of Persia's finest, hand-picked, undefeated.\n"
            "To the ancient world, they were a force of nature."
        ),
        "narr_file": "06_the_immortals.wav",
        "est_dur":   22,
        "sfx_type":  "marching",
        "sfx_file":  "immortals_march.mp3",
        "camera":    "push_in",
        "bg_top":    (0,  0,  0),
        "bg_mid":    (20, 2,  2),
        "bg_bot":    (55, 8,  8),
        "accent":    (200, 160, 30),
        "show_char": False,
        "bg_image":  "lucid-origin_Ancient_Persian_Immortals_marching_into_battle_black_armor_gold_weapons_terrifyi-1.jpg",
    },
    {
        "n": 7,
        "id":      "07_the_stand_begins",
        "chapter": "THE HOT GATES",
        "sub_text": (
            "Leonidas chose the pass at Thermopylae — barely wide enough\n"
            "for a handful of men. For two days, three hundred Spartans\n"
            "held the line against wave after wave of Persian attacks."
        ),
        "narr_file": "07_the_stand_begins.wav",
        "est_dur":   34,
        "sfx_type":  "battle_ambience",
        "sfx_file":  "storm_battle.mp3",
        "camera":    "push_in",
        "bg_top":    (3,  6,  12),
        "bg_mid":    (15, 25, 45),
        "bg_bot":    (40, 55, 80),
        "accent":    (120, 150, 200),
        "show_char": True,
        "bg_image":  "lucid-origin_Spartan_warriors_holding_the_narrow_pass_at_Thermopylae_Persian_army_surrounding-0.jpg",
    },
    {
        "n": 8,
        "id":      "08_the_betrayal_turn",
        "chapter": "THE BETRAYAL",
        "sub_text": (
            "On the third day, a local shepherd showed the Persians\n"
            "a hidden mountain path. Surrounded, Leonidas sent the allies away —\n"
            "and stayed with his three hundred to the last man."
        ),
        "narr_file": "08_the_betrayal_turn.wav",
        "est_dur":   28,
        "sfx_type":  "battle_ambience",
        "sfx_file":  "last_stand_chaos.mp3",
        "camera":    "pull_back",
        "bg_top":    (0,  0,  2),
        "bg_mid":    (10, 5,  20),
        "bg_bot":    (30, 15, 50),
        "accent":    (100, 70, 160),
        "show_char": False,
        "bg_image":  "lucid-origin_Massive_aerial_view_of_the_Battle_of_Thermopylae_Spartan_warriors_defending_the_-0.jpg",
    },
    {
        "n": 9,
        "id":      "09_aftermath",
        "chapter": "THE COST OF DEFIANCE",
        "sub_text": (
            "They did not survive. But their stand bought Greece\n"
            "something it could not buy any other way: time.\n"
            "Time to gather, to unite, to prepare — and to win."
        ),
        "narr_file": "09_aftermath.wav",
        "est_dur":   24,
        "sfx_type":  "battle_ambience",
        "sfx_file":  "aftermath_ambience.mp3",
        "camera":    "pull_back",
        "bg_top":    (5,  5,  5),
        "bg_mid":    (25, 22, 18),
        "bg_bot":    (50, 45, 35),
        "accent":    (120, 100, 70),
        "show_char": False,
        "bg_image":  "lucid-origin_King_Leonidas_standing_alone_after_battle_wounded_Spartan_king_holding_a_broken_-0.jpg",
    },
    {
        "n": 10,
        "id":      "10_legacy_outro",
        "chapter": "THE LEGACY",
        "sub_text": (
            "Twenty-five hundred years later, Thermopylae still means\n"
            "standing your ground against impossible odds.\n"
            "Subscribe to Empire Decoded — history's greatest stories, decoded."
        ),
        "narr_file": "10_legacy_outro.wav",
        "est_dur":   32,
        "sfx_type":  "victory_stinger",
        "sfx_file":  "triumphant_resolution.mp3",
        "camera":    "pull_back",
        "bg_top":    (8,  6,  0),
        "bg_mid":    (40, 30, 5),
        "bg_bot":    (90, 72, 18),
        "accent":    (220, 190, 80),
        "show_char": True,
        "bg_image":  "lucid-origin_King_Leonidas_leading_Spartan_warriors_into_battle_shields_raised_spears_forward-0.jpg",
    },
]

SFX_RECIPES = {
    "tension_drone": (
        "anoisesrc=c=brown:r=44100,volume=0.40,"
        "lowpass=f=300,aecho=0.7:0.8:120:0.5"
    ),
    "marching": (
        "anoisesrc=c=brown:r=44100,volume=0.55,"
        "lowpass=f=220,aecho=0.6:0.7:200:0.5"
    ),
    "battle_ambience": (
        "anoisesrc=c=brown:r=44100,volume=0.45,"
        "lowpass=f=380,aecho=0.7:0.8:80:0.4"
    ),
    "crowd_reaction": (
        "anoisesrc=c=pink:r=44100,volume=0.50,"
        "bandpass=f=700:width_type=o:w=2,"
        "aecho=0.5:0.6:60:0.3"
    ),
    "victory_stinger": (
        "anoisesrc=c=pink:r=44100,volume=0.30,"
        "highpass=f=400,lowpass=f=2000,"
        "aecho=0.6:0.7:80:0.4"
    ),
}


# ── UTILITY ────────────────────────────────────────────────────────────────────

def run(cmd: list, label: str = "") -> bool:
    tag = f"[{label}] " if label else ""
    try:
        r = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if r.returncode != 0:
            print(f"  {tag}FAILED: {r.stderr.decode()[-300:]}")
            return False
        return True
    except Exception as e:
        print(f"  {tag}EXCEPTION: {e}")
        return False


def get_duration(path: Path) -> float:
    """Get audio/video duration via ffprobe."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True
        )
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def wrap_text(text: str, width: int = 42) -> list[str]:
    lines = []
    for para in text.split("\n"):
        lines.extend(textwrap.wrap(para, width) or [""])
    return lines


# ── PIL SCENE GENERATION ───────────────────────────────────────────────────────

def load_real_bg(img_name: str, darken: float = 0.55) -> Image.Image | None:
    """Load a real character/scene image, scale to 1920x1080 (center-crop), darken for text readability."""
    path = CHAR_DIR / img_name
    if not path.exists():
        return None
    try:
        img = Image.open(str(path)).convert("RGB")
        # Scale to cover 1920x1080 (center crop)
        iw, ih = img.size
        scale = max(W / iw, H / ih)
        nw, nh = int(iw * scale), int(ih * scale)
        img = img.resize((nw, nh), Image.LANCZOS)
        left = (nw - W) // 2
        top  = (nh - H) // 2
        img  = img.crop((left, top, left + W, top + H))
        # Darken for subtitle readability
        overlay = Image.new("RGB", (W, H), (0, 0, 0))
        img = Image.blend(img, overlay, darken)
        return img
    except Exception as e:
        print(f"  [bg] Could not load {img_name}: {e}")
        return None


def make_gradient_bg(top: tuple, mid: tuple, bot: tuple) -> Image.Image:
    """Create a cinematic gradient background 1920x1080."""
    img = Image.new("RGB", (W, H))
    px  = img.load()
    half = H // 2
    for y in range(H):
        if y <= half:
            t = y / half
            r = int(top[0] + (mid[0] - top[0]) * t)
            g = int(top[1] + (mid[1] - top[1]) * t)
            b = int(top[2] + (mid[2] - top[2]) * t)
        else:
            t = (y - half) / (H - half)
            r = int(mid[0] + (bot[0] - mid[0]) * t)
            g = int(mid[1] + (bot[1] - mid[1]) * t)
            b = int(mid[2] + (bot[2] - mid[2]) * t)
        for x in range(W):
            px[x, y] = (r, g, b)
    return img


def add_vignette(img: Image.Image, strength: float = 0.7) -> Image.Image:
    """Add cinematic vignette (darken edges)."""
    vign = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    drw  = ImageDraw.Draw(vign)
    cx, cy = W // 2, H // 2
    steps = 80
    for i in range(steps):
        t     = i / steps
        alpha = int(255 * strength * (t ** 2.2))
        rx    = int(cx + cx * (1 - t) * 1.05)
        ry    = int(cy + cy * (1 - t) * 1.05)
        drw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry],
                    fill=(0, 0, 0, alpha))
    base = img.convert("RGBA")
    out  = Image.alpha_composite(base, vign)
    return out.convert("RGB")


def add_grain(img: Image.Image, amount: int = 12) -> Image.Image:
    """Add subtle film grain."""
    import random
    rnd = random.Random(42)
    px  = img.load()
    for y in range(0, H, 2):
        for x in range(0, W, 2):
            n = rnd.randint(-amount, amount)
            r, g, b = px[x, y]
            px[x, y] = (
                max(0, min(255, r + n)),
                max(0, min(255, g + n)),
                max(0, min(255, b + n)),
            )
    return img


def draw_horizontal_lines(img: Image.Image, accent: tuple, n: int = 8, opacity: int = 25) -> Image.Image:
    """Add subtle horizontal scan-line texture."""
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    drw     = ImageDraw.Draw(overlay)
    step    = H // (n * 2)
    for i in range(n):
        y = int(H * 0.2) + i * step * 2
        drw.line([(0, y), (W, y)], fill=(*accent, opacity), width=1)
    base = img.convert("RGBA")
    return Image.alpha_composite(base, overlay).convert("RGB")


def draw_chapter_lines(img: Image.Image, accent: tuple) -> Image.Image:
    """Draw thin horizontal accent lines flanking where chapter text goes."""
    drw = ImageDraw.Draw(img)
    y   = int(H * 0.82)
    drw.line([(int(W * 0.05), y), (int(W * 0.45), y)], fill=accent, width=2)
    drw.line([(int(W * 0.55), y), (int(W * 0.95), y)], fill=accent, width=2)
    return img


def draw_spartan_silhouette(img: Image.Image, accent: tuple, x_frac: float = 0.82) -> Image.Image:
    """Draw a stylized Spartan warrior silhouette."""
    drw  = ImageDraw.Draw(img)
    cx   = int(W * x_frac)
    base = int(H * 0.90)

    # Body (simplified warrior shape)
    drw.ellipse([cx-36, int(H*0.25), cx+36, int(H*0.25)+72], fill=(*accent, 180))  # helmet dome
    # Crest
    drw.polygon([
        (cx-6,  int(H*0.25)),
        (cx+6,  int(H*0.25)),
        (cx+20, int(H*0.12)),
        (cx-20, int(H*0.12)),
    ], fill=(*accent[:3],))
    # Body torso
    drw.rectangle([cx-28, int(H*0.37), cx+28, int(H*0.65)], fill=(*accent[:3],))
    # Legs
    drw.rectangle([cx-28, int(H*0.65), cx-6,  base], fill=(*accent[:3],))
    drw.rectangle([cx+6,  int(H*0.65), cx+28, base], fill=(*accent[:3],))
    # Shield (circle)
    drw.ellipse([cx-80, int(H*0.38), cx-10, int(H*0.72)], fill=(*accent[:3],), outline=(200,200,200), width=2)
    # Spear
    drw.line([(cx+32, int(H*0.10)), (cx+32, base)], fill=(200, 200, 200), width=4)
    drw.polygon([
        (cx+26, int(H*0.09)),
        (cx+38, int(H*0.09)),
        (cx+32, int(H*0.04)),
    ], fill=(220, 220, 220))

    return img


def draw_shield_pattern(img: Image.Image, accent: tuple) -> Image.Image:
    """Draw overlapping shield shapes suggesting a phalanx."""
    drw = ImageDraw.Draw(img)
    for row in range(3):
        for col in range(7):
            cx = int(W * 0.08) + col * int(W * 0.13) + (row % 2) * int(W * 0.065)
            cy = int(H * 0.35) + row * int(H * 0.20)
            r  = int(W * 0.055)
            alpha_val = max(30, 80 - row * 20 - col * 5)
            drw.ellipse([cx-r, cy-r, cx+r, cy+r],
                        outline=(*accent, alpha_val), width=3)
            # Lambda symbol
            drw.line([(cx-10, cy+8), (cx, cy-12), (cx+10, cy+8)], fill=(*accent, alpha_val), width=2)
    return img


def draw_army_silhouettes(img: Image.Image, accent: tuple) -> Image.Image:
    """Draw rows of army silhouettes suggesting a vast force."""
    drw = ImageDraw.Draw(img)
    for row in range(5):
        y_base = int(H * 0.55) + row * int(H * 0.08)
        count  = 18 + row * 4
        alpha  = max(15, 70 - row * 15)
        for col in range(count):
            x = int(W * 0.02) + col * (W // count)
            h_fig = int(H * 0.12) - row * 4
            drw.rectangle([x-4, y_base - h_fig, x+4, y_base], fill=(*accent[:3], alpha))
            drw.ellipse([x-5, y_base - h_fig - 10, x+5, y_base - h_fig], fill=(*accent[:3], alpha))
    return img


def draw_mountain_pass(img: Image.Image, accent: tuple) -> Image.Image:
    """Draw a stylized narrow mountain pass."""
    drw = ImageDraw.Draw(img)
    # Left cliff
    drw.polygon([
        (0, H),
        (int(W * 0.35), H),
        (int(W * 0.45), int(H * 0.55)),
        (int(W * 0.38), int(H * 0.30)),
        (int(W * 0.20), int(H * 0.15)),
        (0, int(H * 0.20)),
    ], fill=(15, 18, 22))
    # Right cliff
    drw.polygon([
        (W, H),
        (int(W * 0.65), H),
        (int(W * 0.55), int(H * 0.55)),
        (int(W * 0.62), int(H * 0.30)),
        (int(W * 0.80), int(H * 0.15)),
        (W, int(H * 0.20)),
    ], fill=(15, 18, 22))
    # Pass floor light
    drw.polygon([
        (int(W * 0.38), H),
        (int(W * 0.62), H),
        (int(W * 0.57), int(H * 0.55)),
        (int(W * 0.43), int(H * 0.55)),
    ], fill=(*accent, 40))
    return img


def draw_temple_columns(img: Image.Image, accent: tuple) -> Image.Image:
    """Draw ancient temple columns."""
    drw = ImageDraw.Draw(img)
    col_positions = [0.15, 0.28, 0.41, 0.59, 0.72, 0.85]
    for fx in col_positions:
        cx    = int(W * fx)
        top_y = int(H * 0.10)
        bot_y = int(H * 0.90)
        width = 28
        alpha = 40
        # Column shaft
        drw.rectangle([cx - width//2, top_y, cx + width//2, bot_y],
                      fill=(*accent[:3], alpha))
        # Capital
        drw.rectangle([cx - width, top_y - 10, cx + width, top_y + 5],
                      fill=(*accent[:3], alpha + 10))
        # Base
        drw.rectangle([cx - width - 5, bot_y - 5, cx + width + 5, bot_y + 15],
                      fill=(*accent[:3], alpha + 10))
    # Entablature (top beam)
    drw.rectangle([int(W*0.10), int(H*0.08), int(W*0.90), int(H*0.12)],
                  fill=(*accent[:3], 35))
    return img


def draw_embers(img: Image.Image) -> Image.Image:
    """Draw glowing embers/sparks for aftermath scene."""
    import random
    drw = ImageDraw.Draw(img)
    rnd = random.Random(99)
    for _ in range(60):
        x    = rnd.randint(0, W)
        y    = rnd.randint(int(H * 0.3), H)
        size = rnd.randint(2, 6)
        heat = rnd.randint(180, 255)
        drw.ellipse([x - size, y - size, x + size, y + size],
                    fill=(heat, heat // 3, 0))
    return img


def draw_memorial_stone(img: Image.Image, accent: tuple) -> Image.Image:
    """Draw a stylized memorial stone / epitaph monument."""
    drw = ImageDraw.Draw(img)
    cx  = W // 2
    # Stone base
    drw.rectangle([cx - 160, int(H * 0.35), cx + 160, int(H * 0.88)],
                  fill=(50, 45, 35), outline=(*accent[:3], 60), width=3)
    # Carved top
    drw.polygon([
        (cx - 160, int(H * 0.35)),
        (cx + 160, int(H * 0.35)),
        (cx + 140, int(H * 0.22)),
        (cx,       int(H * 0.16)),
        (cx - 140, int(H * 0.22)),
    ], fill=(55, 50, 38), outline=(*accent[:3], 60), width=2)
    # Epitaph lines (horizontal text placeholder bars)
    for i, y_frac in enumerate([0.50, 0.57, 0.63, 0.69]):
        w_bar = 220 - i * 20
        y     = int(H * y_frac)
        drw.rectangle([cx - w_bar//2, y - 5, cx + w_bar//2, y + 5],
                      fill=(*accent[:3], 50))
    # Light rays from top of stone
    for angle in range(-40, 50, 12):
        rad = math.radians(angle)
        x2  = int(cx + math.sin(rad) * W * 0.6)
        y2  = int(H * 0.16 + math.cos(rad) * H * 0.6)
        drw.line([(cx, int(H * 0.16)), (x2, y2)],
                 fill=(*accent[:3], 8), width=3)
    return img


def make_scene_still(seg: dict, work: Path) -> Path:
    """Generate a full 1920x1080 scene background with thematic visuals."""
    out = work / f"scene_{seg['n']:02d}_still.png"
    if out.exists():
        return out

    # Use real background image if available
    real_bg = None
    if seg.get("bg_image"):
        real_bg = load_real_bg(seg["bg_image"])

    if real_bg is not None:
        bg = real_bg
        print(f"  [scene {seg['n']}] Using real image: {seg['bg_image']}")
    else:
        bg = make_gradient_bg(seg["bg_top"], seg["bg_mid"], seg["bg_bot"])

    acc = seg["accent"]
    n   = seg["n"]

    if n == 1:
        # Cold open: lone silhouette against crimson sky
        bg = add_vignette(bg, 0.85)
        draw = ImageDraw.Draw(bg)
        # Horizon glow
        for gy in range(int(H * 0.55), int(H * 0.70)):
            t = (gy - int(H * 0.55)) / (int(H * 0.70) - int(H * 0.55))
            alpha = int(60 * (1 - t))
            draw.line([(0, gy), (W, gy)], fill=(acc[0], acc[1]//2, 0))
        bg = draw_spartan_silhouette(bg, (200, 180, 140), x_frac=0.5)
        bg = add_grain(bg, 8)

    elif n == 2:
        # Agoge: training ground
        bg = add_vignette(bg, 0.70)
        bg = draw_horizontal_lines(bg, acc, n=12, opacity=20)
        bg = draw_spartan_silhouette(bg, (160, 130, 80), x_frac=0.75)
        bg = draw_spartan_silhouette(bg, (130, 105, 60), x_frac=0.25)
        bg = add_grain(bg, 10)

    elif n == 3:
        # Phalanx: overlapping shields
        bg = add_vignette(bg, 0.65)
        bg = draw_shield_pattern(bg, acc)
        bg = add_grain(bg, 8)

    elif n == 4:
        # Prophecy: oracle temple
        bg = add_vignette(bg, 0.75)
        bg = draw_temple_columns(bg, (180, 160, 100))
        # Mystical light beam from center
        drw = ImageDraw.Draw(bg.convert("RGBA"))
        bg = add_grain(bg, 6)

    elif n == 5:
        # Persian invasion: vast army
        bg = add_vignette(bg, 0.70)
        bg = draw_army_silhouettes(bg, (180, 100, 20))
        bg = add_grain(bg, 10)

    elif n == 6:
        # The Immortals: dark elite warriors
        bg = add_vignette(bg, 0.90)
        bg = draw_army_silhouettes(bg, (180, 140, 20))
        bg = add_grain(bg, 6)

    elif n == 7:
        # The Stand: mountain pass
        bg = add_vignette(bg, 0.75)
        bg = draw_mountain_pass(bg, (100, 140, 200))
        bg = draw_spartan_silhouette(bg, (200, 180, 150), x_frac=0.50)
        bg = add_grain(bg, 12)

    elif n == 8:
        # Betrayal: mountain path, dark
        bg = add_vignette(bg, 0.85)
        bg = draw_army_silhouettes(bg, (100, 70, 150))
        bg = add_grain(bg, 8)

    elif n == 9:
        # Aftermath: smoldering
        bg = add_vignette(bg, 0.80)
        bg = draw_shield_pattern(bg, (80, 70, 50))
        bg = draw_embers(bg)
        bg = add_grain(bg, 15)

    elif n == 10:
        # Legacy: memorial stone
        bg = add_vignette(bg, 0.65)
        bg = draw_memorial_stone(bg, acc)
        bg = draw_spartan_silhouette(bg, (180, 160, 90), x_frac=0.82)
        bg = add_grain(bg, 6)

    bg = draw_chapter_lines(bg, acc)
    bg.save(str(out))
    return out


def bake_subtitle_onto_still(
    still: Path,
    seg: dict,
    work: Path,
) -> Path:
    """Bake narration subtitle text onto scene still."""
    out = work / f"scene_{seg['n']:02d}_sub.png"
    img = Image.open(str(still)).convert("RGB")
    drw = ImageDraw.Draw(img)

    try:
        font_sub   = ImageFont.truetype(FONT_BOLD, 44)
        font_small = ImageFont.truetype(FONT_REG, 34)
    except Exception:
        font_sub   = ImageFont.load_default()
        font_small = font_sub

    lines = seg["sub_text"].split("\n")
    line_h = 54
    block_h = len(lines) * line_h + 32
    block_y = H - block_h - 80

    # Semi-transparent background box
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    box_drw = ImageDraw.Draw(overlay)
    box_drw.rectangle(
        [int(W * 0.04), block_y - 16, int(W * 0.96), block_y + block_h + 8],
        fill=(0, 0, 0, 170)
    )
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    drw = ImageDraw.Draw(img)

    for i, line in enumerate(lines):
        y = block_y + i * line_h + 8
        # Shadow
        for dx, dy in [(2, 2), (-1, -1)]:
            drw.text((W // 2 + dx, y + dy), line, font=font_sub,
                     fill=(0, 0, 0, 180), anchor="mt")
        # Main text
        drw.text((W // 2, y), line, font=font_sub,
                 fill=(255, 255, 255), anchor="mt")

    img.save(str(out))
    return out


def make_chapter_title_card(seg: dict, work: Path, duration: float = 1.8) -> Path:
    """Create a brief black chapter title card (Empire Decoded style)."""
    still_out = work / f"scene_{seg['n']:02d}_chapter_still.png"
    video_out = work / f"scene_{seg['n']:02d}_chapter.mp4"

    if not still_out.exists():
        img = Image.new("RGB", (W, H), (0, 0, 0))
        drw = ImageDraw.Draw(img)
        acc = seg["accent"]

        try:
            font_big   = ImageFont.truetype(FONT_SERIF, 72)
            font_ep    = ImageFont.truetype(FONT_REG, 30)
        except Exception:
            font_big   = ImageFont.load_default()
            font_ep    = font_big

        # Accent lines
        cy = H // 2
        drw.line([(int(W * 0.05), cy - 55), (int(W * 0.95), cy - 55)],
                 fill=acc, width=1)
        drw.line([(int(W * 0.05), cy + 50), (int(W * 0.95), cy + 50)],
                 fill=acc, width=1)

        # Chapter title (gold/accent)
        drw.text((W // 2, cy - 20), seg["chapter"],
                 font=font_big, fill=acc, anchor="mm")

        # Episode label (smaller, above)
        drw.text((W // 2, cy - 90), "EMPIRE DECODED  ·  EPISODE 5",
                 font=font_ep, fill=(160, 160, 160), anchor="mm")

        # Small corner branding
        drw.text((40, H - 40), "EMPIRE DECODED", font=font_ep,
                 fill=(80, 80, 80), anchor="lm")

        img.save(str(still_out))

    if not video_out.exists():
        # Generate video with silence so concat audio streams match
        tmp_vid = work / f"scene_{seg['n']:02d}_chapter_noaudio.mp4"
        run([
            FFMPEG, "-y",
            "-loop", "1", "-i", str(still_out),
            "-t", str(duration),
            "-vf", f"fps={FPS},scale={W}:{H}",
            "-pix_fmt", "yuv420p",
            "-c:v", "libx264", "-preset", "fast", "-crf", str(CRF),
            "-an",
            str(tmp_vid),
        ], f"chapter_card_{seg['n']}")
        # Add silence track
        if tmp_vid.exists():
            run([
                FFMPEG, "-y",
                "-i", str(tmp_vid),
                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                "-map", "0:v", "-map", "1:a", "-shortest",
                str(video_out),
            ], f"chapter_card_audio_{seg['n']}")
        if not video_out.exists() and tmp_vid.exists():
            shutil.copy2(str(tmp_vid), str(video_out))

    return video_out


def make_title_sequence(work: Path, duration: float = 6.0) -> Path:
    """Create the opening title sequence."""
    still = work / "title_still.png"
    out   = work / "title_sequence.mp4"
    if out.exists():
        return out

    img = Image.new("RGB", (W, H), (0, 0, 0))
    drw = ImageDraw.Draw(img)

    try:
        font_series = ImageFont.truetype(FONT_SERIF,  90)
        font_ep     = ImageFont.truetype(FONT_BOLD,   44)
        font_title  = ImageFont.truetype(FONT_BOLD,   62)
        font_small  = ImageFont.truetype(FONT_REG,    28)
    except Exception:
        font_series = ImageFont.load_default()
        font_ep     = font_series
        font_title  = font_series
        font_small  = font_series

    GOLD = (200, 165, 40)
    cx   = W // 2

    # "EMPIRE DECODED" — main series title
    drw.text((cx, int(H * 0.32)), "EMPIRE DECODED",
             font=font_series, fill=GOLD, anchor="mm")

    # Thin accent line
    line_y = int(H * 0.42)
    drw.line([(int(W * 0.25), line_y), (int(W * 0.75), line_y)],
             fill=(120, 100, 30), width=1)

    # Episode label
    drw.text((cx, int(H * 0.50)), "EPISODE 5",
             font=font_ep, fill=(180, 170, 150), anchor="mm")

    # Episode title
    drw.text((cx, int(H * 0.60)), "THE BATTLE OF THERMOPYLAE",
             font=font_title, fill=(240, 235, 220), anchor="mm")

    # Year / context
    drw.text((cx, int(H * 0.72)), "480 B.C. — THE PASS OF THERMOPYLAE, GREECE",
             font=font_small, fill=(120, 115, 100), anchor="mm")

    still.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(still))

    run([
        FFMPEG, "-y",
        "-loop", "1", "-i", str(still),
        "-t", str(duration),
        "-vf", (
            f"scale={W*2}:{H*2},"
            f"zoompan=z='min(pzoom+0.0005,1.04)'"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={int(duration*FPS)}:s={W}x{H},"
            f"setsar=1,fps={FPS}"
        ),
        "-pix_fmt", "yuv420p",
        "-c:v", "libx264", "-preset", "fast", "-crf", str(CRF),
        "-an",
        str(out),
    ], "title_sequence")
    return out


def make_end_card(work: Path, duration: float = 8.0) -> Path:
    """Create the closing end card."""
    still = work / "end_card_still.png"
    out   = work / "end_card.mp4"
    if out.exists():
        return out

    img = Image.new("RGB", (W, H), (0, 0, 0))
    drw = ImageDraw.Draw(img)

    try:
        font_big   = ImageFont.truetype(FONT_BOLD,  72)
        font_med   = ImageFont.truetype(FONT_REG,   42)
        font_small = ImageFont.truetype(FONT_REG,   30)
        font_ep    = ImageFont.truetype(FONT_SERIF, 48)
    except Exception:
        font_big   = ImageFont.load_default()
        font_med   = font_big
        font_small = font_big
        font_ep    = font_big

    GOLD   = (200, 165, 40)
    WHITE  = (240, 235, 220)
    GRAY   = (130, 125, 110)
    cx     = W // 2

    # Sparta epitaph — historical quote
    quote = "Go, tell the Spartans, stranger passing by,"
    quote2 = "that here, obedient to their laws, we lie."
    drw.text((cx, int(H * 0.22)), quote,  font=font_ep, fill=(160, 140, 80), anchor="mm")
    drw.text((cx, int(H * 0.32)), quote2, font=font_ep, fill=(160, 140, 80), anchor="mm")
    drw.text((cx, int(H * 0.40)), "— Simonides of Ceos, c. 480 B.C.", font=font_small, fill=GRAY, anchor="mm")

    # Divider
    drw.line([(int(W*0.2), int(H*0.52)), (int(W*0.8), int(H*0.52))], fill=(80,70,40), width=1)

    # Subscribe CTA
    drw.text((cx, int(H * 0.62)), "SUBSCRIBE TO EMPIRE DECODED", font=font_big, fill=GOLD, anchor="mm")
    drw.text((cx, int(H * 0.72)), "History's greatest stories — decoded.", font=font_med, fill=WHITE, anchor="mm")

    # Bottom label
    drw.text((cx, int(H * 0.87)), "NEXT: EPISODE 6 — THE FALL OF THE ROMAN REPUBLIC", font=font_small, fill=GRAY, anchor="mm")

    still.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(still))

    run([
        FFMPEG, "-y",
        "-loop", "1", "-i", str(still),
        "-t", str(duration),
        "-vf", f"fps={FPS},scale={W}:{H}",
        "-pix_fmt", "yuv420p",
        "-c:v", "libx264", "-preset", "fast", "-crf", str(CRF),
        "-an",
        str(out),
    ], "end_card")
    return out


# ── AUDIO GENERATION ───────────────────────────────────────────────────────────

def get_or_generate_sfx(sfx_type: str, sfx_file: str, duration: float, work: Path) -> Path:
    """Return local SFX file — real CDN file if present, else synthesize."""
    # Check for real downloaded SFX
    real = SFX_DIR / sfx_file
    if real.exists() and real.stat().st_size > 1000:
        out = work / f"sfx_{sfx_type}.wav"
        if not out.exists():
            run([FFMPEG, "-y", "-i", str(real),
                 "-t", str(duration), "-ar", "44100", "-ac", "2", str(out)],
                f"sfx_trim_{sfx_type}")
        return out

    # Synthesize
    key   = f"{sfx_type}_{int(duration)}"
    cache = SFX_CACHE / f"{key}.wav"
    out   = work / f"sfx_{sfx_type}.wav"

    if cache.exists():
        shutil.copy2(str(cache), str(out))
        return out

    recipe = SFX_RECIPES.get(sfx_type, SFX_RECIPES["tension_drone"])
    SFX_CACHE.mkdir(parents=True, exist_ok=True)
    run([
        FFMPEG, "-y", "-f", "lavfi", "-i", recipe,
        "-t", str(duration), "-ar", "44100", "-ac", "2", str(out),
    ], f"sfx_synth_{sfx_type}")
    if out.exists():
        shutil.copy2(str(out), str(cache))
    return out


def get_or_generate_music(total_dur: float, work: Path) -> Path:
    """Return music track — real CDN file if present, else synthesize."""
    out = work / "music.wav"
    if out.exists():
        return out

    if MUSIC.exists() and MUSIC.stat().st_size > 10000:
        run([FFMPEG, "-y", "-i", str(MUSIC),
             "-t", str(total_dur), "-ar", "44100", "-ac", "2", str(out)],
            "music_trim")
        return out

    # Synthesize layered orchestral-ish drone
    print("  Synthesizing music (no real track found)...")
    # Layer 1: low string drone (brown noise filtered to ~100-250Hz)
    # Layer 2: mid tension (pink noise filtered to 400-900Hz)
    # Layer 3: atmospheric hiss at very low volume
    run([
        FFMPEG, "-y",
        "-f", "lavfi",
        "-i", ("amix=inputs=3:duration=first[a],"
               "[a]aecho=0.5:0.6:300:0.2;"
               "anoisesrc=c=brown:r=44100,volume=0.22,lowpass=f=260,highpass=f=80[l1];"
               "anoisesrc=c=pink:r=44100,volume=0.06,bandpass=f=500:width_type=o:w=1.5[l2];"
               "anoisesrc=c=white:r=44100,volume=0.015[l3];"
               "[l1][l2][l3]amix=inputs=3:duration=first"
               ),
        "-t", str(total_dur),
        "-ar", "44100", "-ac", "2",
        str(out),
    ], "music_synth")

    if not out.exists() or out.stat().st_size < 1000:
        # Simplest fallback
        run([
            FFMPEG, "-y",
            "-f", "lavfi",
            "-i", "anoisesrc=c=brown:r=44100,volume=0.18,lowpass=f=300",
            "-t", str(total_dur), "-ar", "44100", "-ac", "2", str(out),
        ], "music_fallback")

    return out


# ── CAMERA MOTION ─────────────────────────────────────────────────────────────

def apply_camera_motion(still: Path, out: Path, duration: float, mode: str) -> bool:
    """Apply Ken Burns camera motion to a still image."""
    if out.exists():
        return True

    d = int(duration * FPS)

    if mode == "push_in":
        vf = (
            f"scale={W*2}:{H*2},"
            f"zoompan=z='min(pzoom+0.0008,1.10)'"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={d}:s={W}x{H},"
            f"setsar=1,fps={FPS}"
        )
    else:  # pull_back
        vf = (
            f"scale={W*2}:{H*2},"
            f"zoompan=z='if(lte(pzoom,1.0),1.10,max(pzoom-0.0008,1.0))'"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={d}:s={W}x{H},"
            f"setsar=1,fps={FPS}"
        )

    ok = run([
        FFMPEG, "-y",
        "-loop", "1", "-i", str(still),
        "-vf", vf,
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        "-c:v", "libx264", "-preset", "fast", "-crf", str(CRF),
        str(out),
    ], f"camera_{mode}")

    if not ok:
        # Static fallback
        run([
            FFMPEG, "-y", "-loop", "1", "-i", str(still),
            "-t", str(duration), "-pix_fmt", "yuv420p",
            "-vf", f"scale={W}:{H},fps={FPS}",
            "-c:v", "libx264", "-preset", "fast", "-crf", str(CRF), str(out),
        ], "camera_static_fallback")
    return out.exists()


# ── PER-SCENE AUDIO MIX ────────────────────────────────────────────────────────

def mix_scene_audio(
    narration: Path | None,
    sfx: Path,
    music_segment: Path,
    out: Path,
    duration: float,
) -> bool:
    """Mix narration + SFX + music for one scene."""
    inputs = []
    filters = []

    has_narr  = narration and narration.exists() and narration.stat().st_size > 1000
    has_sfx   = sfx and sfx.exists()
    has_music = music_segment and music_segment.exists()

    if not has_sfx and not has_music and not has_narr:
        # Generate pure silence
        run([FFMPEG, "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
             "-t", str(duration), "-c:a", "aac", "-b:a", "192k", str(out)],
            "silence")
        return out.exists()

    idx = 0
    labeled = []

    if has_narr:
        inputs += ["-i", str(narration)]
        filters.append(f"[{idx}:a]volume=1.0[narr]")
        labeled.append("[narr]")
        idx += 1

    if has_sfx:
        inputs += ["-i", str(sfx)]
        filters.append(f"[{idx}:a]volume=0.28[sfx]")
        labeled.append("[sfx]")
        idx += 1

    if has_music:
        vol = 0.12 if has_narr else 0.22
        inputs += ["-i", str(music_segment)]
        filters.append(f"[{idx}:a]volume={vol}[mus]")
        labeled.append("[mus]")
        idx += 1

    n_inputs = len(labeled)
    mix_in   = "".join(labeled)
    filters.append(
        f"{mix_in}amix=inputs={n_inputs}:duration=longest:dropout_transition=0[aout]"
    )

    cmd = [
        FFMPEG, "-y",
        *inputs,
        "-filter_complex", ";".join(filters),
        "-map", "[aout]",
        "-t", str(duration),
        "-c:a", "aac", "-b:a", "192k",
        str(out),
    ]
    return run(cmd, "scene_audio_mix")


# ── MAIN PIPELINE ─────────────────────────────────────────────────────────────

def main():
    print("="*60)
    print("Empire Decoded — Episode 5: The Battle of Thermopylae")
    print("="*60)

    WORK.mkdir(parents=True, exist_ok=True)
    RENDERS.mkdir(parents=True, exist_ok=True)
    SFX_CACHE.mkdir(parents=True, exist_ok=True)
    (ASSETS / "music").mkdir(parents=True, exist_ok=True)

    # ── Check which real assets are available ──────────────────────────────
    print("\n[Asset Check]")
    narr_available = {}
    for seg in SEGMENTS:
        p = NARR / seg["narr_file"]
        ok = p.exists() and p.stat().st_size > 1000
        narr_available[seg["n"]] = p if ok else None
        status = f"✓ REAL ({p.stat().st_size//1024}KB)" if ok else "⚠ SYNTHETIC"
        print(f"  Narration {seg['narr_file']}: {status}")

    music_ok = MUSIC.exists() and MUSIC.stat().st_size > 10000
    print(f"  Music: {'✓ REAL' if music_ok else '⚠ SYNTHETIC'}")
    char_ok = CHAR_IMG.exists() and CHAR_IMG.stat().st_size > 1000
    print(f"  Character image: {'✓ REAL' if char_ok else '⚠ PIL placeholder'}")

    # ── Calculate total duration ───────────────────────────────────────────
    print("\n[Scene Durations]")
    scene_durations = {}
    total_narr = 0
    for seg in SEGMENTS:
        narr_path = narr_available[seg["n"]]
        if narr_path:
            dur = get_duration(narr_path)
            dur = dur if dur > 1 else seg["est_dur"]
        else:
            dur = float(seg["est_dur"])
        scene_durations[seg["n"]] = dur
        total_narr += dur
        print(f"  Scene {seg['n']:2d}: {dur:.1f}s  [{seg['chapter']}]")

    total_dur = 6.0 + sum(1.8 for _ in SEGMENTS) + total_narr + 8.0
    print(f"\n  Total estimated: {total_dur:.0f}s ({total_dur/60:.1f} min)")

    # ── Generate music (full length) ───────────────────────────────────────
    print("\n[Music]")
    music_full = get_or_generate_music(total_dur + 10, WORK)
    print(f"  Music track: {music_full}")

    # ── Build each scene ───────────────────────────────────────────────────
    print("\n[Scene Assembly]")
    scene_clips = []

    for seg in SEGMENTS:
        n   = seg["n"]
        dur = scene_durations[n]
        print(f"\n  Scene {n}: {seg['chapter']} ({dur:.1f}s)")

        # 1. Chapter title card
        print(f"    Chapter card...")
        ch_card = make_chapter_title_card(seg, WORK, duration=1.8)

        # 2. Generate scene still
        print(f"    Scene still...")
        raw_still = make_scene_still(seg, WORK)

        # 3. Bake subtitles into still
        print(f"    Baking subtitles...")
        sub_still = bake_subtitle_onto_still(raw_still, seg, WORK)

        # 4. Apply camera motion
        motion_out = WORK / f"scene_{n:02d}_motion.mp4"
        print(f"    Camera [{seg['camera']}]...")
        apply_camera_motion(sub_still, motion_out, dur, seg["camera"])

        if not motion_out.exists():
            print(f"    WARN: motion failed, using static")
            motion_out = WORK / f"scene_{n:02d}_static.mp4"
            run([FFMPEG, "-y", "-loop", "1", "-i", str(sub_still),
                 "-t", str(dur), "-pix_fmt", "yuv420p",
                 "-vf", f"scale={W}:{H},fps={FPS}",
                 "-c:v", "libx264", "-preset", "fast", "-crf", str(CRF), str(motion_out)],
                "static_fallback")

        # 5. Generate SFX for scene
        print(f"    SFX [{seg['sfx_type']}]...")
        sfx_out = get_or_generate_sfx(seg["sfx_type"], seg["sfx_file"], dur, WORK)

        # 6. Extract music segment for scene
        music_seg = WORK / f"scene_{n:02d}_music.wav"
        if not music_seg.exists():
            offset = sum(scene_durations.get(k, 0) for k in range(1, n))
            run([FFMPEG, "-y", "-i", str(music_full),
                 "-ss", str(offset), "-t", str(dur),
                 "-ar", "44100", "-ac", "2", str(music_seg)],
                f"music_seg_{n}")

        # 7. Mix scene audio
        audio_out = WORK / f"scene_{n:02d}_audio.aac"
        print(f"    Audio mix...")
        mix_scene_audio(
            narr_available[n],
            sfx_out,
            music_seg,
            audio_out,
            dur,
        )

        # 8. Combine video + audio
        final_scene = WORK / f"scene_{n:02d}_final.mp4"
        if not final_scene.exists():
            if audio_out.exists():
                run([
                    FFMPEG, "-y",
                    "-i", str(motion_out),
                    "-i", str(audio_out),
                    "-c:v", "copy", "-c:a", "copy",
                    "-shortest",
                    str(final_scene),
                ], f"scene_{n}_mux")
            else:
                shutil.copy2(str(motion_out), str(final_scene))

        if not final_scene.exists():
            # Emergency fallback
            shutil.copy2(str(motion_out), str(final_scene))

        scene_clips.append(ch_card)
        scene_clips.append(final_scene)
        print(f"    ✓ scene {n} done")

    # ── Title sequence and end card ────────────────────────────────────────
    print("\n[Title + End Card]")
    title = make_title_sequence(WORK, 6.0)
    end   = make_end_card(WORK, 8.0)

    # Add final scene music to title/end
    # Add narration silence to title/end for consistent audio
    title_with_audio = WORK / "title_with_audio.mp4"
    if not title_with_audio.exists():
        music_title = WORK / "music_title.wav"
        run([FFMPEG, "-y", "-i", str(music_full), "-ss", "0", "-t", "6",
             "-ar", "44100", "-ac", "2", str(music_title)], "music_title_seg")
        if music_title.exists():
            run([FFMPEG, "-y", "-i", str(title), "-i", str(music_title),
                 "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                 "-map", "0:v", "-map", "1:a", "-shortest", str(title_with_audio)],
                "title_audio_mux")
        else:
            shutil.copy2(str(title), str(title_with_audio))

    end_with_audio = WORK / "end_with_audio.mp4"
    if not end_with_audio.exists():
        music_end = WORK / "music_end.wav"
        offset_end = total_narr + 6.0
        run([FFMPEG, "-y", "-i", str(music_full),
             "-ss", str(offset_end), "-t", "8",
             "-ar", "44100", "-ac", "2", str(music_end)], "music_end_seg")
        get_or_generate_sfx("victory_stinger", "triumphant_resolution.mp3", 8.0, WORK)
        if music_end.exists():
            run([FFMPEG, "-y", "-i", str(end), "-i", str(music_end),
                 "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                 "-map", "0:v", "-map", "1:a", "-shortest", str(end_with_audio)],
                "end_audio_mux")
        else:
            shutil.copy2(str(end), str(end_with_audio))

    # ── Concatenate all clips ──────────────────────────────────────────────
    print("\n[Final Assembly]")
    all_clips = [
        title_with_audio if title_with_audio.exists() else title,
        *scene_clips,
        end_with_audio if end_with_audio.exists() else end,
    ]
    final_clips = [c for c in all_clips if c.exists()]
    print(f"  Concatenating {len(final_clips)} clips...")

    concat_list = WORK / "concat_list.txt"
    with open(str(concat_list), "w") as f:
        for c in final_clips:
            f.write(f"file '{c}'\n")

    final_out = RENDERS / "thermopylae_final.mp4"
    ok = run([
        FFMPEG, "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-c", "copy", "-movflags", "+faststart",
        str(final_out),
    ], "final_concat")

    if final_out.exists():
        sz  = final_out.stat().st_size
        dur = get_duration(final_out)
        print(f"\n✓ SHIPPED: {final_out}")
        print(f"  Size: {sz/1024/1024:.1f} MB  |  Duration: {dur:.1f}s ({dur/60:.1f} min)")
        backups = RENDERS / "_backups"
        backups.mkdir(parents=True, exist_ok=True)
        import subprocess as _sp
        ts = _sp.run(["date", "-u", "+%Y%m%dT%H%M%SZ"], capture_output=True, text=True).stdout.strip()
        shutil.copy2(str(final_out), str(backups / "thermopylae_final.latest.mp4"))
        shutil.copy2(str(final_out), str(backups / f"thermopylae_final.{ts}.mp4"))
        print(f"  Backed up (3x)")
    else:
        print("\n✗ FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
    end_with_audio = WORK / "end_with_audio.mp4"
    if not end_with_audio.exists():
        music_end = WORK / "music_end.wav"
        offset_end = total_narr + 6.0
        run([FFMPEG, "-y", "-i", str(music_full),
             "-ss", str(offset_end), "-t", "8",
             "-ar", "44100", "-ac", "2", str(music_end)], "music_end_seg")
        get_or_generate_sfx("victory_stinger", "triumphant_resolution.mp3", 8.0, WORK)
        if music_end.exists():
            run([FFMPEG, "-y", "-i", str(end), "-i", str(music_end),
                 "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                 "-map", "0:v", "-map", "1:a", "-shortest", str(end_with_audio)],
                "end_audio_mux")
        else:
            shutil.copy2(str(end), str(end_with_audio))
    all_clips = [
        title_with_audio if title_with_audio.exists() else title,
        *scene_clips,
        end_with_audio if end_with_audio.exists() else end,
    ]
    final_clips = [c for c in all_clips if c.exists()]
    print(f"\n[Final Assembly] Concatenating {len(final_clips)} clips...")
    concat_list = WORK / "concat_list.txt"
    with open(str(concat_list), "w") as f:
        for c in final_clips:
            f.write(f"file '{c}'\n")
    final_out = RENDERS / "thermopylae_final.mp4"
    run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
         "-c", "copy", "-movflags", "+faststart", str(final_out)], "final_concat")
    if final_out.exists():
        sz = final_out.stat().st_size
        dur = get_duration(final_out)
        print(f"\nSHIPPED: {final_out.name}  {sz/1024/1024:.1f}MB  {dur:.0f}s")
        backups = RENDERS / "_backups"
        backups.mkdir(parents=True, exist_ok=True)
        import subprocess as _sp
        ts = _sp.run(["date", "-u", "+%Y%m%dT%H%M%SZ"], capture_output=True, text=True).stdout.strip()
        shutil.copy2(str(final_out), str(backups / "thermopylae_final.latest.mp4"))
        shutil.copy2(str(final_out), str(backups / f"thermopylae_final.{ts}.mp4"))
    else:
        print("FAILED"); sys.exit(1)

if __name__ == "__main__":
    main()
