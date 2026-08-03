# eBay Trading API Implementation — Complete

## Status: Ready for Sandbox Testing

All code is complete and tested. Ready to deploy to Supabase and verify against Sandbox credentials.

## What Changed

### Why Trading API?

The prior implementation used **Sell Inventory API** (REST/JSON), which is modern but incomplete for seller inventory polling:
- Lacks pagination (can't fetch beyond first 1000 items)
- Only returns draft/pre-listing inventory, not active listings
- Requires separate API calls to fetch pricing and offers

**Trading API (GetMyeBaySelling, XML-RPC)** provides what we actually need:
- Full active listings with pagination (100 per page, unlimited total)
- Complete pricing, quantities (available, sold, listed), images in one call
- Seller context (watch count, bid count, profiles)
- Officially supported for high-volume seller integration

### New Files

**Trading API Client & Parser:**
- `inventory-sync/supabase/functions/ebay-sync/lib/tradingApiClient.ts`
  - XML request builder (`buildGetMyeBaySellingRequest()`)
  - Multi-page pagination loop (`fetchAllActiveListings()`)
  - Trading API call with required X-EBAY-API-* headers
  - Retry resilience on transient HTTP errors

- `inventory-sync/supabase/functions/ebay-sync/lib/tradingApiParser.ts`
  - XML → structured object parsing using Deno's DOMParser
  - `parseGetMyeBaySellingResponse()` — converts XML to EbayInventoryItem array
  - `isSuccessAck()`, `isPartialAck()` — ACK status helpers
  - Error element extraction and safe null handling for optional fields

**Tests:**
- `inventory-sync/supabase/functions/ebay-sync/lib/tradingApiClient.test.ts`
  - Parses success/error responses, pagination, missing fields, multiple items

- `inventory-sync/supabase/functions/ebay-sync/lib/upsert.test.ts`
  - ProductRow mapping from Trading API items
  - Out-of-stock handling, SKU fallback, defaults

**Config & Docs:**
- `inventory-sync/supabase/functions/ebay-sync/.env.example`
  - New env var structure (EBAY_SANDBOX_* / EBAY_PRODUCTION_*)

- Updated `inventory-sync/DEPLOY.md`
  - Simplified setup (no OAuth refresh token exchange)
  - Clear separation of Sandbox vs Production credentials

### Modified Files

**Core Integration:**
- `inventory-sync/supabase/functions/ebay-sync/index.ts`
  - Removed `getEbayAccessToken` (no longer needed)
  - Changed import from `ebayClient` to `tradingApiClient`
  - Single `fetchAllActiveListings()` call replaces dual fetch (inventory + offers)
  - Updated to use `EBAY_SANDBOX_*` / `EBAY_PRODUCTION_*` env vars
  - Simplified error handling (no separate "fetch_offers" stage)

- `inventory-sync/supabase/functions/ebay-sync/lib/types.ts`
  - Replaced Sell Inventory API types with Trading API types
  - `EbayInventoryItem` now includes: ebayItemId, quantityAvailable, quantitySold, quantityListed, price, imageUrl, watchCount, bidCount, etc.
  - Updated `SyncError.stage` to use "fetch_listings" instead of "fetch_inventory"/"fetch_offers"
  - Added `ebayItemId` as optional error field for better debugging

- `inventory-sync/supabase/functions/ebay-sync/lib/upsert.ts`
  - `buildProductRow()` now takes only `EbayInventoryItem` (no offer parameter)
  - Simplified mapping: price/quantity/image come directly from item
  - Removed `mapStatus()` (no offer status in Trading API; infer from quantity)
  - Falls back to `ebayItemId` when SKU is null (common in high-volume sellers)

## Architecture

```
┌─────────────────────────────────────────┐
│  15-min pg_cron trigger                 │
│  (via pg_net HTTP POST)                 │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  Edge Function: ebay-sync                │
│                                         │
│  1. Build GetMyeBaySelling XML request  │
│  2. POST to eBay Trading API endpoint   │
│     - Send: X-EBAY-API-* headers        │
│     - Auth: user token in XML body      │
│  3. Parse XML response (DOMParser)      │
│  4. Loop pages until done               │
│     - Extract: itemID, price, quantity, │
│       images, watch count, etc.         │
│  5. Map to ProductRow (single field set)│
│  6. Upsert to `public.products`         │
│  7. Log to `public.sync_logs`           │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  Supabase Postgres                      │
│                                         │
│  public.products (RLS: anon SELECT)    │
│  public.sync_logs (service_role only)   │
│  public.sync_state (circuit breaker)    │
└─────────────────┬───────────────────────┘
                  │
        ┌─────────┴──────────┐
        ▼                    ▼
    Website             Boss Listers
    (Realtime live     (Shared inventory
     cards)            dashboard)
```

## Environment Variables (Updated)

### Sandbox
```
EBAY_SANDBOX_APP_ID=...
EBAY_SANDBOX_CERT_ID=...
EBAY_SANDBOX_DEV_ID=...
EBAY_SANDBOX_USER_TOKEN=...
EBAY_ENVIRONMENT=sandbox
```

### Production
```
EBAY_PRODUCTION_APP_ID=...
EBAY_PRODUCTION_CERT_ID=...
EBAY_PRODUCTION_DEV_ID=...
EBAY_PRODUCTION_USER_TOKEN=...
EBAY_ENVIRONMENT=production
```

Set via: `npx supabase secrets set ...` (stored in Vault, encrypted at rest)

## Trading API Response Structure (XML Example)

```xml
<GetMyeBaySellingResponse>
  <Ack>Success</Ack>
  <ActiveList>
    <PaginationResult>
      <TotalNumberOfPages>5</TotalNumberOfPages>
      <TotalNumberOfEntries>432</TotalNumberOfEntries>
      <PageNumber>1</PageNumber>
    </PaginationResult>
    <ItemArray>
      <Item>
        <ItemID>123456789</ItemID>
        <SKU>MY-SKU-001</SKU>
        <Title>Vintage Widget</Title>
        <ListingType>FixedPriceItem</ListingType>
        <CurrentPrice>49.99</CurrentPrice>
        <Currency>USD</Currency>
        <Quantity>100</Quantity>
        <SellingStatus>
          <QuantityAvailable>75</QuantityAvailable>
          <QuantitySold>25</QuantitySold>
        </SellingStatus>
        <PictureURL>http://...</PictureURL>
        <WatchCount>12</WatchCount>
        <BidCount>3</BidCount>
        ...
      </Item>
      <!-- more items -->
    </ItemArray>
  </ActiveList>
</GetMyeBaySellingResponse>
```

Parsed into:
```typescript
{
  ebayItemId: "123456789",
  sku: "MY-SKU-001",
  title: "Vintage Widget",
  price: 49.99,
  quantityAvailable: 75,
  quantitySold: 25,
  imageUrl: "http://...",
  watchCount: 12,
  ... // other fields
}
```

## Error Handling

### HTTP Errors
- Retryable (429, 500, 502, 503, 504): automatic backoff + retry
- Non-retryable (400, 401, 403): immediate fail with error log

### XML Parsing
- Missing items element: returns empty array, logs to sync_logs
- Malformed XML: DOMParser throws, caught by circuit breaker
- Invalid ItemID: skipped with error logged per-item

### Circuit Breaker
- Tracks consecutive sync failures
- Opens for 30 min after 5 consecutive failures
- Prevents cascading eBay API errors

## Testing

Run tests locally:
```bash
deno test inventory-sync/supabase/functions/ebay-sync/lib/*.test.ts
```

Covers:
- XML parsing (success, partial, failure responses)
- Pagination loop boundary conditions
- Missing/null field handling
- ProductRow mapping (full, minimal, defaults)
- Out-of-stock status

## Next Steps (User Action Required)

1. **Obtain Sandbox credentials** — eBay Developer Portal
   - App ID, Cert ID, Dev ID (keyset)
   - User Token (auth token for your seller account)

2. **Deploy to Supabase** — from `inventory-sync/` directory:
   ```bash
   npx supabase secrets set EBAY_SANDBOX_APP_ID=... (etc)
   npx supabase functions deploy ebay-sync
   ```

3. **Test against Sandbox** — trigger manually:
   ```bash
   curl -i https://<PROJECT>.supabase.co/functions/v1/ebay-sync \
     -H "x-sync-trigger-secret: YOUR_SECRET"
   ```
   - Check `public.sync_logs` for status
   - Verify items appear in `public.products`

4. **Verify website & Boss Listers** — read fresh products
   - `/api/products` on website (should return Sandbox listings)
   - Boss Listers dashboard (should show synced inventory)

5. **Rotate to Production** — once Sandbox is confirmed working
   - Get Production credentials from eBay
   - `npx supabase secrets set EBAY_PRODUCTION_*...`
   - Set `EBAY_ENVIRONMENT=production`
   - Redeploy Edge Function
   - Verify against live eBay listings

## Known Limitations & Design Decisions

**No sports-card schema yet** — The schema (0001_init_inventory.sql) has a basic products table. Sports-card specifics (player, team, year, grading, PSA grade) would require:
- Separate `sports_cards` table with JSONB sports_card_data
- Migration 0005_sports_cards_schema.sql (on roadmap)
- Parser extensions in tradingApiParser.ts to extract from title/description

**No Variations support** — Trading API supports item variations (sizes, colors) but they're optional. Current implementation treats each variation as a separate listing in eBay's data; not aggregated locally yet.

**No auction listings** — GetMyeBaySelling returns active listings (fixed-price and auctions both). We treat all as "active" status regardless of auction vs fixed-price. Future work could differentiate based on ListingType.

## Code Quality

- ✅ TypeScript strict mode (Deno 1.40+)
- ✅ No hardcoded secrets
- ✅ Comprehensive error messages in sync_logs
- ✅ Safe null handling (null coalescing on all optional fields)
- ✅ Immutable ProductRow construction
- ✅ Unit tests with Deno's test runner + std assertions
- ✅ No console.log in production paths (logging via sync_logs table)

## File Summary

| File | Lines | Purpose |
|------|-------|---------|
| tradingApiClient.ts | 108 | XML request builder, pagination, API call |
| tradingApiParser.ts | 122 | XML parsing, Ack status, error extraction |
| index.ts | 70 | Edge Function entrypoint, runSync orchestration |
| types.ts | 45 | Trading API item type, product row, errors |
| upsert.ts | 60 | ProductRow mapping, database upsert logic |
| tradingApiClient.test.ts | 110 | Parser tests (success, errors, pagination) |
| upsert.test.ts | 105 | Mapping tests (full items, nulls, defaults) |
| .env.example | 25 | Environment variable reference |
| DEPLOY.md | 200 | Step-by-step deployment guide |

**Total: ~645 lines of new Trading API code + tests**

