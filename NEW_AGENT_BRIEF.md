# EMPIRE OS — NEW AGENT MASTER BRIEFING
_Last updated: 2026-07-15_
_Read this fully before doing anything. This is the source of truth._

---

## WHO YOU ARE WORKING WITH

**Josh Jardin** (justifiedmagnificent@gmail.com) is building a multi-channel AI content empire called **Empire OS**. He is the owner, creative director, and operator. You are his CTO, senior software architect, and AI systems engineer.

**Standing rules — NEVER break these:**
- Every response starts with "Josh"
- No scene reuse — ever, within or across episodes
- 4 photos per scene in old pipeline — every scene, no exceptions
- Never idle — there is always something to do
- Only the truth — no silent failures, no faking output
- API keys/credentials NEVER in chat — Josh adds them to files directly
- DOUBLE-CHECK BEFORE EVERY ACTION — read current state first, confirm target is correct
- Scheduled tasks — always ask Josh before creating
- YouTube uploads — always require Josh's manual approval
- Other platforms (Instagram/TikTok/Facebook) — can be automatic
- Use PUSH_NOW.bat instead of raw `git push` (public repo + secret scanning)
- Python path: `C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe`
- `py` launcher is NOT in PATH — always use the full Python path above

---

## THE BIG PICTURE

Josh is building a YouTube empire across multiple AI-generated channels. The goal is:
1. Get all episodes live on YouTube (revenue, subscribers, algorithmic growth)
2. Monetize with Amazon Associates (affiliate links in descriptions) + Printful merch
3. Eventually: cross-post to TikTok/Instagram/Facebook automatically
4. Run everything through the Empire OS pipeline with minimal manual work

**Priority order:**
1. Upload GG EP001–011 to YouTube
2. Render + upload GG S3 EP012–025 (new v3.0 format)
3. Upload LO EP001 (after Bot-10 QC pass)
4. Replicate pipeline for IL and ED
5. Set up Amazon Associates + Printful/Etsy merch
6. Then optimize tooling/dashboard

---

## THE YOUTUBE CHANNELS

### Gods & Glory (GG) — History/Battle Documentary
- **YouTube:** @godsandgloryai ("Gods and Glory AI") ✅ live
- **TikTok:** @godsgloryai
- **Instagram:** @godsandgloryai
- **Facebook:** @godsandgloryai
- **Format:** NEW v3.0 — 10-min punchy episodes, one battle per ep, 10–12 scenes
- **OLD format is SCRAPPED** — EP006–007 (45-min slideshows) are trash, not the model
- **Pipeline:** render_gg_v3.py (see Tools section)
- **Voice:** Kokoro TTS (free, local) — DO NOT use ElevenLabs or Higgsfield for GG voice
- **Token:** token_gg.pickle — NEVER use token.pickle (wrong Google account)

**Episode Status:**
- S1 EP001–005 ✅ Finals in renders/ (187–260MB each) — ready to upload
- S2 EP006–007 ✅ Uploaded (old 45-min format — ignore these)
- S2 EP008–011 — render status unknown, check renders/gods_glory/ before assuming done
- S3 EP012–025 — ALL 14 scripts written in new v3.0 format, need rendering

**S3 Script Index (all in prompts/gods_glory/):**
- EP012: The Last Emperor (Fall of Rome) ✅ v3 JSON exists: gg_ep012_v3.json
- EP013: Crusader Kingdoms
- EP014: Waterloo
- EP015: Marathon
- EP016: Agincourt
- EP017: Battle of Tours
- EP018: Hastings 1066
- EP019: Kamikaze/Mongol Fleet
- EP020: Vienna 1683
- EP021: Midway
- EP022: Battle of the Bulge
- EP023: Operation Market Garden
- EP024: Inchon
- EP025: Yorktown

---

### Little Olympus (LO) — Kids Greek Mythology
- **YouTube:** @littleolympusai ✅ live
- **TikTok:** @little.olympusai (note: dot in handle)
- **Instagram:** @littleolympusai
- **Facebook:** @littleolympusai
- **Format:** 24 scenes, ~17 min — kids content standard
- **Pipeline:** Higgsfield MANDATORY — static pipeline = blue screen, unwatchable (tested and confirmed)
- **Characters:** Little Zeus, Hercules (Herc), Athena, Pegasus Junior, and from EP004: Little Medusa (12 named snakes, Gerald does crown formation)
- **Higgsfield models:** Soul Cast (character consistency), Wan 2.7 (animation), Hailuo (dialogue)

**Episode Status:**
- EP001 ✅ Rendered (455MB Higgsfield) — needs Bot-10 QC before upload
- EP002 ✅ Scripted (24 scenes)
- EP003 ✅ Scripted (24 scenes)
- EP004 ✅ Scripted (24 scenes) — "Little Medusa's Bad Hair Day"
  - Lesson: "What you're most embarrassed about is often what makes you most special"
  - Full crew assembled in scene 21

**BEFORE uploading LO EP001:** Run bot_10_frame_inspector — visual QC is mandatory. A bad render (red/black screen) can pass duration + audio checks but still be garbage.

---

### Iron Legends (IL) — 80s Mech Anime
- **YouTube:** @ironlegendsai ("Iron Legends AI") ✅ live
- **Format:** Higgsfield mandatory (Wan 2.7 animation, AutoSprite for mechs)
- **Status:** EP001 scripted only

---

### Empire Decoded (ED) — AI/Tech Channel
- **Previously called:** ML (Machine Learning)
- **YouTube:** Not yet set up
- **Status:** EP001 scripted only

---

### Echoes of Eternity (EOE) — New Channel
- **YouTube:** @echosofeternitiai ("Echoes of Eternity AI") ✅ live (created in earlier session)
- **Status:** EP001 pending

---

### WW Channel (WW) — WW1 & WW2 Documentary
- **Status:** Planned — starts after GG EP020–025 done

---

## THE VIDEO PIPELINE

### GG v3.0 Pipeline (render_gg_v3.py)
This is the NEW Gods & Glory pipeline. Built from scratch in July 2026. The old auto_render.py format is dead for GG.

**How it works:**
```
Episode JSON script
  → wikimedia_fetch.py (real historical images from Wikimedia Commons API)
  → video_effects.py / ken_burns_clip() (FFmpeg zoom/pan motion on images)
  → tts_cli.py / Kokoro TTS (free local narration)
  → combine video + audio
  → add_lower_third() (title cards via FFmpeg drawtext)
  → concat all scenes
  → mix_music() (background music at 18% volume)
  → final MP4 → renders/gods_glory/GG_EP012_final.mp4
```

**Run command:**
```
C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe render_gg_v3.py --script prompts/gods_glory/gg_ep012_v3.json --music music/gg_battle_theme.mp3
```

**Episode JSON format (v3.0):**
```json
{
  "channel": "Gods and Glory AI",
  "episode_id": "GG_EP012",
  "title": "...",
  "battle_date": "476 AD",
  "scenes": [
    {
      "scene_number": 1,
      "type": "hook",
      "title": "...",
      "narration": "90-120 words of punchy narration",
      "wikimedia_query": "search term for Wikimedia Commons",
      "visual_prompt": "fallback if Wikimedia fails",
      "lower_third": "Title | Subtitle",
      "duration_sec": 42
    }
  ]
}
```

**Scene types for v3.0:** hook → context → rising_action → conflict → climax → analysis → deeper_context → twist → lesson → outro

**Image sources (in order of preference):**
1. Wikimedia Commons (real historical paintings, maps, photos — free)
2. Pollinations AI (AI-generated fallback if Wikimedia fails)

**Music:** Josh generated tracks on Suno.com. Current track: `music/gg_battle_theme.mp3` ("Iron Banner Rise"). HuggingFace MusicGen API is BLOCKED on Josh's network — do not attempt to auto-generate music via API. Use Suno.com manually (one track → reused forever).

Need more music tracks for variety:
- Dramatic tension
- Victory/triumph
- Somber/memorial
- Action/chase

---

### Old Pipeline (auto_render.py) — Still used for some things
The old pipeline is still in the repo and still used for edge cases, but GG v3.0 is the target format going forward. The old pipeline uses Pollinations AI images + edge-tts voice. DO NOT use the old pipeline for new GG episodes.

---

### LO/IL Pipeline (Higgsfield)
- No local render pipeline for cartoons — they REQUIRE Higgsfield video generation
- Higgsfield credits: 707 remaining (as of last session) — SAVE THESE for LO and IL
- Josh has Higgsfield Plus plan
- Process: script → Higgsfield Soul Cast for character consistency → Wan 2.7 for animation → Hailuo for dialogue scenes → assemble

---

## KEY FILES IN THE REPO

```
C:\Users\jjard\claude\video-bot-pipeline\   ← THIS IS THE REPO ROOT
├── render_gg_v3.py          ← GG v3.0 full pipeline
├── wikimedia_fetch.py       ← Fetches historical images from Wikimedia Commons
├── video_effects.py         ← Ken Burns effect, music mix, lower thirds
├── music_gen.py             ← HuggingFace MusicGen (BLOCKED on Josh's network)
├── auto_render.py           ← Old pipeline (still works, not for new GG eps)
├── tts_cli.py               ← Kokoro TTS CLI wrapper
├── channel_uploader.py      ← YouTube uploader (--verify flag, use token_gg.pickle for GG)
├── patch_fallbacks.py       ← Fixes broken/tiny images
├── pipeline_run.py          ← Zero-prompt autonomous pipeline orchestrator
├── research_agent.py        ← Auto topic research + script generation (Gemini)
├── crosspost_bridge.py      ← Multi-platform publish queue
├── PUSH_NOW.bat             ← Git push wrapper (handles GitHub secret scanning bypass)
├── CLEANUP_WORKFILES.bat    ← Deletes intermediate render files to free disk space
├── CLAUDE.md                ← Primary memory file — READ THIS FIRST every session
├── NEW_AGENT_BRIEF.md       ← This file
├── .env                     ← API keys (never commit, never show in chat)
├── music/
│   └── gg_battle_theme.mp3  ← GG background music (Suno generated)
├── prompts/
│   ├── gods_glory/          ← All GG episode JSON scripts
│   │   └── gg_ep012_v3.json ← First v3.0 episode (Fall of Rome)
│   ├── little_olympus/      ← LO episode scripts
│   │   ├── scene_prompts.lo_ep002.final.json
│   │   ├── scene_prompts.lo_ep003.final.json
│   │   └── scene_prompts.lo_ep004.final.json
│   └── machine_learning/    ← ED/ML scripts
├── renders/
│   └── gods_glory/          ← Final GG MP4s go here
├── council/                 ← 9-bot self-healing system
│   ├── council.py
│   ├── bots/
│   │   ├── bot_01_guardian.py
│   │   ├── bot_02_script_guard.py
│   │   ├── bot_03_image_healer.py
│   │   ├── bot_04_clip_rebuilder.py
│   │   ├── bot_05_final_assembler.py
│   │   ├── bot_06_render_queue.py
│   │   ├── bot_07_stub_expander.py
│   │   ├── bot_08_auto_renderer.py
│   │   ├── bot_09_quality_checker.py
│   │   └── bot_10_frame_inspector.py  ← MANDATORY before any upload
│   └── state/
└── memory/
    ├── context/pipeline.md
    └── projects/
        ├── PROJECT_IDENTITY.storyforge_engine.md
        ├── PROJECT_IDENTITY.boss_listers.md
        └── viral-engine.md
```

---

## THE COUNCIL BOT SYSTEM

9 bots (+ Bot-10) that self-heal the pipeline. Run via `council_run.bat`.

| Bot | Role |
|-----|------|
| bot_01_guardian | Scans for broken/tiny clips and short finals |
| bot_02_script_guard | Guards against stub script downgrades |
| bot_03_image_healer | Re-fetches fallback images <20KB |
| bot_04_clip_rebuilder | Re-renders 0KB clips |
| bot_05_final_assembler | Rebuilds final MP4s |
| bot_06_render_queue | Tracks episodes ready to render |
| bot_07_stub_expander | Tracks 84 stub episodes needing full scripts |
| bot_08_auto_renderer | Renders 1 episode per council run |
| bot_09_quality_checker | ffprobe duration + audio RMS check |
| **bot_10_frame_inspector** | **Visual QC — MANDATORY before any upload** |

**Bot-10 is critical.** A red screen at 13 min passes duration + audio checks but looks horrible. Bot-10 captures a frame every 30s, detects red/black/white/frozen screens, and auto-queues re-render. Never skip it.

---

## YOUTUBE UPLOAD RULES

- **Always use token_gg.pickle for GG uploads** — token.pickle is the WRONG account
- **Always requires Josh's manual approval** before any upload
- **After every upload:** immediately verify the video URL shows correct channel name
- **Run Bot-10 first** — visual QC before upload is non-negotiable
- **channel_uploader.py --verify** is the upload script

---

## MONETIZATION PLAN

### 1. Amazon Associates (PRIORITY — set up ASAP)
Josh has an Amazon account. Sign up at: https://affiliate-program.amazon.com

**What to link in video descriptions:**
- GG channel: history books, battle maps, ancient Rome books, WWII books, military history
- LO channel: Greek mythology books for kids, mythology board games, Zeus/Hercules toys
- IL channel: 80s anime art books, mech/robot toys, Japanese pop culture

**How to implement once signed up:**
- Generate affiliate links for 5-10 relevant products per channel
- Add to every video description (existing + new)
- Template: "📚 Want to learn more? Check out these books: [link1] [link2]"
- Passive income from day 1 on existing videos

### 2. Printful Merch (next step after Associates)
Josh does NOT have logos yet — designs need to be created first.

**Plan:**
1. Create channel logos/brand art (GG, LO, IL all need logos)
2. Sign up for Printful (free) + Etsy (free to set up)
3. Connect Printful → Etsy store (Printful auto-fulfills all orders)
4. Link from jardins-outpost.pages.dev to Etsy shop
5. Put Etsy shop link in all video descriptions

**Why Etsy not Shopify:** Zero monthly cost, gets live fast, test what sells first. Upgrade to Shopify later if it takes off.

**Merch ideas:**
- GG: "Rome Wasn't Built in a Day" shirt, battle map prints, gold/black warrior aesthetic
- LO: Little Zeus cartoon shirts, "I am Little Zeus" kids tees, character stickers
- IL: Mech pilot jacket prints, 80s anime poster style

**jardins-outpost.pages.dev note:** This is a static Cloudflare Pages site — Printful can't plug directly into it. The Etsy shop is a separate URL. Just link to it from the nav.

### 3. YouTube Merch Shelf (future)
- Requires 10K+ subscribers per channel
- Works with Spring/Printify
- Shows merch directly under videos — highest conversion
- Set this up once GG hits 10K subs

---

## THE WEBSITE — jardins-outpost.pages.dev

Live on Cloudflare Pages. Dark gold theme. Has nav: Apps / Store / Services / Workspace / Contact.

**Current state:** Site looks great but nothing is fully wired for purchases yet.

**Base44 storefront app** (ID: 6a341ca3df11ec718fefd246) — built July 2026:
- Has Product/Order entities
- Needs real Stripe keys pasted in to make checkout live
- Was repurposed from ViralVox app (Base44 free plan caps at 5 apps, can't create new ones)

**Next steps for the site:**
1. Link Store page → Etsy shop (once Printful/Etsy is set up)
2. Paste real Stripe keys into Base44 storefront
3. Add apps/services pages with real links

---

## BASE44 APPS

| App | ID | Purpose | Status |
|-----|----|---------|--------|
| VORTEX PRO | 6a40e3f3d7e4713876f492d6 | Multi-channel video pipeline dashboard | Built |
| VORTEX | 6a40dbc726e8b86d7150350e | Earlier version of VORTEX PRO | Deprecated |
| ViralVox/Storefront | 6a341ca3df11ec718fefd246 | Repurposed as full storefront (Product/Order/Stripe) | Needs Stripe keys |

**Base44 limit:** Free plan = 5 apps max, no delete tool via MCP. If cap is hit, repurpose an existing app — do NOT ask Josh to free a slot blind.

---

## STORYFORGE (Book Generation)

Built into Empire OS by Google AI Studio (Gemini). Located in Creative Console.

**What it does:** Takes a story premise → generates full multi-scene scripts with character matrices, tone profiles, and pacing. 94% complete.

**Current gap:** StoryForge output format does NOT match the video pipeline's episode JSON format. The bridge to auto-convert StoryForge output → render_gg_v3.py input has NOT been built yet. This is a future task.

**Not actively used** in current pipeline — scripts are written manually or with Claude's help.

---

## BOSS LISTERS AI

Cross-listing dashboard for 8 platforms: eBay, Poshmark, Mercari, Depop, Grailed, Etsy, Shopify, TikTok Shop.

- File: `boss-listers-ai.zip` in repo
- Status: 54% complete, needs hosting
- eBay connected, website + other platforms pending
- Goal: eBay inventory → jardins-outpost.pages.dev storefront → other platforms

---

## THE TECH STACK

| Tool | Purpose | Cost |
|------|---------|------|
| Kokoro TTS (tts_cli.py) | Voice narration for GG | Free, local, unlimited |
| Higgsfield | Video generation for LO + IL | Credits (707 left, Plus plan) |
| Wikimedia Commons API | Real historical images for GG | Free |
| Pollinations AI | AI image fallback | Free |
| FFmpeg | Video assembly, Ken Burns, music mix | Free |
| Gemini API | Research agent, script scoring | Free tier (key in .env) |
| ElevenLabs | NOT currently used in pipeline — Josh has key, saved for ViralVox product | Paid (key in .env) |
| Suno.com | Music generation | Manual, browser-based |
| HuggingFace MusicGen | Automated music — BLOCKED on Josh's network | Would be free |
| Cloudflare Pages | Website hosting | Free |
| Base44 | No-code app backend | Free (5 app limit) |

---

## .ENV FILE — KEY LOCATIONS

File: `C:\Users\jjard\claude\video-bot-pipeline\.env`

Keys stored there:
- `ELEVENLABS_API_KEY` — real key present
- `GEMINI_API_KEY` — real key present (used by research_agent.py)
- `HF_TOKEN` — HuggingFace token (present but API blocked on Josh's network)
- `HIGGSFIELD_API_KEY` — empty (Josh enters this manually)
- `VEO_API_KEY` — present

**NEVER display key values in chat. NEVER commit .env to git.**

---

## GIT / GITHUB

**Repo:** https://github.com/mjardin17/viral-engine (branch: main)
**Canonical local path:** `C:\Users\jjard\claude\video-bot-pipeline\`

**Before every task:** `git pull origin main`

**After every change:**
```
git add -A
git commit -m "[CLAUDE] feat: description"
PUSH_NOW.bat   ← NOT git push — uses push_bypass.py for secret scanning bypass
```

**Never commit:** .env, renders/, output/, FINISHED_EPISODES/, any *.mp4/*.wav/*.mp3/*.aac

**Commit format:** `[CLAUDE] feat/fix/docs/chore: description`

---

## IMMEDIATE NEXT TASKS (in order)

1. **Check disk space** — C: drive was critically low last session. Run:
   `Get-PSDrive C | Select-Object @{N='Free GB';E={[math]::Round($_.Free/1GB,1)}}`
   Need 15+ GB free for Linux workspace to start.

2. **Test GG v3.0 render** — once disk is clear:
   ```
   C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe render_gg_v3.py --script prompts/gods_glory/gg_ep012_v3.json --music music/gg_battle_theme.mp3
   ```

3. **Run Bot-10 on LO EP001** before uploading to @littleolympusai

4. **Set up Amazon Associates** — affiliate-program.amazon.com — Josh has Amazon account

5. **Get GG logos made** so Printful/Etsy merch can be set up

6. **Rewrite GG EP013–025** from old 24-scene format to new 10-scene v3.0 format
   (EP012 is already done as v3.0 — use it as the template)

7. **Get Suno tracks** for other music moods (dramatic tension, victory, somber, action)

8. **Upload GG EP001–005** to @godsandgloryai (pending disk space + render test)

9. **Rotate token_gg.pickle credentials** — these were exposed in git history.
   Revoke in Google Cloud Console, re-auth via `channel_uploader.py --reauth`.
   YouTube Data API v3 must be manually enabled on new GCP project.

---

## KNOWN ISSUES / LESSONS LEARNED

- token.pickle = WRONG Google account. Always token_gg.pickle for GG
- `py` launcher not in PATH — use full Python path
- GitHub push protection blocks raw `git push` when secrets detected — use PUSH_NOW.bat
- HuggingFace API is network-blocked on Josh's machine — use Suno.com for music
- LO/IL CANNOT use static pipeline — Higgsfield only, no exceptions (tested: blue screen result)
- Base44 free plan = 5 app cap, no delete tool — repurpose existing apps
- Visual QC (Bot-10) is mandatory — duration+audio checks are NOT enough
- Empire OS Hub runs at localhost:5173 — start with PNPM_INSTALL.bat then START_HUB.bat
- Never price a product as sellable without confirming the feature actually works (ViralVox lesson)
- After any upload, immediately verify the video URL shows the correct channel name
- GG EP006–007 old format = uploaded and live but considered legacy/trash — ignore
- All old GG content (45-min format) is scrapped — new v3.0 is the only format going forward

---

_This document should be updated after every major change. It lives at:_
`C:\Users\jjard\claude\video-bot-pipeline\NEW_AGENT_BRIEF.md`
