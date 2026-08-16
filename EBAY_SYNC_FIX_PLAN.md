# eBay Sync — verified state and fix plan

Written 2026-08-15. Everything in "Verified" was checked by reading the code in
`inventory-sync/supabase/functions/ebay-sync/` this session, not carried over
from notes. Two earlier claims in `CLAUDE.md` turned out to be wrong and are
corrected below.

## Why this matters right now

The storefront is empty because nothing has ever written inventory into it.
`storefront_products` requires `published = true` and
`status in ('active','out_of_stock')`; it currently returns `[]`. eBay sync is
the intended writer, and it has never completed a run.

**Good news, verified:** `buildProductRow` (`lib/upsert.ts:15-30`) omits both
`published` and `tenant_id`, but that is **not** a bug —
`published boolean not null default true` (`0003:11`) and `tenant_id` is
NOT NULL **with a default** of the seed tenant (`0007:121-122`). So a
successful sync lands rows that the storefront view will show, with no
additional mapping work. Nothing to fix in the write path.

## Verified — what is actually true

| # | Fact | Evidence |
|---|---|---|
| 1 | Function reads `EBAY_{SANDBOX\|PRODUCTION}_APP_ID/_CERT_ID/_DEV_ID/_USER_TOKEN` | `index.ts:50-53` |
| 2 | `EBAY_ENVIRONMENT` defaults to **production** when unset | `index.ts:46` |
| 3 | `EBAY_CLIENT_ID` / `EBAY_CLIENT_SECRET` / `EBAY_REFRESH_TOKEN` are read by **nothing** | absent from the whole function |
| 4 | The OAuth/Sell-Inventory implementation is **dead code** — `ebayAuth.ts` and `ebayClient.ts` are imported by no file | import graph |
| 5 | Live path is the legacy **Trading API**: XML `GetMyeBaySelling`, token placed verbatim in `<eBayAuthToken>`. No OAuth exchange exists anywhere. | `tradingApiClient.ts:27,48` |
| 6 | Failure is **silent** — `requireEnv` at `:50-53` sits outside the `try` at `:57`, and `await runSync()` at `:112` has no try/catch, so the `sync_logs` insert at `:115` never runs | `index.ts` |
| 7 | **Only the first page is ever fetched.** `maxPages = Math.min(1000, totalPages)` is computed while `totalPages` is still `1`, as a `const` — the loop runs exactly once, capping every sync at 100 listings | `tradingApiClient.ts:90` |

**Consequence of #6:** an empty `sync_logs` table looks identical to "cron never
fired." Do not diagnose this as a scheduling problem.

**Correction to `CLAUDE.md`:** it records `DEPLOY.md` as the likely origin of the
wrong secret names. It isn't. `DEPLOY.md:82` says "Under **User Tokens**,
generate an Auth Token," and `:93-107` list the correct
`EBAY_SANDBOX_*`/`EBAY_PRODUCTION_*` names. Only `:203` is stale (references
`EBAY_REFRESH_TOKEN`). **The documentation was right; the setup followed a
different path.** The wrong-token-type problem came from running an OAuth
consent flow, which this code never uses.

**Correction to severity:** `CLAUDE.md` describes the pagination bug as affecting
"any seller with >100 active listings." It is worse — `maxPages` is frozen at
`1` before the first request, so the loop always runs exactly once regardless of
what eBay reports.

## Not verified

- Whether the function is currently **deployed** at all (needs Supabase CLI auth
  or a service-role key; neither available this session).
- Whether the production keyset is disabled pending eBay's marketplace-deletion-
  notification compliance. [Reported in `CLAUDE.md`, not confirmed this session.]
- The two Deno test files (`tradingApiClient.test.ts`, `upsert.test.ts`) could
  not be run — **Deno is not installed on this machine.**

---

## Phase 0 — the blocking decision (Josh)

**Sandbox or production?** Everything downstream depends on it, and neither is
free:

- **Production** is what actually populates a real storefront — but is reportedly
  blocked until eBay's compliance requirement is met.
- **Sandbox** works today, but syncs *sandbox* listings. It proves the pipeline
  end-to-end and populates nothing real.

Recommendation: **sandbox first**, purely to prove the chain, while the
production keyset is sorted out separately. But do not confuse a green sandbox
run with a working storefront.

## Phase 1 — code fixes (no credentials needed, can be done now)

| Fix | File | What |
|---|---|---|
| **A** | `tradingApiClient.ts:86-104` | Restructure the loop so `totalPages` is read from the response and the cap is applied per-iteration (`do/while`, or recompute inside the loop). Currently caps every run at one page. |
| **B** | `index.ts:112` | Wrap `await runSync()` in try/catch (or move the `requireEnv` calls inside the existing `try`) so a missing env var produces a `sync_logs` row instead of vanishing. **This is the highest-value fix** — it converts every future failure from invisible to diagnosable. |
| **C** | `lib/ebayAuth.ts`, `lib/ebayClient.ts` | Delete, or move to an `unused/` folder with a README. They describe an OAuth flow the function does not use, and they are why the wrong credentials were obtained. |
| **D** | `DEPLOY.md:203` | Replace the stale `EBAY_REFRESH_TOKEN` reference with the correct `EBAY_{ENV}_USER_TOKEN`. |

Doing **B before anything else** is worth it on its own: it means the next failed
run tells you *why* instead of leaving an empty table.

Worth adding: install Deno so fix **A** can be verified by the existing test file
rather than by deploying and hoping.

## Phase 2 — credentials (Josh only, in Supabase — never in chat)

1. Set `EBAY_ENVIRONMENT` **explicitly**. Do not rely on the `production`
   default, especially if production is disabled.
2. Set all four vars for the chosen environment: `_APP_ID`, `_CERT_ID`,
   `_DEV_ID`, `_USER_TOKEN`. The **Dev ID** is the one never collected during
   the OAuth attempt — it is required and has no OAuth equivalent.
3. Generate the token via **User Tokens → Auth Token** in the eBay portal
   (`DEPLOY.md:82`), *not* an OAuth consent flow.
4. **Delete** the three inert secrets (`EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET`,
   `EBAY_REFRESH_TOKEN`) so the next person doesn't assume they're live.

## Phase 3 — verification (in order; stop at the first failure)

1. Invoke the function manually with the `x-sync-trigger-secret` header
   (`index.ts:101-103`) — do not wait 15 minutes for cron.
2. Confirm a `sync_logs` row exists. **After fix B this happens even on failure**,
   so an empty table now means the function didn't run at all.
3. Confirm `storefront_products` returns rows (it returns `[]` today).
4. Only then fix `InventorySection.tsx` in `mjardin17/jardin-outpost` — swap
   `products` → `storefront_products` and `id` → `slug` (the view has no `id`
   column). Doing it before this point renders an empty list correctly.
