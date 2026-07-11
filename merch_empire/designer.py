"""
merch_empire/designer.py — Empire OS Merch Designer
Takes a trending niche → generates multiple design variations using AI image gen.
Outputs: merch_empire/designs/{niche_slug}/ — PNG files ready for each platform.

Usage:
    python merch_empire/designer.py --niche "vintage wolf"
    python merch_empire/designer.py --auto          # picks top trend from TREND_BOARD.json
    python merch_empire/designer.py --auto --count 5  # generate 5 trending designs
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import requests

MERCH_DIR   = Path(__file__).parent
DESIGNS_DIR = MERCH_DIR / "designs"
TREND_BOARD = MERCH_DIR / "TREND_BOARD.json"
DESIGNS_DIR.mkdir(exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0"}

# Design style prompts — applied on top of the niche keyword
STYLE_VARIANTS = [
    ("vintage",     "vintage retro distressed screen print style, worn texture, muted earth tones, 1970s aesthetic"),
    ("bold",        "bold graphic design, thick outlines, high contrast black and white, street art style"),
    ("minimalist",  "minimalist clean vector art, simple geometric shapes, flat design, white background"),
    ("watercolor",  "watercolor illustration, soft brushstrokes, artistic, painterly, vibrant colors"),
    ("dark_art",    "dark gothic artwork, dramatic lighting, detailed linework, black background, silver and gold accents"),
]

# Platform output specs: (name, width, height, dpi, bg_color)
PLATFORM_SPECS = [
    ("redbubble_main",     4500, 5400, 300, "white"),
    ("mba_shirt",          4500, 5400, 300, "transparent"),
    ("printful_poster",    5400, 7200, 300, "white"),
    ("spring_square",      5400, 5400, 300, "white"),
    ("etsy_preview",       2000, 2000, 150, "white"),
    ("mug_wrap",           3300, 1275, 150, "white"),
    ("hat_front",          2100, 1800, 150, "white"),
]


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:40]


def generate_design_image(niche: str, style_name: str, style_desc: str) -> bytes | None:
    """Generate a design using Pollinations AI (free)."""
    prompt = (
        f"T-shirt design, {niche}, {style_desc}, "
        "print on demand quality, transparent background, "
        "centered composition, no text unless part of design, "
        "high resolution, commercial use"
    )
    url = (
        f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}"
        "?width=2048&height=2048&nologo=true&enhance=true"
    )
    for attempt in range(3):
        try:
            resp = requests.get(url, timeout=60, headers=HEADERS)
            if resp.status_code == 200 and len(resp.content) > 5000:
                return resp.content
        except Exception as e:
            print(f"    [DESIGNER] Attempt {attempt+1} failed: {e}")
            time.sleep(3)
    return None


def resize_for_platform(src_bytes: bytes, name: str, w: int, h: int, dpi: int, bg: str) -> bytes | None:
    """Resize design to platform spec using Pillow."""
    try:
        from PIL import Image
        from io import BytesIO

        img    = Image.open(BytesIO(src_bytes)).convert("RGBA")
        img.thumbnail((w, h), Image.LANCZOS)

        if bg == "transparent":
            canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        else:
            canvas = Image.new("RGBA", (w, h), (255, 255, 255, 255))

        x = (w - img.width)  // 2
        y = (h - img.height) // 2
        canvas.paste(img, (x, y), img)

        out = BytesIO()
        canvas.save(out, format="PNG", dpi=(dpi, dpi))
        return out.getvalue()
    except Exception as e:
        print(f"    [DESIGNER] Resize failed for {name}: {e}")
        return None


def design_niche(niche: str, variants: int = 3) -> Path:
    """Generate N style variants for a niche, export all platform sizes."""
    slug       = slugify(niche)
    design_dir = DESIGNS_DIR / slug
    design_dir.mkdir(exist_ok=True)

    manifest_path = design_dir / "manifest.json"
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text())
        print(f"  [DESIGNER] Already designed: {niche} ({len(existing.get('variants',[]))} variants)")
        return design_dir

    print(f"\n[DESIGNER] Designing: {niche}")
    completed_variants = []

    for style_name, style_desc in STYLE_VARIANTS[:variants]:
        print(f"  [DESIGNER] Style: {style_name}")
        img_bytes = generate_design_image(niche, style_name, style_desc)
        if not img_bytes:
            print(f"    [DESIGNER] Failed to generate {style_name} — skipping")
            continue

        # Save raw source
        raw_path = design_dir / f"{style_name}_source.png"
        raw_path.write_bytes(img_bytes)

        # Resize for all platforms
        platform_files: dict[str, str] = {}
        for p_name, pw, ph, pdpi, pbg in PLATFORM_SPECS:
            resized = resize_for_platform(img_bytes, p_name, pw, ph, pdpi, pbg)
            if resized:
                out_path = design_dir / f"{style_name}_{p_name}.png"
                out_path.write_bytes(resized)
                platform_files[p_name] = str(out_path)
                size_kb = len(resized) // 1024
                print(f"    [DESIGNER] {p_name:25s} {pw}x{ph}  {size_kb}KB")

        completed_variants.append({
            "style":     style_name,
            "source":    str(raw_path),
            "platforms": platform_files,
        })
        time.sleep(2)

    # Save manifest
    manifest = {
        "niche":      niche,
        "slug":       slug,
        "variants":   completed_variants,
        "status":     "designed",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    total_files = sum(len(v["platforms"]) for v in completed_variants)
    print(f"\n[DESIGNER] Done — {len(completed_variants)} variants, {total_files} platform files")
    return design_dir


def auto_design(count: int = 1, variants: int = 3) -> list[Path]:
    """Auto-pick top N niches from TREND_BOARD and design them."""
    if not TREND_BOARD.exists():
        raise RuntimeError("TREND_BOARD.json not found — run scanner.py first")

    data   = json.loads(TREND_BOARD.read_text(encoding="utf-8"))
    niches = [n["niche"] for n in data["niches"][:count]]

    print(f"[DESIGNER] Auto-designing top {count} trending niches: {niches}")
    results = []
    for niche in niches:
        result = design_niche(niche, variants)
        results.append(result)
    return results


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--niche",    default="")
    p.add_argument("--auto",     action="store_true")
    p.add_argument("--count",    type=int, default=1,  help="How many top niches to design (auto mode)")
    p.add_argument("--variants", type=int, default=3,  help="Style variants per niche (max 5)")
    args = p.parse_args()

    if args.auto or not args.niche:
        auto_design(args.count, args.variants)
    else:
        design_niche(args.niche, args.variants)
