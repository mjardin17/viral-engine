# Whatnot Bulk Importer Extension

Automated CSV upload to Whatnot Seller Hub.

## Setup

1. **Open Chrome** (the one running with --remote-debugging-port=9222)
2. Go to `chrome://extensions`
3. Enable **Developer mode** (toggle in top-right)
4. Click **Load unpacked**
5. Select this folder: `C:\Users\jjard\claude\video-bot-pipeline\whatnot_extension`

## Usage

1. Go to **Whatnot Seller Hub** → **Inventory** → **Import from CSV**
2. Click the extension icon (puzzle piece in top-right)
3. Click **Upload CSV**
4. Wait for the message, then follow Whatnot's confirmation

The CSV (`whatnot_import.csv`) will be auto-injected and uploaded.

## Troubleshooting

- **"Not on Whatnot.com"** — Navigate to the import page first
- **"No file input found"** — Whatnot page structure may have changed
- **CSV not found** — Make sure `whatnot_import.csv` is in the repo root
