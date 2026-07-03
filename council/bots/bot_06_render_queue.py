"""
bot_06_render_queue.py — Render Queue Bot
Maintains a queue of episodes that need full renders.
Detects episodes where the script is full but no output exists yet.
Can trigger auto_render.py for queued episodes.
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from council.bot_base import CouncilBot, BotResult, BASE_DIR, STATE_DIR

OUTPUT_DIR = BASE_DIR / "output"
RENDERS_DIR = BASE_DIR / "renders"
PROMPTS_DIR = BASE_DIR / "prompts"
QUEUE_PATH = BASE_DIR / "council" / "state" / "render_queue.json"
MIN_FULL_DURATION = 600


def _load_queue() -> list[dict]:
    if QUEUE_PATH.exists():
        try:
            return json.loads(QUEUE_PATH.read_text())
        except Exception:
            pass
    return []


def _save_queue(queue: list[dict]):
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_PATH.write_text(json.dumps(queue, indent=2))


def _scan_full_scripts() -> dict[str, dict]:
    """Find all full scripts (>= 600s) and their episode IDs."""
    full_scripts = {}
    for p in sorted(PROMPTS_DIR.rglob("*.json")):
        if any(part.startswith("_") for part in p.relative_to(PROMPTS_DIR).parts[:-1]):
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        scenes = data.get("scenes", [])
        ep_id = data.get("episode_id", "")
        if not ep_id:
            stem = p.stem.lower()
            for prefix in ["gg_ep", "ml_ep", "lo_ep"]:
                idx = stem.find(prefix)
                if idx != -1:
                    ep_id = stem[idx:].split(".")[0].upper()
                    break
        if not ep_id:
            continue
        total_dur = sum(s.get("duration_sec", 0) for s in scenes)
        if total_dur >= MIN_FULL_DURATION:
            # Keep longest version per episode
            if ep_id not in full_scripts or total_dur > full_scripts[ep_id]["total_duration_sec"]:
                full_scripts[ep_id] = {
                    "episode_id": ep_id,
                    "script_path": str(p),
                    "scene_count": len(scenes),
                    "total_duration_sec": total_dur,
                    "title": data.get("title", "?"),
                }
    return full_scripts


class RenderQueueBot(CouncilBot):
    name = "bot_render_queue"
    description = "Tracks which episodes have scripts but no renders; manages render queue"
    priority = 30
    auto_fix = False  # queue management only; set auto_fix=True to auto-trigger renders

    def run(self) -> BotResult:
        r = self.result
        full_scripts = _scan_full_scripts()
        queue = _load_queue()
        queued_ids = {q["episode_id"] for q in queue}

        newly_queued = []
        already_rendered = []
        in_queue = []

        for ep_id, script_info in sorted(full_scripts.items()):
            # Check if rendered
            final = RENDERS_DIR / f"{ep_id}_final.mp4"
            has_output = (OUTPUT_DIR / ep_id).exists()

            if final.exists() and final.stat().st_size > 1_000_000:
                already_rendered.append(ep_id)
                # Remove from queue if it was there
                queue = [q for q in queue if q["episode_id"] != ep_id]
                continue

            if ep_id in queued_ids:
                in_queue.append(ep_id)
                r.ok(f"{ep_id}: already queued — {script_info['title'][:40]}")
                continue

            # Needs rendering
            queue.append({
                "episode_id": ep_id,
                "title": script_info["title"],
                "scene_count": script_info["scene_count"],
                "total_duration_sec": script_info["total_duration_sec"],
                "queued_at": datetime.now().isoformat(),
                "status": "pending",
                "has_partial_output": has_output,
            })
            newly_queued.append(ep_id)
            r.warn(f"{ep_id}: QUEUED for render — {script_info['title'][:40]}")

        _save_queue(queue)

        r.ok(f"{len(already_rendered)} rendered, {len(in_queue)} in queue, {len(newly_queued)} newly queued")

        pending = [q for q in queue if q.get("status") == "pending"]
        if pending:
            r.ok(f"Render queue: {len(pending)} episode(s) waiting")
            for q in pending[:5]:
                r.ok(f"  → {q['episode_id']}: {q['title'][:40]}")
            if len(pending) > 5:
                r.ok(f"  ... and {len(pending)-5} more")
            r.next_action = f"Run render_season3.bat or: py auto_render.py --episode {pending[0]['episode_id']}"

        self.save_state({
            "total_full_scripts": len(full_scripts),
            "rendered": len(already_rendered),
            "queued": len(pending),
        })

        return r
