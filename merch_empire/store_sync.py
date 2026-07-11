"""
merch_empire/store_sync.py — Empire OS Store Catalog Generator
Pulls all merch product links from every platform and builds:
  1. catalog.json  — machine-readable product catalog for any website to consume
  2. store.html    — ready-to-embed HTML store widget (drop into any site)
  3. store_widget.js — JS snippet for embedding on website

Usage:
    python merch_empire/store_sync.py          # generate full catalog
    python merch_empire/store_sync.py --html   # also generate HTML store page
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

TREND_BOARD  = ROOT / "merch_empire" / "TREND_BOARD.json"
CATALOG_FILE = ROOT / "merch_empire" / "STORE_CATALOG.json"
STORE_HTML   = ROOT / "merch_empire" / "store_widget.html"
PRINTFUL_KEY = os.getenv("PRINTFUL_API_KEY", "")


# ── Platform URL builders ─────────────────────────────────────────────────────

def redbubble_url(username: str, niche: str) -> str:
    slug = niche.lower().replace(" ", "-").replace("'", "")
    return f"https://www.redbubble.com/shop/{username}/{slug}"


def spring_url(username: str, niche: str) -> str:
    slug = niche.lower().replace(" ", "-").replace("'", "")
    return f"https://www.bonfire.com/{username}"


def printful_product_url(product_id: str) -> str:
    return f"https://www.printful.com/dashboard/product/{product_id}"


# ── Printful catalog fetch ────────────────────────────────────────────────────

def fetch_printful_products() -> list[dict]:
    """Fetch all products from Printful store via API."""
    if not PRINTFUL_KEY:
        print("  No PRINTFUL_API_KEY — skipping Printful sync")
        return []

    try:
        import urllib.request
        url     = "https://api.printful.com/store/products"
        headers = {"Authorization": f"Bearer {PRINTFUL_KEY}"}
        req     = urllib.request.Request(url, headers=headers)

        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())

        products = []
        for item in data.get("result", []):
            products.append({
                "platform":   "printful",
                "id":         str(item.get("id", "")),
                "name":       item.get("name", ""),
                "thumbnail":  item.get("thumbnail_url", ""),
                "buy_url":    item.get("external_url") or f"https://printful.com",
                "price_usd":  None,  # price varies by variant
            })
        return products
    except Exception as e:
        print(f"  Printful fetch failed: {e}")
        return []


# ── Build catalog from TREND_BOARD ───────────────────────────────────────────

def build_catalog(
    redbubble_user: str = "EmpireDesigns",
    spring_user:    str = "EmpireDesigns",
) -> dict:
    """Build unified product catalog from all platforms."""

    catalog: dict = {
        "generated":  datetime.now().isoformat(),
        "store_name": "Empire OS Merch Store",
        "platforms":  ["redbubble", "spring", "printful", "amazon"],
        "products":   [],
    }

    # Load niches from TREND_BOARD
    niches: list[str] = []
    if TREND_BOARD.exists():
        board  = json.loads(TREND_BOARD.read_text(encoding="utf-8"))
        niches = [n["niche"] for n in board.get("top_niches", [])]

    # Load MBA upload log
    mba_log_file = ROOT / "merch_empire" / "MBA_UPLOAD_LOG.json"
    mba_uploads  = []
    if mba_log_file.exists():
        mba_log     = json.loads(mba_log_file.read_text(encoding="utf-8"))
        mba_uploads = mba_log.get("uploaded", [])

    # Load Printful products from API
    printful_products = fetch_printful_products()
    for p in printful_products:
        catalog["products"].append(p)

    # Build Redbubble + Spring + MBA links for each niche
    for niche in niches:
        design_dir  = ROOT / "merch_empire" / "designs" / niche.replace(" ", "_")
        preview_img = ""

        # Find preview image if it exists
        for fname in ["etsy_preview.png", "redbubble_main.png", "spring_square.png"]:
            candidate = design_dir / fname
            if candidate.exists():
                preview_img = str(candidate)
                break

        # Redbubble
        catalog["products"].append({
            "platform":     "redbubble",
            "niche":        niche,
            "name":         f"{niche} — T-Shirt, Sticker, Mug & More",
            "thumbnail":    preview_img,
            "buy_url":      redbubble_url(redbubble_user, niche),
            "price_usd":    19.99,
            "products_available": ["t-shirt", "hoodie", "sticker", "mug", "phone case", "art print"],
        })

        # Spring / Bonfire
        catalog["products"].append({
            "platform":  "spring",
            "niche":     niche,
            "name":      f"{niche} — Apparel",
            "thumbnail": preview_img,
            "buy_url":   spring_url(spring_user, niche),
            "price_usd": 24.99,
            "products_available": ["t-shirt", "hoodie", "tank top"],
        })

        # MBA (Amazon) — only if uploaded
        mba_entry = next((u for u in mba_uploads if u["niche"] == niche), None)
        if mba_entry:
            catalog["products"].append({
                "platform":  "amazon",
                "niche":     niche,
                "name":      mba_entry.get("title", f"{niche} T-Shirt"),
                "thumbnail": preview_img,
                "buy_url":   f"https://www.amazon.com/s?k={niche.replace(' ', '+')}+t-shirt",
                "price_usd": mba_entry.get("price", 24.99),
                "products_available": ["t-shirt"],
            })

    CATALOG_FILE.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    print(f"\n  ✓ Catalog saved: {CATALOG_FILE}")
    print(f"    {len(catalog['products'])} products across {len(catalog['platforms'])} platforms")
    return catalog


# ── HTML store widget ─────────────────────────────────────────────────────────

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Empire OS Merch Store</title>
  <style>
    :root {{
      --bg: #0a0a0a;
      --card: #111;
      --border: #222;
      --text: #eee;
      --accent: #ff4d4d;
      --sub: #888;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: var(--bg); color: var(--text); font-family: 'Segoe UI', sans-serif; }}
    .store-header {{
      text-align: center;
      padding: 40px 20px 20px;
    }}
    .store-header h1 {{
      font-size: 2rem;
      letter-spacing: 2px;
      text-transform: uppercase;
    }}
    .store-header p {{
      color: var(--sub);
      margin-top: 8px;
    }}
    .filters {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      justify-content: center;
      padding: 20px;
    }}
    .filter-btn {{
      background: var(--card);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 6px 16px;
      border-radius: 999px;
      cursor: pointer;
      font-size: 0.85rem;
      transition: all 0.2s;
    }}
    .filter-btn:hover, .filter-btn.active {{
      background: var(--accent);
      border-color: var(--accent);
      color: #fff;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 20px;
      padding: 20px 40px 60px;
      max-width: 1200px;
      margin: 0 auto;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      overflow: hidden;
      transition: transform 0.2s, border-color 0.2s;
    }}
    .card:hover {{
      transform: translateY(-4px);
      border-color: var(--accent);
    }}
    .card img {{
      width: 100%;
      aspect-ratio: 1;
      object-fit: cover;
      background: #222;
    }}
    .card-body {{
      padding: 14px;
    }}
    .card-platform {{
      font-size: 0.7rem;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: var(--accent);
      margin-bottom: 4px;
    }}
    .card-name {{
      font-size: 0.95rem;
      font-weight: 600;
      margin-bottom: 6px;
    }}
    .card-price {{
      color: var(--sub);
      font-size: 0.85rem;
      margin-bottom: 12px;
    }}
    .card-products {{
      font-size: 0.75rem;
      color: var(--sub);
      margin-bottom: 12px;
    }}
    .buy-btn {{
      display: block;
      text-align: center;
      background: var(--accent);
      color: #fff;
      text-decoration: none;
      padding: 8px 0;
      border-radius: 6px;
      font-weight: 600;
      font-size: 0.9rem;
      transition: opacity 0.2s;
    }}
    .buy-btn:hover {{ opacity: 0.85; }}
    .platform-amazon {{ color: #f90; }}
    .platform-redbubble {{ color: #e41b23; }}
    .platform-spring {{ color: #00c8e0; }}
    .platform-printful {{ color: #9b59b6; }}
    .empty {{ text-align: center; color: var(--sub); padding: 60px; }}
  </style>
</head>
<body>
  <div class="store-header">
    <h1>⚡ Empire OS Store</h1>
    <p>Official merch from the Empire OS channels — shipped by Amazon, Redbubble & more</p>
  </div>

  <div class="filters">
    <button class="filter-btn active" onclick="filterPlatform('all', this)">All</button>
    <button class="filter-btn" onclick="filterPlatform('amazon', this)">Amazon</button>
    <button class="filter-btn" onclick="filterPlatform('redbubble', this)">Redbubble</button>
    <button class="filter-btn" onclick="filterPlatform('spring', this)">Spring</button>
    <button class="filter-btn" onclick="filterPlatform('printful', this)">Printful</button>
  </div>

  <div class="grid" id="product-grid"></div>

  <script>
    const PRODUCTS = {products_json};

    function platformLabel(p) {{
      const map = {{
        amazon:    '🛒 Amazon',
        redbubble: '🎨 Redbubble',
        spring:    '👕 Spring',
        printful:  '📦 Printful',
      }};
      return map[p] || p;
    }}

    function renderGrid(products) {{
      const grid = document.getElementById('product-grid');
      if (!products.length) {{
        grid.innerHTML = '<div class="empty">No products yet — run the merch pipeline first.</div>';
        return;
      }}
      grid.innerHTML = products.map(p => `
        <div class="card" data-platform="${{p.platform}}">
          <img src="${{p.thumbnail || ''}}"
               onerror="this.style.background='#1a1a1a';this.removeAttribute('src')"
               alt="${{p.name}}">
          <div class="card-body">
            <div class="card-platform platform-${{p.platform}}">${{platformLabel(p.platform)}}</div>
            <div class="card-name">${{p.name}}</div>
            ${{p.price_usd ? `<div class="card-price">From $${p.price_usd.toFixed(2)}</div>` : ''}}
            ${{p.products_available ? `<div class="card-products">${{p.products_available.join(' · ')}}</div>` : ''}}
            <a href="${{p.buy_url}}" target="_blank" class="buy-btn">Shop Now →</a>
          </div>
        </div>
      `).join('');
    }}

    function filterPlatform(platform, btn) {{
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const filtered = platform === 'all' ? PRODUCTS : PRODUCTS.filter(p => p.platform === platform);
      renderGrid(filtered);
    }}

    renderGrid(PRODUCTS);
  </script>
</body>
</html>
"""


def generate_html(catalog: dict) -> None:
    products_json = json.dumps(catalog["products"], ensure_ascii=False)
    html          = HTML_TEMPLATE.replace("{products_json}", products_json)
    STORE_HTML.write_text(html, encoding="utf-8")
    print(f"  ✓ Store HTML: {STORE_HTML}")
    print(f"    Drop store_widget.html into any website or serve it standalone")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Empire OS Store Catalog Builder")
    ap.add_argument("--html",            action="store_true", help="Also generate HTML store widget")
    ap.add_argument("--redbubble-user",  default="EmpireDesigns")
    ap.add_argument("--spring-user",     default="EmpireDesigns")
    args = ap.parse_args()

    print("\n  Building Empire OS store catalog...")
    cat = build_catalog(args.redbubble_user, args.spring_user)

    generate_html(cat)  # always generate HTML

    print(f"\n  Files written:")
    print(f"    {CATALOG_FILE}")
    print(f"    {STORE_HTML}")
    print(f"\n  To link your website:")
    print(f"    → Copy store_widget.html into your site's public/ folder")
    print(f"    → Or iframe it:  <iframe src='store_widget.html' width='100%' height='800'></iframe>")
