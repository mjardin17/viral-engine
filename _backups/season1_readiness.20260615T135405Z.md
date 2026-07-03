# Empire Decoded — Season 1 Readiness (Episodes 6-15)

All 10 episode scripts are fully written, QA'd, and saved to `prompts/scene_prompts.epNNN.final.json` (each `rendered: false`). Every file is backed up 3x in `_backups/`. `episode_state.json` updated, `next_episode_number: 16`.

| Ep | Title | Scenes | Music | SFX | Character Images |
|----|-------|--------|-------|-----|-------------------|
| 6 | Salamis and Plataea: How Greece Won the War | 6 | 1 | 6 | 2 |
| 7 | Alexander's Gamble: The Battle of Gaugamela | 6 | 1 | 6 | 3 |
| 8 | The Punic Wars: Rome and Carthage at the Brink | 6 | 1 | 6 | 3 |
| 9 | The Mongol Storm: Conquest of the Khwarezmian Empire | 6 | 1 | 6 | 3 |
| 10 | Hannibal's Crossing: Over the Alps and Into Italy | 6 | 1 | 6 | 3 |
| 11 | The Fall of Constantinople: End of an Empire | 6 | 1 | 6 | 3 |
| 12 | Cannae: Rome's Darkest Day | 6 | 1 | 6 | 2 |
| 13 | The Crusader Kingdoms: Rise and Fall of Outremer | 6 | 1 | 6 | 3 |
| 14 | Yorktown: The Battle That Ended an Empire | 6 | 1 | 6 | 2 |
| 15 | Waterloo: Napoleon's Last Gamble (season finale) | 6 | 1 | 6 | 3 |

Every episode follows the villain-strength brief (antagonist faction always overwhelming, victory feels against-impossible-odds).

## What's needed from Higgsfield once credits are back

For each episode, in order:
1. **Narration (inworld_text_to_speech, Hades voice)** — 6 narration lines per episode (one per scene).
2. **Music (sonilo_music)** — 1 score per episode, 300s, prompt included in each file.
3. **Sound effects (mirelo_text_to_audio)** — 6 SFX per episode.
4. **Character reference images (nano_banana_2)** — 2-3 per episode (new characters/objects only; recurring figures like Xerxes from ep6 can be reused).
5. **Video clips (grok_video)** — 6 scene clips per episode, using the `video_prompt` fields, generated from/anchored to the character images for consistency.

## Also pending
- **Episode 5 (Thermopylae)**: assets exist on Higgsfield's cloud (`assets/episode005_thermopylae_manifest.json`) but final assembly hasn't happened — only 1 of 6 video clips done.
- **Little Olympus** side project: 6 narration lines exist (Theodore voice); no music/SFX/images/video yet, no pipeline. Your call on whether this becomes its own series.
- **Season 2**: `topic_backlog` is now empty. Add new topics before running `pipeline.py --auto` for episode 16, or it'll loop back to episode 6's topic. A few suggestions are noted in `episode_state.json` under `season_2_note`.

Once credits return, work through episodes in order (5, then 6-15) — everything's scripted and ready to feed straight into generation.
