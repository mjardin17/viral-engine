#!/usr/bin/env python3
"""
render_orchestrator.py — Parallel episode render orchestrator for Viral Engine / Empire OS.

MISSION m004 (GEMINI_MISSION.md) · GAME_PLAN.md → Tooling #7.

Wraps `auto_render.py` in a bounded worker pool so several episodes render at the
same time. This module NEVER modifies auto_render.py — it only launches it as a
subprocess and watches its output.

What it does
------------
  * Accepts a list of episodes (and/or a season+channel, and/or the pending
    render missions in MISSION_BOARD.json) plus a worker count.
  * Launches up to N simultaneous `auto_render.py --episode <ID>` subprocesses
    (subprocess.Popen, non-blocking).
  * Each worker pulls the next episode off the queue the moment it finishes.
  * Prints live status: which worker is on which episode, % done, elapsed, ETA.
  * On success: appends the job to render_log.json with output path, file size
    (bytes + MB), duration and UTC timestamp.
  * On failure: logs the error (return code + tail of the child's output),
    skips that episode, and keeps the other workers running.
  * When everything finishes: prints a passed / failed / skipped summary.

Interface
---------
    python render_orchestrator.py --episodes GG_EP012,GG_EP013,GG_EP014 --workers 2
    python render_orchestrator.py --season 3 --channel gg --workers 3
    python render_orchestrator.py --pending           # reads MISSION_BOARD.json
    python render_orchestrator.py --season 3 --channel gg --dry-run
    python render_orchestrator.py --self-test         # no API keys / ffmpeg needed

Rules honored
-------------
  * Never more than 3 concurrent workers (RAM limit — higher values are clamped).
  * subprocess.Popen (non-blocking), not subprocess.run.
  * auto_render.py is treated as read-only.
  * Typed, modular, documented. Runs on Python 3.9+ (developed against 3.11/3.14).
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import re
import signal
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Sequence, Tuple

# ── Config ────────────────────────────────────────────────────────────────────

VERSION = "1.0.0"

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_RENDER_SCRIPT = BASE_DIR / "auto_render.py"
DEFAULT_LOG_FILE = BASE_DIR / "render_log.json"
DEFAULT_MISSION_BOARD = BASE_DIR / "MISSION_BOARD.json"
DEFAULT_LOG_DIR = BASE_DIR / "render_logs"
PROMPTS_DIR = BASE_DIR / "prompts"
RENDERS_DIR = BASE_DIR / "renders"

MAX_WORKERS = 3                 # hard RAM ceiling from GEMINI_MISSION.md
DEFAULT_WORKERS = 2
STATUS_INTERVAL_SEC = 20.0      # how often the live status thread prints
TAIL_LINES = 40                 # lines of child output kept for error reporting
DEFAULT_RETRIES = 1             # extra attempt(s) after a non-zero exit

CHANNEL_PREFIXES: Tuple[str, ...] = ("GG", "ML", "LO", "EO", "IL")

# Season → (first episode, last episode) per channel. Used by --season/--channel.
# Anything not listed falls back to --from-ep/--to-ep or a full-channel scan.
SEASON_RANGES: Dict[str, Dict[int, Tuple[int, int]]] = {
    "GG": {1: (1, 5), 2: (6, 11), 3: (12, 25)},
    "ML": {1: (1, 12), 2: (13, 23)},
    "LO": {1: (1, 20), 2: (21, 40)},
    "IL": {1: (1, 99)},
    "EO": {1: (1, 99)},
}

# Progress lines emitted by auto_render.py, e.g. "── Scene 08/24  [The Trap] ──"
_SCENE_RE = re.compile(r"scene\s+(\d+)\s*/\s*(\d+)", re.IGNORECASE)
_DONE_RE = re.compile(r"✓\s*DONE", re.IGNORECASE)
_FATAL_RE = re.compile(r"\bFATAL\b|\bERROR\b|\bTraceback\b", re.IGNORECASE)

# Episode id patterns: GG_EP012, gg_ep012, scene_prompts.gg_ep012.final,
# GG_EP001_thermopylae. The trailing lookahead (not \b) matters: an id is often
# followed by a slug ("GG_EP001_thermopylae"), and "_" is a word character, so a
# \b there would make every Season 1 episode invisible to discovery.
_EP_IN_NAME_RE = re.compile(
    r"(?<![A-Za-z0-9])(GG|ML|LO|EO|IL)[_-]?EP[_-]?(\d{1,4})(?!\d)", re.IGNORECASE
)
_EP_BARE_RE = re.compile(r"^\s*(?:EP[_-]?)?(\d{1,4})\s*$", re.IGNORECASE)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ── Episode discovery ────────────────────────────────────────────────────────

def normalize_episode_id(raw: str, channel: Optional[str] = None) -> str:
    """Normalize user input into a canonical episode id such as ``GG_EP012``.

    Accepts ``gg_ep012``, ``GG_EP012``, ``EP012`` or ``12`` when ``channel`` is
    supplied, and ``scene_prompts.gg_ep012.final.json``.
    """
    token = raw.strip().strip('"').strip("'")
    if not token:
        raise ValueError("empty episode id")

    # A filename or any string containing the full id.
    match = _EP_IN_NAME_RE.search(token)
    if match:
        return f"{match.group(1).upper()}_EP{int(match.group(2)):03d}"

    bare = _EP_BARE_RE.match(token)
    if bare:
        if not channel:
            raise ValueError(
                f"'{raw}' is not a full episode id — pass --channel (e.g. --channel gg) "
                f"or use the full form GG_EP012"
            )
        return f"{channel.upper()}_EP{int(bare.group(1)):03d}"

    raise ValueError(
        f"could not parse episode id from '{raw}' "
        f"(expected something like GG_EP012, or 12 with --channel gg)"
    )


def _load_episode_finder():
    """Return auto_render.find_episode_json if importable, else None.

    Importing auto_render only executes module-level config (paths, env load);
    it performs no network I/O. If anything goes wrong we fall back to our own
    equivalent implementation rather than breaking the orchestrator.
    """
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "_ve_auto_render", str(DEFAULT_RENDER_SCRIPT)
        )
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        return getattr(module, "find_episode_json", None)
    except Exception:
        return None


def _fallback_find_episode_json(episode_id: str) -> Path:
    """Mirror of auto_render.find_episode_json (used when the import fails)."""
    eid_low = episode_id.lower()
    candidates = [
        p for p in PROMPTS_DIR.rglob("*.json")
        if not any(part.startswith("_") for part in p.relative_to(PROMPTS_DIR).parts[:-1])
    ]

    def _prefer_final(p: Path) -> Tuple[int, str]:
        name = p.stem.lower()
        is_final = "final" in name
        is_captions = "captions" in name or "source" in name
        return (0 if is_final else 2 if is_captions else 1, str(p))

    for p in sorted(candidates, key=_prefer_final):
        if p.stem.lower() == eid_low:
            return p
    for p in sorted(candidates, key=_prefer_final):
        if eid_low in p.stem.lower():
            return p
    raise FileNotFoundError(f"No episode JSON found for '{episode_id}' in {PROMPTS_DIR}")


def find_episode_json(episode_id: str) -> Path:
    """Locate the script JSON for an episode (delegates to auto_render when possible)."""
    finder = _load_episode_finder()
    if finder is not None:
        try:
            return Path(finder(episode_id))
        except FileNotFoundError:
            raise
        except Exception:
            pass
    return _fallback_find_episode_json(episode_id)


def discover_episodes(channel: Optional[str] = None) -> List[str]:
    """Scan ``prompts/`` for every episode id that has a script JSON.

    Returns canonical ids sorted by channel then episode number.
    """
    found: Dict[str, str] = {}
    for path in PROMPTS_DIR.rglob("*.json"):
        rel_parts = path.relative_to(PROMPTS_DIR).parts[:-1]
        if any(part.startswith("_") for part in rel_parts):   # _backups, __pycache__
            continue
        if "captions" in path.stem.lower() or "source" in path.stem.lower():
            continue
        match = _EP_IN_NAME_RE.search(path.stem) or _EP_IN_NAME_RE.search(path.name)
        if not match:
            continue
        channel_id = match.group(1).upper()
        if channel and channel_id != channel.upper():
            continue
        found[f"{channel_id}_EP{int(match.group(2)):03d}"] = str(path)
    return sorted(found, key=lambda e: (CHANNEL_PREFIXES.index(e.split("_")[0])
                                        if e.split("_")[0] in CHANNEL_PREFIXES else 99,
                                        e))


def episode_number(episode_id: str) -> int:
    match = re.search(r"EP(\d{1,4})", episode_id, re.IGNORECASE)
    return int(match.group(1)) if match else -1


def episodes_for_season(channel: str, season: int) -> List[str]:
    """Episode ids belonging to ``season`` for ``channel`` that have scripts on disk."""
    channel = channel.upper()
    available = discover_episodes(channel)
    season_range = SEASON_RANGES.get(channel, {}).get(season)
    if season_range is None:
        # No mapping for this season — return everything we can see and let the
        # caller filter with --from-ep/--to-ep if it wants to.
        return available
    lo, hi = season_range
    return [e for e in available if lo <= episode_number(e) <= hi]


def episodes_from_mission_board(board_path: Path) -> List[str]:
    """Episode ids from render missions that are not finished.

    A mission qualifies when its type is ``render`` (or it carries a ``render``
    target/channel) and its status is not already complete/cancelled.
    """
    if not board_path.exists():
        raise FileNotFoundError(f"MISSION_BOARD.json not found at {board_path}")

    with open(board_path, encoding="utf-8") as fh:
        board = json.load(fh)

    missions = board.get("missions", []) if isinstance(board, dict) else list(board)
    done_statuses = {"complete", "completed", "done", "cancelled", "canceled", "failed"}
    episodes: List[str] = []

    for mission in missions:
        if not isinstance(mission, dict):
            continue
        mtype = str(mission.get("type", "")).lower()
        status = str(mission.get("status", "")).lower().replace(" ", "_")
        if mtype != "render" or status in done_statuses:
            continue
        raw_targets: List[str] = []
        for key in ("target", "episode", "episode_id"):
            value = mission.get(key)
            if isinstance(value, str):
                raw_targets.append(value)
            elif isinstance(value, list):
                raw_targets.extend(str(v) for v in value)
        for key in ("episodes", "targets"):
            value = mission.get(key)
            if isinstance(value, list):
                raw_targets.extend(str(v) for v in value)
        channel = mission.get("channel")
        channel = channel if isinstance(channel, str) else None
        for raw in raw_targets:
            try:
                episodes.append(normalize_episode_id(raw, channel))
            except ValueError:
                continue

    # Preserve order, drop duplicates.
    seen: set = set()
    unique: List[str] = []
    for ep in episodes:
        if ep not in seen:
            seen.add(ep)
            unique.append(ep)
    return unique


def count_scenes(script_path: Path) -> int:
    """Number of scenes in an episode JSON (0 if unreadable)."""
    try:
        with open(script_path, encoding="utf-8") as fh:
            data = json.load(fh)
        scenes = data.get("scenes", []) if isinstance(data, dict) else []
        return len(scenes) if isinstance(scenes, list) else 0
    except Exception:
        return 0


def final_output_path(episode_id: str, output_dir: Optional[Path] = None) -> Path:
    """Path auto_render.py writes for this episode (<renders>/<EP_ID>_final.mp4)."""
    return Path(output_dir or RENDERS_DIR) / f"{episode_id}_final.mp4"


# ── Job model ────────────────────────────────────────────────────────────────

ACTIVE_STATUSES = ("running", "queued")
TERMINAL_STATUSES = ("passed", "failed", "skipped", "interrupted")


@dataclass
class RenderJob:
    """A single episode render tracked by the orchestrator."""

    episode_id: str
    script: str = ""
    channel: str = ""
    total_scenes: int = 0
    status: str = "queued"
    worker: Optional[int] = None
    attempts: int = 0
    scenes_done: int = 0
    started_at: str = ""
    finished_at: str = ""
    elapsed_sec: float = 0.0
    return_code: Optional[int] = None
    output: str = ""
    size_bytes: int = 0
    error: str = ""
    log: str = ""

    # ── derived ──────────────────────────────────────────────────────────────
    @property
    def size_mb(self) -> float:
        return round(self.size_bytes / (1024 * 1024), 2) if self.size_bytes else 0.0

    @property
    def progress(self) -> float:
        """0.0–1.0 scene progress (0 if the scene count is unknown)."""
        if self.total_scenes <= 0 or self.scenes_done <= 0:
            return 0.0
        return min(1.0, self.scenes_done / float(self.total_scenes))

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "episode_id": self.episode_id,
            "channel": self.channel,
            "script": self.script,
            "total_scenes": self.total_scenes,
            "status": self.status,
            "worker": self.worker,
            "attempts": self.attempts,
            "scenes_done": self.scenes_done,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "elapsed_sec": round(self.elapsed_sec, 1),
            "return_code": self.return_code,
            "output": self.output,
            "size_bytes": self.size_bytes,
            "size_mb": self.size_mb,
            "error": self.error,
            "log": self.log,
        }
        return data


# ── Persistent render log ────────────────────────────────────────────────────

class RenderLog:
    """Thread-safe append/update log persisted to render_log.json.

    Layout::

        {
          "version": "1.0.0",
          "updated_at": "<iso>",
          "jobs":  { "GG_EP012": {...latest job record...}, ... },
          "runs":  [ {run_id, started_at, finished_at, workers, summary, jobs:[...]} ]
        }
    """

    MAX_RUNS = 50

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self.data: Dict[str, Any] = {"version": VERSION, "updated_at": "", "jobs": {}, "runs": []}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            with open(self.path, encoding="utf-8") as fh:
                loaded = json.load(fh)
            if isinstance(loaded, dict):
                self.data = {
                    "version": loaded.get("version", VERSION),
                    "updated_at": loaded.get("updated_at", ""),
                    "jobs": loaded.get("jobs", {}) or {},
                    "runs": loaded.get("runs", []) or [],
                }
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[WARN] render_log.json is unreadable ({exc}); starting a fresh log.",
                  file=sys.stderr)

    def save(self) -> None:
        """Atomic write (temp file + os.replace) so a crash can't corrupt the log."""
        with self._lock:
            self.data["updated_at"] = _utc_now_iso()
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self.data, fh, indent=2)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self.path)

    def record(self, job: RenderJob) -> None:
        """Upsert the latest record for an episode."""
        with self._lock:
            self.data.setdefault("jobs", {})[job.episode_id] = job.to_dict()

    def record_run(self, run: Dict[str, Any]) -> None:
        with self._lock:
            runs = self.data.setdefault("runs", [])
            runs.append(run)
            if len(runs) > self.MAX_RUNS:
                del runs[: len(runs) - self.MAX_RUNS]

    def completed_episodes(self) -> set:
        return {ep for ep, rec in self.data.get("jobs", {}).items()
                if rec.get("status") == "passed"}


# ── Progress parsing ─────────────────────────────────────────────────────────

def parse_progress(line: str) -> Optional[Tuple[int, int]]:
    """Extract ``(scenes_done, scenes_total)`` from a line of child output."""
    match = _SCENE_RE.search(line)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None


# ── Orchestrator ─────────────────────────────────────────────────────────────

@dataclass
class OrchestratorConfig:
    """Everything the worker pool needs to launch renders."""

    render_script: Path = DEFAULT_RENDER_SCRIPT
    python: str = sys.executable
    workers: int = DEFAULT_WORKERS
    retries: int = DEFAULT_RETRIES
    log_file: Path = DEFAULT_LOG_FILE
    log_dir: Path = DEFAULT_LOG_DIR
    extra_args: List[str] = field(default_factory=list)
    output_dir: Path = RENDERS_DIR
    extra_env: Dict[str, str] = field(default_factory=dict)
    validate_scripts: bool = True
    status_interval: float = STATUS_INTERVAL_SEC
    quiet: bool = False
    skip_completed: bool = False
    skip_existing: bool = False


class RenderOrchestrator:
    """Bounded worker pool that renders episodes in parallel."""

    def __init__(self, config: OrchestratorConfig) -> None:
        self.cfg = config
        self.log = RenderLog(config.log_file)
        self.jobs: List[RenderJob] = []
        self.skipped_jobs: List[RenderJob] = []
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._start_wall = 0.0

    # ── queue building ───────────────────────────────────────────────────────
    def build_jobs(self, episodes: Sequence[str]) -> List[RenderJob]:
        """Resolve episode ids into jobs, skipping anything already done."""
        jobs: List[RenderJob] = []
        self.skipped_jobs = []
        completed = self.log.completed_episodes() if self.cfg.skip_completed else set()

        for raw in episodes:
            episode_id = normalize_episode_id(raw)
            if episode_id in completed:
                print(f"  - {episode_id:<12} SKIP  (already passed in {self.cfg.log_file.name})")
                continue

            job = RenderJob(episode_id=episode_id, channel=episode_id.split("_")[0])
            try:
                script = find_episode_json(episode_id)
                job.script = str(script)
                job.total_scenes = count_scenes(script)
            except FileNotFoundError as exc:
                if self.cfg.validate_scripts:
                    job.status = "skipped"
                    job.finished_at = _utc_now_iso()
                    job.error = str(exc)
                    print(f"  - {episode_id:<12} SKIP  (no script JSON found)")
                    self.skipped_jobs.append(job)
                    self.log.record(job)
                    continue
                job.script = ""
            jobs.append(job)
        return jobs

    # ── execution ────────────────────────────────────────────────────────────
    def run(self, episodes: Sequence[str]) -> Dict[str, Any]:
        """Render every episode with at most ``workers`` concurrent children."""
        self._start_wall = time.time()
        renderable = self.build_jobs(episodes)
        # Skipped episodes stay in self.jobs so they show up in the summary.
        self.jobs = renderable + list(self.skipped_jobs)

        pending: "queue.Queue[RenderJob]" = queue.Queue()
        for job in renderable:
            pending.put(job)

        if not renderable:
            print("Nothing to render — queue is empty.")
            return self._summary([])

        workers = max(1, min(self.cfg.workers, MAX_WORKERS, len(self.jobs)))
        if self.cfg.workers > MAX_WORKERS:
            print(f"[WARN] --workers {self.cfg.workers} exceeds the hard limit "
                  f"({MAX_WORKERS}); clamping to {MAX_WORKERS}.")

        self.cfg.log_dir.mkdir(parents=True, exist_ok=True)
        print(f"\nRendering {len(self.jobs)} episode(s) with {workers} worker(s) — "
              f"{self.cfg.render_script.name}")
        print(f"Log: {self.cfg.log_file}   Child logs: {self.cfg.log_dir}\n")

        completed: List[RenderJob] = []
        completer = threading.Thread(
            target=self._status_loop, args=(completed, len(self.jobs)), daemon=True
        )
        completer.start()

        threads: List[threading.Thread] = []
        for worker_id in range(1, workers + 1):
            thread = threading.Thread(
                target=self._worker, args=(worker_id, pending, completed),
                name=f"worker-{worker_id}", daemon=True,
            )
            thread.start()
            threads.append(thread)

        try:
            for thread in threads:
                thread.join()
        except KeyboardInterrupt:
            print("\n[!] Ctrl-C received — stopping workers (children will be terminated)...")
            self._stop.set()
            for thread in threads:
                thread.join(timeout=30)

        self._stop.set()
        completer.join(timeout=2)
        self.log.save()
        return self._summary(completed)

    def _worker(self, worker_id: int, pending: "queue.Queue[RenderJob]",
                completed: List[RenderJob]) -> None:
        while not self._stop.is_set():
            try:
                job = pending.get_nowait()
            except queue.Empty:
                return
            try:
                self._run_job(worker_id, job)
            finally:
                with self._lock:
                    completed.append(job)
                self.log.record(job)
                self.log.save()
                pending.task_done()

    def _run_job(self, worker_id: int, job: RenderJob) -> None:
        """Render one episode (with retries). Never raises."""
        job.worker = worker_id
        job.status = "running"
        job.started_at = _utc_now_iso()

        attempts_allowed = max(0, self.cfg.retries) + 1
        last_error = ""

        for attempt in range(1, attempts_allowed + 1):
            if self._stop.is_set():
                job.status = "interrupted"
                job.error = "orchestrator stopped before this episode finished"
                job.finished_at = _utc_now_iso()
                return

            job.attempts = attempt
            job.scenes_done = 0
            job.return_code = None

            cmd = [self.cfg.python, str(self.cfg.render_script), "--episode", job.episode_id]
            cmd += list(self.cfg.extra_args)

            child_log = self.cfg.log_dir / f"{job.episode_id}.attempt{attempt}.log"
            job.log = str(child_log)

            started = time.time()
            tail: Deque[str] = deque(maxlen=TAIL_LINES)
            try:
                env = os.environ.copy()
                env.setdefault("PYTHONUNBUFFERED", "1")
                env.update(self.cfg.extra_env)
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(BASE_DIR),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    errors="replace",
                    bufsize=1,
                    env=env,
                )
            except OSError as exc:
                job.status = "failed"
                job.error = f"could not launch {self.cfg.render_script.name}: {exc}"
                job.finished_at = _utc_now_iso()
                return

            assert proc.stdout is not None
            try:
                with open(child_log, "w", encoding="utf-8") as log_fh:
                    for line in proc.stdout:
                        if self._stop.is_set():
                            _terminate(proc)
                            break
                        log_fh.write(line)
                        log_fh.flush()
                        tail.append(line.rstrip("\n"))
                        progress = parse_progress(line)
                        if progress:
                            done, total = progress
                            job.scenes_done = max(job.scenes_done, done)
                            if total and job.total_scenes != total:
                                job.total_scenes = total
                        if not self.cfg.quiet and _FATAL_RE.search(line):
                            print(f"   [W{worker_id}] {job.episode_id}: {line.strip()[:160]}")
            finally:
                # Always release the pipe (and reap the child) so long runs with
                # many episodes don't leak file descriptors.
                try:
                    proc.stdout.close()
                except Exception:
                    pass

            if self._stop.is_set():
                _terminate(proc)
                job.status = "interrupted"
                job.error = "interrupted by operator (Ctrl-C)"
                job.finished_at = _utc_now_iso()
                job.elapsed_sec = time.time() - started
                return

            return_code = proc.wait()
            job.return_code = return_code
            job.elapsed_sec = time.time() - started

            if return_code == 0:
                out = final_output_path(job.episode_id, self.cfg.output_dir)
                if out.exists():
                    job.output = str(out)
                    job.size_bytes = out.stat().st_size
                    job.status = "passed"
                    job.error = ""
                    job.finished_at = _utc_now_iso()
                    print(f"   [W{worker_id}] ✓ {job.episode_id} PASSED  "
                          f"({job.size_mb} MB, {_fmt_hms(job.elapsed_sec)})")
                    return
                last_error = (f"auto_render.py exited 0 but {out.name} is missing — "
                              f"refusing to report success")
            else:
                last_error = f"exit code {return_code}"
                detail = next((ln for ln in reversed(list(tail)) if ln.strip()), "")
                if detail:
                    last_error += f" — last output: {detail.strip()[:200]}"
                if _DONE_RE.search("\n".join(tail)) and return_code != 0:
                    last_error += " (child printed DONE but exited non-zero)"

            print(f"   [W{worker_id}] ✗ {job.episode_id} attempt {attempt}/"
                  f"{attempts_allowed} failed: {last_error}")

        job.status = "failed"
        job.error = last_error
        job.finished_at = _utc_now_iso()

    # ── live status ──────────────────────────────────────────────────────────
    def _status_loop(self, completed: List[RenderJob], total: int) -> None:
        interval = max(2.0, self.cfg.status_interval)
        while not self._stop.is_set():
            time.sleep(interval)
            if self._stop.is_set():
                return
            with self._lock:
                done = len(completed)
            if done >= total:
                return
            self.print_status(completed, total)

    def print_status(self, completed: List[RenderJob], total: int) -> None:
        """Print one live status snapshot (worker → episode, %, elapsed, ETA)."""
        stamp = datetime.now().strftime("%H:%M:%S")
        running = [j for j in self.jobs if j.status == "running"]
        done_n = len(completed)
        failed_n = sum(1 for j in self.jobs if j.status == "failed")
        skipped_n = sum(1 for j in self.jobs if j.status == "skipped")

        print(f"\n── status {stamp} ──────────────────────────────────────────")
        if not running:
            print("   (no worker active)")
        for job in running:
            pct = job.progress * 100
            bar = _bar(job.progress)
            print(f"   W{job.worker}  {job.episode_id:<12} {bar} {pct:5.1f}%  "
                  f"{job.scenes_done}/{job.total_scenes or '?'} scenes  "
                  f"el {_fmt_hms(job.elapsed_sec)}  eta {self._eta_job(job)}")
        queued = [j.episode_id for j in self.jobs if j.status == "queued"]
        if queued:
            print(f"   queued ({len(queued)}): {', '.join(queued[:8])}"
                  f"{' …' if len(queued) > 8 else ''}")
        print(f"   done {done_n}/{total}   failed {failed_n}   skipped {skipped_n}   "
              f"run eta {self._eta_run()}")
        print("─" * 56)
        sys.stdout.flush()

    def _eta_job(self, job: RenderJob) -> str:
        """ETA for a single in-flight job, from scene progress."""
        progress = job.progress
        if progress <= 0.02 or job.elapsed_sec <= 0:
            return "—"
        remaining = job.elapsed_sec * (1.0 - progress) / progress
        return _fmt_hms(remaining)

    def _eta_run(self) -> str:
        """ETA for the whole run: slowest worker + remaining queue / workers."""
        finished = [j for j in self.jobs if j.is_terminal and j.status == "passed"]
        running = [j for j in self.jobs if j.status == "running"]
        queued = [j for j in self.jobs if j.status == "queued"]

        avg = (sum(j.elapsed_sec for j in finished) / len(finished)) if finished else 0.0
        estimates: List[float] = []
        for job in running:
            progress = job.progress
            if progress > 0.02 and job.elapsed_sec > 0:
                estimates.append(job.elapsed_sec * (1.0 - progress) / progress)
            elif avg:
                estimates.append(max(0.0, avg - job.elapsed_sec))
        if queued and avg:
            workers = max(1, len(running) or self.cfg.workers)
            estimates.append(len(queued) * avg / workers)
        elif queued:
            return "—"
        if not estimates:
            return "—"
        return _fmt_hms(max(estimates))

    # ── summary ──────────────────────────────────────────────────────────────
    def _summary(self, completed: Sequence[RenderJob]) -> Dict[str, Any]:
        passed = [j for j in self.jobs if j.status == "passed"]
        failed = [j for j in self.jobs if j.status == "failed"]
        skipped = [j for j in self.jobs if j.status == "skipped"]
        interrupted = [j for j in self.jobs if j.status == "interrupted"]

        print(f"\n{'=' * 60}")
        print("  RENDER ORCHESTRATOR — SUMMARY")
        print(f"{'=' * 60}")
        rows = list(passed) + list(failed) + list(interrupted) + list(skipped)
        if rows:
            print(f"  {'EPISODE':<12} {'STATUS':<12} {'SIZE':>10} {'TIME':>10}  {'ATT':>3}")
            for job in rows:
                print(f"  {job.episode_id:<12} {job.status:<12} "
                      f"{(f'{job.size_mb} MB' if job.status == 'passed' else '-'):>10} "
                      f"{_fmt_hms(job.elapsed_sec):>10}  {job.attempts:>3}")
                if job.error:
                    print(f"      ↳ {job.error[:150]}")
        else:
            print("  (no episodes processed)")

        total_bytes = sum(j.size_bytes for j in passed)
        print(f"\n  passed {len(passed)}   failed {len(failed)}   "
              f"skipped {len(skipped)}   interrupted {len(interrupted)}")
        print(f"  total output: {total_bytes / (1024 * 1024):,.1f} MB   "
              f"wall clock: {_fmt_hms(time.time() - self._start_wall) if self._start_wall else '—'}")
        print(f"  log: {self.cfg.log_file}")
        print(f"{'=' * 60}\n")

        summary = {
            "finished_at": _utc_now_iso(),
            "passed": len(passed),
            "failed": len(failed),
            "skipped": len(skipped),
            "interrupted": len(interrupted),
            "total_bytes": total_bytes,
            "wall_clock_sec": round(time.time() - self._start_wall, 1) if self._start_wall else 0.0,
            "episodes": {
                "passed": [j.episode_id for j in passed],
                "failed": [j.episode_id for j in failed],
                "skipped": [j.episode_id for j in skipped],
                "interrupted": [j.episode_id for j in interrupted],
            },
        }
        self.log.record_run({
            "run_id": datetime.now().strftime("%Y%m%dT%H%M%S"),
            "started_at": datetime.fromtimestamp(self._start_wall, timezone.utc).isoformat(
                timespec="seconds") if self._start_wall else "",
            "workers": self.cfg.workers,
            "jobs": [j.to_dict() for j in self.jobs],
            "summary": summary,
        })
        self.log.save()
        return summary


# ── helpers ──────────────────────────────────────────────────────────────────

def _fmt_hms(seconds: float) -> str:
    seconds = max(0.0, float(seconds or 0.0))
    hours, rem = divmod(int(seconds), 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours:d}h{minutes:02d}m"
    return f"{minutes:02d}m{secs:02d}s"


def _bar(progress: float, width: int = 18) -> str:
    filled = int(round(min(1.0, max(0.0, progress)) * width))
    return "[" + "#" * filled + "." * (width - filled) + "]"


def _terminate(proc: subprocess.Popen) -> None:
    """Best-effort child shutdown (terminate, then kill after a grace period)."""
    if proc.poll() is not None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=15)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


# ── self-test ────────────────────────────────────────────────────────────────

FAKE_RENDER_SCRIPT = '''#!/usr/bin/env python3
"""Fake renderer used by `render_orchestrator.py --self-test`.

Prints the same progress lines auto_render.py prints, so the orchestrator's
parser, worker pool, logging and summary can be verified without ffmpeg,
network access or API keys.
"""
import argparse, os, sys, time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--episode", required=True)
args = parser.parse_args()

ep = args.episode.upper()
SCENES = 5
SECONDS_PER_SCENE = 0.15
OUTPUT_DIR = Path(os.environ.get("VE_FAKE_OUTPUT_DIR", "renders"))

print(f"  VIRAL ENGINE (self-test) — {ep}", flush=True)
for num in range(1, SCENES + 1):
    print(f"\\n── Scene {num:02d}/{SCENES}  [fake scene] ──", flush=True)
    time.sleep(SECONDS_PER_SCENE)

# Episode 9 is the deliberate failure case exercised by the self-test.
if ep.endswith("009"):
    print("FATAL: simulated render failure", flush=True)
    sys.exit(3)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / f"{ep}_final.mp4").write_bytes(b"FAKE-MP4" * 4096)   # ~32 KB stand-in

print(f"  ✓ DONE!  {ep}  ({SCENES}/{SCENES} scenes)", flush=True)
'''


def run_self_test(workers: int = 3, verbose: bool = True) -> int:
    """Exercise the pool end-to-end with a fake renderer. Returns process exit code."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="ve_orchestrator_selftest_"))
    script = tmp_dir / "fake_render.py"
    script.write_text(FAKE_RENDER_SCRIPT, encoding="utf-8")

    renders = tmp_dir / "renders"
    cfg = OrchestratorConfig(
        render_script=script,
        python=sys.executable,
        workers=workers,
        retries=1,
        log_file=tmp_dir / "render_log.json",
        log_dir=tmp_dir / "logs",
        output_dir=renders,
        extra_env={"VE_FAKE_OUTPUT_DIR": str(renders)},
        validate_scripts=False,
        status_interval=1.0,
    )
    orch = RenderOrchestrator(cfg)

    episodes = ["GG_EP001", "GG_EP002", "GG_EP009", "GG_EP003"]  # EP009 = deliberate failure
    if verbose:
        print(f"Self-test: {len(episodes)} fake episodes, {workers} workers, "
              f"1 deliberate failure, 1 retry\n")
    summary = orch.run(episodes)

    checks: List[Tuple[str, bool]] = [
        ("4 jobs dispatched", len(orch.jobs) == 4),
        ("3 passed", summary["passed"] == 3),
        ("1 failed", summary["failed"] == 1),
        ("none skipped", summary["skipped"] == 0),
        ("failure is the deliberate one", summary["episodes"]["failed"] == ["GG_EP009"]),
        ("retry was attempted", sum(j.attempts for j in orch.jobs if j.episode_id == "GG_EP009") == 2),
        ("log file written", cfg.log_file.exists()),
        ("per-episode child log written", (cfg.log_dir / "GG_EP001.attempt1.log").exists()),
        ("no more than 3 workers", cfg.workers <= MAX_WORKERS),
    ]

    log_data = json.loads(cfg.log_file.read_text(encoding="utf-8"))
    records = log_data.get("jobs", {})
    checks.append(("every episode recorded in render_log.json",
                   set(records) == {"GG_EP001", "GG_EP002", "GG_EP003", "GG_EP009"}))
    checks.append(("passed record is complete",
                   bool(records.get("GG_EP001", {}).get("started_at"))
                   and records.get("GG_EP001", {}).get("status") == "passed"))
    checks.append(("failed record captured an error",
                   bool(records.get("GG_EP009", {}).get("error"))))
    checks.append(("passed record captured output path + size",
                   records.get("GG_EP001", {}).get("size_bytes", 0) > 0
                   and records.get("GG_EP001", {}).get("output", "").endswith("_final.mp4")))
    checks.append(("scene progress was parsed",
                   records.get("GG_EP001", {}).get("scenes_done") == 5
                   and records.get("GG_EP001", {}).get("total_scenes") == 5))

    print("── self-test checks " + "─" * 40)
    ok = True
    for name, passed in checks:
        print(f"  {'PASS' if passed else 'FAIL'}  {name}")
        ok = ok and passed
    print("─" * 60)
    print(f"  self-test {'PASSED' if ok else 'FAILED'}  (artifacts: {tmp_dir})")
    return 0 if ok else 1


# ── CLI ──────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="render_orchestrator.py",
        description="Parallel episode render orchestrator for Viral Engine / Empire OS.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            examples:
              python render_orchestrator.py --episodes GG_EP012,GG_EP013,GG_EP014 --workers 2
              python render_orchestrator.py --season 3 --channel gg --workers 3
              python render_orchestrator.py --pending
              python render_orchestrator.py --season 3 --channel gg --dry-run
              python render_orchestrator.py --self-test
        """),
    )
    queue_group = parser.add_argument_group("what to render")
    queue_group.add_argument("--episodes", help="comma-separated episode ids: GG_EP012,GG_EP013")
    queue_group.add_argument("--episodes-file", help="file with one episode id per line")
    queue_group.add_argument("--season", type=int, help="season number (use with --channel)")
    queue_group.add_argument("--channel", help="channel id for --season: gg, ml, lo, il, eo")
    queue_group.add_argument("--from-ep", type=int, help="first episode number (inclusive)")
    queue_group.add_argument("--to-ep", type=int, help="last episode number (inclusive)")
    queue_group.add_argument("--pending", action="store_true",
                             help="read pending render missions from MISSION_BOARD.json")
    queue_group.add_argument("--mission-board", default=str(DEFAULT_MISSION_BOARD),
                             help="path to MISSION_BOARD.json (default: ./MISSION_BOARD.json)")

    pool_group = parser.add_argument_group("worker pool")
    pool_group.add_argument("--workers", type=int, default=DEFAULT_WORKERS,
                            help=f"concurrent renders (default {DEFAULT_WORKERS}, max {MAX_WORKERS})")
    pool_group.add_argument("--retries", type=int, default=DEFAULT_RETRIES,
                            help=f"extra attempts after a failure (default {DEFAULT_RETRIES})")
    pool_group.add_argument("--status-interval", type=float, default=STATUS_INTERVAL_SEC,
                            help=f"live status refresh in seconds (default {STATUS_INTERVAL_SEC:.0f})")

    render_group = parser.add_argument_group("passed through to auto_render.py")
    render_group.add_argument("--skip-images", action="store_true",
                              help="reuse cached scene images (no image network calls)")
    render_group.add_argument("--music", help="path to a background music MP3")
    render_group.add_argument("--portrait", action="store_true", help="1080x1920 Shorts format")
    render_group.add_argument("--images-only", action="store_true",
                              help="generate scene images and stop (no TTS/video)")

    out_group = parser.add_argument_group("paths & output")
    out_group.add_argument("--python", default=sys.executable,
                           help="python interpreter used to launch auto_render.py")
    out_group.add_argument("--render-script", default=str(DEFAULT_RENDER_SCRIPT),
                           help="renderer to launch (default: ./auto_render.py)")
    out_group.add_argument("--log-file", default=str(DEFAULT_LOG_FILE),
                           help="render log (default: ./render_log.json)")
    out_group.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR),
                           help="per-episode child logs (default: ./render_logs)")
    out_group.add_argument("--output-dir", default=str(RENDERS_DIR),
                           help="directory auto_render.py writes finals to (default: ./renders)")
    out_group.add_argument("--json-summary", help="also write the run summary to this JSON file")
    out_group.add_argument("--quiet", action="store_true", help="suppress child FATAL/ERROR echo")

    filter_group = parser.add_argument_group("filters")
    filter_group.add_argument("--skip-completed", action="store_true",
                              help="skip episodes already marked passed in render_log.json")
    filter_group.add_argument("--skip-existing", action="store_true",
                              help="skip episodes whose renders/<ID>_final.mp4 already exists")
    filter_group.add_argument("--no-validate-scripts", action="store_true",
                              help="queue episodes even if no script JSON is found (self-test)")

    parser.add_argument("--dry-run", action="store_true",
                        help="resolve the queue and print the plan without rendering")
    parser.add_argument("--self-test", action="store_true",
                        help="run the orchestrator against a fake renderer (no API keys needed)")
    parser.add_argument("--version", action="version", version=f"render_orchestrator {VERSION}")
    return parser


def resolve_episodes(args: argparse.Namespace) -> List[str]:
    """Turn CLI selectors into an ordered, de-duplicated list of episode ids."""
    episodes: List[str] = []

    if args.episodes:
        episodes += [e for e in args.episodes.split(",") if e.strip()]
    if args.episodes_file:
        path = Path(args.episodes_file)
        if not path.exists():
            sys.exit(f"ERROR: --episodes-file not found: {path}")
        episodes += [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()
                     if ln.strip() and not ln.strip().startswith("#")]
    if args.season is not None:
        if not args.channel:
            sys.exit("ERROR: --season requires --channel (e.g. --channel gg)")
        episodes += episodes_for_season(args.channel, args.season)
    if args.pending:
        try:
            episodes += episodes_from_mission_board(Path(args.mission_board))
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            sys.exit(f"ERROR: {exc}")
    if args.from_ep is not None or args.to_ep is not None:
        if not args.channel:
            sys.exit("ERROR: --from-ep/--to-ep require --channel")
        lo = args.from_ep if args.from_ep is not None else 1
        hi = args.to_ep if args.to_ep is not None else 9999
        episodes += [e for e in discover_episodes(args.channel)
                     if lo <= episode_number(e) <= hi]

    if not episodes:
        return []

    normalized: List[str] = []
    seen: set = set()
    for raw in episodes:
        try:
            episode_id = normalize_episode_id(raw, args.channel)
        except ValueError as exc:
            sys.exit(f"ERROR: {exc}")
        if episode_id not in seen:
            seen.add(episode_id)
            normalized.append(episode_id)
    return normalized


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if args.self_test:
        return run_self_test(workers=max(1, min(args.workers, MAX_WORKERS)))

    episodes = resolve_episodes(args)
    if not episodes:
        build_parser().print_help()
        print("\nNo episodes selected. Use --episodes, --season/--channel, or --pending.")
        return 2

    extra_args: List[str] = []
    if args.skip_images:
        extra_args.append("--skip-images")
    if args.music:
        extra_args += ["--music", args.music]
    if args.portrait:
        extra_args.append("--portrait")
    if args.images_only:
        extra_args.append("--images-only")

    cfg = OrchestratorConfig(
        render_script=Path(args.render_script),
        python=args.python,
        workers=args.workers,
        retries=args.retries,
        log_file=Path(args.log_file),
        log_dir=Path(args.log_dir),
        output_dir=Path(args.output_dir),
        extra_args=extra_args,
        validate_scripts=not args.no_validate_scripts,
        status_interval=args.status_interval,
        quiet=args.quiet,
        skip_completed=args.skip_completed,
        skip_existing=args.skip_existing,
    )

    if args.skip_existing:
        remaining = [e for e in episodes if not final_output_path(e, cfg.output_dir).exists()]
        skipped = [e for e in episodes if e not in remaining]
        for episode_id in skipped:
            print(f"  - {episode_id:<12} SKIP  "
                  f"({final_output_path(episode_id, cfg.output_dir).name} already exists)")
        episodes = remaining

    if args.dry_run:
        print(f"\nDRY RUN — {len(episodes)} episode(s) would render "
              f"with {max(1, min(args.workers, MAX_WORKERS))} worker(s):")
        print(f"  renderer : {args.render_script}")
        print(f"  python   : {args.python}")
        print(f"  output   : {cfg.output_dir}")
        if extra_args:
            print(f"  args     : {' '.join(extra_args)}")
        print()
        for episode_id in episodes:
            try:
                script = find_episode_json(episode_id)
                scenes = count_scenes(script)
                out = final_output_path(episode_id, cfg.output_dir)
                state = "exists" if out.exists() else "not rendered"
                print(f"  - {episode_id:<12} {scenes:>3} scenes   "
                      f"{Path(script).name}   [{state}]")
            except FileNotFoundError:
                print(f"  - {episode_id:<12} NO SCRIPT JSON FOUND")
        print()
        return 0

    if not Path(args.render_script).exists():
        sys.exit(f"ERROR: render script not found: {args.render_script}")

    orchestrator = RenderOrchestrator(cfg)

    def _handle_sigint(signum, frame):  # noqa: ANN001
        orchestrator._stop.set()

    try:
        signal.signal(signal.SIGINT, _handle_sigint)
    except (ValueError, AttributeError):
        pass  # non-main thread / unsupported platform

    summary = orchestrator.run(episodes)

    if args.json_summary:
        out_path = Path(args.json_summary)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"Summary written to {out_path}")

    return 0 if summary["failed"] == 0 and summary["interrupted"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
