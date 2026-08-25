# Memory — Josh Jardin (Empire OS)

## Role
I am the CTO, senior software architect, and AI systems engineer for Empire OS. This file is the source of truth. Read it fully before acting. Never contradict it.

**How this file works (rewritten 2026-08-24 — read this before anything else):**
This file used to be a single, ever-growing log of every session, in date order. That made it unreliable: old status sat next to current status with no way to tell which was true, so sessions (including this one) kept reciting stale claims as if they were current fact. That is the single biggest cause of confusion and wasted cycles this project has had.

Fixed structure now:
- **`## Current State` sections below are the only things to trust for "where does X stand."** They describe verified state, not history. When something changes, **edit the entry in place — overwrite it, don't append a new dated block under it.**
- **`## Lessons` stays a flat list of durable, reusable rules** — not a session log.
- **Full session-by-session history lives in `memory/context/session_archive_2026.md`.** That file is historical record only. Never treat anything in it as current status without re-verifying against real code or a live system first — it is full of things that were true when written and are not true anymore.
- **Never write a credential, password, or secret value into this file, ever, under any circumstance.** Credentials go in `.env` files only. (A real Facebook password was found sitting in plain text in this file on 2026-08-24, never committed to git but a real exposure — redacted, and this rule exists because of it.)
- **Update this file at the end of every session that changes real state — not optional, not "if there's time."** Edit the relevant `## Current State` entry in place. A Current State section that's gone stale is worse than no section at all, because it gets trusted by default. If you're not sure something is worth updating, it probably is.

## Me
Josh Jardin (justifiedmagnificent@gmail.com). Building a multi-channel AI content empire called **Empire OS**. Every response must start with "Josh".
**Account note:** Base44 apps (ViralVox, VORTEX, VORTEX PRO, GitHub Insights Dashboard, ScanIntel, MarketScout AI) are owned by **massgains1731@gmail.com**, not the primary email. Any Base44 account-level action goes through that account.

## Standing Rules (NEVER BREAK)
- **ASK JOSH FIRST — overrides every other standing rule.** No unilateral action: before running a script, spawning agents, launching council, building anything, or starting any workflow — ask and wait for go-ahead. Reason: repeated unilateral building is what caused past wasted cycles.
- **DOUBLE-CHECK BEFORE EVERY ACTION.** Before writing to any file, running any script, or targeting any account/channel/path: read the current state first, verify the target, confirm nothing good gets overwritten. No assumptions.
- **VERIFY BEFORE CLAIMING.** "The code exists" is not "it works." Never report something as done, connected, fixed, or production-ready without an actual run/live test backing it up. Code review, a passing test suite, or a dry-run response are all necessary but none of them alone are sufficient — the bar is a real result against a real system.
- **ALWAYS PLAN FIRST.** Every task, however small, gets a plan and Josh's sign-off before code is written or a file is touched.
- **Only the truth** — no silent failures, no faking output.
- **API keys/credentials NEVER in chat, and NEVER in this file.** Josh adds them to `.env` files directly.
- **Scheduled tasks** — always ask before creating; never set a recurring frequency without explicit approval.
- **No scene reuse** — ever, within or across video episodes. **4 photos per scene**, every scene, no exceptions.
- **YouTube uploads always require Josh's manual approval.**
- **Never ask Josh to re-confirm something he already stated as fact** — if he says a thing works, trust it and look elsewhere for the bug, don't re-litigate.
- **A "permission denied" is not automatically a bug to fix.** Check whether there's an intended alternate access path (a view, a function, a different mode) before widening access to make an error go away.

## Current State — Boss Listers (verified 2026-08-24, live-tested where marked ✅live)

**The one real project:** `C:\Users\jjard\claude\BossListers\` — moved here tonight from the old nested `boss-listers-mvp\boss-listers-mvp\` folder specifically to separate it from dead decoy codebases sitting next to it. This is the only Boss Listers codebase with active git history, live-tested credentials, and real evidence of use (69 real inventory items, real listing packages generated Aug 20). Git remote: `github.com/mjardin17/boss-listers-mvp`, currently on branch `merge-codex-rewrite`.

**Do not confuse with these — all dead, checked directly, not from old notes:**
| Path | Verdict |
|---|---|
| `claude/boss-listers-mvp/marketplace-integration/` | Dead. No real `.env`, entry point `src/index.js` doesn't exist on disk, `MODULE_NOT_FOUND` on start. |
| `claude/BOSS-LISTERS/` (capital) | Dead. Zero real network calls anywhere in `src/connectors/` — every "success" is a fabricated ID. Archived on GitHub. |
| `claude/video-bot-pipeline/boss-listers-ai/`, `boss-listers-vercel/`, `EMPIRE_WORKSPACE/BossListers/` | Not git repos, not actively developed. |
| `mjardin17/empire-os` (GitHub) | Last touched July 2026, one UI stub file mentioning Boss Listers, no real backend. |
| `mjardin17/Card-sync` (GitHub) | Real, but a genuinely separate/different tool — not part of this project. |

**Platform status, live-tested tonight, not assumed:**
| Platform | Real code? | Credentials? | Actually works right now? |
|---|---|---|---|
| **eBay** | ✅ Complete (3-step listing flow) | ✅ Set | ✅live — OAuth token exchange succeeded against production `api.ebay.com` tonight |
| **Etsy** | ✅ Complete | ✅ App-level keys set | App-level ping works; no shop connected yet (`ETSY_SHOP_ID`/`ETSY_ACCESS_TOKEN` unset) — needs one OAuth click via "Connect Etsy" |
| **Instagram** | N/A (no connector built in this project) | ✅live token, tested tonight — real account `@godsandgloryai` | Token works; nothing in this project calls it |
| **Facebook (Marketplace Catalog API)** | ✅ Built + wired tonight, dry-run verified end-to-end through the real Python bridge | ✅ App creds valid (Meta issued a real app token tonight); missing `FB_ACCESS_TOKEN`/`FB_PAGE_ID` (a real Page token) | Not live yet. **Also uncertain even with a token**: Meta's Commerce/Catalog API for creating listings is restricted to an approved-partner program, not open by default — confirm partner approval before assuming a Page token alone unlocks this. |
| **Bonanza** | ✅ Rebuilt tonight against the real Bonapitit API docs (api.bonanza.com/docs) — the first version assumed a REST shape that was wrong and would have failed live; dry-run verified end-to-end through the corrected bridge. **19 old tests are now stale** (they tested the wrong API shape) — need rewriting, not yet done. | Josh has a bonanza.com seller account (created tonight); still needs `BONANZA_DEV_ID`/`BONANZA_CERT_ID` from api.bonanza.com/accounts/new, then `fetchToken` + seller approval for `BONANZA_ACCESS_TOKEN` — three credentials, not one | Not live — needs those 3 credentials, but the code now actually matches Bonanza's real API |
| **Facebook (browser extension automation)** | Fake stub — `extension/content_script.js` fabricates a fake ID, does zero real DOM automation. `background.js` pings a dead domain. | N/A | Not real, never was. Real DOM automation on Facebook specifically also can't be built/tested via the Claude-in-Chrome tool — it's blocked from accessing facebook.com's page content entirely. |
| **Shopify, WooCommerce** | ✅ Real code | Not configured | Not used — no store on either platform |
| **Facebook Marketplace, OfferUp, Craigslist, Mercari, Poshmark** (manual mode) | ✅ Real — generates a copy-paste listing package per item | N/A, no automation attempted (platform policy) | ✅ Working today — 69 real items already have generated packages in `MANUAL_LISTING_PACKAGES.txt` |

**Today's real events, in order (2026-08-24):**
1. `01:37` — real bug fixed: login/scan kept bouncing to login because `middleware.js` used Node's `crypto.timingSafeEqual`, which throws on Next.js Edge Runtime on every call, silently mapped to "Unauthorized." Fixed with Web Crypto's `crypto.subtle`. This is why scanning was broken two days prior — nothing to do with credentials.
2. `10:45` — a separate, unrelated 299-file/37K-line rewrite (`codex/integrate-hot-wheels` branch) got merged on top of that fix, without review against it. Deleted the old `functions/` directory (Cloudflare Pages Functions: card ID, pricing, billing, commercials) and replaced card-scanning with an equivalent (checked: genuinely more built-out, not gutted) implementation under `app/api/`. **One real, unreplaced loss from this merge:** the Stripe billing (`functions/api/billing.js`) and commercial-video-generation (`functions/api/commercials.js`) endpoints were deleted with no replacement anywhere in the new `app/` structure — the underlying library code (`lib/commercialGenerator.js`, `lib/edgeAuth.js`) still exists, nothing calls it.
3. Login fix + merge + cleanup are **5 commits ahead of GitHub's `main`**, none pushed yet. GitHub's `main` reflects yesterday (Aug 23) — real, solid, but doesn't include today.

**What's actually needed to move forward, in priority order:**
1. Decide: keep the hot-wheels merge (it looks like a real upgrade to card-scanning) or revert to just the login fix — asked, not yet decided.
2. Rebuild the billing/commercials endpoints in the new `app/api/` structure, or confirm they're not needed anymore.
3. Push to GitHub — nothing from today is backed up anywhere but this machine.
4. Complete Etsy's shop OAuth (one click on the Channels page).
5. Get a real Facebook Page access token, and confirm Meta partner approval before assuming the Catalog API path will actually work.

**Real inventory:** 69 real items (cards, Transformers, cosmetics, Hot Wheels lots) confirmed and synced via the eBay Browse API, upserted into the shared Supabase `products` table. This is a lower bound — Browse API needs a search term, can't enumerate "everything."

**The real foundation day — commit `ef6d83d`, Thu 2026-08-13, 07:46am (video-bot-pipeline repo).** This is the actual session Josh remembers as "far along" — eBay Trading API sync, Boss Listers channel connectors, a dedicated commercial video renderer (`render_commercial.py`), Instagram Reels publisher, and several new agents, all landed together. It is not lost and not a different codebase — it's the base everything since has been built on top of. Confirmed still present and real as of 2026-08-24: `render_commercial.py`, the eBay/Etsy/Facebook listing clients. Not yet re-verified as of this rewrite: whether the commercial renderer still produces a real video end-to-end — check before assuming, per the Verify Before Claiming rule above.

**A structural map of this codebase exists:** `BossListers/graphify-out/graph.html` (interactive) and `GRAPH_REPORT.md` — built 2026-08-24, 2287 nodes / 5024 edges / 135 communities. The true center of the app is `analyzeFormData()` (75 connections) — the card-scan analysis function. Use this before assuming something is orphaned or missing; check the graph first.

## Agent Fleet (12+ agents, all parallel)
| Agent | Focus | Tasks |
|-------|-------|-------|
| Claude | General reasoning, research, architecture | Planning, analysis, documentation, git commits |
| Grok | Building features, complex systems | New renders, pipelines, infrastructure |
| Gemini | Scripts, content generation, automation | Script writing, batch processing, data transforms |
| Claude Code | Python execution on Josh's machine | empire_render.py, scene_classifier, episode_credit_planner |
| Council Bots | Quality assurance, self-healing | bot_01–bot_19: clips, frames, quality checks, social posts, wiring inspection |
| Video Renderer | Video generation & assembly | FFmpeg, scene composition, final MP4 output |
| Audio Agent | TTS, music, sound design | Kokoro voice, music selection, audio mixing |
| Image Agent | Image generation & fetching | Pollinations, Higgsfield, WikiArt, FLUX |
| Social Agent | Multi-platform publishing | YouTube upload, TikTok, Instagram, Facebook, Pinterest |
| Upload Agent | YouTube & distribution | channel_uploader.py, verification, metadata |

**Dispatch Model:** Every task queued to MISSION_BOARD.json auto-assigns to best-fit agent(s). Read MISSION_BOARD.json at session start — it's an action queue, not a backlog.

## Projects
| Name | What | Status |
|------|------|--------|
| **Boss Listers** | Card/item scanning → identification → pricing → cross-platform listing | See Current State above — this is the active focus |
| **Gods & Glory (GG)** | History/battle documentary channel | S1-S2 uploaded; S3 (EP012-025) scripted, queued for render. YouTube @godsandgloryai |
| **Little Olympus (LO)** | Kids channel (Little Zeus), Higgsfield-animated | EP001 needs re-render (quality issues); EP002-004 scripted |
| **Iron Legends (IL)** | 80s mech anime channel | EP001 scripted |
| **Empire Decoded (ED)** | AI/tech channel | EP001 scripted |
| **Book Factory** | Autonomous trend-scan → manuscript → cover → publish pipeline | MVP built; real book generated end-to-end (mock provider); Etsy digital connector wired; blocked on Claude API integration for real manuscripts |
| **Merch Factory** | Print-on-demand automation (Printful/Printify/Gooten) | Rasteriser + Printify connector built and dry-run verified |
| **Viral Engine (website)** | jardins-outpost.pages.dev | Live, but currently serving a different Next.js app than the documented static-site build — needs investigation into what's actually deployed there |

→ Full episode backlog: memory/projects/viral-engine.md
→ Full pipeline docs: memory/context/pipeline.md
→ Full historical session log: memory/context/session_archive_2026.md

## Key Terms
| Term | Meaning |
|------|---------|
| GG / LO / IL / ED | Gods & Glory / Little Olympus / Iron Legends / Empire Decoded channels |
| Council | Self-healing pipeline monitor bots (council/bots/) |
| auto_render.py | Core video pipeline: JSON → images → TTS → FFmpeg → MP4 |
| lib/ebay_listing.py | **Canonical** eBay listing client (video-bot-pipeline) — Node connectors proxy to this, never duplicate its logic |
| lib/etsy_listing.py | **Canonical** Etsy client (physical + digital) — same rule |
| scripts/listing_service.py | Local HTTP bridge (port 8791) exposing the Python listing clients to boss-listers-mvp's Node app. Dry-run/draft by default; live publishing needs `--allow-live <platform>` + a confirm literal + a service token. |
| orchestrator.py | Standalone 15-platform autonomous listing/publishing loop (video-bot-pipeline). Real, tested, but has only run once, in dry-run, on test data (2026-08-21) — never run against real inventory. |
| graphify-out/ | Knowledge-graph output for a codebase (`/graphify <path>`) — structural map, not a functional/live-status check |
| products table | Shared Supabase table (`irslzufsqjveyibkfjtz` project) — real inventory, read by both the website and Boss Listers |
| token_gg.pickle | Correct GG YouTube token — never use token.pickle (wrong account) |
| Python path | `C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe` — `py`/`python` are not reliably on PATH, always use the full path |

## CTO Operating Mode (NON-NEGOTIABLE)
- **Label uncertainty:** [Certain] / [Likely] / [Guessing] — never fabricate APIs, commands, or docs.
- **Self-learning:** when corrected, or when I catch my own mistake, add a one-line rule under `## Lessons` before continuing.
- **Tell Josh when he's wrong** and explain why — but verify against real state before disagreeing, and verify against real state before agreeing too.
- **Search before creating** — find existing functionality first, reuse architecture, no duplicates.
- **Code must be production-ready, typed, modular, tested.**
- **After every task:** confirm it actually runs, check for regressions, state the single highest-value next task.
- **Debugging:** read everything relevant in one pass before touching anything — root cause, not guess-and-check.

## Production Stack (video channels)
- **GG (documentary):** Empire OS pipeline (auto_render.py + Pollinations + FFmpeg) — Higgsfield rarely needed.
- **IL + LO (cartoons):** Higgsfield essential — Soul Cast (character consistency), Wan 2.7 (animation), Hailuo (dialogue).
- **Voice:** Kokoro (Voice Music Factory, local/free) is the primary and only pipeline voice. ElevenLabs key exists but is not used by auto_render.py.

## Base44 Apps
| App | ID | Purpose |
|-----|----|---------|
| VORTEX PRO | 6a40e3f3d7e4713876f492d6 | Multi-channel video pipeline dashboard |
| ViralVox | 6a341ca3df11ec718fefd246 | Voiceover generator |

## Preferences
- Direct and concise answers.
- Always use the highest-quality/most professional model — never default to budget/turbo.
- Josh handles credentials himself — never enter them, never accept them pasted in chat.
- Wants everything launched, not just planned.

## Lessons
- **Verify before claiming "production-ready."** A plausible HTTP call shape, a passing mocked test, or code that compiles is not evidence something works — the bar is a real result against a real system (a real API 200, a real live-tested token). This exact failure mode has repeated across at least 4 different "complete" marketplace integrations.
- **When five things share a name (e.g. five "Boss Listers" codebases), grep for real network calls (`fetch\(|axios|https\.request`) before trusting any of them.** Zero hits = zero real connectivity, no matter how sophisticated the surrounding code looks.
- **A file's own comment claiming "verified: mocked fetch shows X" is not verification** — a mock can only confirm code does what its author intended, never that the intent matches what the real remote API actually wants. Verify against the live endpoint.
- **Never re-search from scratch for something Josh says exists — ask him once where, specifically** (which machine, which service) rather than re-grepping everything, which wastes real credits.
- **On a recurring failure, read every relevant file completely in one pass before proposing a fix** — reacting to error messages one at a time, guessing, causes hours-long loops.
- **Never claim finished work is unfinished, or unfinished work finished — check actual git/file state before asserting either.**
- **A large, unreviewed merge landing on top of a recent fix is a real risk** — always diff what a merge changed against what was just fixed before trusting both survived together.
- **Windows-specific:** `py`/bare `python` may not be on PATH — always use the full interpreter path in scripts. npm global bins go to `%APPDATA%\npm\`, not always in PATH on first install.
- **Duration + audio RMS checks are not sufficient QA for video** — a red screen at 13 minutes passes both. Visual QC (frame inspection) is mandatory before any upload.
- **GitHub push protection on a public repo cannot be disabled** — use `PUSH_NOW.bat`, which auto-handles bypass URLs when secret scanning blocks a push. If it reports success, independently verify with `gh api repos/<owner>/<repo>/branches/<branch>` — it has reported false success before.
- **Higgsfield is non-negotiable for LO/IL** — the static PNG + Kokoro pipeline cannot produce watchable cartoon content; never attempt to substitute it again.
- **CLAUDE.md itself can become the source of confusion if it's allowed to grow as an undifferentiated session log** — see the "How this file works" note at the top. Keep Current State sections edited in place; put narrative in the archive.

## Git & GitHub
**Repository:** `https://github.com/mjardin17/viral-engine` (branch: `main`)

Before starting work: `git pull origin main`. After a change: `git add -A && git commit -m "[CLAUDE] <type>: <description>" && git push origin main` — but this is a **public repo with secret scanning**, so use `PUSH_NOW.bat` instead of a raw push; it auto-handles GitHub's bypass flow when blocked.

**Never committed:** `.env`, `renders/`, `output/`, `FINISHED_EPISODES/`, any `*.mp4`/`*.wav`/`*.mp3`/`*.aac`.

**Canonical production folder:** `C:\Users\jjard\claude\video-bot-pipeline\` — this IS the repo. No forks, no parallel copies. (Boss Listers is a separate repo: `C:\Users\jjard\claude\BossListers\`, see Current State above.)
