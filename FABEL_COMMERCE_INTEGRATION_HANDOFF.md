# FABEL COMMERCE INTEGRATION HANDOFF

Generated: 2026-07-26 · Author: Claude (Fable 5) · Repo: video-bot-pipeline (`mjardin17/viral-engine`)

## 1. Final architecture

```
CONTENT (this repo — CrossPost lane, already clean):
  empire_render.py → renders/
      → channel_uploader.py            → YouTube
      → crosspost_bridge.py            → CrossPost queue → TikTok/IG/FB
      → social_clips/auto_publisher.py → platform clips
      → social_clips/product_promos.py → READ-ONLY shop links in descriptions  [NEW]

COMMERCE (BossLister lane):
  eBay Sell Inventory API
      ↕ (poll 15 min, pg_cron)  supabase/functions/ebay-sync   [BLOCKED BY CREDENTIALS]
  Supabase Postgres  irslzufsqjveyibkfjtz ("Boss listers prod")  — SOURCE OF TRUTH
      (NOT lgevctbpntndmbwgebwe — that's an unused empty project, don't deploy there)
      products / marketplace_accounts / marketplace_listings /
      marketplace_events / sync_logs / sync_state / storefront_products view
      ↕ service-role (server only)   boss-listers-mvp (Next.js, Josh's GitHub)
      ↓ anon key via public view     Cloudflare Pages Functions /api/storefront/*
      ↓                              index.html "Shop The Inventory" + Realtime
  extension/                          compliant fallback connector  [SCAFFOLD ONLY]
```

**Separation verdict:** CrossPost and BossLister were never entangled in code —
`crosspost_bridge.py`/`social_clips/` contain zero inventory logic. The
"correction" was implemented as guardrails: CrossPost gets a read-only public
promo module; all writes flow through BossLister's DB layer.

## 2. Repository map

| Piece | Location |
|---|---|
| CrossPost (content) | this repo: `crosspost_bridge.py`, `social_clips/`, `channel_uploader.py` |
| BossLister DB + eBay sync | this repo: `inventory-sync/` |
| Storefront API + website | this repo: `functions/`, `index.html` |
| Extension scaffold | this repo: `extension/` |
| BossLister app (real MVP) | `C:\Users\jjard\claude\boss-listers-mvp` (clone of `mjardin17/boss-listers-mvp`, branch `feat/supabase-inventory`, staged, NOT pushed) |

## 3–4. Files created / modified this session (2026-07-26)

**Created (this repo):**
- `inventory-sync/supabase/migrations/0003_commerce_hardening.sql`
- `functions/_lib/supabase.ts`
- `functions/api/storefront/products.ts`
- `functions/api/storefront/products/[slug].ts`
- `functions/api/storefront/inventory/[sku].ts`
- `social_clips/product_promos.py`
- `extension/manifest.json`, `extension/background/service_worker.js`,
  `extension/types/adapter.d.ts`, `extension/marketplace-adapters/poshmark.stub.ts`,
  `extension/README.md`
- this file

**Created (boss-listers-mvp clone, branch `feat/supabase-inventory`):**
- `boss-listers-mvp/lib/supabaseInventory.js` (server-only service-role bridge)
- `boss-listers-mvp/pages/api/inventory.js` (GET list / POST publish)
- `boss-listers-mvp/.env.example` — appended `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`

**Modified:** `inventory-sync/supabase/migrations/0002_schedule_ebay_sync.sql`
(project ref `irslzufsqjveyibkfjtz` filled in), `index.html` (Supabase URL +
publishable key filled in, pair verified live), `CLAUDE.md`.

(Prior session 2026-07-25 created the base: 0001 migration, ebay-sync function,
`/api/products`, boss-listers-ai starter-kit wiring — see CLAUDE.md.)

## 5–6. Database schema & migrations

Run in order via `npx supabase db push` (or SQL editor): `0001` core tables +
RLS + realtime → `0002` pg_cron schedule → `0003` commerce hardening (slug,
published, sold/reserved qty, `sync_version` optimistic locking,
`marketplace_accounts`/`marketplace_listings`/`marketplace_events`,
`record_sale()` idempotent+oversell-safe sale function, `storefront_products`
public view). **None applied yet** — the Supabase project is empty (mobile SQL
editor paste failed; use the CLI from the PC).

## 7–10. Responsibilities

- **BossLister:** products, SKUs, pricing, quantity, marketplace listing IDs,
  eBay sync, oversell prevention (`record_sale` is the ONLY sanctioned
  decrement path), storefront publishing (`published` flag).
- **CrossPost:** video publishing + scheduling + captions; may read
  `/api/storefront/products` via `social_clips/product_promos.py` to append
  tracked shop links. MUST NOT write inventory (module is credential-free by
  design).
- **Website:** reads `storefront_products` view through cached Pages Functions
  + anon-key Realtime. No service-role key, no eBay calls, no reconciliation
  in browser JS.
- **Extension:** compliant fallback for API-less marketplaces. Fill-only,
  never submits, never touches CAPTCHA/MFA, minimal permissions. SCAFFOLD.

## 11. Integration classifications (honest)

| Integration | Status |
|---|---|
| eBay sync | **BLOCKED BY CREDENTIALS** — code complete, no eBay developer account/refresh token exists |
| Supabase schema | **IMPLEMENTED BUT UNVERIFIED** — SQL not applied (empty project, Docker down so no local test) |
| Storefront API | **IMPLEMENTED BUT UNVERIFIED** — parses/builds clean; not deployed (needs Pages env vars) |
| Website live inventory | **IMPLEMENTED BUT UNVERIFIED** — anon key placeholder remains in index.html |
| boss-listers-mvp bridge | **IMPLEMENTED BUT UNVERIFIED** — staged on branch, not pushed, no env vars set |
| CrossPost promo module | **PARTIAL (failure path VERIFIED)** — live run confirmed graceful skip on API failure; happy path untestable until storefront deploys |
| Browser extension | **NOT IMPLEMENTED** — compliant scaffold only |

## 12. API endpoints

Public (Cloudflare Pages Functions, anon key + public view only):
- `GET /api/products` — legacy, kept for index.html back-compat
- `GET /api/storefront/products[?q=]` — cached 300 s
- `GET /api/storefront/products/:slug` — cached 300 s
- `GET /api/storefront/inventory/:sku` — cached 60 s

Admin (server-side, boss-listers-mvp Next API, service-role):
- `GET/POST /api/inventory` — list / publish manual product

Not built (deferred): `/api/admin/*` auth'd suite, categories/search
endpoints, eBay import/reconcile endpoints (blocked on credentials anyway).

## 13. Environment variables

| Var | Where | Status |
|---|---|---|
| `EBAY_CLIENT_ID/SECRET/REFRESH_TOKEN/ENVIRONMENT` | Supabase Edge Function secrets | ❌ Josh must create eBay dev app |
| `SYNC_TRIGGER_SECRET` | Edge Function secret + Vault (`sync_trigger_secret`) | ❌ generate at deploy |
| `sync_service_role_key` | Supabase Vault | ❌ |
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` | Cloudflare Pages env + index.html | URL ✅ / anon key ❌ |
| `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` | boss-listers-mvp server env (Render/Vercel) | ❌ |
| `OPENAI_API_KEY` | boss-listers-mvp (existing vision feature) | Josh had this already |

Security invariants: service-role key server-side only; anon key public-safe
because RLS grants only SELECT on products/view; `record_sale` execute revoked
from anon+authenticated; extension carries zero secrets.

## 14–17. Setup / dev / deploy

- **OAuth + full deploy runbook:** `inventory-sync/DEPLOY.md` (eBay consent
  flow, secrets, pg_cron, Pages env, boss_lister role grant).
- **Extension:** `extension/README.md` (not installable-useful yet).
- **boss-listers-mvp local dev:** `cd C:\Users\jjard\claude\boss-listers-mvp\boss-listers-mvp
  && npm install && npm run dev` (fill `.env` from `.env.example`).

## 18–19. Tests executed (evidence in session log 2026-07-25/26)

| Check | Result |
|---|---|
| esbuild parse: 16 TS files (edge fn, pages fns, boss-listers libs, extension stub) | ✅ pass |
| `node --check` service_worker.js; JSON.parse manifest.json | ✅ pass |
| `ast.parse` + live run `product_promos.py` | ✅ pass — **forced-failure test:** storefront 403 → graceful skip, publish not blocked |
| `new Function()` parse supabaseInventory.js | ✅ pass |
| SQL migrations against real Postgres | ⏭️ skipped — Docker daemon down, Supabase empty |
| E2E workflow (product→eBay→storefront→sale→decrement) | ⏭️ skipped — blocked by credentials |

## 20. Known blockers

1. No eBay developer account / refresh token (Josh, manual).
2. Supabase migrations unapplied (paste failed on mobile; run CLI on PC).
3. Anon key not yet in index.html / Pages env.
4. boss-listers-mvp branch unpushed (needs Josh approval + git auth).
5. `gh` CLI unauthenticated on this machine.
6. Free-tier constraint honored: no paid APIs anywhere in this system.

## 21. Future marketplace adapter plan

Official APIs first: Etsy → Shopify → TikTok Shop → Amazon SP-API → Walmart.
Each becomes an Edge Function sibling of `ebay-sync` writing
`marketplace_listings` + calling `record_sale`. Extension adapters
(Poshmark → Mercari → Depop → Vinted) implement `types/adapter.d.ts` only
after the backend token endpoint exists.

## 22. Rollback

- DB: `drop view storefront_products; drop function record_sale; drop table
  marketplace_events, marketplace_listings, marketplace_accounts;` then
  `alter table products drop column slug, published, sold_quantity,
  reserved_quantity, sync_version;` (or nuke the empty project).
- Repo: all new paths are additive — `git checkout -- .` / delete new dirs.
- boss-listers-mvp: delete local branch; origin untouched.

## 23. Next-agent prompt

> Read `FABEL_COMMERCE_INTEGRATION_HANDOFF.md` and `inventory-sync/DEPLOY.md`.
> Blockers 1–4 are Josh-manual; help him run `npx supabase db push` from the
> PC, then set the anon key in index.html + Cloudflare Pages, deploy
> `ebay-sync` once eBay credentials exist, and wire `marketplace_listings`
> writes + eBay order polling → `record_sale()` into the sync function.
> Do not claim anything is LIVE until an authenticated request succeeds.
