#!/usr/bin/env python3
"""
ollama_bridge.py — Local Ollama Integration for Viral Engine
=============================================================
Scene-level prompt refinement and narration optimization using local Ollama.
Empire OS calls this to improve visual prompts and narration BEFORE render.

Can be used two ways:
  1. Via empire_api.py at POST /ollama/refine
  2. Direct CLI: python ollama_bridge.py --episode GG_EP012 --output refined_ep012.json

Ollama runs locally (default: http://localhost:11434).
Model override: set OLLAMA_MODEL env var (default: llama3).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_DIR      = Path(__file__).resolve().parent
PROMPTS_DIR   = BASE_DIR / "prompts"
OLLAMA_URL    = os.environ.get("OLLAMA_URL",   "http://localhost:11434")
OLLAMA_MODEL  = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b")  # installed model as of 2026-07-04


# ── Core Ollama call ───────────────────────────────────────────────────────

def generate(prompt: str, system: str = "", timeout: int = 120) -> str:
    """Single Ollama generate call. Returns text or raises."""
    payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
    if system:
        payload["system"] = system
    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8")).get("response", "").strip()


def is_available() -> bool:
    try:
        urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=3)
        return True
    except Exception:
        return False


# ── Scene-level refiners ───────────────────────────────────────────────────

SYSTEM_CINEMATOGRAPHER = (
    "You are a senior cinematographer and visual effects director specializing in "
    "cinematic historical documentary imagery. You write precise, evocative AI image "
    "prompts that generate stunning, accurate historical visuals. You understand "
    "lighting, composition, color theory, and period-accurate detail."
)

SYSTEM_NARRATOR = (
    "You are a documentary narrator and script editor for a premium historical "
    "documentary channel called Gods and Glory. Your narration is authoritative, "
    "dramatic, and precise — think Ken Burns meets Ridley Scott. "
    "You tighten scripts without losing historical accuracy or emotional impact."
)


def refine_visual_prompt(visual_prompt: str, scene_title: str,
                          ep_title: str, scene_type: str) -> str:
    """Refine a visual_prompt for maximum Pollinations/Flux quality."""
    p = (
        f"Episode: '{ep_title}'. Scene: '{scene_title}' ({scene_type}).\n\n"
        f"Refine this AI image generation prompt for cinematic historical documentary quality. "
        f"Keep the historical accuracy. Maximize visual drama and composition. "
        f"Add specific lighting direction, camera angle, and color palette hints. "
        f"Output ONLY the refined prompt (under 220 characters), nothing else.\n\n"
        f"Original: {visual_prompt}"
    )
    return generate(p, system=SYSTEM_CINEMATOGRAPHER)


def refine_narration(narration: str, scene_title: str,
                     ep_title: str, target_words: int = 95) -> str:
    """Tighten narration while preserving all facts and impact."""
    p = (
        f"Episode: '{ep_title}'. Scene: '{scene_title}'.\n\n"
        f"Tighten this documentary narration to approximately {target_words} words. "
        f"Preserve all factual content. Increase dramatic tension and forward momentum. "
        f"Remove hedging phrases. Start strong. End with impact. "
        f"Output ONLY the improved narration, nothing else.\n\n"
        f"Original ({len(narration.split())} words): {narration}"
    )
    return generate(p, system=SYSTEM_NARRATOR)


def generate_scene_hook(ep_title: str, scene_title: str, narration: str) -> str:
    """Generate a one-line viral hook for a scene (used in thumbnails/shorts)."""
    p = (
        f"Documentary: '{ep_title}'. Scene: '{scene_title}'.\n"
        f"Narration excerpt: {narration[:300]}\n\n"
        f"Write ONE viral hook sentence (under 15 words) for this moment in history. "
        f"Maximum shock/curiosity. No quotes. Output ONLY the hook."
    )
    return generate(p, system=SYSTEM_NARRATOR)


# ── Episode-level processor ────────────────────────────────────────────────

def refine_episode(episode_json_path: Path, output_path: Path,
                   refine_visuals: bool = True,
                   refine_narration_flag: bool = True,
                   verbose: bool = True) -> dict:
    """
    Load an episode JSON, refine all scenes via Ollama, save to output_path.
    Returns the refined episode dict.
    """
    if not is_available():
        raise RuntimeError(f"Ollama not reachable at {OLLAMA_URL} — is it running?")

    episode = json.loads(episode_json_path.read_text(encoding="utf-8"))
    ep_title = episode.get("title", episode_json_path.stem)
    scenes   = episode.get("scenes", [])
    total    = len(scenes)

    print(f"\nRefinement pass: {ep_title} ({total} scenes)")
    print(f"Model: {OLLAMA_MODEL} @ {OLLAMA_URL}")
    print(f"Refine visuals: {refine_visuals}  |  Refine narration: {refine_narration_flag}\n")

    for i, scene in enumerate(scenes, 1):
        sn   = scene.get("scene_number", i)
        st   = scene.get("title", f"Scene {sn}")
        stype = scene.get("type", "")
        if verbose:
            print(f"  [{i:02d}/{total:02d}] {st}...", end=" ", flush=True)
        t0 = time.time()

        if refine_visuals and scene.get("visual_prompt"):
            try:
                scene["visual_prompt"] = refine_visual_prompt(
                    scene["visual_prompt"], st, ep_title, stype
                )
            except Exception as e:
                if verbose:
                    print(f"[VP ERROR: {e}]", end=" ")

        if refine_narration_flag and scene.get("narration"):
            try:
                scene["narration"] = refine_narration(
                    scene["narration"], st, ep_title
                )
            except Exception as e:
                if verbose:
                    print(f"[NR ERROR: {e}]", end=" ")

        if verbose:
            print(f"✓ ({time.time()-t0:.1f}s)")

    episode["_ollama_refined"] = True
    episode["_refined_at"]     = time.time()
    episode["_ollama_model"]   = OLLAMA_MODEL

    output_path.write_text(json.dumps(episode, indent=2), encoding="utf-8")
    print(f"\nSaved: {output_path}")
    return episode


# ── CLI ────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="Refine Viral Engine episode via Ollama")
    ap.add_argument("--episode",   required=True, help="Episode ID e.g. GG_EP012")
    ap.add_argument("--output",    default=None,  help="Output JSON path (default: overwrite source with _refined suffix)")
    ap.add_argument("--no-visuals",  action="store_true", help="Skip visual prompt refinement")
    ap.add_argument("--no-narration", action="store_true", help="Skip narration refinement")
    ap.add_argument("--model",     default=None,  help="Ollama model override")
    args = ap.parse_args()

    global OLLAMA_MODEL
    if args.model:
        OLLAMA_MODEL = args.model

    ep_id = args.episode.upper()
    # Find the script
    source = None
    for p in PROMPTS_DIR.rglob(f"*{ep_id.lower()}*.json"):
        source = p
        break
    if not source:
        print(f"ERROR: No script found for {ep_id} in {PROMPTS_DIR}")
        sys.exit(1)

    out = Path(args.output) if args.output else source.parent / (source.stem + "_refined.json")
    refine_episode(
        source, out,
        refine_visuals=not args.no_visuals,
        refine_narration_flag=not args.no_narration,
    )


if __name__ == "__main__":
    main()
