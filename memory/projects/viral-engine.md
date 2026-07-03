# Viral Engine — Full Project Details

## What It Is
3-channel AI YouTube documentary pipeline. Auto-renders 18-20 min episodes:
episode JSON script → 4 AI images/scene → edge-tts narration → Ken Burns FFmpeg → music mix → final MP4.

## Channels
1. **Gods & Glory (GG)** — History/battle documentaries. Dark cinematic style, gold/black palette.
2. **Machine Learning (ML)** — Second channel (topic TBD from scripts)
3. **Little Olympus (LO)** — Kid-friendly mythology (Little Zeus)

## File Structure
```
C:\Users\jjard\claude\video-bot-pipeline\
├── auto_render.py          ← Core pipeline
├── patch_fallbacks.py      ← Image repair
├── script_guard.py         ← Script protection
├── script_registry.json    ← 16 registered full scripts
├── council\                ← 9-bot self-healing system
│   ├── council.py
│   ├── bot_base.py
│   └── bots\bot_01 through bot_09
├── prompts\
│   ├── gods_glory\         ← Full GG scripts (auto_render picks these)
│   ├── machine_learning\
│   └── little_olympus\
├── output\                 ← Rendered clips and finals
└── CLAUDE.md               ← This memory system
```

## Season 3 Scripts — ALL COMPLETE ✅
- EP012 ✅ "The Last Emperor" (Fall of Rome, 476 AD) — 24 scenes, 1098s
- EP013 ✅ "The Crusader Kingdoms" — 24 scenes
- EP014 ✅ "Waterloo: The Day Napoleon's Genius Ran Out of Miracles" — 24 scenes, 1117s
- EP015 ✅ "Marathon: The 26-Mile Run That Saved Western Civilization" — 24 scenes, 1101s
- EP016 ✅ "Agincourt: How Mud and Arrows Beat French Chivalry" — 24 scenes, 1105s
- EP017 ✅ "Battle of Tours: The Hammer That Stopped Islam's Conquest of Europe" — 24 scenes, 1098s
- EP018 ✅ "Hastings 1066: The Arrow That Forged a Nation" — 24 scenes, 1104s
- EP019 ✅ "Kamikaze: How Two Typhoons Drowned the Mongol Fleet" — 24 scenes, 1104s
- EP020 ✅ "Vienna 1683: The Winged Hussars" — 24 scenes, 1098s
- EP021 ✅ "Midway: Four Minutes That Turned the Pacific War" — 24 scenes, 1100s
- EP022 ✅ "Battle of the Bulge: Hitler's Last Gamble in the Frozen Ardennes" — 24 scenes, 1098s
- EP023 ✅ "Operation Market Garden: A Bridge Too Far" — 24 scenes, 1097s
- EP024 ✅ "Inchon: MacArthur's Impossible Landing" — 24 scenes, 1097s
- EP025 ✅ "Yorktown: The Battle That Ended an Empire" — 24 scenes, 1094s

**TO RENDER:** run render_season3.bat — will produce GG_EP012 through GG_EP025 finals in renders/

## Stub Backlog (84 episodes across all channels)
GG(14), GG_HIST(10), LO(37), ML(21), IL(1), GG_TRAILER(1)
Tracked in: council/state/stub_backlog.json

## Immediate Fix Needed
GG_EP006 (Pearl Harbor) — 21 of 24 clips are 0KB. Full 24-scene script exists at
prompts/gods_glory/scene_prompts.gg_ep006.final.json. Run render_ep006.bat to fix.

## Technical Notes
- find_episode_json() searches PROMPTS_DIR.rglob("*.json"), sorts alphabetically
- gods_glory/ subdirectory sorts before root-level files → full scripts always win
- 4 images per scene, scene_NN_1.jpg through scene_NN_4.jpg
- Music: battle_epic.mp3 at 0.08 volume
- Image fallback chain: Pollinations → Gemini (GEMINI_API_KEY env var)
- FALLBACK_BYTES threshold: 20KB
