"""
higgsfield_prep.py — Higgsfield shot-list generator for Empire OS

Reads an episode JSON (LO/IL/any channel) and writes a Markdown shot list so
Josh knows exactly which clips to generate in Higgsfield BEFORE spending
credits — model choice, minimum clip duration, prompt, and the exact filename
empire_render.py expects.

Usage:
    python higgsfield_prep.py --episode LO_EP001
    python higgsfield_prep.py --episode IL_EP001 --script prompts/iron_legends/il_ep001.json

Output:
    higgsfield_shotlists/LO_EP001_shotlist.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Console safety on Windows cp1252
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:
        pass

BASE_DIR: Path = Path(__file__).resolve().parent
SHOTLIST_DIR: Path = BASE_DIR / "higgsfield_shotlists"

CHANNEL_PROMPT_DIR: dict[str, str] = {
    "GG": "gods_glory",
    "LO": "little_olympus",
    "IL": "iron_legends",
    "ED": "empire_decoded",
}

# Narration pacing: Kokoro at LO/IL speeds averages ~2.4 words/sec
WORDS_PER_SECOND: float = 2.4
# Higgsfield clips shorter than this aren't worth the credits
MIN_CLIP_SEC: int = 8
# Freeze-frame padding looks fine up to roughly this clip:narration ratio;
# recommend longer clips for very long narrations
MAX_RECOMMENDED_CLIP_SEC: int = 15

ACTION_WORDS = ("run", "fight", "fly", "crash", "chase", "battle", "explosion",
                "storm", "throw", "smash", "race", "attack", "search", "jump")


def find_episode_script(episode_id: str) -> Path | None:
    """Locate the episode JSON by scanning all prompts/ channel subdirectories."""
    ep_lower = episode_id.lower()
    channel = episode_id.split("_")[0].upper()
    dirs = []
    if channel in CHANNEL_PROMPT_DIR:
        dirs.append(BASE_DIR / "prompts" / CHANNEL_PROMPT_DIR[channel])
    dirs.append(BASE_DIR / "prompts")
    for d in dirs:
        if not d.exists():
            continue
        candidates = sorted(
            (p for p in d.rglob("*.json") if ep_lower in p.name.lower()),
            key=lambda p: (("final" not in p.name.lower()), len(p.name)),
        )
        if candidates:
            return candidates[0]
    return None


def estimate_narration_seconds(narration: str) -> float:
    """Estimate spoken duration of narration text from word count."""
    words = len(narration.split())
    return round(words / WORDS_PER_SECOND, 1)


def pick_model(scene: dict, character_names: list[str]) -> tuple[str, str]:
    """
    Choose the Higgsfield model for a scene:
      - Hailuo   → scene contains spoken dialogue (quoted speech in narration)
      - Soul Cast → a named recurring character appears (consistency needed)
      - Wan 2.7  → pure action/environment shots
    Returns (model_name, reason).
    """
    narration = scene.get("narration", "")
    visual = scene.get("visual_prompt", "")
    text = f"{narration} {visual}"

    has_dialogue = narration.count("'") >= 2 or narration.count('"') >= 2 or ": '" in narration
    present = [c for c in character_names if c.lower() in text.lower()]

    if has_dialogue and present:
        return "Hailuo", f"dialogue scene with {', '.join(present[:2])}"
    if present:
        return "Soul Cast", f"character consistency: {', '.join(present)}"
    if any(w in text.lower() for w in ACTION_WORDS):
        return "Wan 2.7", "action/environment shot"
    return "Wan 2.7", "environment/establishing shot"


def characters_in_scene(scene: dict, roster: dict[str, str]) -> list[str]:
    """Return roster character names mentioned in this scene's narration or visual prompt."""
    text = f"{scene.get('narration', '')} {scene.get('visual_prompt', '')}".lower()
    return [name for name in roster if name.lower() in text]


def build_shotlist(script: dict, episode_id: str) -> str:
    """Build the full Markdown shot list for an episode."""
    title = script.get("title", episode_id)
    scenes: list[dict] = sorted(script.get("scenes", []),
                                key=lambda s: int(s.get("scene_number", 0)))

    # Character roster: {name: visual description}
    roster: dict[str, str] = {}
    for role in (script.get("characters") or {}).values():
        if isinstance(role, dict) and role.get("name"):
            roster[role["name"]] = role.get("visual", "")

    lines: list[str] = [
        f"# Higgsfield Shot List — {episode_id}: {title}",
        "",
        f"**Scenes:** {len(scenes)} | **Clips to generate:** {len(scenes)}",
        f"**Save all clips to:** `higgsfield_clips/{episode_id}/`",
        "",
        "> Rule: every clip plays ONCE. empire_render.py trims clips longer than the",
        "> narration and freeze-frames the last frame of clips shorter than it — never loops.",
        "> Longer clips = more real motion on screen. TRIPLE-CHECK prompts before submitting — credits are real money.",
        "",
    ]
    if roster:
        lines.append("## Character Roster (for Soul Cast consistency)")
        for name, visual in roster.items():
            lines.append(f"- **{name}:** {visual}")
        lines.append("")

    for scene in scenes:
        n = int(scene.get("scene_number", 0))
        narration = scene.get("narration", "")
        narr_sec = estimate_narration_seconds(narration)
        clip_sec = min(MAX_RECOMMENDED_CLIP_SEC, max(MIN_CLIP_SEC, int(narr_sec // 4)))
        model, reason = pick_model(scene, list(roster))
        chars = characters_in_scene(scene, roster)

        lines += [
            f"## Scene {n:02d} — {scene.get('title', 'Untitled')}",
            f"- **Model:** {model} ({reason})",
            f"- **Duration needed:** {narr_sec:.0f}s narration → generate at least "
            f"{clip_sec}s clip (will be {'trimmed' if clip_sec >= narr_sec else 'padded'})",
            f"- **Prompt suggestion:** {scene.get('visual_prompt', '(no visual_prompt in scene JSON)')}",
            f"- **Characters:** {', '.join(chars) if chars else 'none (environment shot)'}",
            f"- **Filename to save as:** `scene_{n:02d}.mp4`",
            "",
        ]

    total_est = sum(estimate_narration_seconds(s.get("narration", "")) for s in scenes)
    lines += [
        "---",
        f"**Estimated episode runtime:** {total_est / 60:.1f} min "
        f"(narration-driven; clips are fitted to narration)",
        "",
        f"When all clips are in `higgsfield_clips/{episode_id}/`, render with:",
        "```",
        f"RENDER_EMPIRE.bat --channel {episode_id.split('_')[0]} --episode {episode_id} "
        f"--clips-dir higgsfield_clips/{episode_id}/",
        "```",
    ]
    return "\n".join(lines)


def main() -> None:
    """Parse arguments, load the episode JSON, and write the shot list."""
    parser = argparse.ArgumentParser(description="Generate a Higgsfield shot list for an episode")
    parser.add_argument("--episode", required=True, help="Episode ID, e.g. LO_EP001")
    parser.add_argument("--script", default=None, help="Explicit episode JSON path (auto-located if omitted)")
    args = parser.parse_args()

    episode_id: str = args.episode.upper()
    script_path = Path(args.script) if args.script else find_episode_script(episode_id)
    if not script_path or not script_path.exists():
        print(f"[higgsfield_prep] ❌ No episode JSON found for {episode_id}", file=sys.stderr)
        sys.exit(1)

    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    shotlist = build_shotlist(script, episode_id)
    SHOTLIST_DIR.mkdir(exist_ok=True)
    out_path = SHOTLIST_DIR / f"{episode_id}_shotlist.md"
    out_path.write_text(shotlist, encoding="utf-8")

    print(f"[higgsfield_prep] ✅ Shot list written: {out_path}")
    print(f"[higgsfield_prep] Script used: {script_path}")
    print(f"[higgsfield_prep] Scenes: {len(script.get('scenes', []))}")


if __name__ == "__main__":
    main()
