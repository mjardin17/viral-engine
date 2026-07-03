"""
bot_07_stub_expander.py — Stub Expander Bot
Detects stub scripts (< 600s) that have no full version anywhere.
Reports them so they can be written or queued for AI expansion.
Tracks expansion backlog across runs.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from council.bot_base import CouncilBot, BotResult, BASE_DIR, STATE_DIR

PROMPTS_DIR = BASE_DIR / "prompts"
BACKLOG_PATH = BASE_DIR / "council" / "state" / "stub_backlog.json"
MIN_FULL_DURATION = 600
STUB_CRITICAL = 120


def _load_backlog() -> dict:
    if BACKLOG_PATH.exists():
        try:
            return json.loads(BACKLOG_PATH.read_text())
        except Exception:
            pass
    return {}


def _save_backlog(backlog: dict):
    BACKLOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    BACKLOG_PATH.write_text(json.dumps(backlog, indent=2))


class StubExpanderBot(CouncilBot):
    name = "bot_stub_expander"
    description = "Tracks stub scripts with no full version; maintains expansion backlog"
    priority = 35
    auto_fix = False

    def run(self) -> BotResult:
        r = self.result
        backlog = _load_backlog()

        # Scan all scripts grouped by episode_id
        by_ep: dict[str, list] = {}
        for p in sorted(PROMPTS_DIR.rglob("*.json")):
            if any(part.startswith("_") for part in p.relative_to(PROMPTS_DIR).parts[:-1]):
                continue
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            scenes = data.get("scenes", [])
            if not scenes:
                continue
            ep_id = data.get("episode_id", "")
            if not ep_id:
                stem = p.stem.lower()
                for prefix in ["gg_ep", "ml_ep", "lo_ep", "il_ep"]:
                    idx = stem.find(prefix)
                    if idx != -1:
                        ep_id = stem[idx:].split(".")[0].upper()
                        break
            if not ep_id:
                continue
            total_dur = sum(s.get("duration_sec", 0) for s in scenes)
            by_ep.setdefault(ep_id, []).append({
                "filepath": str(p),
                "scene_count": len(scenes),
                "total_duration_sec": total_dur,
                "title": data.get("title", "?"),
                "is_full": total_dur >= MIN_FULL_DURATION,
            })

        stubs_without_full = []
        for ep_id, versions in sorted(by_ep.items()):
            has_full = any(v["is_full"] for v in versions)
            if has_full:
                # Remove from backlog if it was there
                backlog.pop(ep_id, None)
                continue
            # Pure stub — no full version anywhere
            best = max(versions, key=lambda v: v["total_duration_sec"])
            stubs_without_full.append(ep_id)

            if ep_id not in backlog:
                backlog[ep_id] = {
                    "episode_id": ep_id,
                    "title": best["title"],
                    "current_scenes": best["scene_count"],
                    "current_duration_sec": best["total_duration_sec"],
                    "first_seen": datetime.now().isoformat(),
                    "status": "needs_expansion",
                }
                r.warn(f"{ep_id}: stub only ({best['scene_count']} scenes, "
                       f"{best['total_duration_sec']}s) — added to backlog")
            else:
                r.warn(f"{ep_id}: still stub (backlog since {backlog[ep_id]['first_seen'][:10]})")

        _save_backlog(backlog)

        # Summary
        total_stubs = len(stubs_without_full)
        r.ok(f"Expansion backlog: {total_stubs} episode(s) need full scripts")

        # Group by channel
        channels: dict[str, list] = {}
        for ep_id in stubs_without_full:
            ch = ep_id.split("_EP")[0]
            channels.setdefault(ch, []).append(ep_id)

        for ch, eps in sorted(channels.items()):
            r.ok(f"  {ch}: {len(eps)} stubs ({', '.join(eps[:4])}{'…' if len(eps)>4 else ''})")

        if stubs_without_full:
            r.next_action = ("Write full 24-scene scripts for backlog episodes "
                            "or run: py council/bot_factory.py --expand EPISODE_ID")

        self.save_state({
            "total_stubs_in_backlog": total_stubs,
            "backlog_episode_ids": stubs_without_full,
        })

        return r
