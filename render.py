#!/usr/bin/env python3
"""
render.py

Empire Decoded render orchestrator.
Reads a finished scene_prompts.epNNN.final.json and drives the full
asset generation pipeline:

  Step 1 — Narration audio   (6 clips, one per scene)
  Step 2 — Music score       (1 track per episode)
  Step 3 — Sound effects     (6 clips, one per scene)
  Step 4 — Character images  (2-3 reference images per episode)
  Step 5 — Scene videos      (6 clips, one per scene, anchored to character refs)
  Step 6 — Final assembly    (concatenate via FFmpeg → EP_NNN.mp4)

Usage:
  python3 render.py --episode 6                  # render episode 6
  python3 render.py --episode 6 --steps 1,2,3    # run only steps 1-3
  python3 render.py --episode 6 --step narration # run only narration
  python3 render.py --episode 6 --dry-run        # show what would run, don't submit
  python3 render.py --status                     # show render status for all episodes
  python3 render.py --assemble 6                 # run FFmpeg assembly only (assets must exist)

Provider selection (in priority order):
  Video : $RENDER_VIDEO_PROVIDER   (higgsfield|kling|veo|runway, default: higgsfield)
  Audio : $RENDER_AUDIO_PROVIDER   (higgsfield only for TTS/music/sfx)
  Image : $RENDER_IMAGE_PROVIDER   (higgsfield only for character refs)

All jobs are tracked in render_state.json.
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
PROMPTS_DIR = ROOT / "prompts"
RENDER_DIR = ROOT / "renders"
CHARACTER_IMAGES_DIR = ROOT / "character_images"
RENDER_STATE_PATH = ROOT / "render_state.json"
BACKUPS_DIR = ROOT / "_backups"

STEP_NARRATION  = "narration"
STEP_MUSIC      = "music"
STEP_SFX        = "sfx"
STEP_IMAGES     = "images"
STEP_VIDEO      = "video"
STEP_ASSEMBLY   = "assembly"

ALL_STEPS = [STEP_NARRATION, STEP_MUSIC, STEP_SFX, STEP_IMAGES, STEP_VIDEO, STEP_ASSEMBLY]

STEP_ALIASES = {
    "1": STEP_NARRATION, "narration": STEP_NARRATION,
    "2": STEP_MUSIC,     "music": STEP_MUSIC,
    "3": STEP_SFX,       "sfx": STEP_SFX,
    "4": STEP_IMAGES,    "images": STEP_IMAGES, "chars": STEP_IMAGES, "characters": STEP_IMAGES,
    "5": STEP_VIDEO,     "video": STEP_VIDEO, "scenes": STEP_VIDEO,
    "6": STEP_ASSEMBLY,  "assembly": STEP_ASSEMBLY, "assemble": STEP_ASSEMBLY,
}


# ── Provider loader ────────────────────────────────────────────────────────────

def get_provider(kind: str):
    """
    kind: 'video' | 'audio' | 'image'
    Returns an instantiated provider based on env vars.
    Falls back to Higgsfield as default.
    """
    env_map = {
        "video": "RENDER_VIDEO_PROVIDER",
        "audio": "RENDER_AUDIO_PROVIDER",
        "image": "RENDER_IMAGE_PROVIDER",
    }
    name = os.environ.get(env_map.get(kind, ""), "higgsfield").lower()

    if name == "kling":
        from providers.kling import KlingProvider
        return KlingProvider()
    elif name == "veo":
        from providers.veo import VeoProvider
        return VeoProvider()
    elif name == "runway":
        from providers.runway import RunwayProvider
        return RunwayProvider()
    else:
        from providers.higgsfield import HiggssfieldProvider
        return HiggssfieldProvider()


# ── Render state ──────────────────────────────────────────────────────────────

def load_render_state() -> dict:
    if RENDER_STATE_PATH.exists():
        with open(RENDER_STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_render_state(state: dict):
    with open(RENDER_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    BACKUPS_DIR.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    with open(BACKUPS_DIR / f"render_state.{ts}.json", "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    with open(BACKUPS_DIR / "render_state.latest.json", "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def ep_key(episode_number: int) -> str:
    return f"ep{episode_number:03d}"


# ── Asset output paths ─────────────────────────────────────────────────────────

def ep_render_dir(episode_number: int) -> Path:
    d = RENDER_DIR / ep_key(episode_number)
    d.mkdir(parents=True, exist_ok=True)
    return d


def narration_path(episode_number: int, scene_number: int) -> Path:
    return ep_render_dir(episode_number) / f"narration_s{scene_number:02d}.mp3"


def music_path(episode_number: int) -> Path:
    return ep_render_dir(episode_number) / "music.mp3"


def sfx_path(episode_number: int, scene_number: int) -> Path:
    return ep_render_dir(episode_number) / f"sfx_s{scene_number:02d}.mp3"


def video_path(episode_number: int, scene_number: int) -> Path:
    return ep_render_dir(episode_number) / f"scene_s{scene_number:02d}.mp4"


def final_mp4_path(episode_number: int) -> Path:
    return RENDER_DIR / f"EP_{episode_number:03d}.mp4"


# ── Load episode script ────────────────────────────────────────────────────────

def load_episode(episode_number: int) -> dict:
    path = PROMPTS_DIR / f"scene_prompts.ep{episode_number:03d}.final.json"
    if not path.exists():
        raise FileNotFoundError(f"No script found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Download helper ────────────────────────────────────────────────────────────

def download_file(url: str, dest: Path):
    """Download a URL to dest path."""
    with urllib.request.urlopen(url, timeout=60) as resp:
        dest.write_bytes(resp.read())
    print(f"    ↓ saved {dest.name}")


# ── Job poller ────────────────────────────────────────────────────────────────

def poll_job(provider, job_id: str, dest: Path, label: str,
             poll_interval: int = 10, max_wait: int = 600):
    """Poll until job completes, then download the output."""
    print(f"  ⏳ polling {label} (job {job_id}) ...")
    elapsed = 0
    while elapsed < max_wait:
        result = provider.get_job_status(job_id)
        status = result.get("status", "unknown")
        if status in ("completed", "SUCCEEDED", "succeeded", "success"):
            url = result.get("output_url")
            if url:
                download_file(url, dest)
                return True
            else:
                print(f"  ⚠ job {job_id} completed but no output_url returned")
                return False
        elif status in ("failed", "FAILED", "error", "ERROR"):
            print(f"  ✗ job {job_id} failed: {result}")
            return False
        print(f"    status={status}, waiting {poll_interval}s ...")
        time.sleep(poll_interval)
        elapsed += poll_interval
    print(f"  ✗ timed out waiting for job {job_id}")
    return False


# ── Step implementations ───────────────────────────────────────────────────────

def run_narration(episode: dict, state: dict, dry_run: bool):
    ep = episode["episode_number"]
    key = ep_key(ep)
    provider = get_provider("audio")
    print(f"\n[Step 1: Narration] provider={provider.__class__.__name__} connected={provider.is_connected()}")
    state.setdefault(key, {}).setdefault("narration", {})

    for scene in episode["scenes"]:
        sn = scene["scene_number"]
        dest = narration_path(ep, sn)
        if dest.exists():
            print(f"  ✓ scene {sn} narration already exists, skipping")
            state[key]["narration"][str(sn)] = {"status": "completed", "path": str(dest)}
            continue
        text = scene.get("narration", "")
        if not text:
            print(f"  ⚠ scene {sn} has no narration text, skipping")
            continue
        print(f"  → scene {sn}: {text[:60]}...")
        if dry_run:
            print(f"    [dry-run] would call generate_audio(text, voice='Hades')")
            continue
        result = provider.generate_audio(text, voice="Hades")
        if result.get("status") == "not_connected":
            print(f"    ✗ {result['message']}")
            state[key]["narration"][str(sn)] = {"status": "not_connected"}
            continue
        job_id = result.get("job_id")
        if job_id:
            ok = poll_job(provider, job_id, dest, f"narration s{sn}")
            state[key]["narration"][str(sn)] = {
                "status": "completed" if ok else "failed",
                "job_id": job_id,
                "path": str(dest) if ok else None,
            }
        else:
            print(f"    ✗ no job_id returned: {result}")
            state[key]["narration"][str(sn)] = {"status": "error", "raw": result}

    save_render_state(state)


def run_music(episode: dict, state: dict, dry_run: bool):
    ep = episode["episode_number"]
    key = ep_key(ep)
    provider = get_provider("audio")
    print(f"\n[Step 2: Music] provider={provider.__class__.__name__} connected={provider.is_connected()}")
    state.setdefault(key, {}).setdefault("music", {})

    dest = music_path(ep)
    if dest.exists():
        print(f"  ✓ music already exists, skipping")
        state[key]["music"] = {"status": "completed", "path": str(dest)}
        save_render_state(state)
        return

    music = episode.get("music", {})
    prompt = music.get("prompt", "Epic cinematic historical orchestral score")
    duration = music.get("duration_sec", 300)
    print(f"  → music prompt: {prompt[:80]}...")
    if dry_run:
        print(f"    [dry-run] would call generate_music(prompt, duration={duration})")
        return

    result = provider.generate_music(prompt, duration_sec=duration)
    if result.get("status") == "not_connected":
        print(f"  ✗ {result['message']}")
        state[key]["music"] = {"status": "not_connected"}
        save_render_state(state)
        return

    job_id = result.get("job_id")
    if job_id:
        ok = poll_job(provider, job_id, dest, "music", poll_interval=15, max_wait=900)
        state[key]["music"] = {
            "status": "completed" if ok else "failed",
            "job_id": job_id,
            "path": str(dest) if ok else None,
        }
    else:
        print(f"  ✗ no job_id: {result}")
        state[key]["music"] = {"status": "error", "raw": result}

    save_render_state(state)


def run_sfx(episode: dict, state: dict, dry_run: bool):
    ep = episode["episode_number"]
    key = ep_key(ep)
    provider = get_provider("audio")
    print(f"\n[Step 3: SFX] provider={provider.__class__.__name__} connected={provider.is_connected()}")
    state.setdefault(key, {}).setdefault("sfx", {})

    for i, sfx in enumerate(episode.get("sound_effects", []), start=1):
        label = sfx.get("label", f"sfx_{i}")
        dest = ep_render_dir(ep) / f"sfx_{label}.mp3"
        if dest.exists():
            print(f"  ✓ {label} already exists, skipping")
            state[key]["sfx"][label] = {"status": "completed", "path": str(dest)}
            continue
        prompt = sfx.get("prompt", "")
        print(f"  → {label}: {prompt[:60]}...")
        if dry_run:
            print(f"    [dry-run] would call generate_sfx(prompt)")
            continue
        result = provider.generate_sfx(prompt)
        if result.get("status") in ("not_connected", "not_supported"):
            print(f"  ✗ {result.get('message', result.get('status'))}")
            state[key]["sfx"][label] = {"status": result["status"]}
            continue
        job_id = result.get("job_id")
        if job_id:
            ok = poll_job(provider, job_id, dest, f"sfx {label}")
            state[key]["sfx"][label] = {
                "status": "completed" if ok else "failed",
                "job_id": job_id,
                "path": str(dest) if ok else None,
            }
        else:
            state[key]["sfx"][label] = {"status": "error", "raw": result}

    save_render_state(state)


def run_character_images(episode: dict, state: dict, dry_run: bool):
    ep = episode["episode_number"]
    key = ep_key(ep)
    provider = get_provider("image")
    print(f"\n[Step 4: Character Images] provider={provider.__class__.__name__} connected={provider.is_connected()}")
    state.setdefault(key, {}).setdefault("images", {})

    CHARACTER_IMAGES_DIR.mkdir(exist_ok=True)

    for char in episode.get("character_images", []):
        label = char["label"]
        dest = CHARACTER_IMAGES_DIR / f"{label}.png"
        if dest.exists():
            print(f"  ✓ {label}.png already exists, skipping")
            state[key]["images"][label] = {"status": "completed", "path": str(dest)}
            continue
        prompt = char.get("prompt", "")
        aspect = char.get("aspect_ratio", "3:4")
        print(f"  → {label} ({aspect}): {prompt[:60]}...")
        if dry_run:
            print(f"    [dry-run] would call generate_image(prompt, aspect_ratio='{aspect}')")
            continue
        result = provider.generate_image(prompt, aspect_ratio=aspect)
        if result.get("status") in ("not_connected", "not_supported"):
            print(f"  ✗ {result.get('message', result.get('status'))}")
            state[key]["images"][label] = {"status": result["status"]}
            continue
        job_id = result.get("job_id")
        if job_id:
            ok = poll_job(provider, job_id, dest, f"image {label}", poll_interval=8)
            state[key]["images"][label] = {
                "status": "completed" if ok else "failed",
                "job_id": job_id,
                "path": str(dest) if ok else None,
            }
        else:
            state[key]["images"][label] = {"status": "error", "raw": result}

    save_render_state(state)


def run_scene_videos(episode: dict, state: dict, dry_run: bool):
    ep = episode["episode_number"]
    key = ep_key(ep)
    provider = get_provider("video")
    print(f"\n[Step 5: Scene Videos] provider={provider.__class__.__name__} connected={provider.is_connected()}")
    state.setdefault(key, {}).setdefault("videos", {})

    # Build map of available character images for reference
    char_map = {}
    for char in episode.get("character_images", []):
        img_path = CHARACTER_IMAGES_DIR / f"{char['label']}.png"
        if img_path.exists():
            char_map[char["label"]] = str(img_path)

    # Use first available character image as reference for all scenes
    ref_image = list(char_map.values())[0] if char_map else None
    if ref_image:
        print(f"  Using reference image: {Path(ref_image).name}")
    else:
        print(f"  ⚠ No character images found — videos will generate without reference")

    for scene in episode["scenes"]:
        sn = scene["scene_number"]
        dest = video_path(ep, sn)
        if dest.exists():
            print(f"  ✓ scene {sn} video already exists, skipping")
            state[key]["videos"][str(sn)] = {"status": "completed", "path": str(dest)}
            continue

        prompt = scene.get("video_prompt", scene.get("description", ""))
        duration = scene.get("duration_sec", 8)
        print(f"  → scene {sn}: {prompt[:70]}...")
        if dry_run:
            print(f"    [dry-run] would call generate_video(prompt, ref={Path(ref_image).name if ref_image else None}, duration={duration})")
            continue

        result = provider.generate_video(
            prompt=prompt,
            reference_image_path=ref_image,
            aspect_ratio="16:9",
            duration_sec=duration,
        )
        if result.get("status") in ("not_connected", "not_supported"):
            print(f"  ✗ {result.get('message', result.get('status'))}")
            state[key]["videos"][str(sn)] = {"status": result["status"]}
            continue

        job_id = result.get("job_id")
        if job_id:
            ok = poll_job(provider, job_id, dest, f"video s{sn}", poll_interval=15, max_wait=600)
            state[key]["videos"][str(sn)] = {
                "status": "completed" if ok else "failed",
                "job_id": job_id,
                "path": str(dest) if ok else None,
            }
        else:
            state[key]["videos"][str(sn)] = {"status": "error", "raw": result}

    save_render_state(state)


def run_assembly(episode: dict, state: dict, dry_run: bool):
    """
    Assemble all 6 scene videos + narration + music + SFX into a final MP4.
    Uses FFmpeg. Each scene is:
      - Scene video (background)
      - Narration audio mixed in
      - SFX mixed in at lower volume
    Music runs under the entire episode at -18dB.
    """
    ep = episode["episode_number"]
    key = ep_key(ep)
    print(f"\n[Step 6: Assembly] FFmpeg")
    state.setdefault(key, {}).setdefault("assembly", {})

    # Check FFmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("  ✗ FFmpeg not found. Install FFmpeg to enable assembly.")
        print("    Windows: https://www.gyan.dev/ffmpeg/builds/")
        print("    Then add ffmpeg/bin to your PATH.")
        state[key]["assembly"] = {"status": "ffmpeg_not_found"}
        save_render_state(state)
        return

    # Collect scene video paths
    scene_videos = []
    for scene in episode["scenes"]:
        sn = scene["scene_number"]
        p = video_path(ep, sn)
        if not p.exists():
            print(f"  ✗ Missing scene {sn} video: {p}")
            print(f"    Run --steps video first.")
            state[key]["assembly"] = {"status": "missing_videos"}
            save_render_state(state)
            return
        scene_videos.append(str(p))

    final = final_mp4_path(ep)
    music = music_path(ep)
    has_music = music.exists()

    print(f"  Assembling {len(scene_videos)} scenes → {final.name}")
    if dry_run:
        print(f"    [dry-run] would concatenate {scene_videos}")
        print(f"    [dry-run] music overlay: {has_music}")
        return

    render_d = ep_render_dir(ep)

    # Step A: Concatenate scene videos
    concat_list = render_d / "concat.txt"
    with open(concat_list, "w") as f:
        for v in scene_videos:
            f.write(f"file '{v}'\n")

    concat_output = render_d / "scenes_concat.mp4"
    cmd_concat = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(concat_output),
    ]
    print("  → Concatenating scene videos ...")
    subprocess.run(cmd_concat, check=True, capture_output=True)

    # Step B: Mix narration onto each scene (or build a narration track)
    narration_files = []
    for scene in episode["scenes"]:
        sn = scene["scene_number"]
        p = narration_path(ep, sn)
        if p.exists():
            narration_files.append(str(p))

    if narration_files:
        # Concatenate narration clips into one track
        nar_concat_list = render_d / "narration_concat.txt"
        with open(nar_concat_list, "w") as f:
            for n in narration_files:
                f.write(f"file '{n}'\n")
        nar_track = render_d / "narration_full.mp3"
        cmd_nar = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(nar_concat_list),
            "-c", "copy",
            str(nar_track),
        ]
        subprocess.run(cmd_nar, check=True, capture_output=True)
        print("  → Narration track assembled")
    else:
        nar_track = None
        print("  ⚠ No narration audio found — assembling video only")

    # Step C: Final mix — video + narration + music
    if nar_track and has_music:
        cmd_final = [
            "ffmpeg", "-y",
            "-i", str(concat_output),
            "-i", str(nar_track),
            "-i", str(music),
            "-filter_complex",
            "[1:a]volume=1.0[nar];[2:a]volume=0.15[mus];[nar][mus]amix=inputs=2:duration=first[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(final),
        ]
    elif nar_track:
        cmd_final = [
            "ffmpeg", "-y",
            "-i", str(concat_output),
            "-i", str(nar_track),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-map", "0:v", "-map", "1:a",
            "-shortest",
            str(final),
        ]
    else:
        cmd_final = [
            "ffmpeg", "-y",
            "-i", str(concat_output),
            "-c", "copy",
            str(final),
        ]

    print(f"  → Final mix → {final.name} ...")
    subprocess.run(cmd_final, check=True, capture_output=True)

    if final.exists():
        size_mb = final.stat().st_size / 1_000_000
        print(f"  ✓ DONE: {final} ({size_mb:.1f} MB)")
        state[key]["assembly"] = {
            "status": "completed",
            "path": str(final),
            "size_mb": round(size_mb, 1),
        }
    else:
        print(f"  ✗ Assembly failed — output file not found")
        state[key]["assembly"] = {"status": "failed"}

    save_render_state(state)


# ── Status display ─────────────────────────────────────────────────────────────

def show_status():
    state = load_render_state()
    if not state:
        print("No render state found. Run render.py --episode <N> to start.")
        return

    ICONS = {"completed": "✓", "failed": "✗", "not_connected": "○", "pending": "·", "error": "!"}

    for ep_k in sorted(state.keys()):
        ep_data = state[ep_k]
        print(f"\n{ep_k.upper()}")
        for step in ALL_STEPS[:-1]:  # exclude assembly from item counts
            items = ep_data.get(step, {})
            if not items:
                print(f"  {step:<12} — not started")
                continue
            done = sum(1 for v in items.values() if isinstance(v, dict) and v.get("status") == "completed")
            total = len(items)
            print(f"  {step:<12} {done}/{total} completed")

        asm = ep_data.get("assembly", {})
        asm_status = asm.get("status", "not started")
        final_icon = ICONS.get(asm_status, "·")
        print(f"  {'assembly':<12} {final_icon} {asm_status}")
        if asm.get("path"):
            print(f"               → {asm['path']}")


# ── Main ───────────────────────────────────────────────────────────────────────

def parse_steps(steps_arg: str) -> list[str]:
    """Parse --steps '1,2,3' or --step 'narration' into a list of step names."""
    if not steps_arg:
        return ALL_STEPS
    parts = [s.strip() for s in steps_arg.replace(",", " ").split()]
    resolved = []
    for p in parts:
        if p in STEP_ALIASES:
            resolved.append(STEP_ALIASES[p])
        elif p in ALL_STEPS:
            resolved.append(p)
        else:
            print(f"Unknown step '{p}'. Valid: {', '.join(ALL_STEPS)}")
            sys.exit(1)
    return resolved


def main():
    parser = argparse.ArgumentParser(description="Empire Decoded render orchestrator")
    parser.add_argument("--episode", "-e", type=int, help="Episode number to render")
    parser.add_argument("--steps", type=str, default="", help="Comma-separated steps to run (default: all)")
    parser.add_argument("--step", type=str, default="", help="Single step to run")
    parser.add_argument("--dry-run", action="store_true", help="Show what would run without submitting jobs")
    parser.add_argument("--status", action="store_true", help="Show render status for all episodes")
    parser.add_argument("--assemble", type=int, metavar="EP", help="Run assembly only for episode N")
    args = parser.parse_args()

    # Load .env
    env_path = ROOT / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v

    if args.status:
        show_status()
        return

    ep_num = args.assemble or args.episode
    if not ep_num:
        parser.print_help()
        sys.exit(1)

    if args.assemble:
        episode = load_episode(ep_num)
        state = load_render_state()
        run_assembly(episode, state, dry_run=args.dry_run)
        return

    episode = load_episode(ep_num)
    state = load_render_state()

    steps_str = args.steps or args.step or ""
    steps = parse_steps(steps_str) if steps_str else ALL_STEPS

    print(f"\n=== Empire Decoded — Render Episode {ep_num:03d} ===")
    print(f"Title : {episode.get('title', 'Unknown')}")
    print(f"Steps : {', '.join(steps)}")
    print(f"Dry run: {args.dry_run}")
    print()

    STEP_FNS = {
        STEP_NARRATION: run_narration,
        STEP_MUSIC:     run_music,
        STEP_SFX:       run_sfx,
        STEP_IMAGES:    run_character_images,
        STEP_VIDEO:     run_scene_videos,
        STEP_ASSEMBLY:  run_assembly,
    }

    for step in steps:
        STEP_FNS[step](episode, state, dry_run=args.dry_run)

    print("\n=== Render pass complete ===")
    show_status()


if __name__ == "__main__":
    main()
