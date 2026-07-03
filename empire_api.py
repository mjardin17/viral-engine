#!/usr/bin/env python3
"""
empire_api.py — Empire OS Integration Layer for Viral Engine Pipeline
======================================================================
Wraps the existing pipeline as a REST service.
Does NOT modify auto_render.py or any existing scripts.

Empire OS calls this to:
  POST /render/start          — kick off a render
  GET  /render/status/<id>    — check state + scene progress
  GET  /render/log/<id>       — tail the render log
  POST /render/cancel/<id>    — kill a running render
  GET  /outputs               — list all completed finals
  POST /publish/<id>          — queue episode for CrossPost
  POST /ollama/refine         — refine prompts via local Ollama
  POST /gemini/research       — inject Gemini research into episode
  GET  /health                — alive + pipeline summary

Start: python empire_api.py
       (or double-click empire_api.bat)
Default port: 5757  (override with EMPIRE_API_PORT env var)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.error
from pathlib import Path

from flask import Flask, jsonify, request, abort

# ── Paths (never modify these) ─────────────────────────────────────────────
BASE_DIR      = Path(__file__).resolve().parent
PROMPTS_DIR   = BASE_DIR / "prompts"
OUTPUT_DIR    = BASE_DIR / "output"
RENDERS_DIR   = BASE_DIR / "renders"
MUSIC_PATH    = BASE_DIR / "music" / "battle_epic.mp3"
RUNS_DIR      = BASE_DIR / "empire_runs"
CROSSPOST_DIR = BASE_DIR / "crosspost_queue"

for d in (RUNS_DIR, CROSSPOST_DIR):
    d.mkdir(exist_ok=True)

# ── Ollama config ──────────────────────────────────────────────────────────
OLLAMA_URL   = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3")

# ── Gemini config ──────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_URL     = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

app = Flask(__name__)

# Active render subprocesses: { episode_id: Popen }
_active: dict = {}
_lock = threading.Lock()


# ── Helpers ────────────────────────────────────────────────────────────────

def state_path(ep_id: str) -> Path:
    return RUNS_DIR / f"{ep_id}.json"

def log_path(ep_id: str) -> Path:
    return RUNS_DIR / f"{ep_id}.log"

def write_state(ep_id: str, state: dict) -> None:
    state_path(ep_id).write_text(json.dumps(state, indent=2), encoding="utf-8")

def read_state(ep_id: str) -> dict:
    p = state_path(ep_id)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

def scenes_done(ep_id: str) -> int:
    """Count scene_NN.mp4 > 10 KB — proxy for scenes rendered so far."""
    ep_dir = OUTPUT_DIR / ep_id
    if not ep_dir.exists():
        return 0
    return sum(1 for f in ep_dir.glob("scene_??.mp4") if f.stat().st_size > 10_000)

def final_mp4(ep_id: str) -> Path | None:
    p = RENDERS_DIR / f"{ep_id}_final.mp4"
    return p if p.exists() and p.stat().st_size > 1_000_000 else None

def load_script(ep_id: str) -> dict | None:
    """Find and load the episode JSON from prompts/."""
    for p in PROMPTS_DIR.rglob(f"*{ep_id.lower()}*.json"):
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None

def monitor(ep_id: str, proc: subprocess.Popen) -> None:
    """Background thread: wait for process to exit, update state."""
    proc.wait()
    final = final_mp4(ep_id)
    state = read_state(ep_id)
    state["end_time"] = time.time()
    state["returncode"] = proc.returncode
    if final:
        state["state"]          = "done"
        state["output_path"]    = str(final)
        state["output_size_mb"] = round(final.stat().st_size / 1_000_000, 1)
    else:
        state["state"] = "failed"
    write_state(ep_id, state)
    with _lock:
        _active.pop(ep_id, None)


# ── Routes ─────────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    """Empire OS health check."""
    completed = [
        f.name.replace("_final.mp4", "")
        for f in RENDERS_DIR.glob("*_final.mp4")
        if f.stat().st_size > 1_000_000
    ]
    with _lock:
        active = list(_active.keys())
    return jsonify({
        "status":             "ok",
        "pipeline_dir":       str(BASE_DIR),
        "music_ready":        MUSIC_PATH.exists(),
        "active_renders":     active,
        "completed_episodes": len(completed),
        "ollama_url":         OLLAMA_URL,
        "ollama_model":       OLLAMA_MODEL,
        "gemini_ready":       bool(GEMINI_API_KEY),
        "port":               int(os.environ.get("EMPIRE_API_PORT", 5757)),
    })


@app.route("/render/start", methods=["POST"])
def render_start():
    """
    Start a render.
    Body: { "episode_id": "GG_EP012", "music": true, "skip_images": false }
    """
    body     = request.get_json(silent=True) or {}
    ep_id    = body.get("episode_id", "").strip().upper()
    if not ep_id:
        abort(400, "episode_id is required")

    with _lock:
        if ep_id in _active:
            return jsonify({"status": "already_running", "episode_id": ep_id}), 409

    use_music    = body.get("music", True)
    skip_images  = body.get("skip_images", False)

    cmd = [sys.executable, str(BASE_DIR / "auto_render.py"), "--episode", ep_id]
    if use_music and MUSIC_PATH.exists():
        cmd += ["--music", str(MUSIC_PATH)]
    if skip_images:
        cmd += ["--skip-images"]

    lp = log_path(ep_id)
    lf = open(lp, "w", encoding="utf-8")
    proc = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT, cwd=str(BASE_DIR))

    with _lock:
        _active[ep_id] = proc

    state = {
        "episode_id":  ep_id,
        "state":       "running",
        "start_time":  time.time(),
        "pid":         proc.pid,
        "cmd":         " ".join(cmd),
        "log":         str(lp),
    }
    write_state(ep_id, state)
    threading.Thread(target=monitor, args=(ep_id, proc), daemon=True).start()

    return jsonify({"status": "started", "episode_id": ep_id, "pid": proc.pid})


@app.route("/render/status/<ep_id>")
def render_status(ep_id: str):
    """Live render status with scene progress."""
    ep_id = ep_id.upper()
    state = read_state(ep_id)

    # Episode already done before API started
    if not state:
        f = final_mp4(ep_id)
        if f:
            return jsonify({
                "episode_id":    ep_id,
                "state":         "done",
                "output_path":   str(f),
                "output_size_mb": round(f.stat().st_size / 1_000_000, 1),
            })
        return jsonify({"episode_id": ep_id, "state": "unknown"}), 404

    # Inject live scene count
    state["scenes_done"] = scenes_done(ep_id)

    # Check if process finished since last state write
    with _lock:
        proc = _active.get(ep_id)
    if proc and proc.poll() is not None and state.get("state") == "running":
        state["state"] = "finalizing"

    # Elapsed time
    if "start_time" in state:
        elapsed = time.time() - state["start_time"]
        state["elapsed_sec"] = round(elapsed)

    return jsonify(state)


@app.route("/render/log/<ep_id>")
def render_log(ep_id: str):
    """Last N lines of the render log. ?lines=100"""
    ep_id = ep_id.upper()
    n     = int(request.args.get("lines", 80))
    lp    = log_path(ep_id)
    if not lp.exists():
        return jsonify({"lines": []}), 404
    lines = lp.read_text(encoding="utf-8", errors="replace").splitlines()
    return jsonify({"episode_id": ep_id, "total_lines": len(lines), "lines": lines[-n:]})


@app.route("/render/cancel/<ep_id>", methods=["POST"])
def render_cancel(ep_id: str):
    """Kill a running render."""
    ep_id = ep_id.upper()
    with _lock:
        proc = _active.get(ep_id)
    if not proc:
        return jsonify({"status": "not_running", "episode_id": ep_id}), 404
    proc.terminate()
    state = read_state(ep_id)
    state["state"] = "cancelled"
    state["end_time"] = time.time()
    write_state(ep_id, state)
    return jsonify({"status": "cancelled", "episode_id": ep_id})


@app.route("/outputs")
def list_outputs():
    """All completed finals with paths and sizes."""
    results = []
    for f in sorted(RENDERS_DIR.glob("*_final.mp4")):
        if f.stat().st_size < 1_000_000:
            continue
        ep_id  = f.name.replace("_final.mp4", "")
        script = load_script(ep_id)
        results.append({
            "episode_id":  ep_id,
            "path":        str(f),
            "size_mb":     round(f.stat().st_size / 1_000_000, 1),
            "mtime":       f.stat().st_mtime,
            "title":       script.get("title", ep_id) if script else ep_id,
            "youtube_title": script.get("youtube_title", "") if script else "",
        })
    return jsonify({"count": len(results), "episodes": results})


@app.route("/publish/<ep_id>", methods=["POST"])
def publish(ep_id: str):
    """
    Queue a completed episode for CrossPost.
    Writes a job JSON to crosspost_queue/ for CrossPost agent to pick up.
    Body: { "platforms": ["youtube", "tiktok", "instagram"] }
    """
    ep_id = ep_id.upper()
    f     = final_mp4(ep_id)
    if not f:
        return jsonify({"error": f"{ep_id}_final.mp4 not found or too small"}), 404

    body      = request.get_json(silent=True) or {}
    platforms = body.get("platforms", ["youtube"])
    script    = load_script(ep_id)

    meta = {
        "episode_id":    ep_id,
        "video_path":    str(f),
        "title":         script.get("youtube_title", script.get("title", ep_id)) if script else ep_id,
        "description":   "\n\n".join(filter(None, [
            script.get("tagline", "") if script else "",
            script.get("viral_hook", "") if script else "",
            "\n#GodsAndGlory #History #Documentary #Battle",
        ])),
        "tags":          ["Gods and Glory", "history", "documentary", "battle", ep_id],
        "thumbnail_prompt": script.get("scenes", [{}])[0].get("visual_prompt", "") if script else "",
        "platforms":     platforms,
        "queued_at":     time.time(),
        "status":        "pending",
    }

    job_path = CROSSPOST_DIR / f"{ep_id}_{int(time.time())}.json"
    job_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return jsonify({
        "status":    "queued",
        "episode_id": ep_id,
        "job_file":  str(job_path),
        "platforms": platforms,
        "title":     meta["title"],
    })


@app.route("/crosspost/queue")
def crosspost_queue():
    """List all CrossPost jobs and their status."""
    jobs = []
    for f in sorted(CROSSPOST_DIR.glob("*.json")):
        try:
            job = json.loads(f.read_text(encoding="utf-8"))
            job["job_file"] = f.name
            jobs.append(job)
        except Exception:
            pass
    return jsonify({"count": len(jobs), "jobs": jobs})


# ── Ollama: local prompt refinement ───────────────────────────────────────

def ollama_generate(prompt: str, system: str = "") -> str:
    """Call local Ollama. Returns text or raises on error."""
    payload = {
        "model":  OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    if system:
        payload["system"] = system

    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result.get("response", "").strip()


@app.route("/ollama/refine", methods=["POST"])
def ollama_refine():
    """
    Refine a scene's visual_prompt and/or narration via local Ollama.
    Body: {
      "visual_prompt": "...",
      "narration": "...",
      "scene_type": "battle",
      "episode_title": "Waterloo"
    }
    Returns: { "visual_prompt": "...", "narration": "..." }
    """
    body          = request.get_json(silent=True) or {}
    visual_prompt = body.get("visual_prompt", "")
    narration     = body.get("narration", "")
    scene_type    = body.get("scene_type", "")
    ep_title      = body.get("episode_title", "")

    results = {}

    if visual_prompt:
        vp_prompt = (
            f"You are a cinematographer refining AI image generation prompts for a "
            f"historical documentary series called Gods and Glory. "
            f"Episode: {ep_title}. Scene type: {scene_type}. "
            f"Refine this prompt for maximum cinematic impact and historical accuracy. "
            f"Keep it under 200 characters. Output ONLY the refined prompt, nothing else.\n\n"
            f"Original: {visual_prompt}"
        )
        try:
            results["visual_prompt"] = ollama_generate(vp_prompt)
        except Exception as e:
            results["visual_prompt_error"] = str(e)
            results["visual_prompt"] = visual_prompt  # fallback

    if narration:
        nr_prompt = (
            f"You are a documentary narrator editor for Gods and Glory, a cinematic history channel. "
            f"Tighten this narration: remove filler, increase urgency, keep all facts. "
            f"Target: 80-110 words. Output ONLY the improved narration.\n\n"
            f"Original: {narration}"
        )
        try:
            results["narration"] = ollama_generate(nr_prompt)
        except Exception as e:
            results["narration_error"] = str(e)
            results["narration"] = narration  # fallback

    return jsonify(results)


@app.route("/ollama/status")
def ollama_status():
    """Check if Ollama is reachable and what models are available."""
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        models = [m["name"] for m in data.get("models", [])]
        return jsonify({"status": "online", "models": models, "url": OLLAMA_URL})
    except Exception as e:
        return jsonify({"status": "offline", "error": str(e), "url": OLLAMA_URL}), 503


# ── Gemini: research injection ─────────────────────────────────────────────

@app.route("/gemini/research", methods=["POST"])
def gemini_research():
    """
    Ask Gemini to research an episode topic and return structured facts
    that Empire OS can inject into scene narration.
    Body: { "topic": "Battle of Waterloo 1815", "num_facts": 10 }
    Requires GEMINI_API_KEY env var.
    """
    if not GEMINI_API_KEY:
        return jsonify({"error": "GEMINI_API_KEY not set"}), 503

    body     = request.get_json(silent=True) or {}
    topic    = body.get("topic", "")
    n_facts  = int(body.get("num_facts", 10))

    if not topic:
        abort(400, "topic is required")

    prompt = (
        f"You are a historical researcher for a documentary series. "
        f"Provide {n_facts} compelling, accurate, and verifiable facts about: {topic}. "
        f"Format as a JSON array of objects: "
        f'[{{"fact": "...", "dramatic_hook": "...", "source_era": "..."}}]. '
        f"Prioritize lesser-known facts that would surprise a general audience. "
        f"Output ONLY valid JSON, no markdown."
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 2048},
    }
    url  = f"{GEMINI_URL}?key={GEMINI_API_KEY}"
    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        text = result["candidates"][0]["content"]["parts"][0]["text"]
        # Strip markdown fences if present
        text = text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        facts = json.loads(text)
        return jsonify({"topic": topic, "facts": facts, "count": len(facts)})
    except Exception as e:
        return jsonify({"error": str(e), "topic": topic}), 500


@app.route("/gemini/enrich_episode", methods=["POST"])
def gemini_enrich():
    """
    Load an episode JSON and have Gemini verify/enrich each scene's narration.
    Body: { "episode_id": "GG_EP014", "dry_run": true }
    Returns enriched scenes without modifying files unless dry_run=false.
    """
    if not GEMINI_API_KEY:
        return jsonify({"error": "GEMINI_API_KEY not set"}), 503

    body    = request.get_json(silent=True) or {}
    ep_id   = body.get("episode_id", "").upper()
    dry_run = body.get("dry_run", True)

    script = load_script(ep_id)
    if not script:
        return jsonify({"error": f"Script not found for {ep_id}"}), 404

    title   = script.get("title", ep_id)
    scenes  = script.get("scenes", [])
    enriched = []

    for scene in scenes[:3]:  # limit to first 3 in dry_run to save API calls
        prompt = (
            f"Documentary: '{title}'. Scene {scene['scene_number']}: {scene['title']}.\n"
            f"Current narration: {scene['narration']}\n\n"
            f"Check for factual accuracy and dramatic impact. "
            f"Return JSON: {{\"verified\": true/false, \"corrections\": \"...\", "
            f"\"improved_narration\": \"...\"}}"
        )
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        url  = f"{GEMINI_URL}?key={GEMINI_API_KEY}"
        data = json.dumps(payload).encode("utf-8")
        req  = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            text = text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            enriched.append({
                "scene_number": scene["scene_number"],
                "title": scene["title"],
                "gemini_review": json.loads(text),
            })
        except Exception as e:
            enriched.append({"scene_number": scene["scene_number"], "error": str(e)})

    return jsonify({
        "episode_id":    ep_id,
        "title":         title,
        "dry_run":       dry_run,
        "scenes_checked": len(enriched),
        "results":       enriched,
    })


# ── Entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("EMPIRE_API_PORT", 5757))
    print(f"\n{'='*60}")
    print(f"  EMPIRE OS — Viral Engine API")
    print(f"  http://localhost:{port}")
    print(f"  Pipeline: {BASE_DIR}")
    print(f"  Music:    {'READY' if MUSIC_PATH.exists() else 'MISSING'}")
    print(f"  Ollama:   {OLLAMA_URL}  model={OLLAMA_MODEL}")
    print(f"  Gemini:   {'READY' if GEMINI_API_KEY else 'NO KEY (set GEMINI_API_KEY)'}")
    print(f"{'='*60}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
