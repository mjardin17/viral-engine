# Agent Coordination: Inventory → Commercials

Two autonomous agents that work together to turn Boss Listers inventory into commercials.

## Architecture

```
Boss Listers Inventory
        ↓
  [Crosslister Agent]  ← Monitors new items
        ↓
  Creates render missions
        ↓
  MISSION_BOARD.json
        ↓
  [Video Pipeline Agent]  ← Executes renders
        ↓
  Commercials (MP4s)
        ↓
  [Crosspost Bridge]  ← Queues for publishing
        ↓
  crosspost_queue.json
        ↓
  [Crosspost System]  ← Posts to all platforms
        ↓
  Instagram | TikTok | YouTube Shorts | Facebook
```

## How it works

### 1. Crosslister Agent
- **What:** Monitors Boss Listers inventory for new items
- **When:** Every 60 seconds
- **Action:** For each new item marked `for_sale`:
  - Generates a 30-second commercial render script
  - Creates a mission in `MISSION_BOARD.json`
  - Posts to `#commercials` channel in Buzz
  - Tells Video Pipeline Agent: "New commercial ready to render"

### 2. Video Pipeline Agent
- **What:** Monitors `MISSION_BOARD.json` for render jobs
- **When:** Every 30 seconds
- **Action:** For each `pending` mission:
  - Identifies if it's an episode or commercial
  - Executes render using `empire_render.py`
  - Posts progress to Buzz:
    - 🎬 Starting render
    - ✅ Complete (ready for social media)
    - ❌ Failed (with error details)

### 3. Buzz Relay (Coordinator)
- `#video-pipeline` channel: Episode renders, status
- `#commercials` channel: Product commercials, upload status
- Both agents post real-time status
- Humans can monitor, react, or intervene

## Running

### Start both agents:
```bash
START_AGENTS.bat
```

This opens two windows:
1. **Video Pipeline Agent** — Renders episodes & commercials
2. **Crosslister Agent** — Monitors inventory, queues commercials

### Monitor in Buzz:
- Open `http://localhost:3000` in browser
- Join `#commercials` channel
- Watch commercials get rendered in real-time

## Commercial Render Script

Each commercial is auto-generated with:

| Scene | Duration | Content |
|-------|----------|---------|
| 1 | 3s | Product title (text) |
| 2 | 8s | Product photos carousel |
| 3 | 6s | Description (TTS voice) |
| 4 | 5s | Price + "Buy Now" CTA |
| 5 | 8s | Photo loop + brand message |

**Total:** 30 seconds, suitable for:
- Instagram Reels
- TikTok
- YouTube Shorts
- Facebook Stories

## Mission Flow

```
Product in Boss Listers (for_sale=true)
    ↓
Crosslister Agent detects
    ↓
Creates mission: "commercial-<product_id>-<timestamp>"
    ↓
Adds to MISSION_BOARD.json (status: pending)
    ↓
Posts to #commercials: "📹 New commercial queued: Leather Jacket"
    ↓
Video Pipeline Agent polls and finds pending mission
    ↓
Posts to #commercials: "🎬 Rendering commercial: Leather Jacket ($89.99)"
    ↓
Executes: empire_render.py --script .temp_commercial_xxx.json
    ↓
Posts to #commercials: "✅ Commercial render complete"
    ↓
Posts: "📤 Ready for social media: Instagram, TikTok, YouTube Shorts, Facebook"
    ↓
Crosspost Agent picks up and publishes to all platforms
```

## Configuration

### Boss Listers Product Schema

Products should have:
```json
{
  "id": "jacket-001",
  "name": "Vintage Leather Jacket",
  "description": "Classic brown leather jacket, excellent condition",
  "price": 89.99,
  "images": ["url1", "url2", "url3"],
  "status": "for_sale",
  "create_commercial": true
}
```

Set `create_commercial: false` to skip commercial generation for a product.

### Buzz Channels

- `#video-pipeline` — Episode renders (existing)
- `#commercials` — Product commercials (new)

Both channels auto-created by agents on first run.

## Future Extensions

- [ ] Agent can accept commands from Buzz: "create commercial for item #42"
- [ ] Auto-publish commercials to social platforms after render
- [ ] A/B test different commercial styles (upbeat, luxury, budget, etc.)
- [ ] Integrate with inventory sync to auto-create commercials on warehouse updates
- [ ] Agent-to-agent negotiation ("Video Pipeline too busy, ask again in 30 min")

## Troubleshooting

**Agents not posting to Buzz:**
- Check `BUZZ_RELAY_URL=ws://localhost:3000` is set
- Check `BUZZ_PRIVATE_KEY` matches the keypair
- Verify relay is running: `docker ps | grep buzz-prod-relay`

**Commercials not rendering:**
- Check `empire_render.py` exists and works
- Check `MISSION_BOARD.json` is readable
- Check commercial scene count (should be 5 scenes, ~30s total)

**Inventory not detected:**
- Check `boss-listers-ai/data.json` exists
- Check products have `status: "for_sale"`
- Check `create_commercial` is not `false`
