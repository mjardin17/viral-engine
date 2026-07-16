"""
render_gg_v3.py — Gods & Glory v3.0 pipeline
Short-format episodes: 10 min, one battle, Wikimedia images + Ken Burns + Kokoro + music

Usage:
    python render_gg_v3.py --script prompts/gods_glory/gg_ep012.json
    python render_gg_v3.py --script prompts/gods_glory/gg_ep012.json --music music/epic_battle.mp3

Output: renders/gods_glory/GG_EP012_final.mp4
"""

import argparse
import json
import os
import sys
import subprocess
import shutil
from pathlib import Path

# Local pipeline modules
from wikimedia_fetch import fetch_scene_image
from video_effects import ken_burns_clip, mix_music, add_lower_third
from music_gen import get_or_generate as get_music

PYTHON = r"C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe"
TTS_CLI = os.path.join(os.path.dirname(__file__), "tts_cli.py")
FFMPEG = "ffmpeg"
OUTPUT_ROOT = os.path.join(os.path.dirname(__file__), "renders", "gods_glory")
WORK_ROOT = os.path.join(os.path.dirname(__file__), "output", "gg_v3")


def tts_narrate(text: str, out_wav: str) -> bool:
    """Generate narration using Kokoro TTS via tts_cli.py."""
    os.makedirs(os.path.dirname(out_wav) or ".", exist_ok=True)
    cmd = [PYTHON, TTS_CLI, "--text", text, "--out", out_wav]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not os.path.exists(out_wav):
        print(f"[render_gg_v3] TTS failed: {result.stderr[-300:]}", file=sys.stderr)
        return False
    print(f"[render_gg_v3] TTS ✅ {out_wav}")
    return True


def combine_video_audio(video: str, audio: str, out: str) -> bool:
    """Merge silent video clip with narration audio."""
    cmd = [
        FFMPEG, "-y",
        "-i", video,
        "-i", audio,
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        out,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[render_gg_v3] Combine error: {result.stderr[-300:]}", file=sys.stderr)
        return False
    return True


def concat_clips(clip_list: list[str], out: str) -> bool:
    """Concatenate scene clips into one episode."""
    list_file = out + ".concat_list.txt"
    with open(list_file, "w") as f:
        for c in clip_list:
            f.write(f"file '{os.path.abspath(c)}'\n")
    cmd = [
        FFMPEG, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_file,
        "-c", "copy",
        out,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    os.remove(list_file)
    if result.returncode != 0:
        print(f"[render_gg_v3] Concat error: {result.stderr[-300:]}", file=sys.stderr)
        return False
    return True


def render_episode(script_path: str, music_path: str = None) -> str | None:
    """
    Full pipeline: script JSON → final MP4.
    Returns path to final MP4, or None on failure.
    """
    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    ep_id = script.get("episode_id", Path(script_path).stem.upper())
    title = script.get("title", ep_id)
    battle_date = script.get("battle_date", "")
    scenes = script.get("scenes", [])

    print(f"\n[render_gg_v3] === {ep_id}: {title} ===")
    print(f"[render_gg_v3] Scenes: {len(scenes)}")

    work_dir = os.path.join(WORK_ROOT, ep_id)
    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(OUTPUT_ROOT, exist_ok=True)

    scene_clips = []

    for i, scene in enumerate(scenes):
        scene_num = scene.get("scene_number", i + 1)
        narration = scene.get("narration", "")
        wikimedia_query = scene.get("wikimedia_query", title)
        duration = scene.get("duration_sec", 45)
        scene_title = scene.get("title", "")
        lower_third = scene.get("lower_third", "")

        print(f"\n[render_gg_v3] Scene {scene_num}/{len(scenes)}: {scene_title}")

        img_path = os.path.join(work_dir, f"scene_{scene_num:02d}.jpg")
        kb_path = os.path.join(work_dir, f"scene_{scene_num:02d}_kb.mp4")
        wav_path = os.path.join(work_dir, f"scene_{scene_num:02d}.wav")
        narrated_path = os.path.join(work_dir, f"scene_{scene_num:02d}_narrated.mp4")
        final_scene_path = os.path.join(work_dir, f"scene_{scene_num:02d}_final.mp4")

        # 1. Fetch image from Wikimedia
        if not os.path.exists(img_path):
            ok = fetch_scene_image(wikimedia_query, img_path)
            if not ok:
                # Fallback: use Pollinations AI image
                print(f"[render_gg_v3] Wikimedia failed, falling back to Pollinations")
                visual_prompt = scene.get("visual_prompt", wikimedia_query)
                encoded = visual_prompt.replace(" ", "%20")[:200]
                fallback_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1920&height=1080&nologo=true"
                import urllib.request
                try:
                    urllib.request.urlretrieve(fallback_url, img_path)
                    print(f"[render_gg_v3] Pollinations fallback ✅")
                except Exception as e:
                    print(f"[render_gg_v3] ❌ Image fetch completely failed: {e}", file=sys.stderr)
                    continue

        # 2. Ken Burns motion clip (silent)
        if not os.path.exists(kb_path):
            ok = ken_burns_clip(img_path, kb_path, duration=duration)
            if not ok:
                print(f"[render_gg_v3] ❌ Ken Burns failed scene {scene_num}", file=sys.stderr)
                continue

        # 3. TTS narration
        if narration and not os.path.exists(wav_path):
            ok = tts_narrate(narration, wav_path)
            if not ok:
                print(f"[render_gg_v3] ❌ TTS failed scene {scene_num}", file=sys.stderr)
                continue

        # 4. Combine video + audio
        if narration and not os.path.exists(narrated_path):
            ok = combine_video_audio(kb_path, wav_path, narrated_path)
            if not ok:
                continue
        elif not narration:
            narrated_path = kb_path

        # 5. Optional: lower third title card
        scene_with_lt = narrated_path
        if lower_third and not os.path.exists(final_scene_path):
            parts = lower_third.split("|")
            lt_title = parts[0].strip()
            lt_sub = parts[1].strip() if len(parts) > 1 else ""
            ok = add_lower_third(narrated_path, final_scene_path, lt_title, lt_sub)
            if ok:
                scene_with_lt = final_scene_path
        elif not os.path.exists(final_scene_path):
            shutil.copy2(narrated_path, final_scene_path)
            scene_with_lt = final_scene_path

        scene_clips.append(scene_with_lt)
        print(f"[render_gg_v3] ✅ Scene {scene_num} done")

    if not scene_clips:
        print("[render_gg_v3] ❌ No scenes rendered", file=sys.stderr)
        return None

    # 6. Concatenate all scenes
    assembled_path = os.path.join(work_dir, f"{ep_id}_assembled.mp4")
    print(f"\n[render_gg_v3] Assembling {len(scene_clips)} scenes...")
    ok = concat_clips(scene_clips, assembled_path)
    if not ok:
        return None

    # 7. Mix in background music (auto-generate if not provided)
    final_path = os.path.join(OUTPUT_ROOT, f"{ep_id}_final.mp4")
    if not music_path or not os.path.exists(music_path):
        print(f"[render_gg_v3] No music file provided — auto-generating via MusicGen...")
        music_path = get_music("GG", ep_id, duration=300, music_dir="music")
    if music_path and os.path.exists(music_path):
        print(f"[render_gg_v3] Adding music: {music_path}")
        ok = mix_music(assembled_path, music_path, final_path, music_vol=0.18)
        if not ok:
            shutil.copy2(assembled_path, final_path)
    else:
        print(f"[render_gg_v3] ⚠ Music unavailable (add HF_TOKEN to .env) — rendering without music")
        shutil.copy2(assembled_path, final_path)

    size_mb = os.path.getsize(final_path) / 1024 / 1024
    print(f"\n[render_gg_v3] === DONE ===")
    print(f"[render_gg_v3] Output: {final_path} ({size_mb:.1f}MB)")
    return final_path


def main():
    parser = argparse.ArgumentParser(description="Gods & Glory v3.0 renderer")
    parser.add_argument("--script", required=True, help="Path to episode JSON script")
    parser.add_argument("--music", default=None, help="Optional background music file (mp3/wav)")
    args = parser.parse_args()

    if not os.path.exists(args.script):
        print(f"[render_gg_v3] Script not found: {args.script}", file=sys.stderr)
        sys.exit(1)

    result = render_episode(args.script, args.music)
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
