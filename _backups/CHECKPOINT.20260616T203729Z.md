# VIRAL ENGINE — Project Checkpoint
**Saved:** 2026-06-16T20:36Z

---

## BRAND

**Umbrella:** Viral Engine
**Three channels — ALL BUILT ✅**

| ID | Channel | Category | EP001 | Launch Package |
|----|---------|----------|-------|----------------|
| CH01 | Little Olympus | Kids mythology 3–10 | ✅ Rendered (73s) | ✅ Done |
| CH02 | Gods & Glory | Adult history doc | ✅ Rendered (thermopylae) | ✅ Done |
| CH03 | Mech Legends | Kids robots 4–12 | ✅ Rendered (100s) | ✅ Done |

---

## RENDERED EPISODES

| File | Size | Duration | Status |
|------|------|----------|--------|
| `renders/little_olympus/lo_ep001.mp4` | 6.7MB | 73s | Upload-ready draft |
| `renders/thermopylae_final.mp4` | 17MB | ~8min | Upload-ready |
| `renders/mech_legends/ml_ep001.mp4` | 14.4MB | 100s | Upload-ready draft |

All also copied to `C:\Users\jjard\claude\` for easy access.

---

## MECH LEGENDS CHARACTERS

| Name | Color | Vehicle | Role |
|------|-------|---------|------|
| BLAZE | 🔴 Red | Fire truck → race car | Brave leader |
| STORM | 🔵 Blue | Helicopter | Brains / strategist |
| GRANITE | 🟢 Green | Bulldozer | Gentle giant / muscle |
| NOVA | ⚪ Silver | Rocket | Scientist / gadgets |
| RUMBLE | 🟣 Dark purple | Crusher | OVERWHELMING villain |
| BOLT | ⚫ Black | Lightning bolt | Sneaky sidekick |

---

## LAUNCH PACKAGES

Each channel has a folder with ready-to-paste copy:

- `gods_and_glory_launch/channel_copy.md` — name, handle, description, trailer script, thumbnail spec, sponsorship targets
- `gods_and_glory_launch/episode_titles_and_descriptions.md` — EP005–EP015 YouTube titles + descriptions
- `little_olympus_launch/channel_copy.md` — full channel copy, characters, thumbnail spec
- `mech_legends_launch/channel_copy.md` — full channel copy, characters, IP roadmap, EP001 upload details

---

## KEY FILES

```
video-bot-pipeline/
├── CHECKPOINT.md                    ← THIS FILE
├── viral_engine_bible.json          ← MASTER BRAND BIBLE (all 3 channels)
├── iron_legends_bible.json          ← Older IL bible (kept for reference)
│
├── mech_legends_render.py           ← Mech Legends render engine (BLAZE/RUMBLE colors)
├── little_olympus_render.py         ← Little Olympus render engine (kids cartoon)
├── documentary_render.py            ← Gods & Glory render engine
├── il_batch_render.py               ← Batch render runner
│
├── prompts/
│   ├── scene_prompts.lo_ep001.final.json   ← Little Olympus EP001 script (7 scenes)
│   ├── scene_prompts.ml_ep001.final.json   ← Mech Legends EP001 script (10 scenes, BLAZE/RUMBLE)
│   ├── scene_prompts.il_ep001.final.json   ← Old Iron Legends EP001 (DEPRECATED — use ml_ep001)
│   └── scene_prompts.ep006-015.final.json  ← Gods & Glory season 1 scripts
│
├── renders/
│   ├── little_olympus/lo_ep001.mp4         ← Little Olympus EP001 ✅
│   ├── mech_legends/ml_ep001.mp4           ← Mech Legends EP001 ✅
│   └── thermopylae_final.mp4               ← Gods & Glory EP005 ✅
│
├── gods_and_glory_launch/           ← G&G channel copy + episode descriptions
├── little_olympus_launch/           ← LO channel copy
├── mech_legends_launch/             ← ML channel copy
│
└── _backups/                        ← 131 timestamped backups
    └── (all files backed up at 20260616T203647Z)
```

---

## STANDING RULES

1. **Episode numbering never restarts**
2. **Save 3x:** primary + `_backups/<name>.latest.<ext>` + `_backups/<name>.<UTC-timestamp>.<ext>`
3. **episode_state.json** backups — Write tool only (not bash cp)
4. **Villains are OVERWHELMING** — every antagonist must feel impossible to beat
5. **Three active channels:** Little Olympus · Gods & Glory · Mech Legends

---

## WHAT TO DO NEXT

### Ready to do RIGHT NOW (no credits needed)
- [ ] Create all 3 YouTube channels (handles in channel_copy.md files)
- [ ] Upload EP001s to each channel
- [ ] Render Gods & Glory EP006 (Salamis) — script ready
- [ ] Write Little Olympus EP002 (Baby Hercules and the Giant Snake)
- [ ] Write Mech Legends EP002 (BLAZE's Secret Weapon)

### Needs Higgsfield credits (currently 0.75 — not enough)
- [ ] Generate real character art: BLAZE, STORM, GRANITE, NOVA, RUMBLE, BOLT
- [ ] Generate real character art: Little Zeus, Baby Hercules, Athena
- [ ] Re-render all episodes with real character visuals
- [ ] Generate Gods & Glory EP006–010 battle backgrounds

### Needs ElevenLabs (setup_needed per bible)
- [ ] Wire ElevenLabs into render engines for real voiceover narration

---

## RENDER COMMANDS QUICK REFERENCE

```bash
# Little Olympus
python3 little_olympus_render.py --ep lo_ep001 --scenes 1-3
python3 little_olympus_render.py --ep lo_ep001 --concat

# Mech Legends
python3 mech_legends_render.py --ep ml_ep001 --scenes 1-5
python3 mech_legends_render.py --ep ml_ep001 --concat
python3 mech_legends_render.py --ep ml_ep001 --status

# Gods & Glory (batch runner)
