r"""
empire_server.py -- Video Pipeline Bridge for Empire OS
FastAPI server at port 8002. Accepts render requests from Empire OS
and spawns auto_render.py as a subprocess, streaming progress back.

USAGE:
  cd C:/Users/jjard/claude/video-bot-pipeline
  python empire-os-patch/apps/video-pipeline/empire_server.py

Requires: pip install fastapi uvicorn
auto_render.py must exist at REPO_ROOT.
"""

import asyncio
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

# ── Paths ──────────────────────────────────────────────────────────────────────
# empire_server.py lives at:  <repo>/empire-os-patch/apps/video-pipeline/empire_server.py
# So parents[3] is the repo root: <repo>/
THIS_FILE   = Path(__file__).resolve()
REPO_ROOT   = THIS_FILE.parents[3]
AUTO_RENDER = REPO_ROOT / "auto_render.py"
PROMPTS_DIR = REPO_ROOT / "prompts"
RENDERS_DIR = REPO_ROOT / "renders"
COUNCIL_DIR = REPO_ROOT / "council" / "bots"

PORT = int(os.environ.get("EMPIRE_PIPELINE_PORT", "8002"))

# ── FastAPI import (fail early with clear message) ────────────────────────────
try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, StreamingResponse
    import uvicorn
except ImportError:
    print("[empire_server] ERROR: FastAPI / uvicorn not installed.")
    print("  Run: pip install fastapi uvicorn --break-system-packages")
    sys.exit(1)

# ── Job store ─────────────────────────────────────────────────────────────────
# In-memory. Survives as long as the process is running.
# Schema for each job:
#   id            str      UUID
#   episode_id    str      e.g. "GG_EP001"
#   status        str      queued | running | completed | failed | cancelled
#   queued_at     str      ISO timestamp
#   started_at    str|None
#   completed_at  str|None
#   log_lines     list[str]
#   percent       int      0-100
#   current_scene int|None
#   total_scenes  int|None
#   current_stage str|None e.g. "[IMG]", "[TTS]", "[VID]", "Assembly"
#   output_path   str|None absolute path to final MP4
#   error         str|None
#   pid           int|None subprocess PID (for cancel)
#   args          dict     extra args passed to auto_render.py

_jobs: dict[str, dict[str, Any]] = {}
_jobs_lock = threading.Lock()

def _new_job(episode_id: str, args: dict) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "episode_id": episode_id,
        "status": "queued",
        "queued_at": datetime.utcnow().isoformat() + "Z",
        "started_at": None,
        "completed_at": None,
        "log_lines": [],
        "percent": 0,
        "current_scene": None,
        "total_scenes": None,
        "current_stage": None,
        "output_path": None,
        "error": None,
        "pid": None,
        "args": args,
    }

def _add_log(job: dict, line: str) -> None:
    job["log_lines"].append(line)
    # Keep last 2000 lines to avoid unbounded growth
    if len(job["log_lines"]) > 2000:
        job["log_lines"] = job["log_lines"][-2000:]

# ── Progress parsing ──────────────────────────────────────────────────────────
# auto_render.py prints lines like:
#   ── Scene 01/54  [Pearl Harbor] ──
#   [IMG 1]  Generating image 1/4 ...
#   [TTS]   Synthesizing narration ...
#   [VID]   Building clip ...
#   ✓ Final: renders/GG_EP006_final.mp4
#   FATAL: ...

_RE_SCENE    = re.compile(r'Scene\s+(\d+)/(\d+)', re.IGNORECASE)
_RE_IMG      = re.compile(r'\[IMG', re.IGNORECASE)
_RE_TTS      = re.compile(r'\[TTS\]', re.IGNORECASE)
_RE_VID      = re.compile(r'\[VID\]', re.IGNORECASE)
_RE_FINAL    = re.compile(r'Final.*?renders[/\\](.+\.mp4)', re.IGNORECASE)
_RE_DONE     = re.compile(r'(✓\s*DONE|All done|Episode complete)', re.IGNORECASE)
_RE_FATAL    = re.compile(r'(FATAL|ERROR|Traceback|raise\s+)', re.IGNORECASE)

def _parse_progress(job: dict, line: str) -> None:
    """Update job fields by parsing a stdout line from auto_render.py."""
    m = _RE_SCENE.search(line)
    if m:
        scene_num   = int(m.group(1))
        total       = int(m.group(2))
        job["current_scene"] = scene_num
        job["total_scenes"]  = total
        # Compute percent: each scene has ~3 stages (IMG, TTS, VID)
        # Use (scene-1)/total * 95 as conservative progress
        job["percent"] = max(job["percent"], int((scene_num - 1) / total * 95))
        return

    if _RE_IMG.search(line):
        job["current_stage"] = "Generating images"
        return
    if _RE_TTS.search(line):
        job["current_stage"] = "Text-to-speech"
        return
    if _RE_VID.search(line):
        job["current_stage"] = "Building clip"
        return

    m = _RE_FINAL.search(line)
    if m:
        mp4_name = m.group(1).strip()
        job["output_path"] = str(RENDERS_DIR / mp4_name)
        job["percent"]     = 99
        job["current_stage"] = "Finalizing"
        return

    if _RE_DONE.search(line):
        job["percent"]       = 100
        job["current_stage"] = "Complete"
        return

# ── Episode discovery ─────────────────────────────────────────────────────────

def _episode_id_from_filename(fname: str) -> str | None:
    """
    scene_prompts.gg_ep001.final.json  →  GG_EP001
    scene_prompts.gg_ep012.final.json  →  GG_EP012
    scene_prompts.ml_ep001.final.json  →  ML_EP001
    scene_prompts.lo_ep001.final.json  →  LO_EP001
    """
    m = re.match(r'scene_prompts\.([a-z0-9_]+)\.final\.json$', fname, re.IGNORECASE)
    if not m:
        return None
    raw = m.group(1)
    # Skip captions_source files
    if "captions" in raw:
        return None
    return raw.upper()

def _scan_episodes() -> list[dict]:
    """
    Return list of episode descriptors, deduplicating by episode_id.
    gods_glory/ versions preferred over root versions (they're the full scripts).
    """
    found: dict[str, dict] = {}

    def _add(path: Path, preferred: bool):
        fname = path.name
        ep_id = _episode_id_from_filename(fname)
        if not ep_id:
            return
        if ep_id in found and not preferred:
            return  # root stub: don't overwrite gods_glory full script
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            raw = {}
        scene_count = len(raw.get("scenes", []))
        title = raw.get("title", ep_id)
        render_path = RENDERS_DIR / f"{ep_id}_final.mp4"
        found[ep_id] = {
            "episode_id":  ep_id,
            "title":       title,
            "scene_count": scene_count,
            "script_path": str(path),
            "has_render":  render_path.exists(),
            "render_size_mb": round(render_path.stat().st_size / 1_048_576, 1) if render_path.exists() else None,
            "is_full_script": scene_count >= 10,
            "preferred_dir": "gods_glory" if preferred else "prompts",
        }

    # Root prompts/ (lower priority)
    for f in sorted(PROMPTS_DIR.glob("scene_prompts.*.final.json")):
        _add(f, preferred=False)

    # gods_glory/ (higher priority — full scripts)
    gods_glory = PROMPTS_DIR / "gods_glory"
    if gods_glory.exists():
        for f in sorted(gods_glory.glob("scene_prompts.*.final.json")):
            _add(f, preferred=True)

    return sorted(found.values(), key=lambda e: e["episode_id"])

# ── Render worker ─────────────────────────────────────────────────────────────

def _render_worker(job_id: str) -> None:
    """
    Background thread: spawns auto_render.py, captures stdout, updates job state.
    """
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        return

    episode_id = job["episode_id"]
    args       = job.get("args", {})

    # Build command
    cmd = [sys.executable, str(AUTO_RENDER), "--episode", episode_id]
    if args.get("skip_images"):
        cmd.append("--skip-images")
    if args.get("portrait"):
        cmd.append("--portrait")
    if args.get("images_only"):
        cmd.append("--images-only")
    if args.get("music"):
        cmd.extend(["--music", args["music"]])

    with _jobs_lock:
        job["status"]     = "running"
        job["started_at"] = datetime.utcnow().isoformat() + "Z"
        _add_log(job, f"[empire_server] Starting: {' '.join(cmd)}")
        _add_log(job, f"[empire_server] Working dir: {REPO_ROOT}")

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        with _jobs_lock:
            job["pid"] = proc.pid

        # Stream stdout line by line
        for line in iter(proc.stdout.readline, ""):
            line = line.rstrip()
            if not line:
                continue
            with _jobs_lock:
                _add_log(job, line)
                _parse_progress(job, line)
                if job["status"] == "cancelled":
                    # User cancelled — kill process
                    try:
                        proc.kill()
                    except Exception:
                        pass
                    break

        proc.wait()
        exit_code = proc.returncode

        with _jobs_lock:
            job["completed_at"] = datetime.utcnow().isoformat() + "Z"
            job["pid"]          = None

            if job["status"] == "cancelled":
                _add_log(job, "[empire_server] Cancelled by user.")
                return

            if exit_code == 0:
                # Confirm output exists
                expected = RENDERS_DIR / f"{episode_id}_final.mp4"
                if expected.exists():
                    job["output_path"] = str(expected)
                    job["status"]      = "completed"
                    job["percent"]     = 100
                    job["current_stage"] = "Complete"
                    _add_log(job, f"[empire_server] ✓ Completed: {expected}")
                else:
                    job["status"] = "failed"
                    job["error"]  = f"auto_render.py exited 0 but {expected.name} not found"
                    _add_log(job, f"[empire_server] ERROR: {job['error']}")
            else:
                job["status"] = "failed"
                job["error"]  = f"auto_render.py exited with code {exit_code}"
                _add_log(job, f"[empire_server] FAILED (exit {exit_code})")

    except FileNotFoundError as e:
        with _jobs_lock:
            job["status"]       = "failed"
            job["error"]        = f"Python or auto_render.py not found: {e}"
            job["completed_at"] = datetime.utcnow().isoformat() + "Z"
            _add_log(job, f"[empire_server] ERROR: {job['error']}")
    except Exception as e:
        with _jobs_lock:
            job["status"]       = "failed"
            job["error"]        = str(e)
            job["completed_at"] = datetime.utcnow().isoformat() + "Z"
            _add_log(job, f"[empire_server] EXCEPTION: {e}")

# Render queue — one render at a time (auto_render.py is CPU/GPU bound)
_render_queue: list[str] = []
_queue_lock  = threading.Lock()
_queue_thread_running = False

def _queue_worker() -> None:
    """Single background thread that processes the render queue sequentially."""
    global _queue_thread_running
    while True:
        with _queue_lock:
            if not _render_queue:
                _queue_thread_running = False
                return
            job_id = _render_queue.pop(0)
        _render_worker(job_id)

def _enqueue(job_id: str) -> None:
    global _queue_thread_running
    with _queue_lock:
        _render_queue.append(job_id)
        if not _queue_thread_running:
            _queue_thread_running = True
            t = threading.Thread(target=_queue_worker, daemon=True)
            t.start()

# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Video Pipeline Bridge",
    description="Empire OS ↔ auto_render.py bridge",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # Empire OS localhost, dashboard, etc.
    allow_methods=["*"],
    allow_headers=["*"],
)

def _job_summary(job: dict) -> dict:
    """Return safe job summary (drop log_lines for list endpoints)."""
    return {k: v for k, v in job.items() if k != "log_lines"}

# ── Empire OS integration endpoints ──────────────────────────────────────────

@app.get("/empire/health")
async def empire_health():
    """Health probe — called by video-pipeline.module.ts every N seconds."""
    running  = sum(1 for j in _jobs.values() if j["status"] == "running")
    queued   = sum(1 for j in _jobs.values() if j["status"] == "queued")
    complete = sum(1 for j in _jobs.values() if j["status"] == "completed")
    return {
        "status":    "healthy",
        "service":   "empire_server",
        "port":      PORT,
        "repo_root": str(REPO_ROOT),
        "auto_render_exists": AUTO_RENDER.exists(),
        "jobs": { "running": running, "queued": queued, "completed": complete },
        "uptime_s": int(time.time() - _START_TIME),
    }

@app.get("/empire/status")
async def empire_status():
    return {
        "id":      "video-pipeline",
        "name":    "Video Bot Pipeline",
        "version": "1.0.0",
        "port":    PORT,
        "channels": ["gods-glory", "machine-learning", "little-olympus"],
        "auto_render": str(AUTO_RENDER),
        "auto_render_ok": AUTO_RENDER.exists(),
        "prompts_dir": str(PROMPTS_DIR),
        "renders_dir": str(RENDERS_DIR),
        "episode_count": len(_scan_episodes()),
    }

@app.post("/empire/event")
async def empire_event(request: Request):
    """Receive events from Empire OS event bus."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    topic   = body.get("topic", "")
    payload = body.get("payload", {})

    # Auto-queue render when a script is created
    if topic == "script.created":
        ep_id = payload.get("episode_id") or payload.get("episodeId")
        if ep_id:
            job = _new_job(ep_id.upper(), {})
            with _jobs_lock:
                _jobs[job["id"]] = job
            _enqueue(job["id"])
            return {"received": True, "queued": True, "job_id": job["id"]}

    return {"received": True, "queued": False, "topic": topic}

# ── Episode list ──────────────────────────────────────────────────────────────

@app.get("/api/episodes")
async def list_episodes():
    """Scan prompts/ and prompts/gods_glory/ for available episode scripts."""
    episodes = _scan_episodes()
    # Attach current job status for any running/recent job
    ep_to_latest_job: dict[str, dict] = {}
    with _jobs_lock:
        for job in sorted(_jobs.values(), key=lambda j: j["queued_at"]):
            ep_to_latest_job[job["episode_id"]] = _job_summary(job)
    for ep in episodes:
        ep["latest_job"] = ep_to_latest_job.get(ep["episode_id"])
    return {"episodes": episodes, "count": len(episodes)}

# ── Render control ────────────────────────────────────────────────────────────

@app.post("/api/render")
async def start_render(request: Request):
    """
    Queue a render job.
    Body: { "episode_id": "GG_EP001", "skip_images": false, "portrait": false }
    Returns: { "job_id": "...", "status": "queued" }
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    episode_id = (body.get("episode_id") or body.get("episodeId") or "").strip().upper()
    if not episode_id:
        raise HTTPException(status_code=400, detail="episode_id is required")

    # Validate auto_render.py exists
    if not AUTO_RENDER.exists():
        raise HTTPException(
            status_code=503,
            detail=f"auto_render.py not found at {AUTO_RENDER}. Check REPO_ROOT.",
        )

    # Reject if same episode already running
    with _jobs_lock:
        for job in _jobs.values():
            if job["episode_id"] == episode_id and job["status"] in ("running", "queued"):
                return {
                    "job_id":     job["id"],
                    "status":     job["status"],
                    "message":    f"{episode_id} is already {job['status']}",
                    "already_running": True,
                }

    extra_args = {
        "skip_images":  bool(body.get("skip_images")),
        "portrait":     bool(body.get("portrait")),
        "images_only":  bool(body.get("images_only")),
        "music":        body.get("music") or None,
    }
    job = _new_job(episode_id, extra_args)
    with _jobs_lock:
        _jobs[job["id"]] = job
    _enqueue(job["id"])

    return {
        "job_id":     job["id"],
        "episode_id": episode_id,
        "status":     "queued",
        "message":    f"Render queued for {episode_id}",
    }

@app.get("/api/renders")
async def list_renders():
    """List all render jobs (newest first)."""
    with _jobs_lock:
        jobs = [_job_summary(j) for j in _jobs.values()]
    jobs.sort(key=lambda j: j["queued_at"], reverse=True)
    return {"jobs": jobs, "count": len(jobs)}

@app.get("/api/render/status")
async def render_status(job_id: str | None = None):
    """
    Get status of a specific job (?job_id=xxx) or the most recent job.
    """
    with _jobs_lock:
        if job_id:
            job = _jobs.get(job_id)
        else:
            # Most recent job by queued_at
            job = max(_jobs.values(), key=lambda j: j["queued_at"], default=None) if _jobs else None

    if not job:
        raise HTTPException(status_code=404, detail="No render job found")

    return _job_summary(job)

@app.get("/api/render/logs")
async def render_logs(job_id: str | None = None, offset: int = 0, stream: bool = False):
    """
    Get logs for a job.
    ?job_id=xxx  — specific job
    ?offset=100  — return lines starting from this index
    ?stream=true — Server-Sent Events stream (EventSource)
    """
    with _jobs_lock:
        if job_id:
            job = _jobs.get(job_id)
        else:
            job = max(_jobs.values(), key=lambda j: j["queued_at"], default=None) if _jobs else None

    if not job:
        raise HTTPException(status_code=404, detail="No render job found")

    found_job_id = job["id"]

    if not stream:
        # Polling mode — return current lines from offset
        with _jobs_lock:
            j = _jobs[found_job_id]
            lines = j["log_lines"][offset:]
            status = j["status"]
        return {
            "job_id":  found_job_id,
            "status":  status,
            "lines":   lines,
            "offset":  offset + len(lines),
            "done":    status in ("completed", "failed", "cancelled"),
        }

    # SSE streaming mode
    async def sse_generator():
        sent = offset
        yield f"data: {json.dumps({'type': 'connected', 'job_id': found_job_id})}\n\n"
        while True:
            with _jobs_lock:
                j = _jobs.get(found_job_id, {})
                new_lines = j.get("log_lines", [])[sent:]
                status    = j.get("status", "unknown")
                pct       = j.get("percent", 0)
                stage     = j.get("current_stage")

            for line in new_lines:
                payload = json.dumps({"type": "log", "line": line})
                yield f"data: {payload}\n\n"
                sent += 1

            # Send progress heartbeat
            progress_payload = json.dumps({
                "type":    "progress",
                "percent": pct,
                "stage":   stage,
                "status":  status,
            })
            yield f"data: {progress_payload}\n\n"

            if status in ("completed", "failed", "cancelled"):
                yield f"data: {json.dumps({'type': 'done', 'status': status})}\n\n"
                break

            await asyncio.sleep(1)

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

@app.get("/api/render/output")
async def render_output(job_id: str | None = None):
    """Return the output path for a completed render."""
    with _jobs_lock:
        if job_id:
            job = _jobs.get(job_id)
        else:
            job = max(_jobs.values(), key=lambda j: j["queued_at"], default=None) if _jobs else None

    if not job:
        raise HTTPException(status_code=404, detail="No render job found")

    if job["status"] != "completed":
        return {
            "job_id":   job["id"],
            "status":   job["status"],
            "ready":    False,
            "output_path": None,
        }

    output = job.get("output_path")
    exists = bool(output and Path(output).exists())
    size_mb = round(Path(output).stat().st_size / 1_048_576, 1) if exists else None

    return {
        "job_id":      job["id"],
        "status":      "completed",
        "ready":       exists,
        "output_path": output,
        "size_mb":     size_mb,
        "episode_id":  job["episode_id"],
    }

@app.post("/api/cancel")
async def cancel_render(request: Request):
    """Cancel a queued or running render job."""
    try:
        body = await request.json()
    except Exception:
        body = {}

    job_id = body.get("job_id")

    with _jobs_lock:
        if job_id:
            job = _jobs.get(job_id)
        else:
            # Cancel the most recent active job
            job = None
            for j in sorted(_jobs.values(), key=lambda x: x["queued_at"], reverse=True):
                if j["status"] in ("running", "queued"):
                    job = j
                    break

    if not job:
        raise HTTPException(status_code=404, detail="No active render job found")

    with _jobs_lock:
        j = _jobs[job["id"]]
        if j["status"] == "queued":
            j["status"] = "cancelled"
            j["completed_at"] = datetime.utcnow().isoformat() + "Z"
            _add_log(j, "[empire_server] Cancelled before start.")
            # Remove from queue
            with _queue_lock:
                if job["id"] in _render_queue:
                    _render_queue.remove(job["id"])
            return {"cancelled": True, "job_id": job["id"], "was": "queued"}

        elif j["status"] == "running":
            j["status"] = "cancelled"  # worker thread checks this flag and kills proc
            pid = j.get("pid")
            if pid:
                try:
                    if sys.platform == "win32":
                        subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                                       capture_output=True, timeout=5)
                    else:
                        os.kill(pid, signal.SIGTERM)
                except Exception:
                    pass
            return {"cancelled": True, "job_id": job["id"], "was": "running", "pid": pid}

        else:
            return {
                "cancelled": False,
                "job_id":    job["id"],
                "status":    j["status"],
                "message":   f"Cannot cancel a {j['status']} job",
            }

# ── Council bot status ────────────────────────────────────────────────────────

@app.get("/api/council/status")
async def council_status():
    """
    Read council bot status files from council/bots/bot_*/.
    Returns what each bot last reported.
    """
    bots = []
    if not COUNCIL_DIR.exists():
        return {"bots": [], "count": 0, "error": f"Council dir not found: {COUNCIL_DIR}"}

    for bot_dir in sorted(COUNCIL_DIR.iterdir()):
        if not bot_dir.is_dir():
            continue
        bot_name = bot_dir.name
        # Try to read status.json or last_run.json
        status_file = bot_dir / "status.json"
        last_run    = bot_dir / "last_run.json"
        info: dict[str, Any] = {"name": bot_name}
        for f in [status_file, last_run]:
            if f.exists():
                try:
                    info.update(json.loads(f.read_text(encoding="utf-8")))
                except Exception:
                    pass
        bots.append(info)

    return {"bots": bots, "count": len(bots), "council_dir": str(COUNCIL_DIR)}

# ── Renders directory listing ─────────────────────────────────────────────────

@app.get("/api/renders/files")
async def list_render_files():
    """List completed MP4 files in renders/."""
    files = []
    if RENDERS_DIR.exists():
        for f in sorted(RENDERS_DIR.glob("*_final.mp4")):
            stat = f.stat()
            files.append({
                "filename":  f.name,
                "path":      str(f),
                "size_mb":   round(stat.st_size / 1_048_576, 1),
                "modified":  datetime.utcfromtimestamp(stat.st_mtime).isoformat() + "Z",
            })
    return {"files": files, "count": len(files)}

# ── Root ──────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "service":    "Empire Video Pipeline Bridge",
        "version":    "1.0.0",
        "port":       PORT,
        "repo_root":  str(REPO_ROOT),
        "auto_render_ok": AUTO_RENDER.exists(),
        "endpoints": {
            "health":         "GET  /empire/health",
            "status":         "GET  /empire/status",
            "event":          "POST /empire/event",
            "episodes":       "GET  /api/episodes",
            "render":         "POST /api/render   body: {episode_id, skip_images?, portrait?}",
            "renders":        "GET  /api/renders",
            "render_status":  "GET  /api/render/status?job_id=xxx",
            "render_logs":    "GET  /api/render/logs?job_id=xxx[&stream=true&offset=N]",
            "render_output":  "GET  /api/render/output?job_id=xxx",
            "cancel":         "POST /api/cancel   body: {job_id?}",
            "council":        "GET  /api/council/status",
            "render_files":   "GET  /api/renders/files",
        },
    }

# ── Main ──────────────────────────────────────────────────────────────────────

_START_TIME = time.time()

if __name__ == "__main__":
    print("=" * 60)
    print("  Empire Video Pipeline Bridge")
    print(f"  Port:       {PORT}")
    print(f"  Repo root:  {REPO_ROOT}")
    print(f"  auto_render.py: {'✓ Found' if AUTO_RENDER.exists() else '✗ MISSING!'}")
    print(f"  Prompts dir:    {'✓ Found' if PROMPTS_DIR.exists() else '✗ MISSING!'}")
    print(f"  Renders dir:    {'✓ Found' if RENDERS_DIR.exists() else '✗ MISSING!'}")
    print("=" * 60)
    if not AUTO_RENDER.exists():
        print(f"\n[WARNING] auto_render.py not found at:")
        print(f"  {AUTO_RENDER}")
        print("  Make sure you run this from the correct repo root.\n")

    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
