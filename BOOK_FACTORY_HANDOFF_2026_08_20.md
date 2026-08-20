# Book Factory — Handoff Prompt (2026-08-20)

Paste this whole file into a fresh Claude Code session in `C:\Users\jjard\claude\video-bot-pipeline` to resume Book Factory work.

## Read first, before touching code
1. Read `CLAUDE.md` fully — especially the "🔴 2026-08-20 — lib/platform_connectors.py audited, found non-functional" entry and everything else dated 2026-08-20. That section documents a real pattern in this project: code and docs have repeatedly been marked "production-ready"/"complete" without ever being run against a real credential, and it has cost real trust. Do not repeat it here.
2. **Ground truth on book platforms, verified 2026-08-20 by three independent research passes (web search + GitHub search + direct fetch of official docs) — do not re-litigate this, it's settled:**
   - Amazon KDP, Apple Books, Kobo Writing Life, Barnes & Noble Press, IngramSpark: **no public API of any kind.** Manual web-form upload only.
   - Draft2Digital: **no public API.** Every GitHub reference to a "D2D API" is an unfulfilled TODO. `storyforge2/publishing/registry.py` currently still marks this `DIRECT_API` — that's wrong and needs fixing (see Task 1).
   - Gumroad: has a real REST API, but **product creation is NOT implemented** — their own docs say `POST /v2/products` returns 404, "Product creation must be done through the Gumroad dashboard." The API only supports listing/reading/updating/enabling/disabling **existing** products. `registry.py` currently marks this `DIRECT_API` with "Connector not yet built" — that framing is misleading; it should be `DRAFT_EXPORT` or similar, since creation isn't possible via API at all, only post-creation management.
   - Payhip: real API exists (`payhip.com/api-reference`), documented resources are Coupon and License Key management — **not independently verified for full product creation** in this pass. Verify directly against `https://payhip.com/api-reference` before trusting `registry.py`'s current "Real REST API, verified" claim for product creation specifically.
   - Google Play Books: has a real but gated bulk-feed mechanism (ONIX metadata + SFTP), requiring a formal Service Provider Agreement with Google aimed at aggregators, not individual publishers. Not realistic for this project.
   - Every platform's manual web-form submission **does save as a draft** until you click publish — same safety property as everywhere else, just no bulk-CSV shortcut exists for books like it does for Whatnot/Poshmark on the reselling side.
3. **A real, working (but ToS-risk) browser automation tool exists on GitHub for KDP specifically:** `ekr0/auto-kdp` (Puppeteer, CSV-driven, ~2 years of real use per the author, 29 stars as of 2026-08-20). This is genuine, not fake — but it's browser automation against a platform with no real API, same risk category as unauthorized Poshmark/Facebook automation discussed elsewhere in this project. Do not wire this in without Josh explicitly deciding he wants that risk — same standing rule as the rest of this project's manual-only platforms.

## Task 1 — Fix the real, bounded bug blocking everything (do this first)
`storyforge2/pipeline.py:18` imports `PipelineState, StageStatus` from `storyforge2.state`, but `storyforge2/state.py` defines `StateStore`, `Project`, `StageRun`, `StateError` — not those two names. This has been broken since the Book Factory MVP was built on 2026-08-17 and has blocked every manuscript-generation attempt since. Read both files, decide the correct fix (likely: `pipeline.py` should use `StateStore`/`Project`/`StageRun`, not names that don't exist), and get `python -c "from storyforge2.pipeline import ..."` importing clean. Write/run a test proving it.

## Task 2 — Correct `storyforge2/publishing/registry.py`
Fix the `d2d` and `gumroad` entries per the ground truth in the "Read first" section above. Re-verify `payhip` directly before trusting its current label. Run the file's own `_selftest()` function after fixing — it already has a self-check for exactly this kind of mislabeling (`unimplemented_direct` check), make sure it actually catches what it's supposed to.

## Task 3 — Generate one real test book, free
Use the `GEMINI_API_KEY` already in `.env` (confirmed present) via the existing `GeminiTextProvider` in `storyforge2/manuscript.py` — no paid API key needed for this. Run the full pipeline end-to-end once Task 1 is fixed: trend → brief → manuscript → cover → metadata. This produces the first real book this project has ever generated. Verify the output is real (readable, formula-compliant per `storyforge2/patterson_formula.py`) before calling it done — actually open and read the output, don't just check it didn't crash.

## Task 4 — Build the manual listing-package generator for books
Mirror the pattern already built and verified working tonight for the reselling side: `boss-listers-mvp/lib/channels/manualPackage.js` takes a product and generates platform-optimized title/description/keywords ready to copy-paste. Build the equivalent for one real book (from Task 3) targeting KDP, Apple Books, Kobo, and IngramSpark's real field requirements (title length limits, BISAC categories, keyword counts — check each platform's actual current help docs for real limits, don't guess). This won't post anything automatically — it makes the manual upload faster the same way the cards version does.

## What NOT to do
- Do not build or wire in `auto-kdp` or any other browser-automation posting tool without Josh explicitly asking for it in that session — that's his call to make knowingly, not a default.
- Do not write "production-ready," "complete," or promise a revenue timeline anywhere (CLAUDE.md, commit messages, or to Josh directly) without having actually run the thing against real output first. This exact failure pattern already cost real trust once in this project — see CLAUDE.md's 2026-08-20 entries for the full cost of getting this wrong.
- Do not claim any book platform can be automated beyond what's listed as ground truth above without fetching their real, current official docs yourself and quoting the exact evidence.
