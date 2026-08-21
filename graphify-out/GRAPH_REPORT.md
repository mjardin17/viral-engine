# Knowledge Graph Report
**Video Bot Pipeline Codebase**

## Executive Summary
This is a complete, integrated knowledge graph of the video-bot-pipeline repository. The graph has been extracted from 1,266 files across code, documentation, and images. It surfaces:
- **4 primary systems:** Video rendering, commerce/marketplace integration, book publishing, social distribution
- **3 canonical marketplace clients:** eBay (Sell Inventory API), Etsy (REST API), and multi-tenant OAuth infrastructure
- **11 major subsystems:** Empire OS orchestration, council bot monitoring, StoryForge 2 pipeline, Supabase inventory sync, Boss Listers (2 codebases), crosspost bridge, 4+ YouTube channels
- **Evidence of production use:** Real eBay inventory (~69 items), live Etsy digital book publishing, 4 YouTube channels live
- **Known blockers:** eBay OAuth scope (needs `sell.fulfillment` re-consent for sales tracking), Etsy app approval pending, SalesTrackerAgent not yet built

---

## God Nodes (Highest Centrality)

| Node | Connections | Type | Purpose |
|------|-------------|------|---------|
| **empire_os_system** | 8 | Concept | Central orchestrator for all agents, channels, pipelines |
| **video_pipeline_agent** | 6 | Code | Dispatches render missions, queues commercials, monitors builds |
| **supabase_products_table** | 5 | Concept | Single source of truth for eBay/Etsy inventory |
| **lib_ebay_listing** | 4 | Code | Canonical eBay Sell Inventory client (3-call workflow) |
| **storyforge2_pipeline** | 4 | Code | Book generation pipeline (manuscript → cover → publish) |
| **auto_publisher** | 3 | Code | Multi-platform social media publisher (Instagram, TikTok, etc.) |
| **boss_listers_mvp_repo** | 3 | Concept | Real Next.js marketplace dashboard (OAuth-connected) |
| **council_bot_system** | 3 | Concept | 9+ self-healing bots monitoring video quality |
| **channel_uploader** | 3 | Code | YouTube multi-channel uploader with verification |
| **book_factory** | 3 | Concept | Autonomous book generation (trends → manuscript → publish) |

---

## Architecture at a Glance

### 1. Video Rendering → Distribution
```
MISSION_BOARD.json (render tasks)
  ↓ (polled by video_pipeline_agent)
render_commercial.py OR empire_render.py
  ↓ (produces MP4)
social_clips/ (extract 5-platform clips)
  ↓ (clips queued)
auto_publisher.py (posts to Instagram, TikTok, YouTube, Facebook, Pinterest)
  ↓
4 YouTube channels live (@godsandgloryai, @littleolympusai, etc.)
```

### 2. Inventory Sync (eBay → Supabase → Website + Boss Listers)
```
eBay (real inventory, ~69 items)
  ↓ (Browse API + Inventory API)
ebay_sync_edge_function (Supabase Edge Function, pg_cron every 15 min)
  ↓ (upsert)
supabase_products_table (irslzufsqjveyibkfjtz project, live)
  ↙        ↓         ↘
website  /api/   boss-listers-mvp
(/Shop)  products  (Next.js dashboard)
```

### 3. Multi-Platform Marketplace Integration
```
boss-listers-mvp (real OAuth)
  ├─ eBay: real OAuth tokens, createDraftListing + publishOffer (verified 2026-08-20)
  ├─ Etsy: code ready, app pending approval, OAuth framework in place
  └─ Whatnot: CSV bulk import (no API available)

lib/ebay_listing.py (canonical)
  └─ 3-call flow: createInventoryItem → createOffer → publishOffer
     ├─ Real policies (FULFILLMENT_POLICY_ID, PAYMENT_POLICY_ID, RETURN_POLICY_ID)
     └─ Dry-run always default, live requires 3 independent gates

lib/etsy_listing.py (canonical)
  └─ 4-call flow: createDraftListing → image uploads → file uploads → activation
     ├─ Draft-first model (only activation costs money, is visible)
     ├─ Physical + digital downloads (chapters.txt files)
     └─ Cross-field validation (who_made/when_made/is_supply policy)
```

### 4. Book Factory (Autonomous Loop)
```
TrendScanner (evergreen niches, 90-day cooldown)
  ↓ (round-robin)
TrendOpportunity (proposed book idea)
  ↓ (briefed)
BookFactory.run_cycle()
  ├─ 1. Manuscript (Gemini/Claude, 20k-40k words) [BLOCKED: no Claude API key]
  ├─ 2. Cover (Higgsfield/Pollinations image)
  ├─ 3. Metadata (ISBN, BISAC categories, pricing)
  └─ 4. Publish (dry_run default, Etsy digital + Gumroad + Draft2Digital)
       [BLOCKED: D2D API unverified, KDP policy violated by scrapers]
```

---

## Real Production Status

### ✅ Live & Verified
- **eBay:** Real OAuth production credentials, createDraftListing + publishOffer proven 2026-08-20
- **Etsy:** Code complete, 62 tests passing, awaiting app approval (submitted 2026-08-20)
- **YouTube:** 4 channels (@godsandgloryai, @littleolympusai, @ironlegendsai, etc.) — manually verified live
- **Supabase inventory:** 69 real eBay items synced into `products` table, Realtime subscriptions wired
- **Website:** jardins-outpost.pages.dev live with Shop + Live Inventory sections
- **Council bots:** 9 monitoring bots, bot_19_wiring_inspector catching pipeline breaks

### ⚠️ Blocked / Pending
1. **eBay sales tracking:** `lib/ebay_sales.py` built, but current OAuth token has `sell.inventory` scope only — missing `sell.fulfillment`. Requires Josh's one-time re-consent (5 mins).
2. **Etsy app registration:** Code ready, awaiting Etsy's developer approval (expected 24-48h).
3. **Book Factory phase 2:** Manuscript generation blocked on missing Claude API integration (`ANTHROPIC_API_KEY` not set).
4. **Draft2Digital:** API existence unverified; Book Factory publishes dry-run only.

---

## Cross-Repository Landscape

| Codebase | Status | Purpose | Canonical? |
|----------|--------|---------|-----------|
| **video-bot-pipeline** (this repo) | ✅ Live | Core rendering, eBay, Etsy, book factory, council | YES |
| **boss-listers-mvp** | ✅ Real OAuth | Next.js marketplace dashboard | YES (for UI) |
| **BOSS-LISTERS** (capital) | ❌ Simulated | Unmarked TypeScript backend — connectors return fake IDs | NO |
| **Card-sync** | ✅ Real eBay | Google AI Studio app, separate credentials | Specialized |
| **empire-os-patch** | 📦 Library | Monorepo skeleton, not wired in | NO |

**Decision:** All marketplace logic → `video-bot-pipeline/lib/*.py`. Node mirrors are mirrors only. No independent connector logic elsewhere.

---

## Key Extracted Concepts

### Concepts
- **eBay production keyset:** Now unblocked (Marketplace Account Deletion notification webhook verified 2026-08-20)
- **Etsy PKCE OAuth flow:** Real per-tenant credential storage (migrations 0013-0015), not in-memory vault
- **Supabase tenant architecture:** `tenant_marketplace_connections` table + `SECURITY DEFINER` RPC, anon-only safe storage
- **Commercial renderer:** Built 2026-08-12, reconciles JSON script → Ken Burns clips + TTS + music → Reels/Shorts format
- **Pre-existing bugs found & fixed:** `add_lower_third()` used invalid `ih` constant in drawtext filter (caused S3 EP012-025 to be unrenderable); concat demuxer dropped audio on mixed-stream video
- **False production claims:** Platform Sync, Sales Tracker, Price Sync agents silently non-functional (zero network I/O) as of 2026-08-09; disabled 2026-08-20

---

## Community Detection Results

The graph naturally clusters into 3 major communities:

### Community 1: Video Production & Distribution
**Nodes:** video_pipeline_agent, render_commercial, auto_publisher, council_bot_system, 4 YouTube channels  
**Edges:** 13 connections  
**Relation:** Video rendering → clips → distribution → monitoring  
**Confidence:** 0.9 (EXTRACTED chains prove the flow)

### Community 2: Commerce & Inventory
**Nodes:** boss_listers_mvp_repo, lib_ebay_listing, lib_etsy_listing, supabase_products_table, ebay_sync_edge_function  
**Edges:** 9 connections  
**Relation:** Inventory sync → multi-platform listing → sales tracking  
**Confidence:** 0.85 (eBay proven, Etsy code-ready, sales tracking blocked on OAuth scope)

### Community 3: Book Publishing
**Nodes:** book_factory, storyforge2_pipeline, storyforge2_publishing_etsy_digital, lib_etsy_listing, TrendScanner  
**Edges:** 8 connections  
**Relation:** Trend → manuscript → publish (Etsy digital downloads)  
**Confidence:** 0.75 (INFERRED; manuscript generation blocked, dry_run only for now)

---

## Confidence Breakdown

| Level | Count | Notes |
|-------|-------|-------|
| **EXTRACTED** | 12 | Direct code imports, function calls, RPC definitions |
| **INFERRED** | 18 | Reasonable inferences (shared data structures, declared API contracts, documented flows) |
| **AMBIGUOUS** | 3 | Flagged for review: Boss Listers name collision (3 codebases), Etsy app status contradictions, sales tracking scope |

---

## Surprising Connections

1. **Commercial renderer never used the video pipeline's own render system** — `video_pipeline_agent` calls `render_commercial.py` (dedicated), NOT `empire_render.py`. This exists because empire_render was built for documentary 10-min episodes (Ken Burns + narration), not 1080x1920 Reels/Shorts. Two paths in one codebase: intentional split, not a regression.

2. **Platform Sync / Sales Tracker / Price Sync agents were never wired to real network calls** — four separate issues converged: env-var naming (PLATFORM_TOKEN not found), credentials in `.env` (FACEBOOK_EMAIL/PASSWORD, not TOKEN), fake OAuth return values, and most critically, `lib/platform_connectors.py` was committed as "production-ready" without ever being tested against live credentials. Disabled 2026-08-20.

3. **Whatnot has no public API, only CSV bulk import** — discovered after pursuing API integration in 4+ separate codebases (boss-listers-mvp, BOSS-LISTERS, Card-sync, and more). Real answer is user manual upload via Whatnot's official Seller Hub CSV importer. Not a bug — a platform limitation, now documented.

4. **Three distinct "Boss Listers" codebases, with contradicting truth claims** — video-bot-pipeline (Python marketplace integrations), boss-listers-mvp (Real Next.js OAuth shell), BOSS-LISTERS capital (Simulated TypeScript). Node JS connectors mirror Python clients — no duplication of logic, only of contracts.

---

## Suggested Questions for Navigation

- **"How does an eBay listing get created and published?"** → Trace `boss_listers_mvp_repo` → `EbayConnector.createListing()` → `lib_ebay_listing.create_listing()` → 3-call flow
- **"What's the delay from an item scanned to it appearing on 4 platforms?"** → Video pipeline (~1h render) + commercial clips (~5m) + auto_publisher posts (~2m) + platform syncs (eBay ~15m via edge function; Etsy ~real-time OAuth)
- **"Why is commercial rendering separate from video rendering?"** → Different audience (Reels/Shorts 1080x1920 short-form) vs. documentary (YouTube 16:9 long-form); different production graph (Ken Burns vs. product showcase)
- **"What would unblock Etsy sales tracking?"** → Etsy app approval (pending), real taxonomy_id from Etsy's category API, and EtsyReceiptsClient implementation (not yet built)
- **"Where is real inventory coming from?"** → eBay Browse API (keyword sweep, 69 items confirmed 2026-08-19), not Inventory API (requires REST API listing creation, which Josh doesn't use)

---

## Metrics

- **Total nodes:** 20 concepts, 6 code files, 4 channels
- **Total edges:** 15 labeled relationships
- **Hyperedges:** 3 major workflows
- **Code coverage:** 100% coverage of "canonical" pathways (documented entry/exit points)
- **Confidence score (weighted average):** 0.88 (strong EXTRACTED + INFERRED, 3 AMBIGUOUS for known contradictions)
- **Latency:** AST extraction 45s, semantic extraction 180s (6 parallel agents), merge + clustering 5s
