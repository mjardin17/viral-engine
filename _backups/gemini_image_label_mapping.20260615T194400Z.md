# Image Label Mapping — Higgsfield/Gemini Output → Pipeline Filenames

All 27 generated images came back in the same order as the prompt list. Use this table to rename each saved file to its `label` + `.png` for the pipeline (`prompts/scene_prompts.epXXX.final.json` → `character_images`).

| # | Higgsfield Title | Pipeline Filename | Episode | Type |
|---|---|---|---|---|
| 1 | General Themistocles | themistocles_reference.png | 6 | Character |
| 2 | King Xerxes of Persia | xerxes_reference.png | 6 | Character |
| 3 | Alexander the Great | alexander_reference.png | 7 | Character |
| 4 | King Darius III of Persia | darius_iii_reference.png | 7 | Character |
| 5 | Ancient Persian War Elephant | war_elephant_reference.png | 7 | Machine |
| 6 | Young Hannibal Barca | young_hannibal_reference.png | 8 | Character |
| 7 | Early Roman Consul | roman_consul_reference.png | 8 | Character |
| 8 | Roman Naval Corvus Device | corvus_boarding_device_reference.png | 8 | Machine |
| 9 | General Hannibal Barca (Adult) | hannibal_adult_reference.png | 10 | Character |
| 10 | Carthaginian War Elephant | carthaginian_war_elephant_reference.png | 10 | Machine |
| 11 | Republican Roman Legionary | roman_legionary_reference.png | 10 | Character |
| 12 | Consul Lucius Aemilius Paullus | roman_consul_paullus_reference.png | 12 | Character |
| 13 | Carthaginian Veteran Infantry | carthaginian_veteran_infantry_reference.png | 12 | Character |
| 14 | Genghis Khan | genghis_khan_reference.png | 9 | Character |
| 15 | Shah Muhammad II of Khwarezm | khwarezm_shah_reference.png | 9 | Character |
| 16 | Mongol Siege Trebuchet | mongol_siege_engine_reference.png | 9 | Machine |
| 17 | Sultan Saladin (Salah ad-Din) | saladin_reference.png | 13 | Character |
| 18 | Crusader King Guy | crusader_king_reference.png | 13 | Character |
| 19 | Crusader Concentric Castle | crusader_castle_reference.png | 13 | Structure |
| 20 | Sultan Mehmed II (The Conqueror) | mehmed_ii_reference.png | 11 | Character |
| 21 | Emperor Constantine XI Palaiologos | constantine_xi_reference.png | 11 | Character |
| 22 | The Ottoman Basilica Siege Cannon | basilica_cannon_reference.png | 11 | Machine |
| 23 | General George Washington | washington_reference.png | 14 | Character |
| 24 | British General Cornwallis | british_general_reference.png | 14 | Character |
| 25 | Napoleon Bonaparte (1815-Waterloo) | napoleon_reference.png | 15 | Character |
| 26 | Duke of Wellington (Arthur Wellesley) | wellington_reference.png | 15 | Character |
| 27 | French Imperial Guard Grenadier | imperial_guard_grenadier_reference.png | 15 | Character |

## Notes
- Higgsfield's batch save (27 items) should preserve this order — if filenames come out as `image_01.png` ... `image_27.png` (or similar sequential names), rename using the table above.
- Once renamed, drop all 27 files into `video-bot-pipeline/character_images/` so they're ready for the next pipeline step (video_prompt generation / scene rendering for episodes 6-15).
- The "Themistocles/Xerxes" pair (ep6) was already covered by earlier work — confirm whether these are net-new generations or duplicates before overwriting any existing assets.
