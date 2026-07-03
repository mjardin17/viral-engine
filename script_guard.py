"""
script_guard.py — Viral Engine Council
Guards episode JSON scripts from being downgraded to stubs.

Usage:
    py script_guard.py --audit       # show all scripts, flag stubs
    py script_guard.py --register    # save approved scripts to registry
    py script_guard.py --check       # compare current vs registered, flag downgrades
    py script_guard.py --protect GG_EP006   # restore from backup if stub detected
    py script_guard.py --backup      # backup all full scripts to _backups/
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
PROMPTS_DIR = BASE_DIR / "prompts"
BACKUPS_DIR = PROMPTS_DIR / "_backups"
REGISTRY_PATH = BASE_DIR / "script_registry.json"

MIN_FULL_DURATION = 600    # 10 min minimum to be considered "full"
STUB_CRITICAL = 120        # under 2 min = critical stub
STUB_WARNING = 600         # under 10 min = stub warning


def load_registry() -> dict:
    if REGISTRY_PATH.exists():
        return json.loads(REGISTRY_PATH.read_text())
    return {}


def save_registry(reg: dict):
    REGISTRY_PATH.write_text(json.dumps(reg, indent=2))


def scan_prompts() -> list[dict]:
    """Scan all non-backup prompt JSONs and return episode info."""
    results = []
    for p in sorted(PROMPTS_DIR.rglob("*.json")):
        # Skip backups and hidden dirs
        if any(part.startswith("_") for part in p.relative_to(PROMPTS_DIR).parts[:-1]):
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue

        scenes = data.get("scenes", [])
        if not scenes:
            continue

        ep_id = data.get("episode_id") or ""
        if not ep_id:
            # Infer from filename: scene_prompts.gg_ep006.final.json → GG_EP006
            stem = p.stem.lower()
            for prefix in ["gg_ep", "ml_ep", "lo_ep"]:
                idx = stem.find(prefix)
                if idx != -1:
                    raw = stem[idx:]
                    # take up to next dot or end
                    ep_id = raw.split(".")[0].upper()
                    break

        total_dur = sum(s.get("duration_sec", 0) for s in scenes)

        if total_dur < STUB_CRITICAL:
            status = "CRITICAL_STUB"
        elif total_dur < STUB_WARNING:
            status = "STUB"
        else:
            status = "FULL"

        results.append({
            "episode_id": ep_id or p.stem,
            "filename": p.name,
            "filepath": str(p),
            "scene_count": len(scenes),
            "total_duration_sec": total_dur,
            "title": data.get("title", "?"),
            "status": status,
        })
    return results


def cmd_audit():
    print(f"\n{'='*70}")
    print(f"  SCRIPT GUARD — AUDIT")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")
    print(f"  {'EPISODE':15s} {'SCENES':>6} {'DURATION':>10} {'STATUS':15s} TITLE")
    print(f"  {'-'*65}")

    eps = scan_prompts()
    for e in eps:
        dur_str = f"{e['total_duration_sec']}s ({e['total_duration_sec']/60:.1f}m)"
        icon = "✓" if e["status"] == "FULL" else ("⚠" if e["status"] == "STUB" else "✗")
        print(f"  {icon} {e['episode_id']:14s} {e['scene_count']:>6} {dur_str:>10}  {e['status']:14s} {e['title'][:30]}")

    full = sum(1 for e in eps if e["status"] == "FULL")
    stubs = sum(1 for e in eps if e["status"] == "STUB")
    crit = sum(1 for e in eps if e["status"] == "CRITICAL_STUB")
    print(f"\n  {full} full  {stubs} stubs  {crit} critical stubs\n")


def cmd_register():
    reg = load_registry()
    eps = scan_prompts()
    added, skipped = 0, 0

    for e in eps:
        if e["status"] != "FULL":
            print(f"  [SKIP] {e['episode_id']}: stub ({e['total_duration_sec']}s) — not registering")
            skipped += 1
            continue
        reg[e["episode_id"]] = {
            "filename": e["filename"],
            "scene_count": e["scene_count"],
            "total_duration_sec": e["total_duration_sec"],
            "title": e["title"],
            "registered_at": datetime.now().isoformat(),
        }
        print(f"  [REG] {e['episode_id']}: {e['scene_count']} scenes, {e['total_duration_sec']}s")
        added += 1

    save_registry(reg)
    print(f"\n  Registered {added} episodes, skipped {skipped} stubs → script_registry.json\n")


def cmd_check():
    reg = load_registry()
    if not reg:
        print("  No registry found. Run --register first.")
        sys.exit(0)

    eps = {e["episode_id"]: e for e in scan_prompts()}
    issues = []

    print(f"\n{'='*60}")
    print(f"  SCRIPT GUARD — DOWNGRADE CHECK")
    print(f"{'='*60}\n")

    for ep_id, approved in reg.items():
        current = eps.get(ep_id)
        if not current:
            print(f"  ✗ {ep_id}: MISSING from prompts folder")
            issues.append(ep_id)
            continue
        if current["scene_count"] < approved["scene_count"]:
            print(f"  ✗ {ep_id}: DOWNGRADED — was {approved['scene_count']} scenes, now {current['scene_count']}")
            print(f"      Registered: {approved['title']} ({approved['total_duration_sec']}s)")
            print(f"      Current:    {current['title']} ({current['total_duration_sec']}s)")
            print(f"      ⚠ Re-rendering this episode would produce a short/broken video!")
            issues.append(ep_id)
        else:
            print(f"  ✓ {ep_id}: OK ({current['scene_count']} scenes)")

    if issues:
        print(f"\n  {len(issues)} downgrade(s) detected. Run --protect EPISODE_ID to restore.\n")
        sys.exit(1)
    else:
        print(f"\n  All registered scripts intact.\n")


def cmd_protect(episode_id: str):
    ep_id = episode_id.upper()
    # Find current file
    eps = {e["episode_id"]: e for e in scan_prompts()}
    current = eps.get(ep_id)

    if not current:
        print(f"  {ep_id}: not found in prompts/")
        sys.exit(1)

    if current["status"] == "FULL":
        print(f"  {ep_id}: current script is already full ({current['scene_count']} scenes, {current['total_duration_sec']}s) — nothing to do.")
        sys.exit(0)

    print(f"  {ep_id}: current script is a stub ({current['scene_count']} scenes). Searching backups…")

    # Look in _backups for a fuller version
    best = None
    best_dur = 0
    BACKUPS_DIR.mkdir(exist_ok=True)
    for bf in sorted(BACKUPS_DIR.glob("*.json")):
        stem_low = bf.stem.lower()
        if ep_id.lower() not in stem_low:
            continue
        try:
            data = json.loads(bf.read_text(encoding="utf-8"))
            scenes = data.get("scenes", [])
            dur = sum(s.get("duration_sec", 0) for s in scenes)
            if dur > best_dur:
                best = bf
                best_dur = dur
        except Exception:
            continue

    if not best:
        print(f"  No backup found for {ep_id} in {BACKUPS_DIR}")
        sys.exit(1)

    current_path = Path(current["filepath"])
    # Backup current stub first
    stub_backup = BACKUPS_DIR / f"{current_path.stem}.stub_{datetime.now().strftime('%Y%m%dT%H%M%S')}.json"
    shutil.copy2(current_path, stub_backup)

    # Restore full version
    shutil.copy2(best, current_path)
    print(f"  ✓ Restored {ep_id} from {best.name} ({best_dur}s) → {current_path.name}")
    print(f"  Stub backed up to {stub_backup.name}")


def cmd_backup():
    BACKUPS_DIR.mkdir(exist_ok=True)
    eps = scan_prompts()
    backed_up = 0
    for e in eps:
        if e["status"] != "FULL":
            continue
        src = Path(e["filepath"])
        ts = datetime.now().strftime("%Y%m%dT%H%M%S")
        dst = BACKUPS_DIR / f"{src.stem}.{ts}.json"
        if not dst.exists():
            shutil.copy2(src, dst)
            print(f"  [BAK] {e['episode_id']} → {dst.name}")
            backed_up += 1
        else:
            print(f"  [SKIP] {e['episode_id']}: backup already exists")
    print(f"\n  {backed_up} scripts backed up to prompts/_backups/\n")


def main():
    parser = argparse.ArgumentParser(description="Viral Engine — Script Guard")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("--audit", help="Audit all scripts")
    sub.add_parser("--register", help="Register approved scripts")
    sub.add_parser("--check", help="Check for downgrades")
    prot = sub.add_parser("--protect", help="Restore episode from backup")
    prot.add_argument("episode_id")
    sub.add_parser("--backup", help="Backup all full scripts")

    args, _ = parser.parse_known_args()
    argv = sys.argv[1:]

    if "--register" in argv:
        cmd_register()
    elif "--check" in argv:
        cmd_check()
    elif "--protect" in argv:
        idx = argv.index("--protect")
        if idx + 1 < len(argv):
            cmd_protect(argv[idx + 1])
        else:
            print("Usage: --protect EPISODE_ID")
            sys.exit(1)
    elif "--backup" in argv:
        cmd_backup()
    else:
        cmd_audit()


if __name__ == "__main__":
    main()
