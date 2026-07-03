#!/usr/bin/env python3
"""
pipeline_run.py — Zero-Prompt Autonomous Pipeline Orchestrator

Runs the full Viral Engine pipeline from topic discovery to CrossPost with
zero manual input. One command, one complete video.

Pipeline stages:
  1. Research Agent        → episode JSON (topic discovery + script)
  2. Image Generation      → images/{ep}/ (Pollinations free)
  3. Voice + FFmpeg        → output/{ep}_final.mp4
  4. Caption Finalize      → output/{ep}_final_captioned.mp4
  5. Thumbnail Generation  → output/{ep}_thumbnail.png  (via Gemini Imagen or placeholder)
  6. Metadata Generation   → output/{ep}_metadata.json
  7. CrossPost / Publish   → social_machine (YouTube + others)

Usage:
    python pipeline_run.py --channel gg
    python pipeline_run.py --channel ml
    python pipeline_run.py --channel lo
    python pipeline_run.py --channel gg --topic "Battle of Salamis"
    python pipeline_run.py --channel gg --skip-publish
    python pipeline_run.py --channel gg --start-at images   # resume from stage
    python pipeline_run.py --channel gg --episode GG_EP027  # re-run specific ep

Stages (for --start-at):
    research | images | voice | captions | thumbnail | metadata | publish
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent
PROMPTS_DIR = BASE_DIR / "prompts"
IMAGES_DIR  = BASE_DIR / "images"
AUDIO_DIR   = BASE_DIR / "audio"
OUTPUT_DIR  = BASE_DIR / "output"
LOG_FILE    = BASE_DIR / "pipeline_run.log"

STAGES = ["research", "images", "voice", "captions", "thumbnail", "metadata", "publish"]

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("pipeline_run")


# ── .env loader ───────────────────────────────────────────────────────────────
def _load_dotenv():
    env = BASE_DIR / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v

_load_dotenv()


# ── TTS Guard ─────────────────────────────────────────────────────────────────
def ensure_tts_configured():
    """
    Check TTS configuration and auto-fix the placeholder key issue.
    If ElevenLabs key is the placeholder, switch to free edge-tts automatically.
    """
    eleven_key = os.environ.get("ELEVENLABS_API_KEY", "")
    tts_backend = os.environ.get("TTS_BACKEND", "elevenlabs").lower()

    placeholder_values = {
        "your_elevenlabs_api_key_here", "your_key_here", "none", "", "placeholder"
    }

    if tts_backend == "elevenlabs" and eleven_key.lower() in placeholder_values:
        log.warning(
            "ELEVENLABS_API_KEY is not configured. "
            "Auto-switching to free edge-tts (TTS_BACKEND=local)."
        )
        os.environ["TTS_BACKEND"] = "local"
        os.environ["LOCAL_TTS_BACKEND"] = "edge-tts"
        os.environ["EDGE_TTS_VOICE"] = os.environ.get("EDGE_TTS_VOICE", "en-US-GuyNeural")

        # Also patch the .env file so future runs don't need to do this
        env_path = BASE_DIR / ".env"
        if env_path.exists():
            content = env_path.read_text(encoding="utf-8")
            if "TTS_BACKEND=local" not in content:
                env_path.write_text(
                    content.rstrip() + "\n\n# Auto-set by pipeline_run.py\nTTS_BACKEND=local\nLOCAL_TTS_BACKEND=edge-tts\nEDGE_TTS_VOICE=en-US-GuyNeural\n",
                    encoding="utf-8",
                )
                log.info("Patched .env with TTS_BACKEND=local")

    current = os.environ.get("TTS_BACKEND", "elevenlabs")
    log.info(f"TTS backend: {current}")


# ── Preflight Checks ──────────────────────────────────────────────────────────
def preflight():
    """Abort early if critical dependencies are missing."""
    errors = []

    if not shutil.which("ffmpeg"):
        errors.append("ffmpeg not found in PATH")
    if not shutil.which("ffprobe"):
        errors.append("ffprobe not found in PATH")

    backend = os.environ.get("TTS_BACKEND", "elevenlabs").lower()
    if backend == "local":
        local_backend = os.environ.get("LOCAL_TTS_BACKEND", "edge-tts").lower()
        if local_backend == "edge-tts" and not shutil.which("edge-tts"):
            errors.append(
                "edge-tts not found. Install with: pip install edge-tts"
            )

    if not os.environ.get("GEMINI_API_KEY"):
        errors.append("GEMINI_API_KEY not set — required for research agent")

    if errors:
        for e in errors:
            log.error(f"PREFLIGHT FAIL: {e}")
        sys.exit(1)

    log.info("Preflight: all checks passed")


# ── Stage Runner ──────────────────────────────────────────────────────────────
def run_stage(name: str, cmd: list[str], cwd: Path = BASE_DIR) -> bool:
    """Run a pipeline stage subprocess. Returns True on success."""
    log.info(f"\n{'='*60}")
    log.info(f"STAGE: {name.upper()}")
    log.info(f"CMD:   {' '.join(str(c) for c in cmd)}")
    log.info(f"{'='*60}")
    start = time.time()

    result = subprocess.run(cmd, cwd=str(cwd))
    elapsed = time.time() - start

    if result.returncode == 0:
        log.info(f"✓ {name} completed in {elapsed:.1f}s")
        return True
    else:
        log.error(f"✗ {name} FAILED (exit {result.returncode}) after {elapsed:.1f}s")
        return False


# ── Thumbnail Generation ──────────────────────────────────────────────────────
def generate_thumbnail(episode_id: str, script: dict) -> Path | None:
    """
    Generate a thumbnail using Gemini Imagen or Pollinations.
    Falls back to a solid-color placeholder if neither works.
    """
    output_path = OUTPUT_DIR / f"{episode_id}_thumbnail.png"
    if output_path.exists():
        log.info(f"Thumbnail exists: {output_path.name}")
        return output_path

    # Try Pollinations for thumbnail
    import urllib.request, urllib.parse
    title = script.get("title", episode_id)
    ch = script.get("channel", "GG")

    if ch == "GG":
        thumb_prompt = (
            f"YouTube thumbnail for historical documentary: {title}. "
            "Epic cinematic battle scene, dramatic lighting, gold and dark red color scheme, "
            "high contrast, photorealistic, 1280x720, no text, thumbnail composition"
        )
    elif ch == "ML":
        thumb_prompt = (
            f"YouTube thumbnail for kids robot action cartoon: {title}. "
            "Giant red mech hero vs dark villain mech, dynamic action pose, "
            "bright energy effects, 1280x720, no text, anime style"
        )
    else:
        thumb_prompt = (
            f"YouTube thumbnail for kids cartoon: {title}. "
            "Cute cartoon baby Zeus with lightning bolt, bright colors, "
            "big expressive eyes, 1280x720, no text"
        )

    encoded = urllib.parse.quote(thumb_prompt, safe="")
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1280&height=720&model=flux&nologo=true&seed=9999"

    try:
        log.info("Generating thumbnail via Pollinations...")
        req = urllib.request.Request(url, headers={"User-Agent": "ViralEngine/1.0"})
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = resp.read()
        if len(data) > 5000:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(data)
            log.info(f"Thumbnail saved: {output_path.name} ({len(data)//1024}KB)")
            return output_path
    except Exception as e:
        log.warning(f"Thumbnail generation failed: {e}")

    log.warning("Thumbnail: using placeholder (add Canva/Photoshop for final version)")
    return None


# ── Metadata Generation ───────────────────────────────────────────────────────
def generate_metadata(episode_id: str, script: dict, channel: str) -> Path:
    """Write a complete YouTube metadata JSON from the script."""
    output_path = OUTPUT_DIR / f"{episode_id}_metadata.json"

    channel_configs = {
        "gg": {
            "handle": "@GodsAndGloryAI",
            "tags": ["GodsAndGlory", "HistoryDocumentary", "AncientHistory",
                     "EpicBattles", "HistoryYouTube", "Documentary", "HistoricalBattles",
                     "MilitaryHistory", "WarHistory", "CinematicHistory"],
            "category": "Education",
            "made_for_kids": False,
        },
        "ml": {
            "handle": "@MechLegendsTV",
            "tags": ["MechLegends", "RobotHeroes", "KidsCartoon", "BLAZE",
                     "RobotAction", "KidsYouTube", "MechCartoon", "GiantRobots"],
            "category": "Kids & Family",
            "made_for_kids": True,
        },
        "lo": {
            "handle": "@LittleOlympusTV",
            "tags": ["LittleOlympus", "KidsCartoon", "GreekMythology", "KidsYouTube",
                     "LittleZeus", "KidsMythology", "LearnWithMe", "KidsEducation"],
            "category": "Kids & Family",
            "made_for_kids": True,
        },
    }

    ch_meta = channel_configs.get(channel, channel_configs["gg"])
    title = script.get("youtube_title") or script.get("title", episode_id)
    lesson = script.get("lesson", "")
    hook = script.get("viral_hook", "")

    # Build description
    description = (
        f"{hook}\n\n"
        f"In this episode of {ch_meta['handle']}:\n"
        f"→ {script.get('tagline', '')}\n"
        f"→ {lesson}\n\n"
        f"{'📺 Full series playlist: [link]' if not ch_meta['made_for_kids'] else '📺 Watch more episodes: [link]'}\n"
        f"🔔 SUBSCRIBE for more: {ch_meta['handle']}\n\n"
        f"#{' #'.join(ch_meta['tags'][:5])}"
    )

    metadata = {
        "episode_id": episode_id,
        "channel": channel,
        "handle": ch_meta["handle"],
        "title": title,
        "description": description,
        "tags": ch_meta["tags"],
        "category": ch_meta["category"],
        "made_for_kids": ch_meta["made_for_kids"],
        "language": "en",
        "default_audio_language": "en",
        "thumbnail_file": str(OUTPUT_DIR / f"{episode_id}_thumbnail.png"),
        "video_file": str(OUTPUT_DIR / f"{episode_id}_final.mp4"),
        "captioned_file": str(OUTPUT_DIR / f"{episode_id}_final_captioned.mp4"),
        "upload_status": "ready",
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    log.info(f"Metadata written: {output_path.name}")
    return output_path


# ── Episode Discovery ─────────────────────────────────────────────────────────
def find_episode_json(episode_id: str) -> Path | None:
    """Find the JSON script for a given episode ID."""
    ep_lower = episode_id.lower()
    for match in sorted(PROMPTS_DIR.glob(f"**/*{ep_lower}*.final.json")):
        return match
    return None


# ── Main Pipeline ─────────────────────────────────────────────────────────────
def run_pipeline(
    channel: str,
    topic: str | None = None,
    episode_id: str | None = None,
    start_at: str = "research",
    skip_publish: bool = False,
) -> bool:
    """
    Run the full autonomous pipeline.
    Returns True if pipeline completed successfully.
    """
    log.info("")
    log.info("╔══════════════════════════════════════════════════════╗")
    log.info("║   VIRAL ENGINE — AUTONOMOUS PIPELINE                ║")
    log.info(f"║   Channel: {channel.upper():<44}║")
    log.info(f"║   Start:   {start_at:<44}║")
    log.info("╚══════════════════════════════════════════════════════╝")
    log.info("")

    start_idx = STAGES.index(start_at) if start_at in STAGES else 0
    script_path: Path | None = None
    script: dict = {}

    # ── STAGE 1: Research ────────────────────────────────────────────────────
    if start_idx <= STAGES.index("research"):
        if episode_id:
            # Skip research if a specific episode was requested
            script_path = find_episode_json(episode_id)
            if not script_path:
                log.error(f"Episode JSON not found for: {episode_id}")
                return False
            log.info(f"Using existing script: {script_path}")
        else:
            log.info("\n── STAGE 1: Research Agent")
            from research_agent import run as research_run
            script_path = research_run(channel, forced_topic=topic)
            if not script_path:
                log.error("Research agent returned no script. Aborting.")
                return False

    # Load the script
    if script_path and not script:
        try:
            script = json.loads(script_path.read_text(encoding="utf-8"))
            ep_id = script["episode_id"]
            log.info(f"Episode: {ep_id} — {script.get('title')}")
        except Exception as e:
            log.error(f"Failed to load script: {e}")
            return False
    elif episode_id:
        ep_id = episode_id.upper()
    else:
        log.error("No episode ID resolved")
        return False

    # Normalize episode ID
    ep_id = script.get("episode_id", ep_id)

    # ── STAGE 2: Image Generation ─────────────────────────────────────────────
    if start_idx <= STAGES.index("images"):
        log.info(f"\n── STAGE 2: Image Generation ({ep_id})")
        ep_images_dir = IMAGES_DIR / ep_id
        existing_images = list(ep_images_dir.glob("scene_*.png")) if ep_images_dir.exists() else []
        scene_count = len(script.get("scenes", []))

        if len(existing_images) >= scene_count:
            log.info(f"Images already exist ({len(existing_images)}/{scene_count}), skipping")
        else:
            ok = run_stage(
                "image generation",
                [sys.executable, "generate_images.py",
                 "--episode", ep_id, "--free", "--skip-existing"],
            )
            if not ok:
                log.warning("Image generation had errors — pipeline continues with available images")

    # ── STAGE 3: Voice + FFmpeg Assembly ──────────────────────────────────────
    if start_idx <= STAGES.index("voice"):
        final_mp4 = OUTPUT_DIR / f"{ep_id}_final.mp4"
        if final_mp4.exists() and final_mp4.stat().st_size > 1_000_000:
            log.info(f"\n── STAGE 3: Voice+FFmpeg — {final_mp4.name} exists, skipping")
        else:
            log.info(f"\n── STAGE 3: Voice + FFmpeg Assembly ({ep_id})")
            ok = run_stage(
                "voice + ffmpeg",
                [sys.executable, "voice_video_pipeline.py", "--episode", ep_id],
            )
            if not ok:
                log.error("Voice+FFmpeg stage failed. Aborting.")
                return False

    # ── STAGE 4: Caption Finalize ─────────────────────────────────────────────
    if start_idx <= STAGES.index("captions"):
        captioned = OUTPUT_DIR / f"{ep_id}_final_captioned.mp4"
        if captioned.exists() and captioned.stat().st_size > 1_000_000:
            log.info(f"\n── STAGE 4: Captions — {captioned.name} exists, skipping")
        else:
            log.info(f"\n── STAGE 4: Caption Finalize ({ep_id})")
            ok = run_stage(
                "caption finalize",
                [sys.executable, "caption_finalize_v3.py", "--episode", ep_id],
            )
            if not ok:
                log.warning("Caption stage failed — using uncaptioned final for publish")
                # Use uncaptioned version as fallback
                final_mp4 = OUTPUT_DIR / f"{ep_id}_final.mp4"
                if final_mp4.exists():
                    shutil.copy2(final_mp4, captioned)

    # ── STAGE 5: Thumbnail ────────────────────────────────────────────────────
    if start_idx <= STAGES.index("thumbnail"):
        log.info(f"\n── STAGE 5: Thumbnail Generation ({ep_id})")
        generate_thumbnail(ep_id, script)

    # ── STAGE 6: Metadata ─────────────────────────────────────────────────────
    if start_idx <= STAGES.index("metadata"):
        log.info(f"\n── STAGE 6: Metadata Generation ({ep_id})")
        generate_metadata(ep_id, script, channel)

    # ── STAGE 7: Publish ──────────────────────────────────────────────────────
    if start_idx <= STAGES.index("publish") and not skip_publish:
        log.info(f"\n── STAGE 7: CrossPost / Publish ({ep_id})")
        social_master = BASE_DIR / "social_machine" / "master.py"
        if social_master.exists():
            ok = run_stage(
                "publish",
                [sys.executable, str(social_master),
                 "--channel", channel, "--episode", ep_id],
            )
            if not ok:
                log.warning("Publish stage failed — video is ready but not uploaded")
        else:
            log.warning("social_machine/master.py not found — skipping publish")
    elif skip_publish:
        log.info("\n── STAGE 7: Publish — SKIPPED (--skip-publish)")

    # ── Done ──────────────────────────────────────────────────────────────────
    log.info("")
    log.info("╔══════════════════════════════════════════════════════╗")
    log.info("║   PIPELINE COMPLETE                                  ║")
    log.info(f"║   {ep_id:<52}║")

    captioned_final = OUTPUT_DIR / f"{ep_id}_final_captioned.mp4"
    raw_final       = OUTPUT_DIR / f"{ep_id}_final.mp4"
    best_final = captioned_final if captioned_final.exists() else raw_final
    if best_final.exists():
        size_mb = best_final.stat().st_size / 1024 / 1024
        log.info(f"║   Video: {best_final.name:<47}║")
        log.info(f"║   Size:  {size_mb:.1f} MB{' '*(47 - len(f'{size_mb:.1f} MB'))}║")

    log.info("╚══════════════════════════════════════════════════════╝")
    return True


# ── CLI ────────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(
        description="Viral Engine — Zero-Prompt Autonomous Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pipeline_run.py --channel gg
  python pipeline_run.py --channel ml
  python pipeline_run.py --channel lo
  python pipeline_run.py --channel gg --topic "Battle of Salamis"
  python pipeline_run.py --channel gg --episode GG_EP027
  python pipeline_run.py --channel gg --start-at images
  python pipeline_run.py --channel gg --skip-publish
        """
    )
    ap.add_argument("--channel", "-c", required=True, choices=["gg", "ml", "lo"],
                    help="Channel: gg=Gods & Glory, ml=Mech Legends, lo=Little Olympus")
    ap.add_argument("--topic", "-t", default=None,
                    help="Force a specific topic (skip topic discovery)")
    ap.add_argument("--episode", "-e", default=None,
                    help="Use an existing episode (skip research stage)")
    ap.add_argument("--start-at", default="research",
                    choices=STAGES,
                    help="Resume pipeline from a specific stage")
    ap.add_argument("--skip-publish", action="store_true",
                    help="Stop before publishing (produces ready-to-upload video)")
    args = ap.parse_args()

    # Preflight
    ensure_tts_configured()
    preflight()

    # Run
    success = run_pipeline(
        channel=args.channel,
        topic=args.topic,
        episode_id=args.episode,
        start_at=args.start_at,
        skip_publish=args.skip_publish,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
