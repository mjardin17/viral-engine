#!/usr/bin/env python3
"""
empire_server.py — Video Bot Pipeline Empire OS bridge.

A thin FastAPI server that:
  - Exposes /empire/health, /empire/status, /empire/event (Empire OS contract)
  - Exposes /api/* routes for render control and status inspection
  - Triggers auto_render.py as a subprocess when renders are requested
  - Publishes Empire OS events (render.queued, render.completed, render.failed)

Port: 8002  (StoryForge=8001, this=8002, CrossPost=3000)

Start:
    pip install fastapi uvicorn --break-system-packages
    python empire_server.py

Or in background:
    uvicorn empire_server:app --port 8002

Empire OS connection:
    Set EMPIRE_OS_EVENT_URL=http://localhost:5000/api/events in .env
    (or wherever Empire OS is listening for events)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent
RENDERS_DIR = BASE_DIR / "renders"
PROMPTS_DIR = BASE_DIR / "prompts"
OUTPUT_DIR  = BASE_DIR / "output"
COUNCIL_DIR = BASE_DIR / "council"
STATE_DIR   = COUNCIL_DIR / "state"
QUEUE_PATH  = STATE_DIR / "render_queue.json"

MODULE_ID      = "video-pipeline"
MODULE_VERSION = "1.0.0"
_SERVER_START  = datetime.now().isoformat()
_active_renders: dict[str, dict] = {}   # episode_id → {status, started_at, pid}
_event_log: list[dict] = []             # last 100 Empire OS events received

# Load .env
def _load_dotenv() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val

_load_dotenv()

EMPIRE_OS_EVENT_URL = os.environ.get("EMPIRE_OS_EVENT_URL", "")

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(title="Video Bot Pipeline — Empire OS Bridge", version=MODULE_VERSION)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── Helpers ───────────────────────────────────────────────────────────────────
def _list_episodes() -> list[dict]:
    """Scan prompts/ (and prompts/gods_glory/) for all episode JSON files."""
    episodes = []
    for search_dir in [PROMPTS_DIR / "gods_glory", PROMPTS_DIR]:
        if not search_dir.is_dir():
            continue
        for f in sorted(search_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                ep_id = data.get("episode_id") or f.stem
                scenes = data.get("scenes", [])
                total_dur = sum(s.get("duration", 0) for s in scenes)
                rendered_path = RENDERS_DIR / f"{ep_id}_final.mp4"
                episodes.append({
                    "id": ep_id,
                    "title": data.get("title", ep_id),
                    "scenes": len(scenes),
                    "duration_s": total_dur,
                    "is_full_script": total_dur >= 600,
                    "rendered": rendered_path.exists(),
                    "rendered_size_mb": round(rendered_path.stat().st_size / 1_048_576, 1)
                    if rendered_path.exists() else None,
                    "script_path": str(f),
                })
            except Exception:
                pass
    return episodes


def _council_state() -> dict:
    """Read the latest council state files."""
    state: dict[str, Any] = {}
    if STATE_DIR.is_dir():
        for sf in sorted(STATE_DIR.glob("*.json")):
            try:
                state[sf.stem] = json.loads(sf.read_text(encoding="utf-8"))
            except Exception:
                pass
    return state


def _publish_empire_event(topic: str, payload: dict) -> None:
    """Fire-and-forget POST to Empire OS event bus."""
    if not EMPIRE_OS_EVENT_URL:
        return
    try:
        import urllib.request
        body = json.dumps({
            "topic": topic,
            "source": MODULE_ID,
            "payload": payload,
            "timestamp": datetime.now().isoformat(),
        }).encode()
        req = urllib.request.Request(
            EMPIRE_OS_EVENT_URL,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=2)
    except Exception:
        pass  # Empire OS may not be running — non-fatal


def _run_render(episode_id: str) -> None:
    """Background thread: calls auto_render.py for one episode."""
    _active_renders[episode_id] = {
        "status": "rendering",
        "started_at": datetime.now().isoformat(),
        "pid": None,
    }
    _publish_empire_event("render.started", {"episode": episode_id, "moduleId": MODULE_ID})
    try:
        proc = subprocess.Popen(
            [sys.executable, str(BASE_DIR / "auto_render.py"), "--episode", episode_id],
            cwd=str(BASE_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        _active_renders[episode_id]["pid"] = proc.pid
        stdout, _ = proc.communicate()
        success = proc.returncode == 0
        _active_renders[episode_id]["status"] = "completed" if success else "failed"
        _active_renders[episode_id]["finished_at"] = datetime.now().isoformat()
        _active_renders[episode_id]["return_code"] = proc.returncode
        if success:
            _publish_empire_event("render.completed", {
                "episode": episode_id,
                "moduleId": MODULE_ID,
                "renderPath": str(RENDERS_DIR / f"{episode_id}_final.mp4"),
            })
        else:
            _publish_empire_event("render.failed", {
                "episode": episode_id,
                "moduleId": MODULE_ID,
                "returnCode": proc.returncode,
            })
    except Exception as exc:
        _active_renders[episode_id]["status"] = "error"
        _active_renders[episode_id]["error"] = str(exc)
        _publish_empire_event("render.failed", {"episode": episode_id, "error": str(exc)})


# ── Empire hooks ──────────────────────────────────────────────────────────────
@app.get("/empire/health")
def empire_health():
    can_render = (BASE_DIR / "auto_render.py").exists()
    renders_accessible = RENDERS_DIR.exists()
    status = "healthy" if (can_render and renders_accessible) else "degraded"
    return {
        "status": status,
        "moduleId": MODULE_ID,
        "version": MODULE_VERSION,
        "capabilities": [
            "render-episode", "render-season", "council-run",
            "episode-list", "render-status",
        ],
        "activeRenders": len([r for r in _active_renders.values() if r["status"] == "rendering"]),
        "autoRenderPresent": can_render,
        "rendersDir": str(RENDERS_DIR),
        "startedAt": _SERVER_START,
        "checkedAt": datetime.now().isoformat(),
    }


@app.get("/empire/status")
def empire_status():
    episodes = _list_episodes()
    rendered_count = sum(1 for e in episodes if e["rendered"])
    full_scripts   = sum(1 for e in episodes if e["is_full_script"])
    return {
        "id": MODULE_ID,
        "name": "Video Bot Pipeline",
        "version": MODULE_VERSION,
        "description": (
            "Python auto_render pipeline: JSON scripts → AI images (Pollinations) "
            "→ TTS (edge-tts) → FFmpeg → MP4. "
            "9-bot self-healing Council system. "
            "3 channels: Gods & Glory, Machine Learning, Little Olympus."
        ),
        "capabilities": [
            "render-episode", "render-season", "council-run",
            "episode-list", "render-status",
        ],
        "endpoints": [
            {"path": "/api/episodes",       "method": "GET"},
            {"path": "/api/render",         "method": "POST"},
            {"path": "/api/renders",        "method": "GET"},
            {"path": "/api/council/status", "method": "GET"},
            {"path": "/api/render/status",  "method": "GET"},
            {"path": "/empire/health",      "method": "GET"},
            {"path": "/empire/status",      "method": "GET"},
            {"path": "/empire/event",       "method": "POST"},
        ],
        "stats": {
            "totalEpisodes": len(episodes),
            "fullScripts": full_scripts,
            "rendered": rendered_count,
            "queued": len([r for r in _active_renders.values() if r["status"] == "rendering"]),
        },
        "channels": ["gods-glory", "machine-learning", "little-olympus"],
        "healthPath": "/empire/health",
        "baseUrl": f"http://localhost:8002",
        "priority": 20,
    }


class EmpireEvent(BaseModel):
    topic: str
    source: Optional[str] = None
    payload: Optional[dict] = None
    correlationId: Optional[str] = None


@app.post("/empire/event")
def empire_event(evt: EmpireEvent, background_tasks: BackgroundTasks):
    record = {
        "id": f"evt_{len(_event_log):04d}",
        "receivedAt": datetime.now().isoformat(),
        "topic": evt.topic,
        "source": evt.source,
        "payload": evt.payload or {},
        "correlationId": evt.correlationId,
    }
    _event_log.append(record)
    if len(_event_log) > 100:
        _event_log.pop(0)

    # Auto-queue a render when StoryForge creates a script
    if evt.topic == "script.created":
        episode_id = (evt.payload or {}).get("episodeId")
        if episode_id:
            _publish_empire_event("render.queued", {
                "episode": episode_id,
                "triggeredBy": "script.created",
                "moduleId": MODULE_ID,
            })
            background_tasks.add_task(_run_render, episode_id)

    return {"status": "received", "topic": evt.topic, "internalEventId": record["id"]}


# ── API routes ────────────────────────────────────────────────────────────────
@app.get("/api/episodes")
def list_episodes():
    return {"episodes": _list_episodes()}


class RenderRequest(BaseModel):
    episode_id: str
    skip_images: bool = False
    portrait: bool = False
    music: Optional[str] = None


@app.post("/api/render")
def trigger_render(req: RenderRequest, background_tasks: BackgroundTasks):
    episode_id = req.episode_id
    if episode_id in _active_renders and _active_renders[episode_id]["status"] == "rendering":
        return {"status": "already_rendering", "episode": episode_id}
    _publish_empire_event("render.queued", {"episode": episode_id, "moduleId": MODULE_ID})
    background_tasks.add_task(_run_render, episode_id)
    return {"status": "queued", "episode": episode_id}


@app.get("/api/renders")
def list_renders():
    renders = []
    if RENDERS_DIR.is_dir():
        for f in sorted(RENDERS_DIR.glob("*_final.mp4")):
            stat = f.stat()
            renders.append({
                "file": f.name,
                "episode_id": f.stem.replace("_final", ""),
                "size_mb": round(stat.st_size / 1_048_576, 1),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
    return {"renders": renders, "count": len(renders)}


@app.get("/api/council/status")
def council_status():
    return {"state": _council_state()}


@app.get("/api/render/status")
def render_status():
    return {"active_renders": _active_renders}


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run("empire_server:app", host="0.0.0.0", port=8002, reload=False)
