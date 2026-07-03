#!/usr/bin/env python3
"""
il_batch_render.py — Renders Iron Legends EP001 in batches of N scenes.
Run repeatedly; skips already-done scenes. Final pass does concat.

Usage:
    python3 il_batch_render.py --scenes 1-3
    python3 il_batch_render.py --scenes 4-6
    python3 il_batch_render.py --scenes 7-10
    python3 il_batch_render.py --concat
"""
import argparse, json, shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from iron_legends_render import (
    render_scene, generate_mech_silhouette, make_title_card, make_end_card,
    still_to_video, generate_silence, _run, _probe, _backup,
    PROMPTS_DIR, RENDERS_DIR, CHAR_DIR, IL_RENDERS_DIR,
    C_ELECTRIC, C_CRIMSON, C_GOLD,
    TITLE_DUR, END_DUR, FFMPEG
)

EP_ID      = "IL_EP001"
WORK_DIR   = RENDERS_DIR / "iron_legends" / f"_work_{EP_ID.lower()}"
FINAL_OUT  = IL_RENDERS_DIR / f"{EP_ID.lower()}.mp4"

def load_episode():
    f = PROMPTS_DIR / f"scene_prompts.{EP_ID.lower()}.final.json"
    with open(str(f)) as fh:
        return json.load(fh)

def ensure_chars():
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    paths = {}
    for role, color, key in [
        ("protagonist", C_ELECTRIC, "protagonist"),
        ("antagonist",  C_CRIMSON,  "antagonist"),
        ("ancient",     C_GOLD,     "ancient"),
    ]:
        p = WORK_DIR / f"char_{role}.png"
        if not p.exists():
            generate_mech_silhouette(role, p, color)
        paths[key] = p
    return paths

def ensure_title(ep):
    title_still = WORK_DIR / "title_still.png"
    title_vid   = WORK_DIR / "title.mp4"
    title_audio = WORK_DIR / "title_audio.aac"
    title_final = WORK_DIR / "title_final.mp4"
    if not title_still.exists():
        make_title_card(ep["title"], ep.get("tagline",""), EP_ID, title_still)
    if not title_vid.exists():
        still_to_video(title_still, title_vid, TITLE_DUR, "push_in")
    if not title_audio.exists():
        generate_silence(TITLE_DUR, title_audio)
    if not title_final.exists() and title_vid.exists() and title_audio.exists():
        _run([FFMPEG,"-y","-i",str(title_vid),"-i",str(title_audio),
              "-c:v","copy","-c:a","copy","-shortest",
              "-map","0:v","-map","1:a",str(title_final)], "title_mux")
    return title_final

def ensure_end(ep):
    end_still = WORK_DIR / "end_still.png"
    end_vid   = WORK_DIR / "end.mp4"
    end_audio = WORK_DIR / "end_audio.aac"
    end_final = WORK_DIR / "end_final.mp4"
    if not end_still.exists():
        make_end_card(EP_ID, ep.get("next_episode_preview",""), end_still)
    if not end_vid.exists():
        still_to_video(end_still, end_vid, END_DUR, "push_in")
    if not end_audio.exists():
        generate_silence(END_DUR, end_audio)
    if not end_final.exists() and end_vid.exists() and end_audio.exists():
        _run([FFMPEG,"-y","-i",str(end_vid),"-i",str(end_audio),
              "-c:v","copy","-c:a","copy","-shortest",
              "-map","0:v","-map","1:a",str(end_final)], "end_mux")
    return end_final

def do_concat(ep):
    scenes     = ep["scenes"]
    title_clip = WORK_DIR / "title_final.mp4"
    end_clip   = WORK_DIR / "end_final.mp4"
    scene_clips = []
    missing     = []
    for s in scenes:
        n   = s["scene_number"]
        fp  = WORK_DIR / f"scene_{n:02d}_final.mp4"
        if fp.exists():
            scene_clips.append(fp)
        else:
            missing.append(n)

    if missing:
        print(f"[WARN] Missing scene finals: {missing} — run those batches first")

    all_clips = []
    if title_clip.exists(): all_clips.append(title_clip)
    all_clips.extend(scene_clips)
    if end_clip.exists():   all_clips.append(end_clip)

    print(f"\nConcatenating {len(all_clips)} clips...")
    concat_list = WORK_DIR / "concat.txt"
    with open(str(concat_list), "w") as f:
        for clip in all_clips:
            f.write(f"file '{clip}'\n")

    IL_RENDERS_DIR.mkdir(parents=True, exist_ok=True)
    ok = _run([
        FFMPEG, "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy", "-movflags", "+faststart",
        str(FINAL_OUT)
    ], "final_concat")

    if ok and FINAL_OUT.exists():
        dur     = _probe(FINAL_OUT)
        size_mb = FINAL_OUT.stat().st_size / (1024*1024)
        print(f"\n✓ FINAL: {FINAL_OUT.name}")
        print(f"  Duration: {dur:.1f}s  ({dur/60:.1f} min)  |  {size_mb:.1f} MB")
        _backup(FINAL_OUT)
        return True
    print("[ERR] Concat failed")
    return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenes", type=str, help="Scene range e.g. 1-3")
    parser.add_argument("--concat", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    ep       = load_episode()
    char_paths = ensure_chars()

    if args.status:
        scenes = ep["scenes"]
        print(f"\n{EP_ID} — {ep['title']}")
        print(f"{'Scene':<8} {'Title':<40} {'Done?'}")
        print("-"*60)
        for s in scenes:
            n  = s["scene_number"]
            fp = WORK_DIR / f"scene_{n:02d}_final.mp4"
            print(f"  {n:02d}    {s['title'][:38]:<40} {'✓' if fp.exists() else '·'}")
        title_done = (WORK_DIR / "title_final.mp4").exists()
        end_done   = (WORK_DIR / "end_final.mp4").exists()
        final_done = FINAL_OUT.exists()
        print(f"\n  Title: {'✓' if title_done else '·'}   End: {'✓' if end_done else '·'}   FINAL: {'✓' if final_done else '·'}")
        return

    if args.concat:
        ensure_title(ep)
        ensure_end(ep)
        do_concat(ep)
        return

    if args.scenes:
        ensure_title(ep)
        parts = args.scenes.split("-")
        lo = int(parts[0])
        hi = int(parts[1]) if len(parts) > 1 else lo
        scenes = [s for s in ep["scenes"] if lo <= s["scene_number"] <= hi]
        print(f"\nRendering scenes {lo}-{hi} ({len(scenes)} scenes)...\n")
        for scene in scenes:
            render_scene(scene, WORK_DIR, char_paths, EP_ID)
        print(f"\nBatch {lo}-{hi} complete.")
        return

    parser.print_help()

if __name__ == "__main__":
    main()
