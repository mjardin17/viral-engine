#!/usr/bin/env python3
"""
VIRAL ENGINE — GENERATE_NEXT_EPISODE
=====================================
Master pipeline command. Generates a complete episode package:
  - Scene prompts (JSON)
  - Voice script (MD)
  - Thumbnail prompts (MD)
  - YouTube metadata (JSON)
  - Render job queue

Usage:
  python3 generate_next_episode.py --channel lo
  python3 generate_next_episode.py --channel ml
  python3 generate_next_episode.py --channel gg
  python3 generate_next_episode.py --channel lo --ep 3 --title "Perseus and the Tiny Medusa"
  python3 generate_next_episode.py --status
  python3 generate_next_episode.py --render-next lo
"""

import json, argparse, datetime, shutil, sys, subprocess
from pathlib import Path

# ─── PATHS ────────────────────────────────────────────────────────────────────
BASE    = Path(__file__).parent
PROMPTS = BASE / "prompts"
RENDERS = BASE / "renders"
OUTPUT  = BASE / "episodes"          # standardized output root
BIBLES  = BASE
BACKUPS = BASE / "_backups"

# ─── CHANNEL CONFIGS ──────────────────────────────────────────────────────────
CHANNELS = {
    "lo": {
        "id": "lo",
        "name": "Little Olympus",
        "handle": "@LittleOlympusTV",
        "prefix": "LO",
        "renderer": "little_olympus_render.py",
        "render_dir": RENDERS / "little_olympus",
        "aesthetic": "bright_kids_cartoon",
        "music": "upbeat_kids_adventure",
        "narrator_tone": "warm_playful_encouraging",
        "scene_count": 7,
        "scene_duration": 9,
        "bible": "Little_Olympus_Master_Bible.md",
        "colors": ["#FFD700", "#1A1060", "#00B4E6", "#FF6B35"],
    },
    "ml": {
        "id": "ml",
        "name": "Mech Legends",
        "handle": "@MechLegendsTV",
        "prefix": "ML",
        "renderer": "mech_legends_render.py",
        "render_dir": RENDERS / "mech_legends",
        "aesthetic": "cinematic_action_anime",
        "music": "140bpm_action_synth",
        "narrator_tone": "urgent_epic_cinematic",
        "scene_count": 10,
        "scene_duration": 9,
        "bible": "viral_engine_bible.json",
        "colors": ["#CC0000", "#1A1A2E", "#8B008B", "#FF6B00"],
    },
    "gg": {
        "id": "gg",
        "name": "Gods & Glory",
        "handle": "@GodsAndGloryAI",
        "prefix": "GG",
        "renderer": "documentary_render.py",
        "render_dir": RENDERS / "thermopylae_doc",
        "aesthetic": "cinematic_documentary",
        "music": "epic_orchestral",
        "narrator_tone": "authoritative_documentary",
        "scene_count": 6,
        "scene_duration": 60,
        "bible": "viral_engine_bible.json",
        "colors": ["#8B0000", "#1A1A2E", "#FFD700", "#4A4A4A"],
    },
}

# ─── EPISODE SCENE TYPE TEMPLATES ─────────────────────────────────────────────
SCENE_TYPES = {
    "lo": ["hook", "setup", "problem", "attempt", "solution", "resolution", "lesson_and_cta"],
    "ml": ["cold_open", "hero_intro", "villain_intro", "villain_dominance", "battle_attempt",
           "darkest_moment", "crisis", "turning_point", "hero_action", "cliffhanger"],
    "gg": ["cold_open", "historical_context", "key_players", "rising_tension",
           "climax", "aftermath_and_legacy"],
}

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def utc_stamp():
    return datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

def save_3x(src: Path):
    """Save primary + .latest + .timestamp backups."""
    BACKUPS.mkdir(exist_ok=True)
    stem = src.stem
    ext  = src.suffix
    shutil.copy2(src, BACKUPS / f"{stem}.latest{ext}")
    shutil.copy2(src, BACKUPS / f"{stem}.{utc_stamp()}{ext}")
    print(f"  ✓ Saved 3x: {src.name}")

def next_ep_number(channel_id: str) -> int:
    """Scan prompts dir to find the next episode number for a channel."""
    prefix = channel_id.lower()
    existing = sorted(PROMPTS.glob(f"scene_prompts.{prefix}_ep*.final.json"))
    if not existing:
        return 1
    last = existing[-1].name  # e.g. scene_prompts.lo_ep002.final.json
    num = int(last.split("_ep")[1].split(".")[0])
    return num + 1

def ep_id(channel_id: str, ep_num: int) -> str:
    return f"{channel_id.lower()}_ep{ep_num:03d}"

def ep_id_upper(channel_id: str, ep_num: int) -> str:
    return f"{CHANNELS[channel_id]['prefix']}_EP{ep_num:03d}"

# ─── STATUS ───────────────────────────────────────────────────────────────────
def print_status():
    print("\n╔══════════════════════════════════════════════════════╗")
    print("║       VIRAL ENGINE — PIPELINE STATUS                ║")
    print("╚══════════════════════════════════════════════════════╝\n")

    for ch_id, ch in CHANNELS.items():
        scripts = sorted(PROMPTS.glob(f"scene_prompts.{ch_id}_ep*.final.json"))
        renders = sorted(ch["render_dir"].glob(f"{ch_id}_ep*.mp4")) if ch["render_dir"].exists() else []

        print(f"  {ch['name']} ({ch['handle']})")
        print(f"    Scripts ready : {len(scripts)}")
        print(f"    Episodes rendered: {len(renders)}")
        for r in renders:
            size = r.stat().st_size // 1024
            print(f"      ✓ {r.name}  ({size}KB)")
        next_ep = next_ep_number(ch_id)
        print(f"    Next episode  : EP{next_ep:03d}")
        print()

# ─── GENERATE SCENE PROMPTS ───────────────────────────────────────────────────
def generate_scene_prompts(ch: dict, ep_num: int, title: str, logline: str) -> dict:
    """Generate a structured scene prompts JSON for the episode."""
    ch_id    = ch["id"]
    eid      = ep_id_upper(ch_id, ep_num)
    types    = SCENE_TYPES[ch_id]
    n_scenes = ch["scene_count"]

    scenes = []
    for i, stype in enumerate(types[:n_scenes], start=1):
        scenes.append({
            "scene_number": i,
            "type": stype,
            "title": f"[WRITE: Scene {i} — {stype.replace('_', ' ').title()}]",
            "narration": f"[WRITE: Narration for scene {i}. Keep to ~30 words. Match tone: {ch['narrator_tone']}]",
            "visual_prompt": f"[WRITE: Visual description for scene {i}. Aesthetic: {ch['aesthetic']}. 16:9.]",
            "bg_colors": ch["colors"][:3],
            "accent": ch["colors"][0],
            "camera": "push_in" if i % 2 == 0 else "pull_back",
            "duration_sec": ch["scene_duration"],
            "higgsfield_prompt": f"[WRITE: Higgsfield image prompt for scene {i}. Style: {ch['aesthetic']}. 16:9.]",
        })

    return {
        "channel": ch["name"],
        "episode_number": ep_num,
        "episode_id": eid,
        "title": title,
        "tagline": logline,
        "duration_target_min": (n_scenes * ch["scene_duration"]) // 60 + 1,
        "aesthetic": {
            "color_grade": ch["aesthetic"],
            "primary_colors": ch["colors"],
            "font_style": "rounded_chunky_bold" if ch_id == "lo" else "bold_angular_impact",
            "music_style": ch["music"],
            "narrator_tone": ch["narrator_tone"],
        },
        "scenes": scenes,
        "music": {
            "style": ch["music"],
            "notes": "[WRITE: Specific music direction for this episode]",
        },
        "voice_style": {
            "tone": ch["narrator_tone"],
            "pacing": "[WRITE: Specific pacing notes]",
            "character": "[WRITE: Voice character description]",
        },
        "lesson": "[WRITE: The lesson or takeaway of this episode]",
        "youtube_title": f"[WRITE: YouTube title for {title}]",
        "youtube_description": "[WRITE: Full YouTube description (3–5 paragraphs + hashtags)]",
        "next_episode_preview": "[WRITE: One-line tease for the next episode]",
        "higgsfield_style_notes": f"[WRITE: Style mandate for all scenes — aesthetic: {ch['aesthetic']}]",
    }

# ─── GENERATE VOICE SCRIPT ────────────────────────────────────────────────────
def generate_voice_script(ch: dict, ep_num: int, title: str, scene_data: dict) -> str:
    ch_id = ch["id"]
    eid   = ep_id_upper(ch_id, ep_num)
    lines = [
        f"# {ch['name'].upper()} — {eid}: {title}",
        f"## VOICE SCRIPT",
        f"**Channel:** {ch['handle']}",
        f"**Narrator tone:** {ch['narrator_tone']}",
        f"**ElevenLabs voice:** [ASSIGN VOICE ID]",
        "",
        "---",
        "",
        "### INTRO BUMPER (if applicable)",
        "[Leave blank — bumper is auto-generated by renderer]",
        "",
        "---",
        "",
    ]
    for scene in scene_data.get("scenes", []):
        n = scene["scene_number"]
        t = scene.get("title", f"Scene {n}")
        narration = scene.get("narration", "[WRITE narration]")
        lines += [
            f"### SCENE {n:02d} — {t}",
            f"**Type:** `{scene.get('type', '')}`  |  **Duration:** {scene.get('duration_sec', 9)}s",
            "",
            f"**NARRATION:**",
            f"> {narration}",
            "",
            f"**ElevenLabs settings:**",
            f"- Stability: 0.65",
            f"- Similarity boost: 0.75",
            f"- Style: 0.40",
            "",
            "---",
            "",
        ]
    lines += [
        "### END CARD",
        "[Auto-generated by renderer — no narration needed]",
        "",
        "---",
        "",
        f"*Generated: {utc_stamp()} · Viral Engine Pipeline*",
    ]
    return "\n".join(lines)

# ─── GENERATE THUMBNAIL PROMPTS ───────────────────────────────────────────────
def generate_thumbnail_prompts(ch: dict, ep_num: int, title: str) -> str:
    ch_id = ch["id"]
    eid   = ep_id_upper(ch_id, ep_num)

    if ch_id == "lo":
        bg = "Deep blue-purple (#1A1060)"
        text_color = "Gold (#FFD700)"
        style = "Bright cartoon, CoComelon energy. Big expressive eyes. Happy faces."
        key_elements = "Main character's face (close up, expressive), episode hook text (large), sparkle/star accents"
    elif ch_id == "ml":
        bg = "Dark (#0A0510) with energy effects"
        text_color = "White with red accent"
        style = "Cinematic action anime. Dynamic. Urgent. Epic scale."
        key_elements = "BLAZE (red, front-center) vs RUMBLE (looming background), action text, energy lightning"
    else:
        bg = "Black (#0A0A0A)"
        text_color = "Gold (#FFD700)"
        style = "Epic documentary. Dark. Cinematic. Historical gravitas."
        key_elements = "Battle scene or hero figure, dramatic lighting, gold title text, dark red accent bar"

    return f"""# THUMBNAIL SPEC — {eid}: {title}
**Channel:** {ch['name']} ({ch['handle']})
**Size:** 1280 × 720px

---

## OPTION A (Primary)
**Background:** {bg}
**Text:** {text_color}
**Style:** {style}
**Key elements:** {key_elements}

**Higgsfield prompt:**
```
[WRITE: Full Higgsfield image generation prompt for thumbnail.
Must be 1280x720, eye-catching, thumbnail-optimized.
Style: {ch['aesthetic']}. No text — text added in post.]
```

**Canva overlay text:**
- Headline: [WRITE: 3–5 word hook, all caps]
- Subtitle: [WRITE: Episode number or character name]
- Font: [Bold, rounded for LO / Heavy angular for ML / Serif for GG]

---

## OPTION B (Alternate)
**Concept:** [WRITE: alternate composition concept]

**Higgsfield prompt:**
```
[WRITE: alternate prompt]
```

---

## TEXT PLACEMENT GUIDE
```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  [CHARACTER/SCENE IMAGE]          [HEADLINE TEXT]           │
│                                   [subtitle]                │
│                                                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**A/B test:** Upload both thumbnails for 48 hours, keep whichever has higher CTR.

*Generated: {utc_stamp()} · Viral Engine Pipeline*
"""

# ─── GENERATE METADATA ────────────────────────────────────────────────────────
def generate_metadata(ch: dict, ep_num: int, title: str) -> dict:
    ch_id = ch["id"]
    eid   = ep_id_upper(ch_id, ep_num)

    tags_base = {
        "lo": ["LittleOlympus", "KidsCartoon", "GreekMythology", "KidsYouTube",
               "LittleZeus", "BabyHercules", "Athena", "KidsMythology", "LearnWithMe"],
        "ml": ["MechLegends", "RobotHeroes", "KidsCartoon", "Transformers",
               "BLAZE", "RUMBLE", "KidsYouTube", "MechCartoon", "RobotAction"],
        "gg": ["GodsAndGlory", "HistoryDocumentary", "AncientHistory",
               "MythologyHistory", "EpicBattles", "HistoryYouTube", "Documentary"],
    }

    return {
        "channel": ch["name"],
        "handle": ch["handle"],
        "episode_id": eid,
        "episode_number": ep_num,
        "title": title,
        "youtube_title": f"[WRITE: YouTube title — include emoji, character name, episode number]",
        "youtube_description": (
            f"[WRITE: Hook line (1–2 sentences)]\n\n"
            f"In this episode:\n"
            f"→ [Beat 1]\n→ [Beat 2]\n→ [Lesson/outcome]\n\n"
            f"📺 Full series: [playlist link]\n"
            f"🔔 SUBSCRIBE: [link]\n\n"
            f"#{' #'.join(tags_base[ch_id][:5])}"
        ),
        "tags": tags_base[ch_id],
        "category": "Kids & Family" if ch_id in ("lo", "ml") else "Education",
        "made_for_kids": ch_id in ("lo", "ml"),
        "language": "en",
        "default_audio_language": "en",
        "playlist": f"{ch['name']} Season 1",
        "thumbnail_file": f"[GENERATE: thumbnail_{ch_id}_ep{ep_num:03d}.jpg]",
        "upload_status": "pending",
        "scheduled_publish": "[OPTIONAL: ISO8601 datetime for scheduled publish]",
        "generated_at": utc_stamp(),
    }

# ─── STANDARDIZED OUTPUT STRUCTURE ────────────────────────────────────────────
def create_episode_package(ch: dict, ep_num: int, title: str, logline: str):
    """Generate all assets and write them to the standard folder structure."""
    ch_id = ch["id"]
    eid   = ep_id(ch_id, ep_num)
    pkg   = OUTPUT / ch_id / eid
    pkg.mkdir(parents=True, exist_ok=True)

    print(f"\n🎬  Generating episode package: {eid.upper()}")
    print(f"    Channel : {ch['name']}")
    print(f"    Title   : {title}")
    print(f"    Output  : {pkg}\n")

    # 1. Scene prompts JSON
    scene_data = generate_scene_prompts(ch, ep_num, title, logline)
    script_path = pkg / "script.json"
    with open(script_path, "w") as f:
        json.dump(scene_data, f, indent=2)
    # Also write to prompts/ for renderers
    prompt_path = PROMPTS / f"scene_prompts.{eid}.final.json"
    with open(prompt_path, "w") as f:
        json.dump(scene_data, f, indent=2)
    save_3x(prompt_path)
    print(f"  ✓ Script       → {script_path.name}")
    print(f"  ✓ Scene prompts→ {prompt_path.name}")

    # 2. Voice script
    voice_md = generate_voice_script(ch, ep_num, title, scene_data)
    voice_path = pkg / "voice_script.md"
    voice_path.write_text(voice_md)
    save_3x(voice_path)
    print(f"  ✓ Voice script → {voice_path.name}")

    # 3. Thumbnail prompts
    thumb_md = generate_thumbnail_prompts(ch, ep_num, title)
    thumb_path = pkg / "thumbnail_prompts.md"
    thumb_path.write_text(thumb_md)
    save_3x(thumb_path)
    print(f"  ✓ Thumbnails   → {thumb_path.name}")

    # 4. YouTube metadata
    meta = generate_metadata(ch, ep_num, title)
    meta_path = pkg / "metadata.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    save_3x(meta_path)
    print(f"  ✓ Metadata     → {meta_path.name}")

    # 5. Render job file
    render_job = {
        "episode_id": eid,
        "channel": ch_id,
        "renderer": ch["renderer"],
        "scene_count": ch["scene_count"],
        "commands": [],
        "status": "queued",
        "queued_at": utc_stamp(),
    }
    # Break into 2-scene batches to avoid timeout
    for start in range(1, ch["scene_count"] + 1, 2):
        end = min(start + 1, ch["scene_count"])
        render_job["commands"].append(
            f"python3 {ch['renderer']} --ep {eid} --scenes {start}-{end}"
        )
    render_job["commands"].append(f"python3 {ch['renderer']} --ep {eid} --concat")

    job_path = pkg / "render_job.json"
    with open(job_path, "w") as f:
        json.dump(render_job, f, indent=2)
    save_3x(job_path)
    print(f"  ✓ Render job   → {job_path.name}")

    # 6. README for the package
    readme = f"""# {eid.upper()} — {title}

**Channel:** {ch['name']} ({ch['handle']})
**Generated:** {utc_stamp()}

## Files in this package
| File | Status | Notes |
|------|--------|-------|
| `script.json` | ✅ Template generated | **FILL IN** scene narrations and visual prompts |
| `voice_script.md` | ✅ Template generated | **FILL IN** after script is complete |
| `thumbnail_prompts.md` | ✅ Template generated | **FILL IN** Higgsfield prompts |
| `metadata.json` | ✅ Template generated | **FILL IN** YouTube title and description |
| `render_job.json` | ✅ Queued | Run commands in order after script is complete |

## To complete this episode

1. **Fill in `script.json`** — write all `[WRITE: ...]` placeholders for narration + visual prompts
2. **Update `voice_script.md`** — copy narration from script, assign ElevenLabs voice IDs
3. **Update `metadata.json`** — write final YouTube title + description
4. **Generate thumbnails** — run Higgsfield prompts from `thumbnail_prompts.md`
5. **Run render job** — execute commands in `render_job.json` in order
6. **Upload to YouTube** — use metadata.json for all fields

## Render commands
```bash
{"  ".join(chr(10) + "  " + cmd for cmd in render_job["commands"])}
```
"""
    (pkg / "README.md").write_text(readme)
    print(f"  ✓ README       → README.md")

    print(f"\n  📦 Package complete: episodes/{ch_id}/{eid}/")
    print(f"  ⚠️  Fill in [WRITE: ...] placeholders in script.json before rendering.\n")

    return pkg

# ─── RENDER NEXT ──────────────────────────────────────────────────────────────
def render_next(channel_id: str):
    """Find the next unrendered episode and run its render job."""
    ch = CHANNELS[channel_id]
    render_dir = ch["render_dir"]

    # Find all scripted eps
    scripted = sorted(PROMPTS.glob(f"scene_prompts.{channel_id}_ep*.final.json"))
    if not scripted:
        print(f"No scripts found for {ch['name']}. Run generate first.")
        return

    for script in scripted:
        ep_name = script.stem.replace("scene_prompts.", "").replace(".final", "")
        final = render_dir / f"{ep_name}.mp4"
        if not final.exists():
            print(f"Rendering: {ep_name}")
            job_path = OUTPUT / channel_id / ep_name / "render_job.json"
            if job_path.exists():
                job = json.load(open(job_path))
                for cmd in job["commands"]:
                    print(f"  $ {cmd}")
                    subprocess.run(["python3"] + cmd.split()[1:], cwd=BASE)
            else:
                # Run without job file
                n = CHANNELS[channel_id]["scene_count"]
                for start in range(1, n + 1, 2):
                    end = min(start + 1, n)
                    subprocess.run(
                        ["python3", ch["renderer"], "--ep", ep_name, "--scenes", f"{start}-{end}"],
                        cwd=BASE
                    )
                subprocess.run(
                    ["python3", ch["renderer"], "--ep", ep_name, "--concat"],
                    cwd=BASE
                )
            return
    print(f"All scripted episodes for {ch['name']} are already rendered.")

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="VIRAL ENGINE — GENERATE_NEXT_EPISODE",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 generate_next_episode.py --channel lo
  python3 generate_next_episode.py --channel ml --title "GRANITE's Sacrifice"
  python3 generate_next_episode.py --channel lo --ep 3 --logline "Perseus faces the mirror monster"
  python3 generate_next_episode.py --status
  python3 generate_next_episode.py --render-next lo
        """
    )
    parser.add_argument("--channel", "-c", choices=["lo", "ml", "gg"],
                        help="Channel ID (lo=Little Olympus, ml=Mech Legends, gg=Gods & Glory)")
    parser.add_argument("--ep", type=int, default=None,
                        help="Episode number (auto-detects if not specified)")
    parser.add_argument("--title", "-t", default=None,
                        help="Episode title (prompted if not specified)")
    parser.add_argument("--logline", "-l", default="",
                        help="One-line episode logline / tagline")
    parser.add_argument("--status", "-s", action="store_true",
                        help="Show pipeline status for all channels")
    parser.add_argument("--render-next", metavar="CHANNEL",
                        help="Find and render the next unrendered episode for a channel")

    args = parser.parse_args()

    if args.status:
        print_status()
        return

    if args.render_next:
        if args.render_next not in CHANNELS:
            print(f"Unknown channel: {args.render_next}. Use: lo, ml, gg")
            sys.exit(1)
        render_next(args.render_next)
        return

    if not args.channel:
        print("\nViral Engine — Generate Next Episode\n")
        print("Channels:")
        for k, v in CHANNELS.items():
            print(f"  {k}  →  {v['name']} ({v['handle']})")
        ch_input = input("\nChannel (lo/ml/gg): ").strip().lower()
        if ch_input not in CHANNELS:
            print("Invalid channel.")
            sys.exit(1)
        args.channel = ch_input

    ch     = CHANNELS[args.channel]
    ep_num = args.ep or next_ep_number(args.channel)
    title  = args.title or input(f"Episode title for {ch['name']} EP{ep_num:03d}: ").strip()
    logline = args.logline or input("One-line tagline (Enter to skip): ").strip()

    create_episode_package(ch, ep_num, title, logline)

if __name__ == "__main__":
    main()
