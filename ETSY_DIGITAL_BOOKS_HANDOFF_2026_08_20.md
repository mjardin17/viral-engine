# Extend Etsy for Digital Book Sales — Handoff Prompt (2026-08-20)

Paste this whole file into a fresh Claude Code session in
`C:\Users\jjard\claude\video-bot-pipeline` to build this.

## Context — read first
Tonight, two real things were built and verified in this repo, independently:

1. **A real, working Etsy client for physical products** —
   `lib/etsy_listing.py` (dataclass validation, dry-run default, draft-first
   publish flow) + `scripts/listing_service.py` (the bridge service Node
   code calls). 34 tests passing. Verified against Etsy's real, current API
   parameter tables. Currently used for physical trading cards.
2. **A real, working Book Factory pipeline** — `storyforge2/pipeline.py`,
   fixed tonight (was broken since 2026-08-17). Verified end-to-end: a real
   book brief produces a real manuscript, a real 9-variant cover package,
   a real EPUB (`storyforge2/export/epub.py`), and a real PDF
   (`storyforge2/export/pdf.py`). This actually ran and produced real files
   on disk tonight — this is not aspirational.

**The gap these two don't yet bridge:** nothing calls the Etsy client with a
finished book's EPUB/PDF. `storyforge2/publishing/registry.py` lists
`etsy_digital` as `DIRECT_API` with the note "Wraps existing
lib/platform_connectors.py. Not yet wired into Story Forge 2." — that
`lib/platform_connectors.py` Etsy connector is a **different, older,
independent implementation** (see CLAUDE.md's 2026-08-20 audit) — do not
use it. Build against `lib/etsy_listing.py`, the real one, same as the
card-selling code does.

## What's actually different about digital vs. physical Etsy listings
Etsy's Open API v3 handles both through the same core endpoints
(`POST /application/shops/{shop_id}/listings`), with real differences:

- `type` field: `"download"` for digital products, not `"physical"`.
- No `shipping_profile_id` required for digital listings (it's required
  for physical, per `lib/etsy_listing.py`'s existing validation — that
  validation needs a corresponding branch for digital, not a copy-paste
  bypass).
- Digital files attach via a **separate endpoint**:
  `POST /application/shops/{shop_id}/listings/{listing_id}/files` — this
  needs building; `lib/etsy_listing.py` currently only has image upload
  (`uploadListingImage`-equivalent), not a digital-file upload method.
- `who_made`/`when_made`/`is_supply` — Etsy's cross-field policy validation
  (already real and implemented in `lib/etsy_listing.py`'s
  `EtsyProduct.__post_init__`) may not apply the same way to digital
  downloads — **verify this against Etsy's real, current API docs before
  assuming the existing validation logic transfers as-is.** Do not guess;
  the existing validation was built from a real parameter table
  (`gordonturner/etsy-open-api-client` on GitHub) — find the current
  equivalent for digital listings the same way, don't invent field names.

## Task
1. Read `lib/etsy_listing.py` fully before changing it — understand
   `EtsyProduct`, `EtsyImageSource`, `EtsyListingClient.create_listing()`,
   and the existing dry-run/draft/activate gating before extending it.
2. Verify Etsy's real digital-listing requirements directly against their
   current API docs or a current, real parameter reference (same method
   used to verify the physical-listing fields — cite the actual source).
3. Add digital-file support: a new `EtsyDigitalFileSource` (mirrors
   `EtsyImageSource`'s validation pattern — real local path or https URL,
   size/type checks) and a method to attach it via the real files endpoint.
4. Extend `EtsyProduct` (or add a sibling dataclass, whichever avoids
   breaking existing physical-listing callers) so `type="download"`
   listings skip shipping-profile validation and use the digital-file flow.
5. Wire `storyforge2/pipeline.py`'s `publish()` method to call this for the
   `etsy_digital` platform_id — right now it correctly reports
   `not_implemented` for every DIRECT_API platform except `manual_export`;
   this is the one to make real.
6. Write tests mirroring the existing physical-listing test structure
   (`tests/etsy/test_etsy_listing.py`) — dry-run coverage, validation
   coverage, at minimum.
7. Run a real end-to-end dry-run: a real book (use `storyforge2/pipeline.py`
   to generate one with the `mock` provider, zero cost, same as tonight's
   verified test) through to a dry-run Etsy digital listing payload. Print
   and inspect the actual payload — don't just check it didn't crash.

## What NOT to do
- Do not claim this works without running it — same standing rule as the
  rest of tonight's work (see CLAUDE.md's "verify before production-ready"
  entry).
- Do not touch `lib/platform_connectors.py`'s Etsy connector — that's a
  separate, unrelated, lower-quality implementation; extending it would
  create a second, diverging Etsy client.
- Do not assume real credentials exist — Etsy's real app is still pending
  their approval as of tonight (see CLAUDE.md). This task is buildable and
  testable entirely in dry-run without real credentials; live-testing
  happens later, once Josh has the real Etsy keys.
- Do not promise a timeline or call this "production-ready" until it has
  actually been run against a real Etsy account and produced a real
  listing — same discipline, no exceptions.

## Report back with
- What Etsy's real digital-listing requirements actually are (cited source)
- The diff/new files
- Real test output (pass/fail counts)
- The actual dry-run payload printed from a real end-to-end run
- What's still missing before this could go live (real Etsy credentials,
  anything else discovered while building)
