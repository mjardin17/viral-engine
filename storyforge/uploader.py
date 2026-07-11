"""
storyforge/uploader.py — Empire OS Book Auto-Uploader
Reads storyforge/UPLOAD_QUEUE.json and publishes books to all platforms.

Platforms:
  - Amazon KDP     (Playwright browser automation)
  - Draft2Digital  (REST API — one call covers B&N, Apple, Kobo, Scribd, etc.)
  - Google Play    (Playwright browser automation)
  - Payhip         (REST API — your own store, 100% margin)

Credentials go in .env (Josh adds them — never in code):
  KDP_EMAIL, KDP_PASSWORD
  D2D_API_KEY
  PAYHIP_API_KEY
  GOOGLE_PLAY_EMAIL, GOOGLE_PLAY_PASSWORD

Usage:
    python storyforge/uploader.py
    python storyforge/uploader.py --platform kdp
    python storyforge/uploader.py --platform d2d
    python storyforge/uploader.py --dry-run
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

STORYFORGE = Path(__file__).parent
UPLOAD_Q   = STORYFORGE / "UPLOAD_QUEUE.json"
LOG_FILE   = STORYFORGE / "upload_log.json"


# ── Queue helpers ─────────────────────────────────────────────────────────────

def load_queue() -> dict:
    if not UPLOAD_Q.exists():
        print("[BOOK UPLOADER] No upload queue — run pipeline.py first")
        sys.exit(0)
    return json.loads(UPLOAD_Q.read_text(encoding="utf-8"))


def save_queue(q: dict) -> None:
    UPLOAD_Q.write_text(json.dumps(q, indent=2), encoding="utf-8")


def load_log() -> list:
    return json.loads(LOG_FILE.read_text()) if LOG_FILE.exists() else []


def save_log(log: list) -> None:
    LOG_FILE.write_text(json.dumps(log, indent=2), encoding="utf-8")


def log_result(slug: str, platform: str, status: str, url: str = "", error: str = "") -> None:
    log = load_log()
    log.append({
        "slug": slug, "platform": platform, "status": status,
        "url": url, "error": error,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })
    save_log(log)


# ── Playwright helper ─────────────────────────────────────────────────────────

def get_browser(headless: bool = False):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[UPLOADER] Run: pip install playwright --break-system-packages && playwright install chromium")
        sys.exit(1)
    pw      = sync_playwright().start()
    browser = pw.chromium.launch(headless=headless, slow_mo=100)
    return pw, browser


# ── Amazon KDP uploader ───────────────────────────────────────────────────────

def upload_to_kdp(book: dict, dry_run: bool = False) -> bool:
    """Upload eBook to Amazon KDP via browser automation."""
    email    = os.getenv("KDP_EMAIL", "")
    password = os.getenv("KDP_PASSWORD", "")
    if not email or not password:
        print("  [KDP] KDP_EMAIL / KDP_PASSWORD not in .env — skipping")
        return False

    epub_path = book.get("epub", "")
    if not epub_path or not Path(epub_path).exists():
        print(f"  [KDP] EPUB not found: {epub_path} — run formatter.py first")
        return False

    if dry_run:
        print(f"  [KDP] DRY RUN — would upload: {book['title']}")
        return True

    print(f"  [KDP] Uploading: {book['title']}")
    pw, browser = get_browser(headless=False)
    page = browser.new_page()

    try:
        # Login to KDP
        page.goto("https://kdp.amazon.com/en_US/", timeout=30000)
        page.click("a:has-text('Sign in')")
        page.wait_for_load_state("networkidle")
        page.fill("input[name='email']", email)
        page.click("input[id='continue']")
        page.wait_for_selector("input[name='password']", timeout=10000)
        page.fill("input[name='password']", password)
        page.click("input[id='signInSubmit']")
        page.wait_for_url("**/kdp.amazon.com/**", timeout=30000)
        print("    [KDP] Logged in")
        time.sleep(2)

        # Create new Kindle eBook
        page.goto("https://kdp.amazon.com/en_US/title-setup/kindle/new/details", timeout=30000)
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # Book title
        page.fill("input[id='data-print-book-title']", book["title"])
        time.sleep(0.3)

        # Subtitle
        if book.get("subtitle"):
            sub = page.locator("input[id='data-print-book-subtitle']")
            if sub.count():
                sub.fill(book["subtitle"])

        # Description
        desc_field = page.locator("textarea[id='data-print-book-description'], div[contenteditable='true']").first
        if desc_field.count():
            desc_field.fill(book.get("description", ""))
        time.sleep(0.3)

        # Keywords (7 boxes)
        keywords = book.get("keywords", "").split(",")[:7]
        for i, kw in enumerate(keywords):
            kw_field = page.locator(f"input[id='data-print-book-keywords-{i}']")
            if kw_field.count():
                kw_field.fill(kw.strip())

        # Save and continue
        page.click("input[id='save-announce'], button:has-text('Save and continue')")
        page.wait_for_load_state("networkidle", timeout=30000)
        time.sleep(2)

        # Upload EPUB
        upload_input = page.locator("input[type='file'][accept*='epub'], input[name='data-manuscript-file']").first
        if upload_input.count():
            upload_input.set_input_files(str(epub_path))
            print("    [KDP] EPUB uploading, waiting...")
            page.wait_for_load_state("networkidle", timeout=120000)
            time.sleep(5)

        # Save and continue to pricing
        page.click("input[id='save-announce'], button:has-text('Save and continue')")
        page.wait_for_load_state("networkidle", timeout=30000)

        # Set price $3.99 USD
        price_field = page.locator("input[id='data-print-book-marketplace-price-0'], input[name*='price']").first
        if price_field.count():
            price_field.fill("3.99")

        # Publish
        publish_btn = page.locator("button:has-text('Publish'), input[value*='Publish']").first
        if publish_btn.count():
            publish_btn.click()
            page.wait_for_load_state("networkidle", timeout=60000)

        url = page.url
        print(f"    [KDP] Submitted: {url}")
        log_result(book["slug"], "kdp", "success", url=url)
        return True

    except Exception as e:
        print(f"    [KDP] Error: {e}")
        log_result(book["slug"], "kdp", "error", error=str(e))
        return False
    finally:
        browser.close()
        pw.stop()


# ── Draft2Digital API uploader ────────────────────────────────────────────────

def upload_to_d2d(book: dict, dry_run: bool = False) -> bool:
    """
    Upload to Draft2Digital — distributes to B&N, Apple Books, Kobo, Scribd,
    Tolino, Vivlio, BorrowBox, and more in one API call.
    """
    api_key = os.getenv("D2D_API_KEY", "")
    if not api_key:
        print("  [D2D] D2D_API_KEY not in .env — skipping")
        return False

    epub_path = book.get("epub", "")
    if not epub_path or not Path(epub_path).exists():
        print(f"  [D2D] EPUB not found — skipping")
        return False

    if dry_run:
        print(f"  [D2D] DRY RUN — would distribute: {book['title']}")
        return True

    import requests as req
    print(f"  [D2D] Distributing: {book['title']}")

    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    # Upload EPUB file
    with open(epub_path, "rb") as f:
        upload_resp = req.post(
            "https://api.draft2digital.com/v1/books/upload",
            headers=headers,
            files={"file": (Path(epub_path).name, f, "application/epub+zip")},
            timeout=120,
        )

    if upload_resp.status_code not in (200, 201):
        print(f"    [D2D] Upload failed: {upload_resp.text[:300]}")
        log_result(book["slug"], "d2d", "error", error=upload_resp.text[:300])
        return False

    book_id = upload_resp.json().get("book_id") or upload_resp.json().get("id")
    print(f"    [D2D] Uploaded — book ID: {book_id}")

    # Set metadata
    meta_resp = req.put(
        f"https://api.draft2digital.com/v1/books/{book_id}",
        headers={**headers, "Content-Type": "application/json"},
        json={
            "title":       book["title"],
            "description": book.get("description", ""),
            "keywords":    book.get("keywords", "").split(",")[:7],
            "price":       3.99,
            "currency":    "USD",
            "language":    "en",
        },
        timeout=30,
    )

    # Publish to all channels
    pub_resp = req.post(
        f"https://api.draft2digital.com/v1/books/{book_id}/publish",
        headers=headers,
        json={"channels": "all"},
        timeout=30,
    )

    if pub_resp.status_code in (200, 201, 202):
        print(f"    [D2D] Published to all channels (B&N, Apple, Kobo, Scribd...)")
        log_result(book["slug"], "d2d", "success", url=str(book_id))
        return True
    else:
        print(f"    [D2D] Publish failed: {pub_resp.text[:200]}")
        log_result(book["slug"], "d2d", "error", error=pub_resp.text[:200])
        return False


# ── Payhip API uploader ───────────────────────────────────────────────────────

def upload_to_payhip(book: dict, dry_run: bool = False) -> bool:
    """Upload to Payhip — your own store, 100% margin (minus 5% Payhip fee)."""
    api_key = os.getenv("PAYHIP_API_KEY", "")
    if not api_key:
        print("  [PAYHIP] PAYHIP_API_KEY not in .env — skipping")
        return False

    pdf_path = book.get("pdf", "")
    if not pdf_path or not Path(pdf_path).exists():
        print(f"  [PAYHIP] PDF not found — skipping")
        return False

    if dry_run:
        print(f"  [PAYHIP] DRY RUN — would upload: {book['title']}")
        return True

    import requests as req
    print(f"  [PAYHIP] Uploading: {book['title']}")

    headers = {"Authorization": f"Bearer {api_key}"}

    with open(pdf_path, "rb") as f:
        resp = req.post(
            "https://payhip.com/api/v1/product",
            headers=headers,
            data={
                "title":       book["title"],
                "description": book.get("description", ""),
                "price":       "4.99",
                "currency":    "USD",
            },
            files={"file": (Path(pdf_path).name, f, "application/pdf")},
            timeout=120,
        )

    if resp.status_code in (200, 201):
        result = resp.json()
        url = result.get("link", "")
        print(f"    [PAYHIP] Live: {url}")
        log_result(book["slug"], "payhip", "success", url=url)
        return True
    else:
        print(f"    [PAYHIP] Failed: {resp.text[:200]}")
        log_result(book["slug"], "payhip", "error", error=resp.text[:200])
        return False


# ── Main runner ───────────────────────────────────────────────────────────────

PLATFORM_FUNCS = {
    "kdp":     upload_to_kdp,
    "d2d":     upload_to_d2d,
    "payhip":  upload_to_payhip,
}


def run_uploader(platform_filter: str = "all", dry_run: bool = False) -> None:
    q       = load_queue()
    books   = q.get("books", [])
    pending = [b for b in books if b["status"] == "pending_upload"]

    if not pending:
        print("[BOOK UPLOADER] No pending books in queue.")
        return

    print(f"\n[BOOK UPLOADER] {len(pending)} books pending upload")
    if dry_run:
        print("[BOOK UPLOADER] DRY RUN — no uploads\n")

    for book in pending:
        print(f"\n[BOOK UPLOADER] Book: {book['title']}")
        platforms = ["kdp", "d2d", "payhip"]
        if platform_filter != "all":
            platforms = [p for p in platforms if p == platform_filter]

        results: dict[str, bool] = {}
        for plat in platforms:
            fn = PLATFORM_FUNCS.get(plat)
            if fn:
                results[plat] = fn(book, dry_run=dry_run)
            time.sleep(2)

        uploaded = [p for p, ok in results.items() if ok]
        failed   = [p for p, ok in results.items() if not ok]
        book["uploaded_to"] = uploaded
        book["failed_on"]   = failed
        book["status"]      = "uploaded" if uploaded else "failed"
        book["uploaded_at"] = datetime.utcnow().isoformat() + "Z"

    save_queue(q)
    succeeded = sum(1 for b in pending if b["status"] == "uploaded")
    print(f"\n[BOOK UPLOADER] Done — {succeeded}/{len(pending)} books uploaded")
    print(f"  Log: storyforge/upload_log.json")


if __name__ == "__main__":
    import argparse
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

    p = argparse.ArgumentParser()
    p.add_argument("--platform", default="all", help="kdp | d2d | payhip | all")
    p.add_argument("--dry-run",  action="store_true")
    args = p.parse_args()
    run_uploader(args.platform, args.dry_run)
