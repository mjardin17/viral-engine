#!/usr/bin/env python3
"""
watch_and_save.py — Auto-saves new images from Downloads to character_images.

Run this ONCE in a terminal, then just download images normally.
Each new image gets a name prompt, then lands in character_images automatically.

Usage:
    python watch_and_save.py

Or with a specific watch folder:
    python watch_and_save.py --watch "C:\\Users\\jjard\\Pictures"
"""

import argparse
import shutil
import time
from pathlib import Path

CHARS_DIR    = Path(__file__).resolve().parent / "character_images"
DOWNLOADS    = Path.home() / "Downloads"
IMG_EXTS     = {".jpg", ".jpeg", ".png", ".webp"}

# Scene name shortcuts — type the number and it fills this in
QUICK_NAMES = {
    # ── GG_EP001 Thermopylae ─────────────────────────────────
    "101":  "spartans_holding_thermopylae_pass_cliff_sea",
    "102":  "spartan_army_marching_thermopylae_wide",
    "103":  "spartan_300_phalanx_formation",
    "104":  "leonidas_overlooking_persian_army",
    "105":  "leonidas_bloodied_battle_worn",
    "106":  "xerxes_commanding_army_pass",
    "107":  "athens_burning_spartan_view_sunset",
    "108":  "athens_siege_night_fireballs",
    "109":  "greek_gods_zeus_athena_poseidon_watching",
    "110":  "persian_immortals_marching",
    "111":  "spartan_army_final_stand",
    "112":  "spartan_army_with_shields_rain",
    # ── GG_EP002 Gaugamela ───────────────────────────────────
    "201":  "gaugamela_alexander_overlook_persian_camp",
    "202":  "gaugamela_persian_empire_peak",
    "203":  "gaugamela_darius_iii_portrait",
    "204":  "gaugamela_alexander_biography",
    "205":  "gaugamela_terrain_preparation",
    "206":  "gaugamela_armies_scale_comparison",
    "207":  "gaugamela_macedonian_phalanx_sarissa",
    "208":  "gaugamela_scythed_chariots",
    "209":  "gaugamela_alexander_night_before",
    "210":  "gaugamela_chariot_charge_neutralized",
    "211":  "gaugamela_oblique_advance_gap_opens",
    "212":  "gaugamela_companion_cavalry_charge",
    "213":  "gaugamela_darius_flees",
    "214":  "gaugamela_parmenion_crisis_left_flank",
    "215":  "gaugamela_pursuit_darius_escapes",
    "216":  "gaugamela_aftermath_honors_persian_guard",
    "217":  "gaugamela_babylon_gates_open",
    "218":  "gaugamela_persepolis_burning",
    "219":  "gaugamela_death_of_darius_bessus",
    "220":  "gaugamela_alexander_persian_court",
    "221":  "gaugamela_hellenistic_age_library",
    "222":  "gaugamela_military_legacy_west_point",
    "223":  "gaugamela_darius_reassessed",
    "224":  "gaugamela_modern_plain_legacy",
    # ── GG_EP003 Cannae ──────────────────────────────────────
    "301":  "cannae_70000_dead_hook",
    "302":  "cannae_hannibal_background",
    "303":  "cannae_carthage_vs_rome_context",
    "304":  "cannae_alps_crossing",
    "305":  "cannae_trebia_trasimene_fabius",
    "306":  "cannae_consuls_varro_paullus",
    "307":  "cannae_army_composition",
    "308":  "cannae_ground_selection",
    "309":  "cannae_roman_legion_system",
    "310":  "cannae_weak_center_trap",
    "311":  "cannae_cavalry_hasdrubal_ride",
    "312":  "cannae_center_bends",
    "313":  "cannae_african_veterans_pivot",
    "314":  "cannae_encirclement_closes",
    "315":  "cannae_killing_ground_interior",
    "316":  "cannae_death_of_paullus",
    "317":  "cannae_dead_count_aftermath",
    "318":  "cannae_maharbal_reproach",
    "319":  "cannae_rome_refuses_to_break",
    "320":  "cannae_scipio_africanus",
    "321":  "cannae_why_generals_study_it",
    "322":  "cannae_schlieffen_plan_1914",
    "323":  "cannae_reassessment_hannibal",
    "324":  "cannae_legacy_perfect_battle",
    # ── GG_EP004 Mongols ─────────────────────────────────────
    "401":  "mongols_largest_empire_aerial",
    "402":  "mongols_steppe_civilization",
    "403":  "mongols_temujin_origin",
    "404":  "mongols_coalition_building",
    "405":  "mongols_genghis_coronation",
    "406":  "mongols_horse_archer_system",
    "407":  "mongols_feigned_retreat",
    "408":  "mongols_psychological_warfare_surrender",
    "409":  "mongols_siege_capabilities",
    "410":  "mongols_china_xi_xia_jin",
    "411":  "mongols_khwarezmian_samarkand",
    "412":  "mongols_merv_destroyed",
    "413":  "mongols_genghis_dies_empire_accelerates",
    "414":  "mongols_russia_europe_nearly_fall",
    "415":  "mongols_baghdad_1258_burning",
    "416":  "mongols_house_of_wisdom_tigris_ink",
    "417":  "mongols_ain_jalut_defeat",
    "418":  "mongols_empire_fractures",
    "419":  "mongols_kublai_yuan_dynasty",
    "420":  "mongols_pax_mongolica_silk_road",
    "421":  "mongols_black_death_connection",
    "422":  "mongols_khanates_collapse",
    "423":  "mongols_death_toll_reckoning",
    "424":  "mongols_modern_legacy_genetics",
    # ── GG_EP005 Constantinople ──────────────────────────────
    "501":  "constantinople_aerial_city_1453",
    "502":  "constantinople_dying_empire",
    "503":  "constantinople_mehmed_ii_obsession",
    "504":  "constantinople_theodosian_walls",
    "505":  "constantinople_urbans_cannon",
    "506":  "constantinople_ottoman_arrival",
    "507":  "constantinople_constantine_diplomacy",
    "508":  "constantinople_giustiniani_genoese",
    "509":  "constantinople_cannon_bombardment",
    "510":  "constantinople_chain_golden_horn",
    "511":  "constantinople_ships_dragged_overland",
    "512":  "constantinople_encirclement_defenders",
    "513":  "constantinople_final_night_hagia_sophia",
    "514":  "constantinople_three_front_assault",
    "515":  "constantinople_giustiniani_wounded",
    "516":  "constantinople_constantine_last_stand",
    "517":  "constantinople_city_falls",
    "518":  "constantinople_mehmed_enters",
    "519":  "constantinople_scholars_flee_west",
    "520":  "constantinople_ottoman_rise",
    "521":  "constantinople_renaissance_connection",
    "522":  "constantinople_hinge_of_history",
    "523":  "constantinople_legacy_summary",
    "524":  "constantinople_next_episode",
    # ── GG_EP006 Salamis ────────────────────────────────────
    "601":  "salamis_greek_fleet_massive",
    "602":  "salamis_trireme_closeup",
    "603":  "themistocles_commanding",
    "604":  "salamis_persian_fleet_burning",
}

def watch(folder: Path) -> None:
    CHARS_DIR.mkdir(parents=True, exist_ok=True)
    seen = {f for f in folder.iterdir() if f.suffix.lower() in IMG_EXTS}

    print(f"\n👀  Watching: {folder}")
    print(f"💾  Saving to: {CHARS_DIR}")
    print(f"\nQuick names (type the number):")
    for k, v in QUICK_NAMES.items():
        print(f"  {k:>3} → {v}")
    print("\nOr type any custom name. Ctrl+C to stop.\n")

    while True:
        current = {f for f in folder.iterdir() if f.suffix.lower() in IMG_EXTS}
        new_files = current - seen

        for img in sorted(new_files, key=lambda f: f.stat().st_mtime):
            print(f"\n🖼️  New image: {img.name}")
            raw = input("   Name (number or custom, Enter to skip): ").strip()

            if not raw:
                print("   Skipped.")
                seen.add(img)
                continue

            name = QUICK_NAMES.get(raw, raw)
            if not name.endswith((".jpg", ".png", ".jpeg")):
                name += img.suffix

            dest = CHARS_DIR / name
            shutil.copy2(str(img), str(dest))
            print(f"   ✓ Saved as character_images/{name}")

        seen = current
        time.sleep(1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", default=str(DOWNLOADS), help="Folder to watch")
    args = ap.parse_args()
    watch(Path(args.watch))


if __name__ == "__main__":
    main()
