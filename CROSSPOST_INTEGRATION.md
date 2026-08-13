# Crosspost Integration

## Full Workflow: Item → Commercial → Published

```
1. INVENTORY DETECTION
   └─ New item in Boss Listers (status: "for_sale")

2. COMMERCIAL GENERATION
   └─ Crosslister Agent detects (every 60s)
   └─ Creates render mission
   └─ Posts to #commercials: "📹 New commercial queued"

3. RENDERING
   └─ Video Pipeline Agent finds mission (every 30s)
   └─ Posts: "🎬 Rendering commercial..."
   └─ Executes: empire_render.py
   └─ Generates: commercial_xxx.mp4

4. QUEUEING FOR CROSSPOST
   └─ Video Pipeline Agent completes render
   └─ [Crosspost Bridge activates]
   └─ Copies MP4 to social_clips/
   └─ Adds entry to crosspost_queue.json
   └─ Posts: "📤 Queued for Crosspost"

5. SOCIAL PUBLISHING
   └─ Crosspost system reads crosspost_queue.json
   └─ auto_publisher.py picks up commercial
   └─ Publishes to:
      ├─ Instagram (feed + Reels)
      ├─ TikTok
      ├─ YouTube Shorts
      └─ Facebook

6. MONITORING
   └─ All status posted to #commercials channel
   └─ Humans can watch in real-time
   └─ Reactions/comments show engagement
```

## How Crosspost Integration Works

### Files Involved

| File | Purpose |
|------|---------|
| `lib/crosspost_bridge.py` | Routes commercials to Crosspost |
| `social_clips/` | Directory where Crosspost finds files |
| `crosspost_queue.json` | Queue of commercials to publish |
| `auto_publisher.py` | Existing Crosspost system (posts to all platforms) |

### Flow

1. **Video Pipeline Agent renders commercial**
   - Creates: `output/commercial_xxx.mp4`
   - Calls: `queue_commercial_for_posting()`

2. **Crosspost Bridge activates**
   - Copies MP4 to `social_clips/commercial_xxx_[timestamp].mp4`
   - Creates queue entry in `crosspost_queue.json`:
     ```json
     {
       "id": "commercial-jacket-001",
       "type": "commercial",
       "file": "social_clips/commercial_jacket_001_1723234567.mp4",
       "platforms": ["instagram", "tiktok", "youtube_shorts", "facebook"],
       "status": "queued",
       "caption_template": "🛍️ Check out this Leather Jacket!..."
     }
     ```

3. **Crosspost system picks it up**
   - Watches `crosspost_queue.json`
   - Calls `auto_publisher.py` for each platform
   - Publishes to all social accounts

4. **Status updates in Buzz**
   - Posts to `#commercials` channel
   - "📤 Queued for Crosspost"
   - "🚀 Crosspost will publish automatically"

## Running It All

```bash
START_AGENTS.bat
```

Then monitor in Buzz:
- Open `http://localhost:3000`
- Join `#commercials` channel
- Watch items get turned into commercials and published

## Configuration

### Crosspost platforms

Edit `lib/crosspost_bridge.py` line 26:
```python
platforms = ["instagram", "tiktok", "youtube_shorts", "facebook"]
```

### Caption template

Edit line 58 in `lib/crosspost_bridge.py` to customize how commercials are captioned on social media.

## Files Created

```
lib/
  └─ crosspost_bridge.py       (new - routes to Crosspost)

agents/
  ├─ video_pipeline_agent.py   (updated - calls Crosspost Bridge)
  └─ crosslister_agent.py      (no changes needed)
```

## Status

⚠️ **THE DOC ABOVE DESCRIBES THE INTENT, NOT THE CURRENT STATE.**
Audited 2026-08-12. The chain does not connect. Do not trust the flow diagram
above until this block says otherwise.

There are **three disconnected publish paths** in this repo, built by three
separate sessions that never reconciled:

| # | File | Writes | Consumer | State |
|---|------|--------|----------|-------|
| 1 | `lib/crosspost_bridge.py:13` | `crosspost_queue.json` (a FILE) | ✅ `process_queue()` (added 2026-08-12) | **FIXED** |
| 2 | `crosspost_bridge.py:28` (root) | `crosspost_queue/` (a DIRECTORY) → POSTs to external SaaS via `crosspost_api_url` | `crosspost_config.json` never filled in | dead branch |
| 3 | `social_clips/auto_publisher.py` | the real per-platform functions | — | all 4 platforms are `TODO(api)` |

Neither `crosspost_queue.json` nor `crosspost_queue/` exists on disk — meaning
**no commercial has ever completed this loop, not once.**

### What actually works
- ✅ Photo → listing (`/capture`, `/card-scan` in boss-listers-mvp)
- ✅ Listing → commercial JSON (verified: `.temp_commercial_*.json` are well-formed)
- ⚠️ Commercial JSON → MP4 — **untested with real photos**; the only test run used
  `via.placeholder.com` images, not real product shots
- ❌ MP4 → queue — broken (paths #1/#2 above)
- ❌ Queue → social — not implemented (see below)

### auto_publisher.py is NOT "just missing tokens"
This is the most expensive misconception in this repo. Every platform is
**unimplemented**, not merely unconfigured:

| Line | Platform | Actual state |
|------|----------|--------------|
| `auto_publisher.py:168` | Instagram | `TODO(api): implement container create + publish` |
| `auto_publisher.py:186` | TikTok | `TODO(api): implement init + chunked upload` |
| `auto_publisher.py:204` | Facebook | `TODO(api): implement page video upload` |
| `auto_publisher.py:227` | Pinterest | `TODO(api): implement /v5/pins POST` |

With the token **present**, `publish_instagram` returns
`"IG_ACCESS_TOKEN present but Graph API call not yet implemented"`.
Adding tokens to `.env` will not make these post. The HTTP calls must be written.

### ✅ Wiring FIXED 2026-08-12 — path #1 → path #3
`lib/crosspost_bridge.py` gained **`process_queue()`**, the consumer that never
existed. It reads `crosspost_queue.json` and dispatches each item to the
`auto_publisher.py` platform functions. Path #2's external-SaaS design was never
finished and is deliberately NOT built on.

**Run it:**
```bash
# always dry-run first — publishing is irreversible
python lib/crosspost_bridge.py process --dry-run
python lib/crosspost_bridge.py process
python lib/crosspost_bridge.py list      # per-platform status of every item
```

**Safety design.** Instagram has no unpublish API, so "never double-post" outranks
throughput:

| Property | Mechanism |
|---|---|
| IG success + TikTok failure won't re-post IG | per-**platform** results, not per-item |
| Crash mid-post never silently re-posts | platform marked `posting` **before** the attempt; on restart that state is **quarantined** for a human, never auto-retried |
| Crash mid-write can't corrupt state | atomic queue writes (temp file + `os.replace`) |
| Two agents polling can't both post | `O_EXCL` lock file, stale locks reclaimed after 30 min |
| Corrupt queue can't cause a re-post | `_load_queue()` raises instead of falling back to empty |

**Tested** (`ALL PASS`, 14 assertions): producer→consumer visibility, idempotency
after `posted`, quarantine after simulated crash, lock rejection, corrupt-queue
refusal, atomic write leaves no partial file. Nothing was posted — dry-run only.

⚠ A quarantined platform means a previous run died mid-publish and **we cannot
tell whether it went live.** Check the account manually, then edit
`results[<platform>].status` in `crosspost_queue.json` to `posted` or `failed`.

### Hard prerequisites before Instagram can work at all
- Instagram account must be **Business or Creator** linked to a Facebook Page.
  Personal accounts cannot use the Content Publishing API under any conditions.
- Meta fetches the video from a **public HTTPS URL** — a local file in
  `social_clips/` cannot be handed to the API. Needs hosting (Supabase Storage
  is the obvious candidate; the project already runs Supabase).
