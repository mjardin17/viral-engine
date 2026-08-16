# Boss Listers — Handoff for a new session

This is a status snapshot, not a build-in-progress doc — unlike Story Forge 2, no active build was running against this project in the session this was written from. Everything below is either verified directly (git state, file presence) or clearly marked as coming from `CLAUDE.md`'s own history, which itself may have drifted from reality — verify before trusting.

## The real project: `boss-listers-mvp`

- **Local path**: `C:\Users\jjard\claude\boss-listers-mvp\boss-listers-mvp\` — note the **nested folder**: the outer `boss-listers-mvp\` only has `.git\` and `render.yaml`; the actual Next.js app (`package.json`, `pages\`, `lib\`, `functions\`, `supabase\`) lives one level deeper, in the inner `boss-listers-mvp\boss-listers-mvp\`. This nesting is real, not a mistake to "fix" by flattening — every path reference elsewhere assumes it.
- **GitHub**: `mjardin17/boss-listers-mvp`, branch `main`, confirmed at commit `1e3548e` ("fix: restore missing deps and add PriceCharting evidence-based valuation") as of this write. Local `main` == `origin/main`, clean tree, verified via `git status`/`git log` directly — not assumed.
- **What it is**: a multi-tenant trading-card resale/listing app. Photo-capture → AI card identification (Gemini vision) → evidence-based pricing (PriceCharting) → multi-channel listing packages (manual export for FB Marketplace/OfferUp/Craigslist/Mercari/Poshmark; real eBay Trading API sync; Etsy/Shopify scaffolded, not credentialed).
- **9 Supabase migrations applied** (`supabase/migrations/0001` through `0009`), confirmed present on disk: inventory init, eBay sync scheduling, commerce hardening, channels+grants, listings+storage, commercials, multi-tenant conversion, security hardening, storefront-view fix.
- **Supabase project**: `irslzufsqjveyibkfjtz` ("Boss listers prod"). Do not confuse with the other, unused Supabase project `lgevctbpntndmbwgebwe` ("mjardin17's Project") — that one is empty and was flagged in earlier session notes as a candidate for deletion to avoid confusion, never acted on.
- **Deploy target**: Cloudflare Pages (`boss-listers.pages.dev`) via `wrangler.toml` + `functions/` — **not** Vercel, despite an earlier deploy attempt landing there. A prior audit (recorded in this repo's `CLAUDE.md`) found the Vercel deployment has **no working backend** (`next.config.js` uses `output: 'export'`, so all `/api/*` routes compile but never deploy) and sits behind Vercel's Deployment Protection auth wall. If reviving deployment, Cloudflare Pages is the real target, not a re-attempt on Vercel.
- **eBay sync status (per CLAUDE.md's own audit, unverified by me this session)**: the Edge Function reads `EBAY_{SANDBOX|PRODUCTION}_APP_ID/_CERT_ID/_DEV_ID/_USER_TOKEN` (legacy Trading API), **not** the OAuth secrets (`EBAY_CLIENT_ID`/`EBAY_CLIENT_SECRET`/`EBAY_REFRESH_TOKEN`) that were actually set up during a consent flow — those three are dead, never read. `EBAY_ENVIRONMENT` defaults to `production`, which is currently disabled pending Amazon's marketplace-deletion-notification compliance — needs to be explicitly set to `sandbox`. Also fails silently (missing-env throw sits outside the try/catch, so an empty `sync_logs` table looks identical to "cron never fired" — don't diagnose an empty log table as a cron problem without checking this first).
- **Setup guide**: `CHANNEL_SETUP.md` in the inner app folder has exact env var names for every channel connector.

## The other repo: `BOSS-LISTERS` (all-caps) — do not confuse with the above

- **Local path**: `C:\Users\jjard\claude\BOSS-LISTERS\`
- **GitHub**: `mjardin17/BOSS-LISTERS`, 2 commits total ("Initial commit", "feat: initialize project structure and base app") — essentially a fresh scaffold, not the real product. If a new session goes looking for "Boss Listers" and lands here first, that's the wrong repo — redirect to `boss-listers-mvp` above.

## "Buzz" — flagging a likely misunderstanding before it propagates

You asked for "the finished buzz project for agents." What's actually on disk is **not an in-house finished product** — it's a git clone of `block/buzz`, a real external open-source project from Block Inc., sitting in a folder literally named `buzz-research`:

- `C:\Users\jjard\claude\buzz-research\buzz\` — clone of `github.com/block/buzz`, branch `main`, at `block/buzz`'s own commit `cf03bd7` ("Improve desktop search scoping (#5306)" — a real numbered PR from that project's own history). Clean tree.
- A second clone of the same external repo exists at `C:\Users\jjard\eval\buzz\` (also `origin` = `github.com/block/buzz`) — looks like a second checkout for evaluation, not a different or more-finished version.
- A third, non-git copy/setup-script bundle sits at `C:\Users\jjard\Downloads\Cprojectsbuzz\` (`setup-buzz*.bat` scripts) — never inspected this session, unclear if it's just install scripts for the same external tool or something else.

This matches `CLAUDE.md`'s description of a "Buzz relay" used for agent-to-agent status messages (`#video-pipeline`, `#commercials` channels, `ws://localhost:3000`) — but that description reads as **research into adopting Block's Buzz tool for that purpose**, not confirmation that it's wired in and running. I did not check this session whether Buzz is actually running, whether Empire OS agents actually connect to it, or whether `BUZZ_RELAY_URL`/`BUZZ_PRIVATE_KEY` in `.env` point at a real live instance. Don't carry forward "Buzz is finished and agents use it" as settled fact — verify by trying to connect to `ws://localhost:3000` and checking whether anything's listening, and by checking whether any agent code actually publishes to it, before building anything else on top of that assumption.

## What wasn't checked this session

- Whether the Cloudflare Pages deployment is live and serving real traffic.
- Live status of the eBay sync (whether `sync_logs` has ever had a real row).

If the next session's first move is "make sure Boss Listers actually launches," start there before trusting anything else in this doc as more than a starting point.

---

# VERIFIED — 2026-08-15 session

Everything above was re-checked by running it, not by reading notes. Results below
supersede the "what wasn't checked" list.

## ✅ It builds. Structure and git state were accurate.

`npm run build` succeeds from the inner folder. The nested-path layout, the
`1e3548e` commit, clean tree, `main == origin/main`, and the 9 migrations on disk
are all confirmed exactly as described above.

**The `output: 'export'` finding is confirmed by Next.js itself**, not just by the
earlier audit. The build prints: *"Statically exporting a Next.js application via
`next export` disables API routes and middleware."* All 9 `pages/api/*` routes plus
`middleware.js` compile and are then discarded — `out/` contains only static pages.
Cloudflare Pages is the real target; `functions/` supplies the backend there.

⚠ **`functions/` does NOT cover the same surface as `pages/api/`** — this is a gap,
not a clean swap. Cloudflare has 7 handlers, Next has 9 routes, and they only
partially overlap:

| Only in `functions/` (CF) | Only in `pages/api/` (Next) | In both |
|---|---|---|
| `billing`, `commercials`, `identify-card` | `channels` (+`test`, `manual-package`, `manual-status`), `inventory`, `uploads/[file]` | `analyze`, `health`, `listings` |

So the **entire `/api/channels/*` surface — the manual-export listing packages that
`CLAUDE.md` calls the one feature "working now" — has no Cloudflare backend.** On a
Pages deploy the `/channels` page ships but its four API routes 404. Whoever revives
deployment should treat this as the blocking item, not the eBay credentials.

## 🔴 Tests fail: 10 failing, and it is not a trivial rename

`npm test` → 10 failures, all in `tests/cardPricing.test.js`.

**Cause:** the tests `require('../lib/cardPricing')` destructuring **`isExactMatch`**,
which that module does not export. It exports `textMatchesIdentity`. Nine tests
throw `TypeError: isExactMatch is not a function`.

**This is not a rename — the two functions have materially different contracts.**
The tests assume PriceCharting returns *structured* fields (`cardNumber`, `parallel`,
`isLot`, `isReprint`, `isDigital`, `gradingCompany`). `lib/cardPricing.js`'s own header
documents — citing the live API docs as of 2026-08-12 — that **PriceCharting has no
structured fields at all**, only free-text `product-name`/`console-name`, which is
precisely why the implementation does token matching instead. **The implementation
reflects the real API; the tests encode an earlier, idealized design that was never
built.** Deleting the tests to go green would throw away the safety intent below.

**The 10th failure is separate and worth its own look:** `getCardValuation: exact
match returns PROVIDER_ESTIMATE` fails on the *number*, not the missing function —
the fixture expects `market === 10` (`cib-price`) for a **raw/ungraded** card, but the
implementation maps ungraded → `loose-price` → `5`. The implementation matches
PriceCharting's published card key table (loose = Ungraded, cib = Grade 7–7.5), so
the **fixture's expectation looks wrong**, not the code. [Likely, not Certain — worth
one confirm against their live "Description of Keys" table before changing anything.]

## 🔴 Real gap the failing tests are pointing at (money risk)

The stale tests are wrong about the *API shape* but right about the *danger*. The
module header claims strict matching, and `textMatchesIdentity` does not deliver it:

- **`parallel` is never checked.** `fields.parallel` is never added to the required
  token list. A base card, a Gold Refractor, and a Superfractor all match each other.
  Parallels routinely differ 10–100x in price. **This is the highest-value bug here.**
- **Lots, reprints, and digital cards are not excluded.** Token matching is
  `haystack.includes(token)`, so a product named `"2024 Topps Chrome #123 Lot of 5"`
  or `"... Reprint"` or `"... Digital"` contains every required token and matches.

Raw-vs-graded is *not* in this list — that one is genuinely handled, correctly, by
selecting the price *field* rather than filtering products, which suits PriceCharting's
one-product-many-tiers model.

**Not fixed this session — deliberately.** Tightening this changes what price Josh
lists real cards at, and the right fix (exclude lots/reprints/digital, require
parallel agreement) is a product decision about false-negatives vs mispricing, not a
mechanical patch. Flagging for a decision rather than guessing.

## 🔴 Buzz is NOT wired in. The handoff's caution was correct.

Confirmed dead, three independent ways:

1. **`buzz-cli` is not on PATH** (`which buzz-cli` → not found). Seven agents shell
   out to it (`video_pipeline_agent`, `crosslister_agent`, `platform_sync_agent`,
   `price_sync_agent`, `sales_tracker_agent`, `scanner_uploader_agent`,
   `whatnot_specialist_agent`).
2. **Port 3000 is listening — but it is Docker, not Buzz.** PID 19412 is
   `com.docker.backend.exe`, PID 8664 is WSL's `wslrelay.exe`. Anyone checking
   "is something on 3000?" as a proxy for "is Buzz up?" gets a **false yes**.
3. **The clone was never built.** `buzz-research/buzz/` is a Rust project
   (`Cargo.toml`) with no compiled binary — consistent with research, not adoption.

**It fails silently by construction.** `agents/video_pipeline_agent.py:60` reads
`elif "not found" not in stderr.lower():` — the one error this situation actually
produces is the exact string the code suppresses. Every agent prints `#video-pipeline:
<msg>` to stdout and reports nothing wrong while posting nowhere. Do not treat clean
agent logs as evidence Buzz is working.

Net: **"Buzz is finished and agents use it" is false.** Agents degrade to stdout, which
is survivable — but no cross-agent messaging exists today.
