# RENDER_ORCHESTRATOR — Parallel Episode Renderer

**Status:** ✅ Built (MISSION m004) · **Version:** 1.0.0 · **Added:** 2026-09-14

`render_orchestrator.py` wraps `auto_render.py` in a bounded worker pool so several
episodes render at the same time. It **never modifies `auto_render.py`** — it only
launches it as a subprocess and watches its output.

This is GAME_PLAN.md → Tooling #7 ("Build `render_orchestrator.py`") and
GEMINI_MISSION.md → m004.

---

## Quick start

```bat
REM Windows (repo root)
RENDER_ORCHESTRATOR.bat --episodes GG_EP012,GG_EP013,GG_EP014 --workers 2
RENDER_ORCHESTRATOR.bat --season 3 --channel gg --workers 3
RENDER_ORCHESTRATOR.bat --pending
```

```bash
# Linux / macOS / CI
python3 render_orchestrator.py --episodes GG_EP012,GG_EP013 --workers 2
python3 render_orchestrator.py --season 3 --channel gg --workers 3
python3 render_orchestrator.py --pending
python3 render_orchestrator.py --season 3 --channel gg --dry-run   # plan only
python3 render_orchestrator.py --self-test                         # no API keys needed
```

---

## Selecting episodes

| Flag | Meaning |
|---|---|
| `--episodes GG_EP012,GG_EP013` | explicit list (case-insensitive) |
| `--episodes-file queue.txt` | one id per line, `#` comments allowed |
| `--season 3 --channel gg` | every episode of that season that has a script |
| `--from-ep 12 --to-ep 25 --channel gg` | numeric range |
| `--pending` | pending/in-progress `render` missions from `MISSION_BOARD.json` |

Season → episode map (`SEASON_RANGES` in the script):

| Channel | S1 | S2 | S3 |
|---|---|---|---|
| GG | 1–5 | 6–11 | 12–25 |
| ML | 1–12 | 13–23 | — |
| LO | 1–20 | 21–40 | — |
| IL / EO | 1–99 | — | — |

`--season 3 --channel gg` resolves to exactly the 14 episodes in
PROJECT_ROADMAP Phase 2 (GG_EP012 → GG_EP025).

---

## Behaviour

- **Worker pool** — N concurrent `python auto_render.py --episode <ID>` children
  (`subprocess.Popen`, non-blocking). A worker grabs the next episode the instant
  it finishes. **Hard cap: 3 workers** (RAM limit); higher values are clamped.
- **Live status** — printed every 20 s (`--status-interval`): worker → episode,
  progress bar, % done, scenes done/total, elapsed, ETA per job and for the run.
- **Logging** — every finished episode is written to `render_log.json`
  (status, output path, size in bytes + MB, duration, attempts, UTC timestamps,
  error text). Full child stdout is kept in `render_logs/<EP>.attempt<N>.log`.
- **Failure handling** — a non-zero exit (or `auto_render.py` exiting 0 without
  producing `renders/<EP>_final.mp4`) is logged as a failure, retried
  (`--retries`, default 1), then skipped. **Other workers keep running.**
- **Never lies** — exiting 0 with no MP4 on disk is reported as FAILED, not passed.
- **Ctrl-C** — children are terminated and in-flight jobs are marked `interrupted`.
- **Summary** — passed / failed / skipped / interrupted counts, per-episode table,
  total MB and wall clock.

### Useful extras

| Flag | Meaning |
|---|---|
| `--dry-run` | resolve the queue and print the plan without rendering |
| `--skip-completed` | skip episodes already marked `passed` in `render_log.json` |
| `--skip-existing` | skip episodes whose `renders/<EP>_final.mp4` already exists |
| `--skip-images` / `--music X.mp3` / `--portrait` / `--images-only` | passed straight through to `auto_render.py` |
| `--retries N` | extra attempts after a failure (default 1) |
| `--python PATH` | interpreter used to launch the renderer |
| `--render-script PATH` | render a different script (used by the self-test) |
| `--output-dir PATH` | where finals land (default `./renders`) |
| `--json-summary out.json` | machine-readable run summary |
| `--self-test` | run the pool against a fake renderer — no ffmpeg, network or keys |

Exit code is `0` only when nothing failed and nothing was interrupted.

---

## Output files

| File | Tracked in git? | Contents |
|---|---|---|
| `render_log.json` | yes | every episode's latest result + last 50 runs |
| `render_logs/` | **no** (gitignored) | full stdout of every child process |

`render_log.json` layout:

```json
{
  "version": "1.0.0",
  "updated_at": "2026-09-14T…",
  "jobs": { "GG_EP012": { "status": "passed", "size_mb": 412.8, "output": "…", … } },
  "runs":  [ { "run_id": "20260914T…", "workers": 3, "jobs": […], "summary": {…} } ]
}
```

Writes are atomic (temp file + `os.replace`), so an interrupted run can't corrupt
the log, and an unreadable log starts fresh with a warning rather than crashing.

---

## Verification

```bash
python3 test_render_orchestrator.py        # 33 stdlib-only tests, offline
python3 render_orchestrator.py --self-test # end-to-end pool check with a fake renderer
```

The tests cover id parsing, progress parsing, script discovery, season mapping,
mission-board parsing, log round-trip/corruption, the worker pool (pass / fail /
retry / skip / skip-completed / worker clamp), and the "exit 0 but no MP4" trap.

## Recommendation for Season 3

Season 3 is 14 episodes of ~54 scenes each. Run:

```bat
RENDER_ORCHESTRATOR.bat --season 3 --channel gg --workers 2 --skip-existing
```

Then re-run the same command later — completed episodes are recorded in
`render_log.json`, so `--skip-existing` makes restarts cheap and safe.
