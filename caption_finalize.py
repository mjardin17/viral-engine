#!/usr/bin/env python3
"""
caption_finalize.py — retrofit captions onto an already-rendered GG episode
and reassemble the final.mp4, WITHOUT re-fetching images or re-doing TTS.

Use case: auto_render.py rendered the per-scene clips before subtitle
support existed (or before audio/images were refreshed), and we just need
to (a) burn captions onto each existing scene clip and (b) rebuild the
final concatenated + music-mixed render from the result.

Usage:
    python3 caption_finalize.py --episode GG_EP001 --music music/battle_epic.mp3
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
RENDERS_DIR = BASE_DIR / "renders"
PROMPTS_DIR = BASE_DIR / "prompts"

FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"


def find_episode_json(episode_id: str) -> Path:
    eid = episode_id.lower()
    candidates = [
        PROMPTS_DIR / "gods_glory" / f"scene_prompts.{eid}.final.json",
        PROMPTS_DIR / f"scene_prompts.{eid}.final.json",
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(f"No scene prompts JSON found for {episode_id}")


def get_duration(path: Path) -> float:
    try:
        result = subprocess.run(
            [FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=30,
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def is_valid_clip(path: Path, min_duration: float = 0.5) -> bool:
    if not path.exists() or path.stat().st_size < 10_000:
        return False
    d = get_duration(path)
    return d >= min_duration


def split_into_caption_chunks(text: str, max_chars: int = 58) -> list:
    words, chunks, cur, cur_len = text.split(), [], [], 0
    for word in words:
        if cur and cur_len + len(word) + 1 > max_chars:
            chunks.append(" ".join(cur))
            cur, cur_len = [word], len(word)
        else:
            cur.append(word)
            cur_len += len(word) + 1
    if cur:
        chunks.append(" ".join(cur))
    return chunks


def srt_timestamp(t: float) -> str:
    t = max(0.0, t)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    ms = int((s - int(s)) * 1000)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{ms:03d}"


def build_srt(text: str, duration: float, out_path: Path) -> Path:
    chunks = split_into_caption_chunks(text) if text else []
    total_words = sum(len(c.split()) for c in chunks) or 1
    t = 0.0
    lines = []
    for i, chunk in enumerate(chunks, 1):
        share = len(chunk.split()) / total_words
        seg_dur = max(0.8, duration * share)
        start, end = t, min(duration, t + seg_dur)
        lines.append(f"{i}\n{srt_timestamp(start)} --> {srt_timestamp(end)}\n{chunk}\n")
        t = end
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def burn_subtitles(in_video: Path, srt_path: Path, out_video: Path) -> bool:
    srt_arg = str(srt_path).replace("\\", "/").replace(":", "\\:")
    style = (
        "FontSize=14,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
        "BorderStyle=3,Outline=1,Shadow=0,MarginV=60"
    )
    vf = f"subtitles='{srt_arg}':force_style='{style}'"
    cmd = [
        FFMPEG, "-y", "-i", str(in_video),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "copy",
        str(out_video),
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=600)
    if result.returncode != 0:
        print(result.stderr.decode(errors="replace")[-1500:])
    return result.returncode == 0


def concat_scenes(scene_files: list, out_path: Path) -> bool:
    list_path = out_path.parent / f"{out_path.stem}_concat.txt"
    with open(list_path, "w") as f:
        for sf in scene_files:
            f.write(f"file '{sf.resolve()}'\n")
    result = subprocess.run(
        [FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(list_path),
         "-c", "copy", str(out_path)],
        capture_output=True, timeout=900,
    )
    try:
        list_path.unlink()
    except Exception:
        pass
    if result.returncode != 0:
        print(result.stderr.decode(errors="replace")[-1500:])
    return result.returncode == 0 and is_valid_clip(out_path, min_duration=10)


def mix_music(video_path: Path, music_path: Path, out_path: Path) -> bool:
    dur = get_duration(video_path)
    result = subprocess.run(
        [FFMPEG, "-y",
         "-i", str(video_path),
         "-stream_loop", "-1", "-i", str(music_path),
         "-filter_complex",
         "[1:a]volume=0.12[music];[0:a][music]amix=inputs=2:duration=first[aout]",
         "-map", "0:v", "-map", "[aout]",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-t", str(dur), str(out_path)],
        capture_output=True, timeout=600,
    )
    if result.returncode != 0:
        print(result.stderr.decode(errors="replace")[-1500:])
    return result.returncode == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", required=True)
    ap.add_argument("--music", default=None)
    ap.add_argument("--prompts-file", default=None, help="Override path to scene prompts JSON")
    args = ap.parse_args()

    episode_id = args.episode.upper()
    work_dir = OUTPUT_DIR / episode_id
    ep_path = Path(args.prompts_file) if args.prompts_file else find_episode_json(episode_id)
    with open(ep_path, encoding="utf-8") as f:
        ep_data = json.load(f)
    scenes = ep_data.get("scenes", [])
    print(f"{episode_id}: {len(scenes)} scenes, captions source = {ep_path.name}")

    captioned_files = []
    for idx, scene in enumerate(scenes):
        num = scene.get("scene_number", idx + 1)
        narr = scene.get("narration", "")
        clip_path = work_dir / f"scene_{num:02d}.mp4"
        if not clip_path.exists():
            print(f"  [{num:02d}] MISSING {clip_path.name} — skipping episode-level concat for this scene")
            continue

        backup = work_dir / f"scene_{num:02d}_nocaption_backup.mp4"
        if not backup.exists():
            shutil.copy2(str(clip_path), str(backup))

        srt_path = work_dir / f"scene_{num:02d}.srt"
        sub_out = work_dir / f"scene_{num:02d}_subbed.mp4"
        dur = get_duration(backup)
        build_srt(narr, dur, srt_path)
        ok = burn_subtitles(backup, srt_path, sub_out)
        if ok and is_valid_clip(sub_out, min_duration=dur * 0.8):
            shutil.move(str(sub_out), str(clip_path))
            print(f"  [{num:02d}] captioned OK ({dur:.1f}s)")
        else:
            print(f"  [{num:02d}] caption burn FAILED — keeping original clip")
        try:
            srt_path.unlink()
        except Exception:
            pass
        try:
            sub_out.unlink()
        except Exception:
            pass
        captioned_files.append(clip_path)

    if not captioned_files:
        sys.exit("No scene clips found — aborting.")

    raw_out = work_dir / f"{episode_id}_captioned_raw.mp4"
    print(f"\nConcatenating {len(captioned_files)} captioned clips…")
    if not concat_scenes(captioned_files, raw_out):
        sys.exit("Concat failed.")

    final_out = RENDERS_DIR / f"{episode_id}_final.mp4"
    if args.music and Path(args.music).exists():
        print("Mixing music…")
        if not mix_music(raw_out, Path(args.music), final_out):
            sys.exit("Music mix failed.")
    else:
        shutil.copy2(str(raw_out), str(final_out))

    final_dur = get_duration(final_out)
    print(f"\n✓ DONE — {final_out} ({final_dur/60:.1f} min, {final_out.stat().st_size/1e6:.0f} MB)")


if __name__ == "__main__":
    main()
