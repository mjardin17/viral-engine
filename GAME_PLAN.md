# Empire OS — Master Game Plan
_Last updated: 2026-07-12_

---

## 🟢 ACTIVE RIGHT NOW
- `render_season3.bat` — rendering GG EP012–EP025 (14 episodes, running overnight)
- GG EP013 — uploading to YouTube (kicked off at 5:10 PM)

---

## 🔴 URGENT — Do Before Anything Else

- [ ] **Make GG_EP008, EP009, EP010 Private on YouTube** — these are 10-13 min stubs, already live. Go to YouTube Studio → set to Private so they don't tank the channel.
- [ ] **Rotate Google OAuth credentials** — token_gg.pickle + credentials.json were in early git history and are now publicly visible. Revoke in Google Cloud Console → re-auth via `channel_uploader.py --reauth`.

---

## 📺 DISTRIBUTION — Get GG Live (PRIMARY GOAL)

### Phase 1 — Upload what's rendered (after render_season3.bat finishes)
- [ ] Run `UPLOAD_GG_NOW.bat` — will auto-queue all finished S3 episodes ≥38 min
- [ ] Verify each upload hit the correct channel (Gods and glory ai / UC7bNdZSXGmh6K8B5kt9TWOg) before moving on
- [ ] EP006 (Pearl Harbor) — confirm it uploaded; was showing as "already uploaded" in dry run

### Phase 2 — Fix the stubs (EP008–EP011)
- [ ] Write full 24-scene scripts for GG_EP008, EP009, EP010, EP011
- [ ] Re-render them with `auto_render.py`
- [ ] Replace the private stub versions on YouTube with the full episodes

### Phase 3 — Other channels (after GG EP001-025 are live)
- [ ] **Iron Legends (IL)** — EP001 scripted → render → upload to @IronLegendsai
- [ ] **Little Olympus (LO)** — EP001 rendered → upload (compare Ken Burns vs Higgsfield first)
- [ ] **Empire Decoded (ED)** — EP001 scripted → render → upload
- [ ] **WW Channel** — starts after GG EP020-025 done

---

## 🎬 LO EP001 — Two Versions

- [ ] **Run `ASSEMBLE_LO_HIGGSFIELD.bat`** — assembles the animated Higgsfield version (all 24 clips ready)
- [ ] **Check `RENDER_LO_EP001_FREE.bat` status** — Ken Burns free version (was rendering, got closed)
  - If it didn't finish: re-run it
- [ ] **Compare both outputs** — pick the better one (or upload both to different channels)
- [ ] Upload winner to Little Olympus channel

---

## 🚀 VIRAL ENGINE LAUNCH — Opening Day

Everything below is for the public launch. Still need info from Josh (marked ⚠️):

- [ ] **YouTube** — channels already created ✅
- [ ] **Website / Landing Page** — https://jardins-outpost.pages.dev (Cloudflare Pages) — needs content built out
- [ ] **Store** — eBay store live on Boss Listers ✅ Website storefront (jardins-outpost.pages.dev) needs to be linked to eBay via Boss Listers
- [ ] **Apps to launch:**
  - **Voice Music Factory** — Kokoro TTS voice + music/video generation tool — lives in `voice-music-factory/` in the repo — needs to be deployed/hosted
  - **ViralVox** — voiceover generator (Base44 `6a341ca3df11ec718fefd246`) — currently edge-tts, upgrade to ElevenLabs before launch
  - **Boss Listers AI** — cross-listing dashboard (React/Vite) — `boss-listers-ai.zip` in repo — needs to be deployed/hosted
- [ ] **Newsletter signup** — needs platform + landing page
- [ ] **Social media opening day posts** — one for each platform × each channel
  - Platforms: YouTube, Instagram, TikTok, Facebook, X
  - Channels: GG, IL, LO, ED
- [ ] **VORTEX PRO dashboard** — Base44 app `6a40e3f3d7e4713876f492d6` — verify it's ready

---

## 🔊 AUDIO UPGRADE

- [ ] **Upgrade ViralVox to ElevenLabs** — Base44 app `6a341ca3df11ec718fefd246` currently uses edge-tts → swap to ElevenLabs API (key is in .env as `ELEVENLABS_API_KEY`, voice: JBFqnCBsd6RMkjVDRZzb — George)
- [ ] **Re-render any episodes** that used edge-tts if audio quality matters for launch

---

## 🛠️ TOOLING

- [ ] **Build `render_orchestrator.py`** — parallel multi-worker renderer (Gemini mission m004)
  - Runs N episodes simultaneously, live status, auto-retries, logs to render_log.json
- [ ] **Wire crosspost_bridge.py** — fill in `crosspost_config.json` → auto-publish to Instagram/TikTok/Facebook after upload
- [ ] **bot_10_frame_inspector** — already in council; make sure it runs before every upload (visual QC mandatory)

---

## 📋 BACKLOG (Do When Distribution Is Handled)

- [ ] 84 stub episodes across all channels need full scripts written
  - GG(14), GG_HIST(10), LO(37), ML(21), IL(1), GG_TRAILER(1)
- [ ] StoryForge book generation system — built into Empire OS, needs launch plan
- [ ] Boss Listers reseller app — separate product, needs own launch plan
- [ ] WW Channel (WW1/WW2) — starts after GG EP020-025 done

---

## ✅ DONE (Don't Redo)

- GG S1 (EP001-005) — uploaded ✅
- GG S2 EP006 — uploaded ✅
- GG S2 EP007 — uploaded ✅ (but is a stub — may want to replace)
- GG S2 EP012 — uploaded ✅
- GG S3 EP012-025 scripts — all written ✅
- render_season3.bat — running ✅
- Council bot system (10 bots) — live ✅
- token_gg.pickle verified → "Gods and glory ai" ✅
- Duplicate GG channel under justifiedmagnificent@gmail.com — being deleted ✅
- Smart uploader (upload_gg_full.py) with min-duration gate — built ✅
- All 24 LO EP001 Higgsfield clips generated ✅
- video_urls.json + ASSEMBLE_LO_HIGGSFIELD.bat — built ✅

---

## ORDER OF ATTACK (Recommended)

1. 🔴 Make EP008/009/010 private on YouTube NOW
2. 🔴 Rotate Google OAuth credentials
3. 📺 Wait for overnight renders → upload batch in morning
4. 🎬 Run ASSEMBLE_LO_HIGGSFIELD.bat + compare LO outputs
5. 🚀 Get launch info from Josh (website URL, store, apps) → build launch assets
6. 🔊 Upgrade ViralVox to ElevenLabs
7. 🛠️ Build render_orchestrator.py (parallel rendering)
8. 📋 Stub backlog + WW Channel
