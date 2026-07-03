# VIRAL ENGINE — Project Checkpoint
**Saved:** 2026-06-16T19:53Z

---

## BRAND

**Umbrella:** Viral Engine (formerly Legend Empire)

**Three channels:**
| ID | Name | Category | Status |
|----|------|----------|--------|
| CH01 | Little Olympus | Kids mythology 3–10 | Scripted, not rendered |
| CH02 | Gods & Glory | Adult history doc (formerly Empire Decoded) | Season 1 rendered (EP005) |
| CH03 | Mech Legends | Kids robots 4–12 (formerly Iron Legends) | EP001 drafted, needs real character art |

**Brand bibles:**
- `viral_engine_bible.json` — master bible (all 3 channels, BLAZE/STORM/GRANITE/NOVA/RUMBLE/BOLT)
- `iron_legends_bible.json` — older Iron Legends bible (kept for reference)

---

## MECH LEGENDS — CHARACTERS

| Name | Color | Vehicle | Role |
|------|-------|---------|------|
| BLAZE | 🔴 Red | Fire truck → race car | Brave leader |
| STORM | 🔵 Blue | Helicopter | Brains / strategist |
| GRANITE | 🟢 Green | Bulldozer | Gentle giant / muscle |
| NOVA | ⚪ Silver | Rocket | Scientist / gadgets |
| RUMBLE | 🟣 Dark purple | Crusher | OVERWHELMING villain |
| BOLT | ⚫ Black | Lightning bolt | Sneaky sidekick |

---

## MECH LEGENDS EP001 — STATUS

**Episode:** "Origin: The First Transformer Wakes Up" (`IL_EP001`)
**Script:** `prompts/scene_prompts.il_ep001.final.json` (10 scenes × 9s each)

⚠️ **NOTE:** Script still uses OLD character names (Iron Vanguard / Ravager Prime / Alpha Prime)
→ Needs rewrite for BLAZE / RUMBLE / etc.
⚠️ **NOTE:** Channel field says "Iron Legends" → needs update to "Mech Legends"

**Draft render:** `renders/iron_legends/il_ep001.mp4` (100s, 25MB) ✅
- Uses PIL placeholder silhouettes (user rejected — needs real character art)

**Blocker:** No real Mech Legends character images exist yet
- empiredecoded folder = historical characters only (Gods & Glory)
- Higgsfield credits: **0.75** (essentially empty — need top-up to generate art)

---

## GODS & GLORY — STATUS

**Completed render:** `renders/thermopylae_final.mp4` ✅
**Season 1 scripts:** EP001–EP015 written ✅
**Character images:** 25+ Higgsfield/Gemini images in `character_images/` (historical)
**Render engine:** `documentary_render.py` (Phase 3) ✅

---

## KEY FILES

```
video-bot-pipeline/
├── viral_engine_bible.json          ← MASTER BRAND BIBLE
├── iron_legends_bible.json          ← Older IL bible
├── iron_legends_render.py           ← Mech Legends render engine
├── il_batch_render.py               ← Batch render runner (scenes 1-3, 4-6, etc.)
├── documentary_render.py            ← Gods & Glory render engine
├── episode_state.json               ← Episode tracker
├── prompts/
│   └── scene_prompts.il_ep001.final.json   ← EP001 script (needs char name update)
├── character_images/                ← Historical images (no mech art yet)
├── renders/
│   ├── iron_legends/il_ep001.mp4   ← Draft render (placeholder chars)
│   └── thermopylae_final.mp4       ← Gods & Glory EP005
└── _backups/                        ← All timestamped backups
```

---

## STANDING RULES (always apply)

1. **Episode numbering never restarts** across sessions
2. **Save 3x:** primary + `_backups/<name>.latest.<ext>` + `_backups/<name>.<UTC-timestamp>.<ext>`
3. **episode_state.json** backups MUST use Write tool (not bash cp) — mount staleness
4. **Villains are OVERWHELMING** — every antagonist must feel impossible to beat
5. **Three active channels:** Little Olympus · Gods & Glory · Mech Legends

---

## WHAT TO DO NEXT

### Priority 1 — Get Mech Legends character art
- Add Higgsfield credits → generate 6 character images (BLAZE, STORM, GRANITE, NOVA, RUMBLE, BOLT)
- OR: improve PIL placeholder art as a stopgap

### Priority 2 — Update EP001 script
- Change channel: "Iron Legends" → "Mech Legends"
- Replace character names: Iron Vanguard → BLAZE, Ravager Prime → RUMBLE, Alpha Prime → (ancient mech TBD)
- Rewrite narration to match toyetic vehicle-transformer style

### Priority 3 — Re-render EP001 with real characters
- Run `il_batch_render.py --scenes 1-3`, `--scenes 4-6`, `--scenes 7-10`, `--concat`

### Priority 4 — Sound upgrade
- Current: synthesized tones + silence (no real voice, no real music)
- Need: ElevenLabs voice (setup_needed per bible) + better SFX
- iron_legends_render.py has `generate_synth_music()` and `generate_sfx()` — can be upgraded

---

## RENDER PIPELINE QUICK REFERENCE

```bash
# Render EP001 in batches (run from video-bot-pipeline/)
python3 il_batch_render.py --scenes 1-3
python3 il_batch_render.py --scenes 4-6
python3 il_batch_render.py --scenes 7-10
python3 il_batch_render.py --concat
python3 il_batch_render.py --status
```

**FFmpeg path:** `/usr/bin/ffmpeg` (Ubuntu 22 sandbox)
**Scene clip duration:** 9 seconds (safe for batch timeout)
**Clips >12s:** ultrafast static encode (no zoompan)
**Clips ≤12s:** zoompan camera motion

---

*All key files backed up to `_backups/` with timestamp `20260616T195356Z`*
