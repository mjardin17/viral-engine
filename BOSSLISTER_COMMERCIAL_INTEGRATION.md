# BossListers → Commercial Renderer Integration

Wire BossListers product listings into the viral-engine commercial rendering pipeline.

## Architecture

```
BossListers (Supabase)
    ↓
bosslister_commercial_feeder.py (fetches products, generates missions)
    ↓
MISSION_BOARD.json (job queue with type: "commercial")
    ↓
render_commercial.py (renders 30s vertical MP4)
    ↓
Output: 1080x1920 MP4 with Kokoro TTS narration
```

## Quick Start

### 1. Set Environment Variables

From BossListers `.env.local`:

```bash
export SUPABASE_URL=https://irslzufsqjveyibkfjtz.supabase.co
export SUPABASE_SERVICE_ROLE_KEY=<copy from BossListers .env.local>
```

### 2. Test Fetcher (Dry-Run)

See what ONE product would look like without saving:

```bash
python tools/bosslister_commercial_feeder.py --test
```

Output shows:
- Product fetched from Supabase
- 5 scenes in 30-second commercial
- Scene breakdown: title → showcase → description → price → product loop
- Audio: Kokoro TTS for description + price, upbeat music background

### 3. Queue All Products

Add all active products to the mission board:

```bash
python tools/bosslister_commercial_feeder.py --all
```

### 4. Queue Specific Product

Queue one product by SKU:

```bash
python tools/bosslister_commercial_feeder.py --sku NIKE-NIKEAIRM-NOSCAN
```

## Commercial Scene Structure

Each mission generates a 30-second vertical commercial with 5 scenes:

**Scene 1: Title (3s)**
- Product name on gradient background
- Sets brand identity

**Scene 2: Product Showcase (8s)**
- Product image with Ken Burns zoom effect
- Upbeat background music starts
- "Premium quality" caption

**Scene 3: Description (6s)**
- Product description as text overlay
- Kokoro TTS narration of full description
- Gold text color

**Scene 4: Price & CTA (5s)**
- Price displayed prominently
- "Available now on Boss Listers" text
- "Buy Now" CTA button
- TTS: "Only $X.XX"

**Scene 5: Product Loop (8s)**
- Continuous product image rotation
- Music fade-out
- Brand tagline: "Boss Listers: Curated, Affordable, Authentic"

## Output Formats

Renders produce three platform-specific outputs:

- **Instagram Feed:** 1080×1920 (vertical)
- **TikTok:** 9:16 (vertical native)
- **Instagram Reels:** 1:1 (square)

All exported as H.264 MP4 with Kokoro TTS audio.

## Workflow

1. **Fetch:** `bosslister_commercial_feeder.py --all`
   - Queries `public.products` from Supabase
   - Creates mission for each product with `lib/commercial_generator.py`
   - Adds to `MISSION_BOARD.json` with status "pending"

2. **Queue:** Missions sit in `MISSION_BOARD.json`
   - `mission_board.py list` shows all queued jobs
   - `mission_board.py next --claim` claims next pending mission

3. **Render:** `python render_commercial.py --script <mission.json>`
   - Reads render_script from mission
   - Executes scene-by-scene rendering
   - Uses `video_effects.py` primitives (proven from episode rendering)
   - Outputs MP4 at 1080x1920 / 30fps

4. **Publish:** (Manual step — reserved for Josh)
   - Review rendered output
   - Post to social platforms (Reels, TikTok, etc.)
   - Track engagement

## Command Reference

| Command | Purpose |
|---------|---------|
| `--test` | Dry-run with one product (no save) |
| `--all [--limit N]` | Queue all products (or first N) |
| `--sku SKU123` | Queue one specific product |

## Troubleshooting

**"SUPABASE_SERVICE_ROLE_KEY not set"**
- Copy `SUPABASE_SERVICE_ROLE_KEY` from BossListers `.env.local`
- Export before running: `export SUPABASE_SERVICE_ROLE_KEY=...`

**"No image found" (products skipped)**
- Check BossListers product has `image_url` set
- Images stored in `/uploads/` directory

**"Already queued"**
- Product's SKU already has a pending mission
- View board: `python mission_board.py list`

## Next Steps

1. Test one product: `python tools/bosslister_commercial_feeder.py --test`
2. Queue all: `python tools/bosslister_commercial_feeder.py --all`
3. Monitor: `python mission_board.py list`
4. Render: `python mission_board.py next --claim`
5. View output at path shown in mission status

## Notes

- BossListers products fetched from `public.products` table
- Each mission gets unique ID: `commercial-{SKU}-{timestamp}`
- Duplicates prevented (won't re-queue same SKU)
- Image URLs resolved to absolute paths for renderer
- Price formatting automatic ($X.XX)
- Product description used as-is in commercial narration
