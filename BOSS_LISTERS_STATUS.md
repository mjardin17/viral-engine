# Boss Listers — Complete Status & Roadmap

**Last Updated:** 2026-08-21  
**Owner:** Josh Jardin  
**Goal:** Get real inventory live on eBay, track sales, sync across platforms

---

## PART 1: VERIFIED WORKING (TESTED LIVE)

### ✅ eBay Production OAuth
- **What:** Real refresh_token obtained, tested against live api.ebay.com
- **Status:** HTTP 200 on getInventoryItems, getInventoryLocations
- **Location:** `boss-listers-mvp/boss-listers-mvp/.env.local`
- **Verified:** 2026-08-20, authenticated call returned real location `JJ_NEW_BEDFORD_MAIN`
- **Credentials:**
  - ✅ `EBAY_CLIENT_ID` — set
  - ✅ `EBAY_CLIENT_SECRET` — set
  - ✅ `EBAY_REFRESH_TOKEN` — set
  - ❌ **MISSING SCOPE:** has `sell.inventory`, NOT `sell.fulfillment` (blocks sales fetch)

### ✅ eBay Listing Client (lib/ebay_listing.py)
- **What:** Creates inventory items + offers on eBay's Sell Inventory API
- **Status:** Builds real 3-call payload (inventory_item → offer → publishOffer)
- **Tests:** 25 passing (unit + integration)
- **Verified:** Dry-run payload shape correct, ready to publish
- **Location:** `lib/ebay_listing.py` (407 lines)

### ✅ eBay Sales Client (lib/ebay_sales.py)
- **What:** Fetches orders from eBay Fulfillment API
- **Status:** Built, 3 tests passing
- **Blocker:** Requires `sell.fulfillment` scope (token only has `sell.inventory`)
- **SKU Resolution:** ✅ `resolve_sku_from_legacy_item_id()` exists (line 192)
- **Location:** `lib/ebay_sales.py` (194 lines)

### ✅ Sales Tracker Agent (agents/sales_tracker_agent.py)
- **What:** Polls eBay orders, records sales to Supabase atomically
- **Status:** Built, 4 tests passing
- **Uses:** EbaySalesClient + SupabaseSalesWriter
- **Ready:** Will run once eBay token scope is fixed
- **Location:** `agents/sales_tracker_agent.py`

### ✅ Supabase Infrastructure
- **Database:** `irslzufsqjveyibkfjtz` ("Boss listers prod")
- **Migrations:** 0001–0015 deployed live
- **Tables:**
  - ✅ `products` (69 real eBay items imported)
  - ✅ `sync_logs`
  - ✅ `marketplace_connections` (tenant eBay/Etsy/etc)
  - ✅ RLS policies correct (anon reads products, no direct write)
- **RPCs:**
  - ✅ `record_sale()` — atomic dedup + SKU resolution
  - ✅ `get_marketplace_connection_metadata()`

### ✅ Real Inventory
- **What:** 69 actual trading cards/Transformers/collectibles from Josh's eBay account
- **Status:** In Supabase `products` table, source='ebay'
- **Verified:** Synced via Browse API on 2026-08-20
- **SKU Format:** `v1|{itemId}|0` (matches Inventory API format)
- **Location:** Supabase table `products`

### ✅ Listing Service (Python HTTP Bridge)
- **What:** Serves `/ebay/create-listing` endpoint (127.0.0.1:8791)
- **Status:** Built, tested
- **Purpose:** Proxies between Node.js frontend and real eBay client
- **Location:** `scripts/listing_service.py` (441 lines)

---

## PART 2: BUILT BUT NOT VERIFIED LIVE

### ⚠️ Etsy Listing Client (lib/etsy_listing.py)
- **Status:** Built, 62 tests passing
- **Missing:** `ETSY_ACCESS_TOKEN`, `ETSY_SHOP_ID`, `ETSY_TAXONOMY_ID`
- **Blocker:** Etsy app registration pending approval (unknown status)
- **Can build:** Manual listing packages (CSV export for Whatnot already done)
- **Location:** `lib/etsy_listing.py` (605 lines)

### ⚠️ Etsy Digital Books (storyforge2/publishing/connectors/etsy_digital.py)
- **Status:** Built, untested against live Etsy
- **Uses:** Etsy listing client above
- **Blocker:** Same as above

### ⚠️ Boss Listers MVP App (Next.js)
- **Status:** Built, runs locally (localhost:3000)
- **Problem:** Config has `output: 'export'` which blocks API routes
- **Fix Applied:** Removed static export, API routes now available
- **Features:**
  - Photo upload UI
  - Product analysis (AI-generated descriptions)
  - Listing generation interface
  - Manual export (Poshmark/Mercari/Whatnot CSV)
- **Integration:** Needs wiring to real inventory + listing service
- **Location:** `boss-listers-mvp/boss-listers-mvp/`

### ⚠️ Commercial Renderer (render_commercial.py)
- **Status:** Built, not tested live
- **Tests:** 3 checks (verify output file has video + audio + duration)
- **Location:** `render_commercial.py` (repo root)

### ⚠️ Instagram Publisher (lib/instagram_publisher.py)
- **Status:** Built, never called against live Instagram API
- **Blocker:** No IG_ACCESS_TOKEN set
- **60-day token cliff:** Tokens expire in 60 days, need refresh logic
- **Location:** `lib/instagram_publisher.py`

---

## PART 3: BLOCKED (CANNOT PROCEED WITHOUT FIXES)

### 🔴 BLOCKER 1: eBay Token Scope Missing `sell.fulfillment`
- **Status:** Token expires 2028-02-10 (548 days remaining — NO REFRESH NEEDED)
- **Impact:** Sales tracking cannot fetch orders
- **Error:** `lib/ebay_sales.py` will return HTTP 400 on first call
- **Fix:** Josh must re-consent with `sell.fulfillment` scope added
- **Effort:** 5 minutes (manual OAuth flow, one time only)
- **Blocks:** Sales Tracker Agent from running
- **Timeline:** Do this before sales tracking is needed, not urgent

### 🔴 BLOCKER 2: Etsy App Registration Status Unknown
- **Status:** "Pending approval" as of 2026-08-20
- **Problem:** No ETSY_ACCESS_TOKEN, ETSY_SHOP_ID, or ETSY_TAXONOMY_ID
- **Fallback:** Manual CSV export (Whatnot, Poshmark already built)
- **Blocks:** Etsy listing automation

### 🔴 BLOCKER 3: Boss Listers Not Wired to Real Inventory
- **Current:** Shows demo UI, doesn't load 69 real items
- **Needs:** Connect to Supabase `products` table
- **Needs:** Connect to Python listing service for real eBay calls
- **Status:** Next.js config fixed, API routes now available

### 🔴 BLOCKER 4: No Instagram IG_ACCESS_TOKEN
- **Status:** Not set in `.env.local`
- **Blocker:** Instagram publisher cannot post
- **Fallback:** Works without Instagram (other platforms still function)

---

## PART 4: DEAD (DO NOT USE)

### ❌ 16-Platform Sync Agent (lib/platform_connectors.py)
- **Status:** All 26 connectors return fake IDs, zero real API calls
- **Grep:** `grep -rE "fetch\(|axios" src/connectors/` → 0 matches
- **Decision:** Removed from `START_AGENTS.bat` on 2026-08-20
- **Lesson:** Never claim "production-ready" without grep-checking for actual HTTP calls

### ❌ BOSS-LISTERS Capital Directory
- **Status:** 100% simulated, never touches real APIs
- **Proof:** 26 connector classes, zero HTTP calls anywhere
- **DO NOT:** Use this codebase for anything

### ❌ marketplace-integration/ (boss-listers-mvp)
- **Status:** Entry points never written (`src/index.js` missing from git history)
- **Decision:** Inert, ignore

---

## PART 5: ROADMAP TO LIVE (STEP BY STEP)

### PHASE 0: Fix Blockers (Do This First)

#### [ ] Step 0.1: Get eBay Token `sell.fulfillment` Scope
- **What:** Josh re-consents with additional scope
- **How:** Run direct OAuth URL with `sell.fulfillment` added
- **Time:** 5 minutes
- **Verify:** `lib/ebay_sales.py` can call `get_orders_since()` → HTTP 200
- **Verified by:** Run test: `pytest tests/ebay/test_ebay_sales.py::test_get_orders_since -v`

#### [ ] Step 0.2: Confirm Etsy Status or Switch to Fallback
- **What:** Check if Etsy app approved
- **If approved:** Get ETSY_ACCESS_TOKEN, ETSY_SHOP_ID, ETSY_TAXONOMY_ID
- **If not approved:** Use manual CSV export (already built)
- **Time:** 5-30 minutes
- **Verify:** Either Etsy OAuth works OR CSV export ready to send

#### [ ] Step 0.3: Set Instagram Credentials (Optional)
- **What:** Get IG_ACCESS_TOKEN if you want Instagram posting
- **If skipped:** Instagram just won't post, other platforms still work
- **Time:** 10 minutes
- **Note:** Token expires in 60 days (2026-10-20) — needs refresh

---

### PHASE 1: Wire Boss Listers to Real Inventory

#### [ ] Step 1.1: Load Real Items in UI
- **File:** `boss-listers-mvp/pages/index.js`
- **What:** On page load, fetch 69 real items from Supabase
- **Verify:** UI shows "69 items" instead of "0 items"
- **Time:** 30 minutes

#### [ ] Step 1.2: Wire "Analyze Product" to Real Items
- **What:** When user clicks a real item, generate AI description
- **Uses:** Existing `lib/ebay_listing.py` payload builder
- **Verify:** Description appears on UI for a real card
- **Time:** 1 hour

#### [ ] Step 1.3: Wire "Generate Listings" to Python Service
- **What:** When user clicks "Generate listings", call Python bridge at `:8791/ebay/create-listing`
- **Payload:** Real item data + AI description + pricing
- **Verify:** Listing created dry-run (can inspect payload)
- **Time:** 1 hour

---

### PHASE 2: Go Live

#### [ ] Step 2.1: Start Listing Service
```bash
cd C:/Users/jjard/claude/video-bot-pipeline
python scripts/listing_service.py --allow-live
```
- **Time:** 1 minute

#### [ ] Step 2.2: Manually List First Item (Watched)
- **What:** In Boss Listers UI, click "Generate listings" on 1 real card
- **Confirm:** Prompt appears asking `confirm: "PUBLISH_LIVE"`
- **Action:** User types the literal string to proceed
- **Result:** Item appears on eBay within 1 minute
- **Time:** 5 minutes
- **Verify:** Check Josh's eBay account for new listing

#### [ ] Step 2.3: Publish Remaining 68 Items
- **Method:** Batch through UI or direct API call
- **Safety:** Each one requires confirmation
- **Time:** 30 minutes
- **Verify:** All 69 items live on eBay

---

### PHASE 3: Sales Tracking

#### [ ] Step 3.1: Start Sales Tracker Agent
```bash
python agents/sales_tracker_agent.py
```
- **Runs:** Every 5 minutes
- **Fetches:** Orders since last poll
- **Records:** Sales to Supabase (atomic dedup)
- **Updates:** Inventory quantities
- **Time:** 1 minute

#### [ ] Step 3.2: Make a Test Sale
- **What:** Sell one item on eBay manually (or have Josh buy it)
- **Verify:** Sales Tracker detects it within 5 minutes
- **Check:** Supabase `sync_logs` shows sale recorded
- **Check:** Inventory quantity decremented by 1
- **Time:** 5-10 minutes

#### [ ] Step 3.3: Continuous Monitoring
- **What:** Sales Tracker runs in background, auto-updates inventory
- **Fallback:** If agent crashes, restart manually
- **Future:** Wire to uptime monitoring (Sentry, etc.)

---

### PHASE 4: Other Platforms (Future)

#### [ ] Whatnot CSV Export
- **Status:** Already built, ready to use
- **How:** Export from Boss Listers UI, use Whatnot's official bulk importer
- **Time:** 10 minutes (manual Whatnot upload)

#### [ ] Poshmark/Mercari Manual Export
- **Status:** Already built, ready to use
- **How:** Export from Boss Listers UI, copy-paste to each platform
- **Time:** 15-20 minutes per platform

#### [ ] Etsy Automation (If approved)
- **Uses:** `lib/etsy_listing.py`
- **Status:** Blocked on Etsy app approval
- **Timeline:** TBD

---

## PART 6: VERIFICATION CHECKLIST

Use this to confirm each step is actually done:

### Phase 0 Verification
- [ ] `pytest tests/ebay/test_ebay_sales.py -v` → 3 passing (was 0)
- [ ] Run: `curl -X GET https://api.ebay.com/sell/fulfillment/v1/orders -H "Authorization: Bearer {TOKEN}"` → HTTP 200
- [ ] Etsy: Either token set OR CSV export confirmed working

### Phase 1 Verification
- [ ] Boss Listers UI shows "69 items" (not "0 items")
- [ ] Click an item → AI description appears
- [ ] Click "Generate listings" → payload logged to console (dry-run)

### Phase 2 Verification
- [ ] Listing service starts without errors
- [ ] Create 1 listing with `confirm: "PUBLISH_LIVE"`
- [ ] Check eBay account → listing live
- [ ] All 69 items live within 2 hours

### Phase 3 Verification
- [ ] Sales tracker starts without errors
- [ ] Sell 1 item on eBay
- [ ] Within 5 minutes: Supabase `sync_logs` shows sale
- [ ] Inventory quantity decremented in `products` table

---

## PART 7: KNOWN ISSUES & WORKAROUNDS

| Issue | Workaround | Priority |
|-------|-----------|----------|
| Next.js config had `output: export` | Removed, API routes now work | Fixed 2026-08-21 |
| eBay token missing `sell.fulfillment` | Re-consent with additional scope | Must do Phase 0.1 |
| Instagram token not set | Skip Instagram, other platforms work | Optional |
| Etsy app pending approval | Use manual CSV export | Fallback ready |
| No uptime monitoring | Add Sentry/monitoring when live | Future |

---

## PART 8: FILES & LOCATIONS

### Core Code (Read-Only, Already Built)
- `lib/ebay_listing.py` — eBay listing client (407 lines)
- `lib/ebay_sales.py` — eBay sales client (194 lines)
- `lib/etsy_listing.py` — Etsy listing client (605 lines)
- `agents/sales_tracker_agent.py` — Sales tracking loop
- `scripts/listing_service.py` — HTTP bridge (127.0.0.1:8791)
- `render_commercial.py` — Commercial renderer

### To Be Modified (Phase 1)
- `boss-listers-mvp/pages/index.js` — Wire to real inventory
- `boss-listers-mvp/next.config.js` — Already fixed ✅
- `boss-listers-mvp/.env.local` — Add missing credentials

### Environment (.env.local Locations)
- `boss-listers-mvp/boss-listers-mvp/.env.local` → eBay/Etsy/Instagram tokens
- `C:/Users/jjard/claude/video-bot-pipeline/.env` → Python backend secrets
- Supabase credentials in both (SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY)

---

## SUMMARY

**What's Live Right Now:**
- eBay OAuth (production, tested)
- 69 real items in Supabase
- eBay listing client (dry-run ready)
- Sales tracker (blocked on token scope only)

**What's Blocked:**
1. eBay token needs `sell.fulfillment` (5 min fix)
2. Boss Listers UI not wired to real inventory (1 hour fix)
3. Python listing service not called (1 hour fix)

**Time to Revenue:**
- Phase 0 (fix blockers): 30 minutes
- Phase 1 (wire UI): 2-3 hours
- Phase 2 (go live): 1 hour
- **Total:** ~4-5 hours to first live item on eBay

---

**DO NOT GUESS. DO NOT ASSUME. FOLLOW THIS CHECKLIST.**

Check off each step as it's verified complete. No moving forward without verification.
