"""
merch_empire/uploader.py — Empire OS Merch Auto-Uploader
Reads merch_empire/UPLOAD_QUEUE.json and uploads to all platforms automatically.

Platforms:
  - Redbubble    (Playwright browser automation)
  - Spring       (Playwright browser automation)
  - Printful     (REST API — needs PRINTFUL_API_KEY in .env)

Credentials go in .env (Josh adds them — never in code):
  REDBUBBLE_EMAIL, REDBUBBLE_PASSWORD
  SPRING_EMAIL, SPRING_PASSWORD
  PRINTFUL_API_KEY

Usage:
    python merch_empire/uploader.py
    python merch_empire/uploader.py --platform redbubble
    python merch_empire/uploader.py --platform printful
    python merch_empire/uploader.py --dry-run   # shows what would be uploaded, no action
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

MERCH_DIR = Path(__file__).parent
UPLOAD_Q  = MERCH_DIR / "UPLOAD_QUEUE.json"
LOG_FILE  = MERCH_DIR / "upload_log.json"


# ── Queue helpers ─────────────────────────────────────────────────────────────

def load_queue() -> dict:
    if not UPLOAD_Q.exists():
        print("[UPLOADER] No upload queue found — run pipeline.py first")
        sys.exit(0)
    return json.loads(UPLOAD_Q.read_text(encoding="utf-8"))


def save_queue(q: dict) -> None:
    UPLOAD_Q.write_text(json.dumps(q, indent=2), encoding="utf-8")


def load_log() -> list:
    if LOG_FILE.exists():
        return json.loads(LOG_FILE.read_text(encoding="utf-8"))
    return []


def save_log(log: list) -> None:
    LOG_FILE.write_text(json.dumps(log, indent=2), encoding="utf-8")


def log_result(slug: str, platform: str, status: str, url: str = "", error: str = "") -> None:
    log = load_log()
    log.append({
        "slug":      slug,
        "platform":  platform,
        "status":    status,
        "url":       url,
        "error":     error,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })
    save_log(log)


# ── Playwright setup ──────────────────────────────────────────────────────────

def get_browser(headless: bool = False):
    """Launch Playwright Chromium. headless=False so Josh can see it working."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[UPLOADER] Playwright not installed.")
        print("  Run: pip install playwright --break-system-packages")
        print("  Then: playwright install chromium")
        sys.exit(1)
    pw      = sync_playwright().start()
    browser = pw.chromium.launch(headless=headless, slow_mo=80)
    return pw, browser


# ── Redbubble uploader ────────────────────────────────────────────────────────

def upload_to_redbubble(design: dict, dry_run: bool = False) -> bool:
    """Upload one design (all variants) to Redbubble."""
    email    = os.getenv("REDBUBBLE_EMAIL", "")
    password = os.getenv("REDBUBBLE_PASSWORD", "")
    if not email or not password:
        print("  [REDBUBBLE] REDBUBBLE_EMAIL / REDBUBBLE_PASSWORD not in .env — skipping")
        return False

    niche      = design["niche"]
    design_dir = Path(design["design_dir"])
    manifest   = json.loads((design_dir / "manifest.json").read_text())

    # Find the redbubble main asset for first variant
    variants   = manifest.get("variants", [])
    if not variants:
        print(f"  [REDBUBBLE] No variants for {niche} — skipping")
        return False

    # Use the bold or vintage variant first
    chosen_variant = variants[0]
    asset_key      = "redbubble_main"
    asset_path     = chosen_variant.get("platforms", {}).get(asset_key, "")
    if not asset_path or not Path(asset_path).exists():
        print(f"  [REDBUBBLE] Asset not found: {asset_path}")
        return False

    if dry_run:
        print(f"  [REDBUBBLE] DRY RUN — would upload: {niche} from {asset_path}")
        return True

    print(f"  [REDBUBBLE] Uploading: {niche}")
    pw, browser = get_browser(headless=False)
    page = browser.new_page()

    try:
        # Login
        page.goto("https://www.redbubble.com/auth/login", timeout=30000)
        page.fill("input[name='credentials[username]']", email)
        page.fill("input[name='credentials[password]']", password)
        page.click("button[type='submit']")
        page.wait_for_url("**/dashboard**", timeout=20000)
        print("    [REDBUBBLE] Logged in")

        # Go to upload page
        page.goto("https://www.redbubble.com/portfolio/images/new", timeout=30000)
        page.wait_for_load_state("networkidle")

        # Upload file
        file_input = page.locator("input[type='file']").first
        file_input.set_input_files(str(asset_path))
        print("    [REDBUBBLE] File uploaded, waiting for processing...")
        time.sleep(5)
        page.wait_for_load_state("networkidle", timeout=60000)

        # Fill title
        title_field = page.locator("input[name='work[title]'], input[placeholder*='title' i]").first
        title_field.fill(f"{niche.title()} Design — Premium Quality")
        time.sleep(0.5)

        # Fill tags (Redbubble uses comma-separated tags)
        tags = f"{niche}, trending, {niche.replace(' ', ', ')}, gift, premium design"
        tag_field = page.locator("input[name='work[tag_field]'], input[placeholder*='tag' i]").first
        tag_field.fill(tags)
        time.sleep(0.5)

        # Enable all products
        enable_all = page.locator("text=Enable all products, a:has-text('Select all'), button:has-text('Enable all')")
        if enable_all.count() > 0:
            enable_all.first.click()
            time.sleep(1)

        # Submit
        submit = page.locator("input[type='submit'][value*='Save'], button:has-text('Save Work')").first
        submit.click()
        page.wait_for_load_state("networkidle", timeout=30000)

        current_url = page.url
        print(f"    [REDBUBBLE] Published: {current_url}")
        log_result(design["slug"], "redbubble", "success", url=current_url)
        return True

    except Exception as e:
        print(f"    [REDBUBBLE] Error: {e}")
        log_result(design["slug"], "redbubble", "error", error=str(e))
        return False
    finally:
        browser.close()
        pw.stop()


# ── Printful API uploader ─────────────────────────────────────────────────────

def upload_to_printful(design: dict, dry_run: bool = False) -> bool:
    """Upload product mockup to Printful store via API."""
    api_key = os.getenv("PRINTFUL_API_KEY", "")
    if not api_key:
        print("  [PRINTFUL] PRINTFUL_API_KEY not in .env — skipping")
        return False

    import requests as req

    niche      = design["niche"]
    design_dir = Path(design["design_dir"])
    manifest   = json.loads((design_dir / "manifest.json").read_text())
    variants   = manifest.get("variants", [])
    if not variants:
        return False

    # Use printful_poster asset
    asset_path = variants[0].get("platforms", {}).get("printful_poster", "")
    if not asset_path or not Path(asset_path).exists():
        print(f"  [PRINTFUL] Asset not found — skipping")
        return False

    if dry_run:
        print(f"  [PRINTFUL] DRY RUN — would upload: {niche}")
        return True

    print(f"  [PRINTFUL] Uploading file: {niche}")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
    }

    # Step 1: Upload file to Printful
    with open(asset_path, "rb") as f:
        files_resp = req.post(
            "https://api.printful.com/files",
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": (Path(asset_path).name, f, "image/png")},
            timeout=60,
        )

    if files_resp.status_code not in (200, 201):
        print(f"  [PRINTFUL] File upload failed: {files_resp.text[:200]}")
        log_result(design["slug"], "printful", "error", error=files_resp.text[:200])
        return False

    file_url = files_resp.json()["result"]["url"]
    print(f"    [PRINTFUL] File uploaded: {file_url}")

    # Step 2: Create product (Unisex Staple T-Shirt = variant 4011)
    product_payload = {
        "sync_product": {
            "name":         f"{niche.title()} — Empire Design",
            "thumbnail":    file_url,
        },
        "sync_variants": [
            {
                "variant_id": 4011,
                "retail_price": "24.99",
                "files": [{"url": file_url}],
            }
        ],
    }

    prod_resp = req.post(
        "https://api.printful.com/store/products",
        headers=headers,
        json=product_payload,
        timeout=30,
    )

    if prod_resp.status_code in (200, 201):
        result = prod_resp.json()["result"]
        print(f"    [PRINTFUL] Product created: ID {result['id']}")
        log_result(design["slug"], "printful", "success", url=str(result.get("id", "")))
        return True
    else:
        print(f"    [PRINTFUL] Product creation failed: {prod_resp.text[:200]}")
        log_result(design["slug"], "printful", "error", error=prod_resp.text[:200])
        return False


# ── Spring uploader ───────────────────────────────────────────────────────────

def upload_to_spring(design: dict, dry_run: bool = False) -> bool:
    """Upload design to Spring (Teespring) via browser automation."""
    email    = os.getenv("SPRING_EMAIL", "")
    password = os.getenv("SPRING_PASSWORD", "")
    if not email or not password:
        print("  [SPRING] SPRING_EMAIL / SPRING_PASSWORD not in .env — skipping")
        return False

    niche      = design["niche"]
    design_dir = Path(design["design_dir"])
    manifest   = json.loads((design_dir / "manifest.json").read_text())
    variants   = manifest.get("variants", [])
    if not variants:
        return False

    asset_path = variants[0].get("platforms", {}).get("spring_square", "")
    if not asset_path or not Path(asset_path).exists():
        print(f"  [SPRING] Asset not found — skipping")
        return False

    if dry_run:
        print(f"  [SPRING] DRY RUN — would upload: {niche}")
        return True

    print(f"  [SPRING] Uploading: {niche}")
    pw, browser = get_browser(headless=False)
    page = browser.new_page()

    try:
        page.goto("https://www.spri.ng/login", timeout=30000)
        page.fill("input[type='email']", email)
        page.fill("input[type='password']", password)
        page.click("button[type='submit']")
        page.wait_for_url("**/dashboard**", timeout=20000)

        page.goto("https://www.spri.ng/dashboard/listings/new", timeout=30000)
        page.wait_for_load_state("networkidle")

        # Upload design
        file_input = page.locator("input[type='file']").first
        file_input.set_input_files(str(asset_path))
        time.sleep(3)

        # Fill title
        page.fill("input[name='title']", f"{niche.title()} Design")

        # Click next / create
        next_btn = page.locator("button:has-text('Next'), button:has-text('Create'), button:has-text('Launch')").first
        next_btn.click()
        page.wait_for_load_state("networkidle", timeout=30000)

        url = page.url
        print(f"    [SPRING] Published: {url}")
        log_result(design["slug"], "spring", "success", url=url)
        return True

    except Exception as e:
        print(f"    [SPRING] Error: {e}")
        log_result(design["slug"], "spring", "error", error=str(e))
        return False
    finally:
        browser.close()
        pw.stop()


# ── Main runner ───────────────────────────────────────────────────────────────

PLATFORM_FUNCS = {
    "redbubble": upload_to_redbubble,
    "printful":  upload_to_printful,
    "spring":    upload_to_spring,
}


def run_uploader(platform_filter: str = "all", dry_run: bool = False) -> None:
    """Process all pending designs in the upload queue."""
    q        = load_queue()
    designs  = q.get("designs", [])
    pending  = [d for d in designs if d["status"] == "pending_upload"]

    if not pending:
        print("[UPLOADER] No pending designs in queue.")
        return

    print(f"\n[UPLOADER] {len(pending)} designs pending upload")
    if dry_run:
        print("[UPLOADER] DRY RUN MODE — no uploads will happen\n")

    for design in pending:
        niche     = design["niche"]
        platforms = design.get("platforms", list(PLATFORM_FUNCS.keys()))
        if platform_filter != "all":
            platforms = [p for p in platforms if p == platform_filter]

        print(f"\n[UPLOADER] Design: {niche}")
        results: dict[str, bool] = {}

        for plat in platforms:
            fn = PLATFORM_FUNCS.get(plat)
            if fn:
                results[plat] = fn(design, dry_run=dry_run)
            else:
                print(f"  [{plat.upper()}] No uploader for this platform yet")

        # Update queue status
        uploaded = [p for p, ok in results.items() if ok]
        failed   = [p for p, ok in results.items() if not ok]

        design["uploaded_to"] = uploaded
        design["failed_on"]   = failed
        design["status"]      = "uploaded" if uploaded else "failed"
        design["uploaded_at"] = datetime.utcnow().isoformat() + "Z"

    save_queue(q)

    succeeded = sum(1 for d in pending if d["status"] == "uploaded")
    print(f"\n[UPLOADER] Done — {succeeded}/{len(pending)} designs uploaded successfully")
    print(f"  Log: merch_empire/upload_log.json")


if __name__ == "__main__":
    import argparse
    # Load .env
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

    p = argparse.ArgumentParser(description="Empire OS Merch Uploader")
    p.add_argument("--platform", default="all", help="redbubble | printful | spring | all")
    p.add_argument("--dry-run",  action="store_true")
    args = p.parse_args()

    run_uploader(args.platform, args.dry_run)
