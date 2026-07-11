"""
mission_board.py — Empire OS Agent Mission Orchestration
=========================================================
Single source of truth for agent work assignments: MISSION_BOARD.json (repo root).

USAGE:
  python mission_board.py list
      Print all missions with status.

  python mission_board.py next
      Print the highest-priority pending mission as a ready-to-paste
      Claude Code prompt (does NOT change status).

  python mission_board.py next --claim
      Same, but also marks the mission "in_progress" on the board.
      (This is what agent_runner.bat calls.)

  python mission_board.py complete m001 "url1,url2,url3"
      Mark mission done with its result.

  python mission_board.py block m001 "error message"
      Mark mission blocked with the error.

RULES (from CLAUDE.md):
  - YouTube uploads always require Josh's manual approval.
  - Never use token.pickle for GG — token_gg.pickle only.
  - No silent failures: if a mission fails, block it with the real error.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
BOARD_PATH = BASE_DIR / "MISSION_BOARD.json"
REPO_WIN_PATH = r"C:\Users\jjard\claude\video-bot-pipeline"

VALID_STATUSES = ("pending", "in_progress", "done", "blocked")
STATUS_ICONS = {
    "pending": "[ ]",
    "in_progress": "[>]",
    "done": "[x]",
    "blocked": "[!]",
}

# ── Board I/O ─────────────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_board() -> dict:
    if not BOARD_PATH.exists():
        sys.exit(f"ERROR: {BOARD_PATH} not found. Board must live at repo root.")
    try:
        with BOARD_PATH.open("r", encoding="utf-8") as f:
            board = json.load(f)
    except json.JSONDecodeError as exc:
        sys.exit(f"ERROR: MISSION_BOARD.json is not valid JSON: {exc}")
    if "missions" not in board or not isinstance(board["missions"], list):
        sys.exit("ERROR: MISSION_BOARD.json missing 'missions' list.")
    return board


def save_board(board: dict) -> None:
    board["updated_at"] = _now_iso()
    tmp = BOARD_PATH.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(board, f, indent=2, ensure_ascii=False)
        f.write("\n")
    tmp.replace(BOARD_PATH)


def find_mission(board: dict, mission_id: str) -> dict:
    for m in board["missions"]:
        if m.get("id") == mission_id:
            return m
    sys.exit(
        f"ERROR: mission '{mission_id}' not found. "
        f"Known ids: {', '.join(m.get('id', '?') for m in board['missions'])}"
    )


def next_pending(board: dict) -> dict | None:
    pending = [m for m in board["missions"] if m.get("status") == "pending"]
    if not pending:
        return None
    return sorted(pending, key=lambda m: m.get("priority", 999))[0]


# ── Prompt generation ─────────────────────────────────────────────────────────


def _episodes(mission: dict) -> list[str]:
    return [e.strip() for e in mission.get("target", "").split(",") if e.strip()]


def build_prompt(mission: dict) -> str:
    """Build the ready-to-paste Claude Code prompt for a mission."""
    mtype = mission.get("type", "")
    if mtype == "upload":
        return _upload_prompt(mission)
    if mtype == "render":
        return _render_prompt(mission)
    return _generic_prompt(mission)


def _header(mission: dict) -> str:
    eps = _episodes(mission)
    return (
        f"You are working in {REPO_WIN_PATH} (Empire OS repo).\n"
        f"Read CLAUDE.md and AGENT_MEMORY.md fully before acting. "
        f"Run 'git pull origin main' first.\n"
        f"\n"
        f"MISSION {mission['id']} — {mission.get('type', '?').upper()} "
        f"(channel: {mission.get('channel', '?')}, priority: {mission.get('priority', '?')})\n"
        f"Episodes: {', '.join(eps)}\n"
        f"Notes: {mission.get('notes', '')}\n"
    )


def _footer(mission: dict) -> str:
    mid = mission["id"]
    return (
        f"\nWHEN FINISHED, report back on the mission board (repo root):\n"
        f'  python mission_board.py complete {mid} "<comma-separated results, e.g. URLs or final mp4 names>"\n'
        f"If anything fails and you cannot fix it:\n"
        f'  python mission_board.py block {mid} "<exact error / reason>"\n'
        f"NO SILENT FAILURES — only the truth. Then commit the updated "
        f"MISSION_BOARD.json: git add -A && git commit -m \"[CLAUDE] chore: mission {mid} update\" && git push origin main\n"
    )


def _upload_prompt(mission: dict) -> str:
    eps = _episodes(mission)
    channel = mission.get("channel", "gg")
    ep_arg = ",".join(eps)
    steps = (
        f"\nSTEPS (in order, verify each before moving on):\n"
        f"1. VERIFY THE TOKEN FIRST — never use token.pickle (wrong account):\n"
        f"     python channel_uploader.py --channel {channel} --verify\n"
        f"   Confirm the account shown is the correct {channel.upper()} account. "
        f"If wrong, STOP and block the mission.\n"
        f"2. Confirm each final exists in renders\\ and is healthy "
        f"(size >100MB and ffprobe duration sane):\n"
    )
    for ep in eps:
        steps += f"     ffprobe -v error -show_entries format=duration,size renders\\{ep}_final.mp4\n"
    steps += (
        f"3. GET JOSH'S EXPLICIT APPROVAL before uploading (YouTube uploads are "
        f"never automatic). Show him the file list and wait for his yes.\n"
        f"4. Upload:\n"
        f"     python channel_uploader.py --channel {channel} --episodes {ep_arg}\n"
        f"5. IMMEDIATELY verify each returned video URL shows the correct channel "
        f"name before moving on (this was missed once — never again).\n"
    )
    return _header(mission) + steps + _footer(mission)


def _render_prompt(mission: dict) -> str:
    eps = _episodes(mission)
    notes = mission.get("notes", "").lower()
    steps = (
        f"\nSTEPS (in order, verify each before moving on):\n"
        f"1. Confirm each episode's FULL script JSON exists in prompts\\gods_glory\\ "
        f"(54-72 scenes; if only a stub exists, block the mission — stubs are unusable).\n"
    )
    if "tts" in notes or "rate" in notes:
        steps += (
            f"2. BEFORE rendering: confirm the TTS rate fix (-35%) is actually in "
            f"auto_render.py. If not, apply it first — otherwise the re-render "
            f"reproduces the same short episodes.\n"
        )
        n = 3
    else:
        n = 2
    if "render_season3" in notes:
        steps += (
            f"{n}. Render (Season 3 batch script covers all of these):\n"
            f"     render_season3.bat\n"
            f"   Or render individually if resuming after a failure:\n"
        )
    else:
        steps += f"{n}. Render each episode:\n"
    for ep in eps:
        steps += f"     py auto_render.py --episode {ep} --music music\\battle_epic.mp3\n"
    steps += (
        f"{n + 1}. Verify every final in renders\\ with ffprobe: duration matches the "
        f"script length and audio is not silent (RMS check). A 0KB or tiny clip is "
        f"a failure — root-cause it, do not fake output.\n"
        f"{n + 2}. Do NOT upload anything — uploads are a separate mission requiring "
        f"Josh's approval.\n"
    )
    return _header(mission) + steps + _footer(mission)


def _generic_prompt(mission: dict) -> str:
    return (
        _header(mission)
        + f"\nSTEPS:\n"
        f"1. Read the notes above and CLAUDE.md, work out the exact commands "
        f"needed, and double-check every target before acting.\n"
        + _footer(mission)
    )


# ── Commands ──────────────────────────────────────────────────────────────────


def cmd_list(board: dict) -> None:
    print(f"MISSION BOARD  (updated: {board.get('updated_at', '?')})")
    print("-" * 78)
    for m in sorted(board["missions"], key=lambda x: x.get("priority", 999)):
        icon = STATUS_ICONS.get(m.get("status", ""), "[?]")
        eps = _episodes(m)
        line = (
            f"{icon} {m['id']}  p{m.get('priority', '?')}  "
            f"{m.get('type', '?'):<7} {m.get('channel', '?'):<3} "
            f"{m.get('status', '?'):<12} {len(eps)} ep(s): {m.get('target', '')}"
        )
        print(line)
        if m.get("notes"):
            print(f"      notes:  {m['notes']}")
        if m.get("result"):
            print(f"      result: {m['result']}")
        if m.get("error"):
            print(f"      error:  {m['error']}")
    print("-" * 78)
    counts = {s: 0 for s in VALID_STATUSES}
    for m in board["missions"]:
        counts[m.get("status", "pending")] = counts.get(m.get("status", "pending"), 0) + 1
    print(
        f"pending: {counts['pending']}  in_progress: {counts['in_progress']}  "
        f"done: {counts['done']}  blocked: {counts['blocked']}"
    )


def cmd_next(board: dict, claim: bool) -> None:
    mission = next_pending(board)
    if mission is None:
        in_prog = [m["id"] for m in board["missions"] if m.get("status") == "in_progress"]
        blocked = [m["id"] for m in board["missions"] if m.get("status") == "blocked"]
        print("No pending missions on the board.")
        if in_prog:
            print(f"In progress: {', '.join(in_prog)}")
        if blocked:
            print(f"Blocked (need attention): {', '.join(blocked)}")
        return
    if claim:
        mission["status"] = "in_progress"
        mission["started_at"] = _now_iso()
        save_board(board)
    print("=" * 78)
    print(
        f"NEXT MISSION: {mission['id']}  ({mission.get('type')}, "
        f"priority {mission.get('priority')})"
        + ("  — status set to in_progress" if claim else "")
    )
    print("=" * 78)
    print()
    print("--- PASTE EVERYTHING BELOW THIS LINE INTO CLAUDE CODE " + "-" * 23)
    print()
    print(build_prompt(mission))
    print("-" * 78)


def cmd_complete(board: dict, mission_id: str, result: str) -> None:
    mission = find_mission(board, mission_id)
    mission["status"] = "done"
    mission["result"] = result
    mission["error"] = ""
    mission["completed_at"] = _now_iso()
    save_board(board)
    print(f"Mission {mission_id} marked DONE.")
    print(f"Result: {result}")
    nxt = next_pending(board)
    if nxt:
        print(f"Next up: {nxt['id']} ({nxt.get('type')}, priority {nxt.get('priority')}) "
              f"— run: python mission_board.py next")
    else:
        print("Board clear — no pending missions.")


def cmd_block(board: dict, mission_id: str, error: str) -> None:
    mission = find_mission(board, mission_id)
    mission["status"] = "blocked"
    mission["error"] = error
    mission["blocked_at"] = _now_iso()
    save_board(board)
    print(f"Mission {mission_id} marked BLOCKED.")
    print(f"Error: {error}")


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = argv[1].lower()
    board = load_board()

    if cmd == "list":
        cmd_list(board)
    elif cmd == "next":
        cmd_next(board, claim="--claim" in argv[2:])
    elif cmd == "complete":
        if len(argv) < 4:
            sys.exit('Usage: python mission_board.py complete <id> "<result>"')
        cmd_complete(board, argv[2], argv[3])
    elif cmd == "block":
        if len(argv) < 4:
            sys.exit('Usage: python mission_board.py block <id> "<error message>"')
        cmd_block(board, argv[2], argv[3])
    else:
        sys.exit(f"Unknown command '{cmd}'. Valid: list, next, complete, block")


if __name__ == "__main__":
    main(sys.argv)
