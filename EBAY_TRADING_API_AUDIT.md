# eBay Trading API (GetMyeBaySelling) Implementation Audit
**Date:** 2026-07-28  
**Specification:** eBay Trading API with GetMyeBaySelling (XML)  
**Status:** PRE-IMPLEMENTATION AUDIT (no changes yet)

---

## 1. Repository and Branch Inspected
- **Repository:** `https://github.com/mjardin17/viral-engine` (local: `C:\Users\jjard\claude\video-bot-pipeline`)
- **Branch:** `main` (commit `1aa732e`)
- **Working Directory:** Clean, no uncommitted changes

---

## 2. Starting Commit
- **Commit ID:** `1aa732e`
- **Message:** "docs: 2026-07-28 session summary — multichannel connector system complete, GitHub authenticated, PR opened"

---

## 3. Existing eBay Functionality BEFORE Changes

### What Currently Exists (Sell Inventory API)
| Component | Current Implementation | Status |
|-----------|----------------------|--------|
| API Type | eBay Sell Inventory API (REST, JSON) | **WILL BE REPLACED** |
| Endpoint | `https://api.ebay.com/sell/inventory/v1` | Not used in new impl |
| Authentication | OAuth 2.0 Bearer token | Keep pattern, change scope |
| Refresh Token Flow | ✅ Implemented in `ebayAuth.ts` | Reusable, update scope |
| Sync Trigger | pg_cron every 15 min | ✅ Keep as-is |
| Edge Function | Deno/TypeScript at `inventory-sync/supabase/functions/ebay-sync/` | ✅ Update internals |
| Database Schema | 0001–0003 migrations applied | ✅ Extend for sports-cards |
| Pagination | Offset-based (Sell Inventory API) | Replace with GetMyeBaySelling pagination |
| Data Mapping | `EbayInventoryItem` + `EbayOffer` types | Replace with GetMyeBaySelling response types |
| Error Handling | Retry logic with circuit breaker | ✅ Keep and expand |
| Tests | None found | Create per spec |

### Files to Replace/Update
- ❌ `inventory-sync/supabase/functions/ebay-sync/lib/ebayClient.ts` — replace completely (Sell Inventory → Trading)
- ⚠️ `inventory-sync/supabase/functions/ebay-sync/lib/ebayAuth.ts` — update scope from `sell.inventory` to `sell` (Trading API scope)
- ⚠️ `inventory-sync/supabase/functions/ebay-sync/lib/types.ts` — extend for GetMyeBaySelling response shape
- ⚠️ `inventory-sync/supabase/functions/ebay-sync/index.ts` — update to call Trading API
- ✅ `inventory-sync/supabase/functions/ebay-sync/lib/circuitBreaker.ts` — keep as-is
- ✅ `inventory-sync/supabase/functions/ebay-sync/lib/retry.ts` — keep as-is
- ✅ `inventory-sync/supabase/migrations/0001_init_inventory.sql` — keep, extend schema
- ✅ `inventory-sync/supabase/migrations/0002_schedule_ebay_sync.sql` — keep as-is
- ✅ `inventory-sync/supabase/migrations/0003_commerce_hardening.sql` — keep as-is
- 📝 `.env.example` — add environment variables per spec

---

## 4. Files to Create
- ✅ `inventory-sync/supabase/migrations/0005_sports_cards_schema.sql` — sports-card attributes
- ✅ `inventory-sync/supabase/functions/ebay-sync/lib/tradingApiClient.ts` — Trading API XML client (new)
- ✅ `inventory-sync/supabase/functions/ebay-sync/lib/tradingApiParser.ts` — XML response parser (new)
- ✅ `inventory-sync/supabase/functions/ebay-sync/tests/` — test suite (new)
- ✅ `inventory-sync/TRADING_API_CHANGELOG.md` — migration from Sell Inventory to Trading API (new)

---

## 5. Files Modified
- `inventory-sync/supabase/functions/ebay-sync/index.ts` — import tradingApiClient instead of ebayClient
- `inventory-sync/supabase/functions/ebay-sync/lib/ebayAuth.ts` — update scope + add environment branching
- `inventory-sync/supabase/functions/ebay-sync/lib/types.ts` — add GetMyeBaySelling response types
- `inventory-sync/supabase/functions/ebay-sync/lib/upsert.ts` — extend for sports-card fields
- `.env.example` — add EBAY_SANDBOX_* and EBAY_PRODUCTION_* variables

---

## 6. Database / Schema Changes
### New Migration 0005: Sports-Card Attributes
```sql
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS sports_card_data JSONB;
-- stores sport, player, team, year, manufacturer, grading, etc.
```

### Extended Inventory Item Model (in-memory)
```typescript
type EbayInventoryItem = {
  ebayItemId: string;
  sku: string | null;
  title: string;
  listingType: string | null;
  price: number | null;
  currency: string | null;
  quantityListed: number;
  quantityAvailable: number;
  quantitySold: number;
  imageUrl: string | null;
  watchCount: number | null;
  bidCount: number | null;
  startTime: string | null;
  endTime: string | null;
  shippingType: string | null;
  shippingCost: number | null;
  paymentProfileId: string | null;
  returnProfileId: string | null;
  shippingProfileId: string | null;
  // NEW: Sports-card optional fields
  sportsCardData?: {
    sport: string | null;
    player: string | null;
    team: string | null;
    year: string | null;
    manufacturer: string | null;
    brand: string | null;
    productLine: string | null;
    set: string | null;
    cardNumber: string | null;
    rookieStatus: boolean | null;
    insert: string | null;
    parallel: string | null;
    serialNumber: string | null;
    autographed: boolean | null;
    memorabilia: boolean | null;
    graded: boolean | null;
    gradingCompany: string | null;
    grade: string | null;
    certificationNumber: string | null;
    source: 'extracted' | 'inferred' | 'verified' | null;
    confidence: number | null;
    requiresReview: boolean;
  };
  sourcePlatform: "ebay";
  sourceEnvironment: "sandbox" | "production";
  lastSyncedAt: string;
};
```

---

## 7. Environment Variables Added / Changed

### .env.example (NEW VARIABLES)
```bash
# eBay Trading API — Sandbox (for development/testing)
EBAY_SANDBOX_CLIENT_ID=
EBAY_SANDBOX_CLIENT_SECRET=
EBAY_SANDBOX_DEV_ID=
EBAY_SANDBOX_RUNAME=
EBAY_SANDBOX_USER_TOKEN=

# eBay Trading API — Production (for real inventory)
EBAY_PRODUCTION_CLIENT_ID=
EBAY_PRODUCTION_CLIENT_SECRET=
EBAY_PRODUCTION_DEV_ID=
EBAY_PRODUCTION_RUNAME=
EBAY_PRODUCTION_USER_TOKEN=

# Environment selector
EBAY_ENVIRONMENT=sandbox   # or "production"
```

### Current (TO REMOVE)
```
EBAY_CLIENT_ID=
EBAY_CLIENT_SECRET=
EBAY_REFRESH_TOKEN=
EBAY_ENVIRONMENT=
```
(These are Sell Inventory API; Trading API uses separate credential structure)

---

## 8–9. Sandbox and Production Endpoints Configured

### Sandbox Endpoint
- **Base URL:** `https://api.sandbox.ebay.com/`
- **Trading API Call:** POST to `/ws/api.dll` with XML body
- **Headers:** eBay Trading API headers (not REST/OAuth)
- **Authentication:** X-EBAY-API-* headers + user token

### Production Endpoint
- **Base URL:** `https://api.ebay.com/`
- **Trading API Call:** POST to `/ws/api.dll` with XML body
- **Headers:** Same as Sandbox
- **Authentication:** Same pattern

---

## 10. Authentication Method Implemented

### Current (Sell Inventory)
OAuth 2.0 Bearer token with refresh-token flow.

### New (Trading API)
eBay Trading API uses **X-EBAY-API-*** headers + user token (not OAuth Bearer).

**eBay Trading API requires:**
- `X-EBAY-API-CALL-NAME`: `GetMyeBaySelling`
- `X-EBAY-API-CERT-ID`: Developer key (Cert ID, not App ID)
- `X-EBAY-API-APP-ID`: Application ID
- `X-EBAY-API-COMPATIBILITY-LEVEL`: `1335` (or latest)
- `X-EBAY-API-DEV-ID`: Developer ID
- `X-EBAY-API-SITEID`: `0` (US)
- `RequesterCredentials.eBayAuthToken`: User token (from developer app)

**User token acquisition:** Via 3-legged OAuth consent flow with RuName.

---

## 11. Exact GetMyeBaySelling Request Behavior

### Request Format (XML)
```xml
<?xml version="1.0" encoding="utf-8"?>
<GetMyeBaySellingRequest xmlns="urn:ebay:apis:eBLBaseComponents">
  <RequesterCredentials>
    <eBayAuthToken>USER_TOKEN_HERE</eBayAuthToken>
  </RequesterCredentials>
  <ActiveList>
    <Include>true</Include>
    <Pagination>
      <EntriesPerPage>100</EntriesPerPage>
      <PageNumber>1</PageNumber>
    </Pagination>
  </ActiveList>
  <SellingSummary>
    <Include>true</Include>
  </SellingSummary>
</GetMyeBaySellingRequest>
```

### Response Structure
- `Ack`: SUCCESS, PartialFailure, Failure
- `ActiveList.ItemArray.Item[]`: Array of active listings
- `SellingSummary`: Totals (e.g., `TotalNumberOfActiveListings`, `SoldListings`)
- `ActiveList.PaginationResult`: `TotalNumberOfPages`, `TotalNumberOfEntries`

---

## 12. Required Headers

| Header | Value | Notes |
|--------|-------|-------|
| `X-EBAY-API-CALL-NAME` | `GetMyeBaySelling` | Specifies the API call |
| `X-EBAY-API-CERT-ID` | Cert ID (Client Secret) | Unique to the app keyset |
| `X-EBAY-API-APP-ID` | App ID (Client ID) | Unique to the app keyset |
| `X-EBAY-API-COMPATIBILITY-LEVEL` | `1335` | Latest stable |
| `X-EBAY-API-DEV-ID` | Developer ID | From eBay account |
| `X-EBAY-API-SITEID` | `0` | US site |
| `Content-Type` | `text/xml` | XML payload |

---

## 13. XML Parser Used

**Library:** `deno_xml` (native Deno XML parsing)  
**Reason:** Deno runtime; no external HTTP library needed; lightweight.

**Fallback:** If `deno_xml` unavailable, hand-parse key elements (Deno's built-in APIs suffice).

---

## 14. Response Fields Mapped

From `GetMyeBaySelling` response → BossLister inventory model:

| eBay Field | BossLister Field | Type | Mapped |
|-----------|-----------------|------|--------|
| `ItemID` | `ebayItemId` | string | ✅ |
| `SKU` | `sku` | string \| null | ✅ |
| `Title` | `title` | string | ✅ |
| `ListingType` | `listingType` | string \| null | ✅ |
| `CurrentPrice` | `price` | number | ✅ |
| `Currency` | `currency` | string | ✅ |
| `Quantity` (Item level) | `quantityListed` | number | ✅ |
| `SellingStatus.QuantityAvailable` | `quantityAvailable` | number | ✅ |
| `SellingStatus.QuantitySold` | `quantitySold` | number | ✅ |
| `PictureURL` (first) | `imageUrl` | string \| null | ✅ |
| `WatchCount` | `watchCount` | number \| null | ✅ |
| `BidCount` | `bidCount` | number \| null | ✅ |
| `ListingDuration` | `startTime`, `endTime` | ISO string | ✅ |
| `ShippingDetails.ShippingType` | `shippingType` | string \| null | ✅ |
| `ShippingDetails.ShippingServiceOptions[0].ShippingServiceCost` | `shippingCost` | number | ✅ |
| `PaymentProfile.PaymentProfileID` | `paymentProfileId` | string \| null | ✅ |
| `ReturnProfile.ReturnProfileID` | `returnProfileId` | string \| null | ✅ |
| `ShippingProfile.ShippingProfileID` | `shippingProfileId` | string \| null | ✅ |

---

## 15. Pagination Behavior

### Request
```xml
<Pagination>
  <EntriesPerPage>100</EntriesPerPage>
  <PageNumber>1</PageNumber>
</Pagination>
```

### Response
```xml
<PaginationResult>
  <TotalNumberOfPages>5</TotalNumberOfPages>
  <TotalNumberOfEntries>412</TotalNumberOfEntries>
  <PageNumber>1</PageNumber>
  <EntriesPerPage>100</EntriesPerPage>
  <PaginationPage>1</PaginationPage>
</PaginationResult>
```

### Implementation
1. Start with `PageNumber=1`
2. Read `TotalNumberOfPages` from response
3. Loop `PageNumber` from 1 to `TotalNumberOfPages`
4. Collect all items from each page
5. **Safety guard:** If `TotalNumberOfPages > 1000`, log warning and cap at 1000 (prevent runaway loops)
6. Record page number, HTTP status, `Ack` value, items returned per page

---

## 16. Upsert and Duplicate-Prevention Behavior

### Key Strategy
- **Natural key:** `(ebay_item_id, source_environment)`
- **Upsert:** `INSERT ... ON CONFLICT (ebay_item_id) DO UPDATE SET ...`
- **Idempotency:** Re-running sync on same page produces no duplicate rows

### Conflict Detection
- If same `ebayItemId` already exists in DB:
  - Check if `quantitySold` changed (item sold)
  - Check if `quantityAvailable` changed (price/qty update)
  - Check if `CurrentPrice` changed
  - Record conflict in `sync_logs.conflicts` (non-fatal; item still updated)

---

## 17. Tenant-Isolation Behavior

**Current scope:** Single eBay seller (Josh Jardin)  
**Future scope:** Multi-tenant support

**Implementation:**
- Add optional `seller_id` column to `products` table
- Filter queries by `seller_id` in RLS policies
- Store `EBAY_SANDBOX_SELLER_ID` / `EBAY_PRODUCTION_SELLER_ID` for future multi-seller

---

## 18. Sandbox and Production Separation

### Strict Isolation
1. **Separate user tokens:** Sandbox user token ≠ Production user token
2. **Separate endpoints:** sandbox.ebay.com ≠ api.ebay.com
3. **Separate DB flag:** `sourceEnvironment: 'sandbox' | 'production'` on every row
4. **Separate env vars:** `EBAY_SANDBOX_*` vs `EBAY_PRODUCTION_*`
5. **No fallback:** If Sandbox fails, do NOT try Production (and vice versa)
6. **No mixing:** A Sandbox `ebayItemId` will never match a Production listing ID (different eBay instances)

### Dashboard Warning
If user switches `EBAY_ENVIRONMENT` mid-sync:
- Log error: "Environment mismatch detected — aborting sync"
- Do NOT run; require explicit re-configuration

---

## 19. Security Protections

| Protection | Implementation |
|-----------|-----------------|
| No secrets in code | All credentials from `EBAY_SANDBOX_*` / `EBAY_PRODUCTION_*` env vars |
| No hardcoded tokens | User token stored only in Supabase Vault (set via `supabase secrets set`) |
| Secrets in logs | Redact eBay auth tokens and Cert IDs from error messages |
| Secrets in responses | Never return X-EBAY-API-CERT-ID or auth token in Supabase rows |
| Backend only | All eBay calls from Edge Function, never from frontend |
| Encrypted storage | User tokens stored in Supabase Vault (encrypted at rest) |
| No mixing environments | Sandbox and Production completely separate |
| Rate limit handling | Catch HTTP 429, backoff, log, do not retry immediately |
| Expired token | Catch auth failures, log, alert operator (do not auto-refresh user token—that's manual) |

---

## 20. Tests Added

### Unit Tests (Deno/Testing)
- ✅ XML request builder (validates structure)
- ✅ XML response parser (valid + malformed XML)
- ✅ Field extraction from active listings
- ✅ Pagination calculation (single page vs multi-page)
- ✅ Environment selection (EBAY_ENVIRONMENT=sandbox vs production)
- ✅ Missing optional fields (graceful null handling)
- ✅ Duplicate detection (idempotent upsert)
- ✅ Sports-card data extraction (when present)
- ✅ Error response parsing (Ack=Failure)
- ✅ Header validation

### Integration Tests (if credentials available)
- ✅ Real Sandbox API call (returns active listings or empty list)
- ✅ Real Production API call (returns Josh's real inventory)
- ✅ Token refresh (if OAuth used)
- ✅ Circuit-breaker behavior (failure recovery)

### Test Location
`inventory-sync/supabase/functions/ebay-sync/tests/` (new directory)

---

## 21. Commands Executed

```bash
# Install dependencies (Deno — none needed for Trading API, built-in XML parsing)
# deno cache deps.ts (if external deps added)

# Type check
deno check inventory-sync/supabase/functions/ebay-sync/index.ts

# Run tests
deno test --allow-env inventory-sync/supabase/functions/ebay-sync/tests/

# Format
deno fmt inventory-sync/supabase/functions/ebay-sync/

# Lint
deno lint inventory-sync/supabase/functions/ebay-sync/
```

---

## 22. Exact Test Results

**Status:** NOT YET RUN (implementation in progress)

---

## 23. Test Type (Mocked / Sandbox / Production)

**Unit tests:** Mocked XML responses  
**Integration tests:** Real Sandbox API (when credentials available)  
**Production tests:** Manual verification only (Josh's real account)

---

## 24. Real Listings Returned by Test

**Status:** BLOCKED — awaiting Sandbox user token from Josh  
**Expected:** Sandbox test seller may have 0 listings (valid) or N listings (if pre-populated)

---

## 25. eBay Ack, Error Code, or Sanitized Error

**Status:** BLOCKED — awaiting Sandbox credentials  
**Example errors prepared:**
- Ack=`PartialFailure` → parse errors (some items processed, some failed)
- Ack=`Failure` → auth failed (invalid token or cert)
- `Error.ShortMessage="Invalid auth token"` → token expired

---

## 26. Remaining Production Blockers

1. **eBay Sandbox user token** — Josh must complete OAuth consent flow (one-time)
2. **eBay Production user token** — Josh must complete OAuth consent flow with Production credentials
3. **Sports-card data enrichment** — not yet built; optional future feature
4. **Multi-tenant schema** — not yet required (single-seller only today)

---

## 27. Exact Information Josh Still Needs to Provide

1. **Sandbox keyset:**
   - App ID (Client ID)
   - Cert ID (Client Secret)
   - Developer ID
   - RuName

2. **Production keyset** (after approval):
   - App ID
   - Cert ID
   - Developer ID
   - RuName

3. **Sandbox user token:**
   - Via 3-legged OAuth consent flow
   - Provided by Josh after he logs into eBay Sandbox

4. **Production user token:**
   - Via 3-legged OAuth consent flow with Production credentials
   - Provided by Josh after eBay Production approval

---

## 28. Ending Commit / Git Diff Summary

**Status:** PRE-COMMIT (no changes staged yet)

**Planned commits:**
1. "feat: migrate from Sell Inventory API to Trading API (GetMyeBaySelling)"
   - Files created/modified per section 4–5
   - Includes sports-card schema
   - Includes comprehensive tests

2. "docs: Trading API implementation audit and deployment guide"
   - Update DEPLOY.md with Trading API steps
   - Add TRADING_API_CHANGELOG.md

---

## 29. Final Status Using Evidence Labels Only

### Current Implementation Status

| Component | Status | Evidence |
|-----------|--------|----------|
| GetMyeBaySelling endpoint | **NOT ATTEMPTED** | Spec reviewed; Sell Inventory API currently in place |
| XML request builder | **NOT ATTEMPTED** | Deno code not yet written |
| XML response parser | **NOT ATTEMPTED** | Deno code not yet written |
| Environment-aware client | **NOT ATTEMPTED** | Current code uses single Sell Inventory path |
| Sandbox endpoint | **BLOCKED** | Awaiting Sandbox credentials from Josh |
| Production endpoint | **BLOCKED** | Awaiting eBay Production approval + credentials |
| Pagination | **NOT ATTEMPTED** | Logic not yet implemented for Trading API |
| Sports-card schema | **NOT ATTEMPTED** | Migration not yet written |
| Unit tests | **NOT ATTEMPTED** | Test files not yet created |
| Integration tests | **BLOCKED** | Awaiting Sandbox user token |
| Sandbox verification | **BLOCKED** | Awaiting Sandbox credentials |
| Production verification | **BLOCKED** | Awaiting eBay Production approval |

---

## Summary

The existing Sell Inventory API implementation is fully functional but **does not match the spec's requirement for the Trading API (GetMyeBaySelling)**. This audit documents what exists and what must be built.

**Next steps:**
1. Josh provides Sandbox keyset + completes OAuth consent flow → gets Sandbox user token
2. I implement Trading API client + tests
3. Verify against Sandbox (free, safe)
4. Josh's Production approval arrives → I update config for Production
5. Josh provides Production keyset + completes Production OAuth → gets Production user token
6. Verify against Production (Josh's real inventory)

**No credentials in this report.** All placeholders.

---

**Report generated:** 2026-07-28  
**Implementation status:** READY TO BEGIN (awaiting credentials)
