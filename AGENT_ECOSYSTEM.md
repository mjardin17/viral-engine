# Empire OS Agent Ecosystem

## Overview

Five autonomous agents orchestrating the complete video pipeline and inventory management system. All agents communicate via Buzz relay on a shared Nostr network.

```
                     BOSS LISTERS INVENTORY
                              │
                ┌─────────────┼─────────────┐
                │             │             │
           (items)         (items)      (prices)
                │             │             │
         ┌──────▼──────┐  ┌──▼──────┐  ┌──▼──────┐
         │ Crosslister │  │Platform │  │ Price   │
         │   Agent     │  │  Sync   │  │  Sync   │
         │             │  │ Agent   │  │ Agent   │
         └──────┬──────┘  └──┬──────┘  └──┬──────┘
                │            │            │
         (render jobs)   (synced)     (updated)
                │            │            │
                └──────┬─────┴────┬───────┘
                       │          │
                ┌──────▼──────┐   │
                │   Video     │   │
                │ Pipeline    │   │  RESALE PLATFORMS
                │  Agent      │   │  ├─ Poshmark
                │             │   │  ├─ Mercari
                └──────┬──────┘   │  ├─ Etsy
                       │          │  ├─ Depop
                  (MP4s ready)    │  └─ Grailed
                       │          │
         ┌─────────────┴─────┐    │
         │                   │    │
         ▼                   ▼    │
      Crosspost         Sales      │
      Queue             Tracker ───┘
         │               Agent
         │                │
    (→ Instagram)    (← sales data)
    (→ TikTok)       (update inventory)
    (→ YouTube)      (mark as sold)
    (→ Facebook)

         BUZZ RELAY (Coordinator)
    ┌─────────────────────────────┐
    │ #video-pipeline             │
    │ #commercials                │
    │ #inventory-sync             │
    └─────────────────────────────┘
```

## Agents

### 1. Video Pipeline Agent
**File:** `agents/video_pipeline_agent.py`

Renders video content for episodes and commercials.

**Triggers:**
- Polls `MISSION_BOARD.json` every 30 seconds
- Executes pending render missions

**Actions:**
- Calls `empire_render.py` with JSON script
- Detects output files (episode_{ep}_final.mp4, commercial_*.mp4)
- Posts progress to #video-pipeline
- Queues commercials for Crosspost

**Output:**
- Final MP4 files in `renders/` directory
- Buzz messages: 🎬 Rendering, ✅ Complete, ❌ Failed

---

### 2. Crosslister Agent
**File:** `agents/crosslister_agent.py`

Monitors Boss Listers inventory and queues commercials for new items.

**Triggers:**
- Polls `boss-listers-ai/data.json` every 60 seconds
- Detects items with `status="for_sale"` and `create_commercial=true`

**Actions:**
- Creates 30-second commercial render mission
- Adds to `MISSION_BOARD.json` with unique ID
- Posts to #commercials: "📹 New commercial queued"

**Output:**
- New entries in `MISSION_BOARD.json`
- Buzz messages: 📹 Commercial queued for [Product]

---

### 3. Platform Sync Agent
**File:** `agents/platform_sync_agent.py`

Pushes new inventory items to all resale platforms.

**Triggers:**
- Polls `boss-listers-ai/data.json` every 120 seconds
- Detects items with `status="for_sale"` not yet synced

**Actions:**
- Authenticates with each platform (Poshmark, Mercari, Etsy, etc.)
- Calls `connector.create_listing()` for each platform
- Tracks synced items in `crosslist_sync_state.json`
- Posts to #inventory-sync per platform

**Output:**
- Items listed on all platforms
- Buzz messages: 📤 Synced to platforms: Poshmark, Mercari, Etsy

---

### 4. Sales Tracker Agent
**File:** `agents/sales_tracker_agent.py`

Monitors platforms for sold items and updates Boss Listers inventory.

**Triggers:**
- Polls all platforms every 300 seconds (5 minutes)
- Fetches sales since last check

**Actions:**
- Calls `connector.get_sales()` on each platform
- Updates Boss Listers inventory: decrements quantity
- Marks items as `status="sold"` when quantity reaches zero
- Logs sales to `crosslist_sales.json`
- Posts to #inventory-sync per sale

**Output:**
- Updated inventory quantities in Boss Listers
- Buzz messages: 💸 Sale: [Product], Qty sold: N, Remaining: M

---

### 5. Price Sync Agent
**File:** `agents/price_sync_agent.py`

Syncs prices bidirectionally between Boss Listers and platforms.

**Triggers:**
- Polls `boss-listers-ai/data.json` every 300 seconds (5 minutes)
- Detects price changes since last check

**Actions:**
- Compares current vs. tracked prices
- Pushes price changes to all platforms
- Calls `connector.update_listing(listing_id, price=new_price)`
- Tracks price history in `price_sync_state.json`
- Posts to #inventory-sync per update

**Output:**
- Updated prices on all platforms
- Buzz messages: 💹 Price update: [Product], $X → $Y, Updated on: Poshmark, Mercari

---

## Communication

All agents post real-time status to Buzz channels:

| Channel | Purpose |
|---------|---------|
| `#video-pipeline` | Episode renders, render status |
| `#commercials` | Product commercial generation |
| `#inventory-sync` | Cross-platform syncing (Platform Sync, Sales Tracker, Price Sync) |

**Message format:** `[emoji] [Action]: [Details]`

Examples:
- 🎬 Rendering commercial: Leather Jacket ($89.99)
- ✅ Commercial render complete
- 📤 Synced to platforms: Poshmark, Mercari, Etsy
- 💸 Sale: Leather Jacket, Qty sold: 1, Remaining: 2
- 💹 Price update: Leather Jacket, $89.99 → $79.99

---

## Data Flow

### Commercial Pipeline

```
1. New item in Boss Listers
   └─ status: "for_sale"
   └─ create_commercial: true

2. Crosslister Agent detects
   └─ Creates render mission in MISSION_BOARD.json
   └─ Posts to #commercials

3. Video Pipeline Agent picks up
   └─ Executes empire_render.py
   └─ Generates commercial_xxx.mp4

4. Crosspost Bridge queues
   └─ Copies to social_clips/
   └─ Adds to crosspost_queue.json

5. Crosspost system publishes
   └─ Instagram Reels
   └─ TikTok
   └─ YouTube Shorts
   └─ Facebook
```

### Inventory Sync Pipeline

```
1. New item in Boss Listers
   └─ status: "for_sale"
   └─ sync_to_platforms: true (default)

2. Platform Sync Agent detects
   └─ Authenticates to each platform
   └─ Calls create_listing() for each
   └─ Tracks in crosslist_sync_state.json

3. Sales Tracker monitors
   └─ Polls platforms every 5 min
   └─ Fetches sales since last check
   └─ Updates Boss Listers quantity
   └─ Marks as sold when qty=0

4. Price Sync monitors
   └─ Polls Boss Listers every 5 min
   └─ Detects price changes
   └─ Pushes updates to all platforms
   └─ Maintains price_sync_state.json
```

---

## Running All Agents

```bash
START_AGENTS.bat
```

This opens 5 separate windows:
1. Video Pipeline Agent
2. Crosslister Agent
3. Platform Sync Agent
4. Sales Tracker Agent
5. Price Sync Agent

**Monitor in Buzz:**
```
http://localhost:3000
```

Join channels to watch real-time status:
- #video-pipeline
- #commercials
- #inventory-sync

---

## Configuration

### Agent Poll Intervals

| Agent | Interval | File |
|-------|----------|------|
| Video Pipeline | 30s | `MISSION_BOARD.json` |
| Crosslister | 60s | `boss-listers-ai/data.json` |
| Platform Sync | 120s | `boss-listers-ai/data.json` |
| Sales Tracker | 300s | All platforms |
| Price Sync | 300s | `boss-listers-ai/data.json` |

### Boss Listers Product Schema

```json
{
  "id": "jacket-001",
  "name": "Vintage Leather Jacket",
  "description": "Classic brown leather jacket",
  "price": 89.99,
  "quantity": 5,
  "images": ["url1", "url2", "url3"],
  "status": "for_sale",
  "create_commercial": true,
  "sync_to_platforms": true,
  "platform_listings": {
    "poshmark": "listing-123",
    "mercari": "listing-456",
    "etsy": "listing-789"
  }
}
```

### Environment Variables

```bash
# Buzz relay
BUZZ_RELAY_URL=ws://localhost:3000
BUZZ_PRIVATE_KEY=31a697cb1a00d32c0ef5ef7b03dee1567e24d7798cb225302864f886d2af0f04

# Platform API tokens
POSHMARK_TOKEN=<your-poshmark-api-key>
MERCARI_TOKEN=<your-mercari-api-key>
ETSY_TOKEN=<your-etsy-api-key>
```

---

## State Files

| File | Purpose | Agent |
|------|---------|-------|
| `MISSION_BOARD.json` | Render queue (episodes & commercials) | Video Pipeline |
| `crosslist_sync_state.json` | Tracks which items synced to platforms | Platform Sync |
| `crosslist_sales.json` | Sales history | Sales Tracker |
| `price_sync_state.json` | Price tracking for bidirectional sync | Price Sync |

---

## Platform Connectors

Base class: `lib/platform_connectors.py`

### Implemented

- **PoshmarkConnector** — Poshmark API (stub implementation, waiting for API docs)
- **MercariConnector** — Mercari API (stub implementation)
- **EtsyConnector** — Etsy API (stub implementation, OAuth2-ready)

### Planned

- **DepopConnector** — Depop API
- **GrailedConnector** — Grailed API
- **ShopifyConnector** — Shopify storefront
- **WooCommerceConnector** — WooCommerce

Each connector implements:
- `authenticate()` — Verify API credentials
- `create_listing()` — Create new listing
- `update_listing()` — Modify price, quantity, description
- `delist()` — Remove listing
- `get_sales()` — Fetch recent sales
- `get_inventory()` — Get all active listings

---

## Troubleshooting

### Agents not posting to Buzz
- Check `BUZZ_RELAY_URL=ws://localhost:3000` is set
- Verify relay is running: `docker ps | grep buzz-prod-relay`
- Check `BUZZ_PRIVATE_KEY` is correct

### Platform sync failing
- Verify `POSHMARK_TOKEN` / `MERCARI_TOKEN` / `ETSY_TOKEN` are set
- Check platform API documentation for auth format
- Look for "⚠️ Auth failed" in agent output

### Inventory not detected
- Check `boss-listers-ai/data.json` exists and is valid JSON
- Verify products have `status: "for_sale"`
- Check `create_commercial` / `sync_to_platforms` not explicitly false

### Sales not tracked
- Verify platforms are actually authenticated (agents log "✓ Authenticated")
- Check `Sales Tracker Agent` window for errors
- Sales are fetched every 5 minutes; wait and check again

### Price sync not working
- Check products have a `price` field
- Verify `Price Sync Agent` is detecting changes (log shows "💰 Price change:")
- Confirm platforms support `update_listing()` method

---

## Future Extensions

- [ ] Agent can accept commands from Buzz ("@agent sync item #42")
- [ ] Smart scheduling (e.g., sync on-demand for hot-selling items)
- [ ] Per-platform price adjustments (e.g., 5% markup on Etsy)
- [ ] Competitor price monitoring
- [ ] Automatic repricing based on demand
- [ ] Multi-warehouse inventory sync
- [ ] Agent health checks and auto-restart on failure
- [ ] Dashboard showing real-time agent status and KPIs

---

## Status

✅ All 5 agents implemented and ready to run
✅ Buzz relay integration complete
✅ Platform connector framework ready for API implementations
✅ State tracking for sales, prices, and sync status

**Next:** Implement actual platform API calls (Poshmark, Mercari, Etsy). The framework is production-ready; the connectors just need real API methods.

