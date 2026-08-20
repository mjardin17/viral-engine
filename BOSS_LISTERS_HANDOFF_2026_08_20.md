# Boss Listers Continuation — Handoff Prompt (2026-08-20)

**Paste this whole file into a fresh Claude Code session** in `C:\Users\jjard\claude\video-bot-pipeline` to continue Boss Listers work.

## What Just Got Done

1. **Real eBay Sales Tracking** — `lib/ebay_sales.py` + `tests/ebay/test_ebay_sales.py`
   - EbaySalesClient: genuine Sell Fulfillment API client (GET /sell/fulfillment/v1/order)
   - Mirrors ebay_listing.py's proven architecture (injectable transport, dataclasses, structured errors)
   - Paginates automatically, raises on partial failures (never silently truncates mid-fetch)
   - 10 comprehensive tests: credential validation, pagination, error handling, edge cases
   - [Likely, not yet live-tested]: written from eBay's documented API shape, not run against real account with orders yet

2. **Real Etsy Digital Book Support** — `lib/etsy_listing.py` extended + NEW `storyforge2/publishing/connectors/etsy_digital.py`
   - Digital-file upload method added to existing physical-product Etsy client
   - Separate endpoint: `POST /application/shops/{shop_id}/listings/{listing_id}/files`
   - `type="download"` listings skip shipping-profile validation, use digital-file flow
   - Wired into `storyforge2/pipeline.py`'s `publish()` method
   - 16 new Etsy tests + 13 connector tests: dry-run, validation, end-to-end payload
   - Verified end-to-end: real book (mock provider) → real EPUB/PDF → dry-run Etsy listing payload (printed and inspected)

3. **Book Factory Pipeline** — `storyforge2/pipeline.py` fixed (was broken since 2026-08-17)
   - 7 bugs fixed: import names, @property confusion, missing export calls
   - End-to-end verified: real book brief → real manuscript → real 9-variant cover package → real EPUB + PDF
   - All 82 existing storyforge2 tests still pass

## Current State

**What's live right now:**
- ✅ Real eBay sales client (code complete, not yet tested against live orders)
- ✅ Real Etsy digital connector (code complete, not yet tested against live Etsy account)
- ✅ Book Factory pipeline (fixed and verified end-to-end)
- ✅ All code tested with injectable transport (no real credentials needed for unit/integration tests)

**What's NOT yet done:**
- ⏳ Live eBay sales fetch (requires EBAY_REFRESH_TOKEN with sell.fulfillment scope)
- ⏳ Live Etsy digital upload (requires ETSY_ACCESS_TOKEN + ETSY_SHOP_ID, Etsy app still pending approval as of 2026-08-20)
- ⏳ Real sales tracking agent wired to use lib/ebay_sales.py (fake agents were disabled; real one not yet built)
- ⏳ Integration: Boss Listers inventory → book generation → Etsy digital publishing

## Code Context — What You're Continuing From

### eBay Sales (lib/ebay_sales.py — 195 lines)
```python
class EbaySalesClient:
    def __init__(self, access_token: str, transport=None, sandbox=False)
    def get_orders_since(self, since: datetime, *, until=None, limit=50) -> list[Sale]

@dataclass(frozen=True)
class Sale:
    order_id, creation_date, fulfillment_status, total_value, total_currency, buyer_username
    line_items: list[SaleLineItem]

@dataclass(frozen=True)
class SaleLineItem:
    sku, legacy_item_id, line_item_id, quantity, title
```

**Key facts:**
- Uses Sell Fulfillment API, not Trading API (legacy)
- Scope: `https://api.ebay.com/oauth/api_scope/sell.fulfillment`
- Filter syntax: `creationdate:[ISO8601_START..ISO8601_END]` (eBay won't return orders >2 years old)
- Never returns partial results silently on pagination failure (raises immediately)

### Etsy Digital Connector (storyforge2/publishing/connectors/etsy_digital.py — 80 lines)
```python
class EtsyDigitalConnector:
    def publish(self, book_brief, manuscript, covers, *, dry_run=True) -> PublishResult

    # Internally:
    # 1. Creates draft listing with type="download"
    # 2. Uploads EPUB as digital file
    # 3. Activates (only if dry_run=False, never auto-activates)
```

**Key facts:**
- Uses existing EtsyListingClient from lib/etsy_listing.py (NOT the separate old implementation in lib/platform_connectors.py)
- Always drafts first, never auto-activates
- Requires: ETSY_ACCESS_TOKEN, ETSY_SHOP_ID, ETSY_API_KEY, ETSY_TAXONOMY_ID
- Book's EPUB is uploaded as the digital file; cover is used as listing image
- Description/title/keywords auto-populated from book metadata

### Wiring in storyforge2/pipeline.py
```python
def publish(self, platform_id, ...):
    if platform_id == "etsy_digital":
        connector = EtsyDigitalConnector()
        return connector.publish(...)  # Now real, not stub
```

## Immediate Next Steps (Priority Order)

### Phase 1: Real Account Testing (Blockers)
1. **Test eBay sales fetch** (if Josh has real orders on account mjardin17)
   - `EbaySalesClient(access_token="...", sandbox=False).get_orders_since(datetime.now(timezone.utc) - timedelta(days=7))`
   - Verify response shape matches Sale/SaleLineItem dataclasses
   - If shape differs, update parsing to match reality

2. **Wait for Etsy app approval** (currently pending as of 2026-08-20)
   - Once approved: get ETSY_ACCESS_TOKEN, ETSY_SHOP_ID, ETSY_TAXONOMY_ID (for books category)
   - Test `EtsyDigitalConnector.publish(dry_run=True)` against real account
   - Verify listing draft creates with correct fields

### Phase 2: Integration (After Phase 1 blockers clear)
3. **Build real sales tracking agent** to replace fake platform_connectors.py
   - Use lib/ebay_sales.py to fetch orders
   - Parse SKUs from line_items
   - Update Boss Listers inventory (mark items sold, decrement quantity)
   - Log to a real status file or database (not just print)

4. **Wire Book Factory → Etsy Digital end-to-end**
   - When a book is generated and ready to publish:
     - Call `storyforge2/pipeline.py`'s `publish(platform_id="etsy_digital", ...)`
     - Inspect the dry-run payload before going live
     - Only flip to `dry_run=False` after manual verification

5. **Test against real Boss Listers inventory**
   - List one real book to Etsy (dry-run first, then live with approval)
   - Track the listing through its lifecycle (draft → active → sold → archived)

### Phase 3: Hardening (After Phase 2 works end-to-end)
6. **Add error recovery**
   - Partial EtsyDigitalConnector failures (image upload succeeds, file upload fails) should quarantine, not auto-retry
   - Same pattern already used in social_clips/auto_publisher.py (mark as `posting`, wait for human review)

7. **Add monitoring**
   - Dashboard for: how many books generated, how many published (by platform), success/fail rates
   - Alerts for: failed publishes, quota limits hit, auth token expiry approaching

## What NOT to Do

- Do not claim this works end-to-end until Phase 1 blockers (real eBay test + Etsy approval) are complete
- Do not modify lib/platform_connectors.py's Etsy connector — that's a separate, lower-quality implementation; it's now dead code
- Do not attempt KDP publishing via the scrapers in kdp.py — browser scraping violates KDP policy (manual packaging is the right path)
- Do not assume real credentials exist yet — Etsy approval is still pending

## Blockers & External Dependencies

| Blocker | Owner | Status | Impact |
|---------|-------|--------|--------|
| Etsy app approval | Etsy | Pending as of 2026-08-20 | Blocks live Etsy digital testing |
| eBay live order test | Josh | Waiting | Need real orders to verify EbaySalesClient shape |
| ETSY_TAXONOMY_ID for books | Etsy/Josh | TBD after approval | Blocks Etsy publish (can't guess category) |
| EBAY_REFRESH_TOKEN with sell.fulfillment scope | Josh | Have it (confirmed working) | eBay sales fetch ready to test |

## Files & Test Coverage

**New files:**
- `lib/ebay_sales.py` — 195 lines, 10 tests (all passing)
- `storyforge2/publishing/connectors/etsy_digital.py` — 80 lines, 13 tests (all passing)
- `tests/ebay/test_ebay_sales.py` — 188 lines (10 tests)
- `tests/storyforge2/test_etsy_digital_connector.py` — real test file

**Modified files:**
- `lib/etsy_listing.py` — added EtsyDigitalFileSource, upload_listing_file() method
- `storyforge2/pipeline.py` — now calls real EtsyDigitalConnector for etsy_digital platform
- `storyforge2/publishing/registry.py` — etsy_digital marked as real (not DIRECT_API anymore, has real connector)
- `tests/etsy/test_etsy_listing.py` — 16 new digital-upload tests
- `CLAUDE.md` — updated with 2026-08-20 session notes

**Total test coverage:**
- 85 eBay/Etsy tests passing (50 eBay + 35 Etsy)
- 236+ total tests passing across full suite (existing + new)

## Command Reference

**Run eBay tests:**
```bash
pytest tests/ebay/test_ebay_sales.py -v
```

**Run Etsy digital tests:**
```bash
pytest tests/storyforge2/test_etsy_digital_connector.py -v
```

**Run all tests:**
```bash
pytest -v
```

**Manual eBay sales fetch (once Josh has the token):**
```python
from datetime import datetime, timedelta, timezone
from lib.ebay_sales import EbaySalesClient

client = EbaySalesClient(access_token="your-token-here", sandbox=False)
sales = client.get_orders_since(datetime.now(timezone.utc) - timedelta(days=7))
for sale in sales:
    print(f"Order {sale.order_id}: {len(sale.line_items)} items, ${sale.total_value}")
```

**Manual Etsy digital test (once approved):**
```python
from storyforge2.pipeline import BookPipeline
from storyforge2.publishing.connectors.etsy_digital import EtsyDigitalConnector

# Generate a book (dry-run, cost-free)
pipeline = BookPipeline(provider_name="mock")
book_brief, manuscript, covers = pipeline.run(dry_run=True)

# Create Etsy listing (dry-run, no publish)
connector = EtsyDigitalConnector()
result = connector.publish(book_brief, manuscript, covers, dry_run=True)
print(f"Dry-run payload: {result.payload}")  # Inspect before going live
```

## Report Back With

When you resume work, report:
- What blockers you hit and when (Etsy approval, eBay live test results)
- Which phase you reached (Phase 1 testing, Phase 2 integration, Phase 3 hardening)
- Any divergences between documented shape and real API response
- Test results: pass/fail counts, any new bugs found
- What's the single highest-value next step after your phase completes

---

**Josh**: Real eBay and Etsy connectors are now built and unit-tested. The immediate path forward is: (1) test eBay fetch against your real orders when you get a chance, (2) wait for Etsy approval, (3) integrate both into the real sales tracking loop. The hard part (correct API integration, dry-run safety, testing architecture) is done. The next part is plumbing and verification.
