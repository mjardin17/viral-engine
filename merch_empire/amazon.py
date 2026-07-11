"""
merch_empire/amazon.py — Merch by Amazon (MBA) Uploader
Playwright browser automation for MBA design uploads.

REQUIRES: MBA account approved at merch.amazon.com
REQUIRES: MBA_EMAIL and MBA_PASSWORD in .env

Usage:
    python merch_empire/amazon.py --design path/to/design.png --niche "Viking Warrior" --price 24.99
    python merch_empire/amazon.py --batch  # uploads all pending designs from TREND_BOARD.json
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass


EMAIL    = os.getenv("MBA_EMAIL", "")
PASSWORD = os.getenv("MBA_PASSWORD", "")

TREND_BOARD = ROOT / "merch_empire" / "TREND_BOARD.json"
UPLOAD_LOG  = ROOT / "merch_empire" / "MBA_UPLOAD_LOG.json"


def load_upload_log() -> dict:
    if UPLOAD_LOG.exists():
        return json.loads(UPLOAD_LOG.read_text(encoding="utf-8"))
    return {"uploaded": []}


def save_upload_log(log: dict) -> None:
    UPLOAD_LOG.write_text(json.dumps(log, indent=2), encoding="utf-8")


async def upload_design(
    design_path: str,
    niche: str,
    price: float = 24.99,
    color: str = "Black",
) -> bool:
    """Upload one design to Merch by Amazon via Playwright."""

    if not EMAIL or not PASSWORD:
        print("  ✗ Set MBA_EMAIL and MBA_PASSWORD in .env first")
        return False

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("  ✗ Run: pip install playwright && playwright install chromium")
        return False

    design_file = Path(design_path)
    if not design_file.exists():
        print(f"  ✗ Design file not found: {design_path}")
        return False

    print(f"\n  Uploading to MBA: {niche}")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)  # headless=False so Josh can see + handle CAPTCHAs
        page    = await browser.new_page()

        try:
            # ── Login ─────────────────────────────────────────────────────────
            print("  Logging in to merch.amazon.com...")
            await page.goto("https://merch.amazon.com/dashboard", timeout=30000)
            await page.wait_for_timeout(2000)

            # Amazon login flow
            if "signin" in page.url or "ap/signin" in page.url:
                await page.fill("#ap_email",    EMAIL)
                await page.click("#continue")
                await page.wait_for_timeout(1000)
                await page.fill("#ap_password", PASSWORD)
                await page.click("#signInSubmit")
                await page.wait_for_timeout(3000)

            # Check if 2FA / CAPTCHA appeared
            if "mfa" in page.url or "captcha" in page.url.lower():
                print("  ⚠  2FA or CAPTCHA detected — complete it in the browser, then press Enter here...")
                input("  > ")

            # ── Create new product ────────────────────────────────────────────
            print("  Navigating to create new product...")
            await page.goto("https://merch.amazon.com/designs/new", timeout=20000)
            await page.wait_for_timeout(2000)

            # Upload design file
            print("  Uploading design image...")
            upload_input = page.locator("input[type='file']").first
            await upload_input.set_input_files(str(design_file.resolve()))
            await page.wait_for_timeout(3000)

            # Fill product details
            # Title
            title = f"{niche} T-Shirt"
            await page.fill("input[name='title']", title)

            # Brand (use channel name or Empire OS)
            brand_input = page.locator("input[name='brand']")
            if await brand_input.count() > 0:
                await brand_input.fill("Empire Designs")

            # Description
            desc = (
                f"Premium {niche.lower()} design on a high-quality unisex t-shirt. "
                f"Perfect gift for fans of {niche.lower()}. "
                f"Available in multiple colors. Printed and shipped by Amazon."
            )
            await page.fill("textarea[name='description']", desc)

            # Bullet points (feature bullets)
            bullets = [
                f"Premium {niche} design",
                "Lightweight and comfortable",
                "Printed by Amazon — fast shipping",
            ]
            bullet_inputs = page.locator("input[name^='bullet']")
            count = await bullet_inputs.count()
            for i, bullet in enumerate(bullets[:count]):
                await bullet_inputs.nth(i).fill(bullet)

            # Price
            price_input = page.locator("input[name='price']")
            if await price_input.count() > 0:
                await price_input.fill(str(price))

            # Color selection — default Black
            try:
                color_checkbox = page.locator(f"label:has-text('{color}') input[type='checkbox']")
                if await color_checkbox.count() > 0:
                    await color_checkbox.click()
            except Exception:
                pass

            # Submit / Save Draft
            print("  Submitting design...")
            submit_btn = page.locator("button[type='submit']:has-text('Submit'), button:has-text('Publish')")
            if await submit_btn.count() > 0:
                await submit_btn.first.click()
                await page.wait_for_timeout(4000)

            print(f"  ✓ Uploaded: {title} @ ${price:.2f}")

            # Log the upload
            log = load_upload_log()
            log["uploaded"].append({
                "niche":       niche,
                "design_file": str(design_file),
                "price":       price,
                "title":       title,
                "status":      "submitted",
            })
            save_upload_log(log)
            return True

        except Exception as e:
            print(f"  ✗ Upload failed: {e}")
            return False
        finally:
            await page.wait_for_timeout(2000)
            await browser.close()


async def batch_upload(max_designs: int = 3) -> None:
    """Upload pending designs from TREND_BOARD.json."""
    if not TREND_BOARD.exists():
        print("  TREND_BOARD.json not found — run merch_empire/scanner.py first")
        return

    board  = json.loads(TREND_BOARD.read_text(encoding="utf-8"))
    log    = load_upload_log()
    done   = {u["niche"] for u in log.get("uploaded", [])}
    niches = [n for n in board.get("top_niches", []) if n["niche"] not in done]

    if not niches:
        print("  All niches already uploaded to MBA.")
        return

    print(f"\n  Uploading {min(max_designs, len(niches))} designs to MBA...")

    uploaded = 0
    for niche_data in niches[:max_designs]:
        niche       = niche_data["niche"]
        design_dir  = ROOT / "merch_empire" / "designs" / niche.replace(" ", "_")

        # Find the mba_shirt PNG if it exists
        design_file = design_dir / "mba_shirt.png"
        if not design_file.exists():
            print(f"  Skipping '{niche}' — no mba_shirt.png (run designer.py first)")
            continue

        ok = await upload_design(str(design_file), niche)
        if ok:
            uploaded += 1

    print(f"\n  Done — {uploaded} designs uploaded to Merch by Amazon")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Merch by Amazon Uploader")
    ap.add_argument("--design", default="",    help="Path to design PNG")
    ap.add_argument("--niche",  default="",    help="Niche/design name")
    ap.add_argument("--price",  default=24.99, type=float)
    ap.add_argument("--batch",  action="store_true", help="Upload all pending from TREND_BOARD")
    ap.add_argument("--max",    default=3,     type=int, help="Max designs per batch run")
    args = ap.parse_args()

    if not EMAIL or not PASSWORD:
        print("\n  ✗ Set MBA_EMAIL and MBA_PASSWORD in .env before running")
        print("  Run: python setup_wizard.py to add credentials")
        sys.exit(1)

    if args.batch:
        asyncio.run(batch_upload(args.max))
    elif args.design and args.niche:
        asyncio.run(upload_design(args.design, args.niche, args.price))
    else:
        print("  Usage: python merch_empire/amazon.py --batch")
        print("     or: python merch_empire/amazon.py --design file.png --niche 'Viking' --price 24.99")
