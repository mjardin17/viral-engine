"""
scene_classifier.py — Empire OS Higgsfield Credit-Stretching System (BUILD 1)
==============================================================================
Assigns each scene in an episode script a render_tier BEFORE any generation
happens, so Higgsfield credits are spent only on scenes that truly need real
character video. Everything else routes to free/cheap alternatives already
wired into ai_router (flux_kontext, wan22, etc.) and providers/waterfall.py.

ADDITIVE ONLY — does not touch empire_render.py, auto_render.py, or existing
script files. Run this BEFORE queuing an LO/IL episode for render.

Render tiers (highest cost → lowest):
    higgsfield_video  — full Higgsfield video generation. Peak moments only.
    higgsfield_image  — Higgsfield still, animated via Ken Burns. Mid cost.
    composited        — FLUX Kontext character-onto-cached-background. Cheap.
    free              — Free provider (Ken Burns on cached/free image). $0.

Classification is deterministic and explainable — never AI-guessed:
    1. Scene explicitly tagged "is_peak_moment": true            -> higgsfield_video
    2. Scene is the cold open (first) or in the climax/resolution
       (last 2 scenes), capped at MAX_HIGGSFIELD_VIDEO_SCENES    -> higgsfield_video
    3. Scene tagged "action_level": "high" AND image budget left -> higgsfield_image
    4. Scene reuses a known cached character + cached background -> composited
    5. Everything else                                           -> free

── OPTIONAL scene JSON fields (documented here; NOT required — missing
   fields default sensibly so existing LO/IL scripts keep working untouched) ──
    "is_peak_moment": bool    default False
    "action_level":   str     default "medium"  ("low"|"medium"|"high")
    "character":      str|None default None     — cache key, e.g. "little_zeus"
    "location":       str|None default None     — cache key, e.g. "olympus_throne_room"
    "render_tier":    str|None default None     — filled in by this module,
                                                    never read as input
Example (all fields optional, additive to existing scene schema):
    {
      "scene_id": "scene_03",
      "narration": "...",
      "is_peak_moment": false,
      "action_level": "medium",
      "character": "little_zeus",
      "location": "olympus_throne_room",
      "render_tier": null
    }

CLI:
    python scene_classifier.py prompts/little_olympus/LO_EP002.json
    python scene_classifier.py <script.json> --max-higgsfield-video 4 --max-higgsfield-image 8
Writes {episode_id}_render_plan.json next to the script.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR: Path = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from asset_cache import AssetCache  # noqa: E402

TAG = "[scene_classifier]"

RENDER_TIERS: dict[str, str] = {
    "higgsfield_video": "Full Higgsfield video generation — reserved for peak moments only",
    "higgsfield_image": "Higgsfield still image only, animated via Ken Burns — mid cost",
    "composited": "FLUX Kontext character compositing onto cached background — cheap (~$0.02)",
    "free": "Free provider (Ken Burns on cached/free image) — zero cost",
}

# Defaults (overridable via CLI / function args)
DEFAULT_MAX_HIGGSFIELD_VIDEO_SCENES = 4
DEFAULT_MAX_HIGGSFIELD_IMAGE_SCENES = 8

# Cost estimates — Higgsfield does not publish an exact credit-to-scene
# ratio, so these are clearly-marked guesses to size budgets, not invoices.
HIGGSFIELD_VIDEO_CREDITS_PER_SCENE = 10.0   # [ESTIMATE] range 8-12 credits/scene
HIGGSFIELD_IMAGE_CREDITS_PER_SCENE = 2.5    # [ESTIMATE] range 2-3 credits/scene
COMPOSITED_FAL_COST_USD = 0.02              # matches flux_kontext_adapter.default_cost_usd
FREE_COST_USD = 0.0


def _slug(text: str) -> str:
    return "_".join(str(text).strip().lower().split())


def _scene_id(scene: dict, idx: int) -> str:
    if scene.get("scene_id"):
        return str(scene["scene_id"])
    if scene.get("scene_number") is not None:
        return f"scene_{int(scene['scene_number']):02d}"
    return f"scene_{idx + 1:02d}"


def classify_episode(script_path: str, max_higgsfield_video: int = DEFAULT_MAX_HIGGSFIELD_VIDEO_SCENES,
                     max_higgsfield_image: int = DEFAULT_MAX_HIGGSFIELD_IMAGE_SCENES) -> dict:
    """Classify every scene in an episode script into a render_tier.

    Returns {"episode_id":, "channel":, "scenes": [{"scene_id","render_tier","reason",
    "is_peak_moment","action_level","character","location"}], "summary": {...}}
    Never raises — a missing/broken script returns an empty classification with
    an "error" key in summary so callers can handle it gracefully.
    """
    path = Path(script_path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"episode_id": path.stem, "channel": "", "scenes": [],
                "summary": {"error": f"could not read/parse {path}: {e}"}}

    episode_id = data.get("episode_id") or path.stem
    channel_raw = data.get("channel", "")
    channel_slug = _slug(channel_raw) if channel_raw else ""
    scenes: list[dict] = data.get("scenes", [])
    n = len(scenes)

    cache = AssetCache()
    out_scenes: list[dict] = []

    tier_counts = {t: 0 for t in RENDER_TIERS}
    higgsfield_video_used = 0
    higgsfield_image_used = 0
    missing_characters: set[str] = set()
    missing_backgrounds: set[str] = set()

    for idx, scene in enumerate(scenes):
        sid = _scene_id(scene, idx)
        is_peak_moment = bool(scene.get("is_peak_moment", False))
        action_level = str(scene.get("action_level", "medium")).lower()
        character = scene.get("character")
        location = scene.get("location")

        is_position_peak = (idx == 0) or (n >= 2 and idx >= n - 2)

        tier: str
        reason: str

        if is_peak_moment:
            tier = "higgsfield_video"
            reason = "explicit is_peak_moment=true"
            higgsfield_video_used += 1
        elif is_position_peak and higgsfield_video_used < max_higgsfield_video:
            tier = "higgsfield_video"
            reason = "cold open (first scene)" if idx == 0 else \
                     "climax/resolution (last 2 scenes)"
            higgsfield_video_used += 1
        elif action_level == "high" and higgsfield_image_used < max_higgsfield_image:
            tier = "higgsfield_image"
            reason = f"action_level=high, within image budget ({higgsfield_image_used + 1}/{max_higgsfield_image})"
            higgsfield_image_used += 1
        else:
            char_cached = bool(character) and channel_slug and \
                cache.get_character(channel_slug, character) is not None
            bg_cached = bool(location) and channel_slug and \
                cache.get_background(channel_slug, location) is not None
            if character and location and char_cached and bg_cached:
                tier = "composited"
                reason = f"cached character '{character}' + cached background '{location}'"
            else:
                tier = "free"
                if character and not char_cached:
                    missing_characters.add(character)
                    reason = f"character '{character}' not yet cached — needs one-time Higgsfield gen"
                elif location and not bg_cached:
                    missing_backgrounds.add(location)
                    reason = f"background '{location}' not yet cached — needs one-time Higgsfield gen"
                else:
                    reason = "no peak/action/cache match — default free tier"

        tier_counts[tier] += 1
        out_scenes.append({
            "scene_id": sid,
            "render_tier": tier,
            "reason": reason,
            "is_peak_moment": is_peak_moment,
            "action_level": action_level,
            "character": character,
            "location": location,
        })

    summary = {
        "total_scenes": n,
        "tier_counts": tier_counts,
        "max_higgsfield_video_scenes": max_higgsfield_video,
        "max_higgsfield_image_scenes": max_higgsfield_image,
        "missing_character_cache": sorted(missing_characters),
        "missing_background_cache": sorted(missing_backgrounds),
        "classified_at": datetime.now().isoformat(),
    }

    return {
        "episode_id": episode_id,
        "channel": channel_raw,
        "channel_slug": channel_slug,
        "script_path": str(path),
        "scenes": out_scenes,
        "summary": summary,
    }


def estimate_episode_cost(classification: dict) -> dict:
    """Roll up per-scene tiers into an episode cost estimate.

    All Higgsfield credit figures are [ESTIMATE] — Higgsfield does not
    publish an exact credit-to-scene ratio, so these size budgets, they
    are not invoices.
    """
    tier_counts = (classification.get("summary") or {}).get("tier_counts", {})
    hv = tier_counts.get("higgsfield_video", 0)
    hi = tier_counts.get("higgsfield_image", 0)
    comp = tier_counts.get("composited", 0)
    free = tier_counts.get("free", 0)
    total = hv + hi + comp + free

    higgsfield_credits_est = (hv * HIGGSFIELD_VIDEO_CREDITS_PER_SCENE) + \
                              (hi * HIGGSFIELD_IMAGE_CREDITS_PER_SCENE)
    fal_cost_usd = comp * COMPOSITED_FAL_COST_USD

    return {
        "higgsfield_credits_est": round(higgsfield_credits_est, 1),
        "fal_cost_usd": round(fal_cost_usd, 2),
        "free_scenes": free,
        "total_scenes": total,
        "breakdown": {
            "higgsfield_video_scenes": hv,
            "higgsfield_image_scenes": hi,
            "composited_scenes": comp,
            "free_scenes": free,
        },
    }


def _print_report(classification: dict, cost: dict) -> None:
    ep = classification.get("episode_id", "?")
    ch = classification.get("channel", "?")
    print(f"\n{TAG} {ep} ({ch}) — {classification['summary'].get('total_scenes', 0)} scenes\n")
    print(f"{'scene':<12} {'tier':<18} reason")
    print("-" * 90)
    for s in classification.get("scenes", []):
        print(f"{s['scene_id']:<12} {s['render_tier']:<18} {s['reason'][:70]}")
    print("-" * 90)
    tc = classification["summary"]["tier_counts"]
    print(f"\nTier totals: higgsfield_video={tc.get('higgsfield_video',0)}  "
          f"higgsfield_image={tc.get('higgsfield_image',0)}  "
          f"composited={tc.get('composited',0)}  free={tc.get('free',0)}")
    print(f"\nCost estimate [ESTIMATE — Higgsfield credit ratios are guesses]:")
    print(f"  Higgsfield credits: ~{cost['higgsfield_credits_est']}")
    print(f"  FAL (composited):   ${cost['fal_cost_usd']}")
    print(f"  Free scenes:        {cost['free_scenes']}/{cost['total_scenes']}")
    missing_c = classification["summary"].get("missing_character_cache") or []
    missing_b = classification["summary"].get("missing_background_cache") or []
    if missing_c:
        print(f"\n⚠ missing_character_cache: {missing_c} — one-time Higgsfield gen needed")
    if missing_b:
        print(f"⚠ missing_background_cache: {missing_b} — one-time Higgsfield gen needed")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify episode scenes into Higgsfield-stretching render tiers")
    parser.add_argument("script_path", help="Path to episode scene JSON")
    parser.add_argument("--max-higgsfield-video", type=int, default=DEFAULT_MAX_HIGGSFIELD_VIDEO_SCENES)
    parser.add_argument("--max-higgsfield-image", type=int, default=DEFAULT_MAX_HIGGSFIELD_IMAGE_SCENES)
    args = parser.parse_args()

    classification = classify_episode(args.script_path, args.max_higgsfield_video,
                                      args.max_higgsfield_image)
    if classification["summary"].get("error"):
        print(f"{TAG} ERROR: {classification['summary']['error']}", file=sys.stderr)
        sys.exit(1)

    cost = estimate_episode_cost(classification)
    _print_report(classification, cost)

    out_path = Path(args.script_path).parent / f"{classification['episode_id']}_render_plan.json"
    plan = {**classification, "cost_estimate": cost, "approved": False}
    out_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    print(f"{TAG} wrote {out_path}")


if __name__ == "__main__":
    main()
