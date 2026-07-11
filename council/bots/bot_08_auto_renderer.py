"""
bot_08_auto_renderer.py — Auto Renderer Bot
Reads the render queue and auto-triggers auto_render.py for pending episodes.
Marks episodes as in-progress so other council runs don't double-trigger.
"""

import json
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from council.bot_base import CouncilBot, BotResult, BASE_DIR, STATE_DIR

MUSIC_PATH = BASE_DIR / "music" / "battle_epic.mp3"
AUTO_RENDER = BASE_DIR / "auto_render.py"
MAX_PER_RUN = 1   # render 1 episode per council run (don't hog CPU for hours)


def _load_queue(queue_path: Path) -> list[dict]:
    if queue_path.exists():
        try:
            return json.loads(queue_path.read_text())
        except Exception:
            pass
    return []


def _save_queue(queue: list[dict], queue_path: Path):
    queue_path.write_text(json.dumps(queue, indent=2))


class AutoRendererBot(CouncilBot):
    name = "bot_auto_renderer"
    description = "Triggers auto_render.py for queued episodes (1 per council run)"
    priority = 60
    auto_fix = True

    def run(self) -> BotResult:
        r = self.result
        queue_path = self.state_dir / "render_queue.json"
        queue = _load_queue(queue_path)

        pending = [q for q in queue if q.get("status") == "pending"]
        in_progress = [q for q in queue if q.get("status") == "in_progress"]

        # Don't start a new render if one is already in progress
        if in_progress:
            r.ok(f"Render in progress: {in_progress[0]['episode_id']} — waiting")
            return r

        if not pending:
            r.ok("Render queue is empty — nothing to do")
            return r

        # Check if a render finished since last run
        for q in in_progress:
            final = self.renders_dir / f"{q['episode_id']}_final.mp4"
            if final.exists() and final.stat().st_size > 1_000_000:
                q["status"] = "done"
                q["completed_at"] = datetime.now().isoformat()
                r.fixed(f"{q['episode_id']}: render completed ✓")

        # Pick next pending
        to_render = pending[:MAX_PER_RUN]

        for item in to_render:
            ep_id = item["episode_id"]

            if not AUTO_RENDER.exists():
                r.error(f"auto_render.py not found at {AUTO_RENDER}")
                break

            music_arg = str(MUSIC_PATH) if MUSIC_PATH.exists() else ""

            cmd = [sys.executable, str(AUTO_RENDER), "--episode", ep_id]
            if music_arg:
                cmd += ["--music", music_arg]

            self.log(f"Launching render: {ep_id}…")
            r.ok(f"Starting render: {ep_id} — {item.get('title','')[:40]}")

            # Mark in-progress BEFORE launching so other bots see it
            item["status"] = "in_progress"
            item["started_at"] = datetime.now().isoformat()
            _save_queue(queue)

            # Run render (blocking — this is the long part)
            result = subprocess.run(cmd, timeout=7200)  # 2 hour max per episode

            if result.returncode == 0:
                final = self.renders_dir / f"{ep_id}_final.mp4"
                if final.exists() and final.stat().st_size > 1_000_000:
                    item["status"] = "done"
                    item["completed_at"] = datetime.now().isoformat()
                    r.fixed(f"{ep_id}: render complete → {final.stat().st_size // 1_048_576}MB")
                else:
                    item["status"] = "failed"
                    r.error(f"{ep_id}: render finished but no final found")
            else:
                item["status"] = "failed"
                item["failed_at"] = datetime.now().isoformat()
                r.error(f"{ep_id}: render exited with code {result.returncode}")

        _save_queue(queue, queue_path)
        return r
