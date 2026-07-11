"""
storyforge/merch.py — Empire OS Merch Asset Generator
Takes book cover → generates print-ready assets for every merch platform.
Outputs: storyforge/books/{slug}/merch/

Platforms covered:
  - Redbubble       (PNG 4500x5400 + 300 DPI variants)
  - Merch by Amazon (PNG 4500x5400 transparent + 15x18 shirt)
  - Printful/Etsy   (PNG 4500x5400 + mug, poster, phone case)
  - Spring          (PNG 5400x5400 square for social)
  - Poster (generic 24x36 @ 300 DPI)

Usage:
    python storyforge/merch.py --slug lost_battles_of_wwii
    python storyforge/merch.py --all
"""

from __future__ import annotations

import json
from pathlib import Path

BOOKS_DIR = Path(__file__).parent / "books"

# Platform specs: (name, width_px, height_px, dpi)
PLATFORM_SPECS: list[tuple[str, int, int, int]] = [
    ("redbubble_sticker",      2400, 2400, 150),
    ("redbubble_poster_a2",    4961, 7016, 300),
    ("merch_amazon_shirt",     4500, 5400, 300),
    ("merch_amazon_transparent", 4500, 5400, 300),
    ("printful_poster_18x24",  5400, 7200, 300),
    ("printful_mug_wrap",      3000, 1145, 150),
    ("spring_square",          5400, 5400, 300),
    ("etsy_listing",           2000, 2000, 150),
]


def generate_merch_assets(slug: str) -> Path:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("  [MERCH] Pillow not installed — run: pip install Pillow --break-system-packages")
        return Path()

    book_dir  = BOOKS_DIR / slug
    merch_dir = book_dir / "merch"
    merch_dir.mkdir(exist_ok=True)

    manifest_path = book_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"No manifest for '{slug}'")

    manifest  = json.loads(manifest_path.read_text(encoding="utf-8"))
    cover_src = Path(manifest.get("cover", ""))
    title     = manifest["title"]

    if not cover_src.exists():
        print(f"  [MERCH] Cover not found: {cover_src} — skipping")
        return merch_dir

    print(f"\n[MERCH] Generating assets for: {title}")
    base_img = Image.open(cover_src).convert("RGBA")

    for name, w, h, dpi in PLATFORM_SPECS:
        out_path = merch_dir / f"{name}.png"
        if out_path.exists():
            continue

        # Resize cover to fit within canvas, centered on white background
        canvas = Image.new("RGBA", (w, h), (255, 255, 255, 255))
        img    = base_img.copy()
        img.thumbnail((w, h), Image.LANCZOS)

        # Center on canvas
        x = (w - img.width)  // 2
        y = (h - img.height) // 2
        canvas.paste(img, (x, y), img if img.mode == "RGBA" else None)

        # Transparent version for MBA
        if "transparent" in name:
            canvas = img.copy()

        canvas.save(str(out_path), dpi=(dpi, dpi))
        print(f"  [MERCH] {name:35s} {w}x{h}px @ {dpi}dpi")

    # Update manifest
    manifest["merch_dir"] = str(merch_dir)
    manifest["status"]    = "merch_ready"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    asset_count = len(list(merch_dir.glob("*.png")))
    print(f"[MERCH] {asset_count} assets saved to {merch_dir}")
    return merch_dir


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--slug", default="")
    p.add_argument("--all",  action="store_true")
    args = p.parse_args()

    if args.all:
        for d in BOOKS_DIR.iterdir():
            if d.is_dir() and (d / "manifest.json").exists():
                generate_merch_assets(d.name)
    elif args.slug:
        generate_merch_assets(args.slug)
    else:
        print("Provide --slug <slug> or --all")
