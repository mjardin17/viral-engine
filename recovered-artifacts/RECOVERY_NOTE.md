# Recovery provenance — 2026-08-14

These 9 files were reconstructed from the transcript of a cloud Claude Code
session ("Buzz platform validation on Windows 11") whose GitHub write path
never had push access, so this work existed only as chat history and (per
that session's own report) as live Claude Artifacts until now.

They were independently verified against this repo's actual git history
before being added here — see the recovery audit for method. Everything
else that session claimed to have "recovered" (80 other video-bot-pipeline
files, all 33 boss-listers-mvp files, and the 1 jardins-outpost file) was
found to be **stale**: byte-identical to, or an outright older/less secure
version of, what is already committed on GitHub. None of that was copied in.

## What's here
- `landing_page.html`, `packages_pricing.html`, `empire_os_proposal.html`,
  `automation_services.html` — Empire OS marketing site pages (landing,
  pricing, business proposal, automation-services pitch). Static, standalone
  HTML — not wired into any build or deploy pipeline yet.
- `storyforge_v2_landing.html`, `storyforge_publishing.html`,
  `storyforge_custom_books.html` — three different StoryForge product
  pitches. Note `storyforge_custom_books.html` describes a **different
  product** than this repo's `storyforge/` Python pipeline: a "send
  custom books to incarcerated loved ones" service concept, not the
  Patterson-formula book-factory automation. Same name, unrelated product.
- `STORYFORGE_README.md`, `STORYFORGE_UPGRADES_MASTER.md` — docs for that
  same custom-books product concept, not this repo's book pipeline.

## Not yet done
No routing, deployment, or linking has been set up for these pages. They
are static files only. If any of these should go live (e.g. on
jardins-outpost.pages.dev or a dedicated Empire OS site), that's a
separate decision — confirm destination before wiring them in.
