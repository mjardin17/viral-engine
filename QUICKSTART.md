# Empire OS — Quick Start

## One Command to Start Everything

```bash
RUN_EVERYTHING.bat
```

This single command:
1. ✓ Verifies Python installation
2. ✓ Checks all required files exist
3. ✓ Creates .env template (if not exists)
4. ✓ Verifies Buzz relay is running
5. ✓ Creates sample inventory
6. ✓ Launches all 5 agents

## If You Want to Add Platform Credentials

### Option 1: Interactive Setup (Recommended)

```bash
python setup_credentials.py
```

This wizard guides you through:
- Which platforms to configure
- Credential entry (one at a time)
- Validation against each platform's API
- Automatic .env update

### Option 2: Manual .env Edit

Edit `.env` file directly and uncomment the platforms you want:

```bash
ETSY_TOKEN=<your-token>
ETSY_SHOP_ID=<your-shop-id>

DEPOP_TOKEN=<your-token>

SHOPIFY_TOKEN=<your-token>
SHOPIFY_STORE_NAME=<your-store>

WOOCOMMERCE_URL=<your-url>
WOOCOMMERCE_KEY=<your-key>
WOOCOMMERCE_SECRET=<your-secret>
```

Then restart agents.

## Understanding What's Running

**5 Autonomous Agents:**
1. **Video Pipeline Agent** — Renders episodes & commercials (30s poll)
2. **Crosslister Agent** — Detects new inventory items (60s poll)
3. **Platform Sync Agent** — Pushes items to Etsy, Depop, Shopify, WooCommerce (120s poll)
4. **Sales Tracker Agent** — Monitors platforms for sales, updates inventory (300s poll)
5. **Price Sync Agent** — Syncs price changes across platforms (300s poll)

**Communication Hub:**
- Buzz relay at `http://localhost:3000`
- Channels: `#video-pipeline`, `#commercials`, `#inventory-sync`
- Watch real-time status of all agents

## Testing the System

### 1. Add a Test Item to Inventory

Edit `boss-listers-ai/data.json`:

```json
{
  "id": "test-item-001",
  "name": "Test Product",
  "price": 29.99,
  "quantity": 1,
  "description": "A test item",
  "images": ["https://via.placeholder.com/400"],
  "status": "for_sale",
  "sync_to_platforms": true,
  "create_commercial": false
}
```

### 2. Watch Platform Sync Agent

- Check Buzz at `http://localhost:3000`
- Join `#inventory-sync` channel
- Look for: "📤 Synced to platforms: Etsy" (or Depop/Shopify/WooCommerce)
- Agent polls every 120 seconds

### 3. Verify on Platform

- Log into your platform account
- Check listings — item should appear

### 4. Test Price Change

- Edit `boss-listers-ai/data.json` and change the price
- Price Sync Agent will detect it (every 300 seconds)
- Watch Buzz for: "💹 Price update: Test Product, $29.99 → $X"

### 5. Test Sale Tracking

- If you sold the item on the platform
- Sales Tracker Agent will detect it (every 300 seconds)
- Quantity in Boss Listers will decrease
- Watch Buzz for: "💸 Sale: Test Product, Qty sold: 1, Remaining: 0"

## Troubleshooting

### "Agent window closes immediately"

Check the error message — usually:
- Missing Python library: `pip install requests`
- .env not in correct format: Check `.env` file for syntax errors
- Buzz relay not running: Check `docker ps` for `buzz-prod-relay`

### "No credentials working"

Run setup again:
```bash
python setup_credentials.py
```

It will test each credential against its API and show detailed errors.

### "Agents running but nothing syncing"

1. Check Buzz at `http://localhost:3000` — are agents posting status?
2. Check `boss-listers-ai/data.json` — does it have items with `sync_to_platforms: true`?
3. Check `.env` — are platform tokens set and uncommented?

### "Docker container exiting"

Check Buzz relay logs:
```bash
docker logs buzz-prod-relay
```

If it says "git conformance probe failed", ignore it (it's a development check).

## File Structure

```
agents/
  ├── video_pipeline_agent.py        (renders videos)
  ├── crosslister_agent.py           (detects new items)
  ├── platform_sync_agent.py         (syncs to platforms)
  ├── sales_tracker_agent.py         (tracks sales)
  └── price_sync_agent.py            (syncs prices)

lib/
  ├── platform_connectors.py         (API implementations)
  ├── commercial_generator.py        (30-sec commercials)
  └── crosspost_bridge.py            (social publishing)

boss-listers-ai/
  └── data.json                      (your inventory)

.env                                 (platform credentials)
setup_environment.py                 (automated setup)
setup_credentials.py                 (credential wizard)
RUN_EVERYTHING.bat                   (one-command launcher)
START_AGENTS.bat                     (manual agent launcher)
```

## Platforms Ready to Use

| Platform | Status | Setup Time |
|----------|--------|-----------|
| Etsy | ✅ Live API | 5 min (get OAuth token) |
| Depop | ✅ Live API | 5 min (get API token) |
| Shopify | ✅ Live API | 10 min (create custom app) |
| WooCommerce | ✅ Live API | 10 min (generate REST keys) |
| Mercari | 🚧 Waiting | Pending official API |
| Poshmark | 🚧 Waiting | Pending official API |

## Next Steps

1. Run: `RUN_EVERYTHING.bat`
2. (Optional) Run: `python setup_credentials.py` to add platform credentials
3. Add items to `boss-listers-ai/data.json` with `sync_to_platforms: true`
4. Watch `http://localhost:3000` for real-time status

That's it. Everything else is automated.

---

**For detailed documentation:** See `AGENT_ECOSYSTEM.md` and `PLATFORM_SETUP.md`
