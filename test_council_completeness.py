#!/usr/bin/env python3
"""
test_council_completeness.py — Regression test for the empire_render.py
completeness gate (fixed 2026-08-08).

Defect: an episode with skipped scenes could still reach "COUNCIL APPROVED"
because expected_dur was derived FROM the surviving scene_clips, making the
duration check tautological. Fix: render_episode() now checks stats.skipped
BEFORE calling council_evaluator.evaluate() or the upload-staging hook.

This test never touches ffmpeg/TTS/network — it monkeypatches the heavy I/O
functions so it runs in well under a second and proves the *control flow*:
  1. When a scene is forced to fail, render_episode() must return None,
     council_evaluator.evaluate() must NOT be called, and the upload hook
     must NOT be called.
  2. When all scenes succeed, council_evaluator.evaluate() IS called, and
     (assuming it passes) the upload hook IS called.

Run: python test_council_completeness.py
Exit code 0 = all checks passed, non-zero = regression.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from unittest import mock

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import empire_render  # noqa: E402


def _make_script(tmp_dir: Path, n_scenes: int) -> Path:
    scenes = [
        {"scene_number": i + 1, "narration": f"Scene {i + 1} narration text."}
        for i in range(n_scenes)
    ]
    script = {"episode_id": "TEST_EP000", "title": "Regression Test Episode", "scenes": scenes}
    path = tmp_dir / "TEST_EP000.json"
    path.write_text(json.dumps(script), encoding="utf-8")
    return path


def _run_with_mocks(tmp_dir: Path, script_path: Path, force_fail_scene: int | None):
    """Run render_episode with all heavy I/O stubbed. Returns (result, evaluate_called, hook_called)."""
    evaluate_called = {"n": 0}
    hook_called = {"n": 0}
    fake_out = tmp_dir / "renders" / "little_olympus"
    fake_out.mkdir(parents=True, exist_ok=True)

    def fake_render_scene_clip(scene, index, total, work_dir, clips_dir, voice, speed, channel):
        n = int(scene.get("scene_number", index + 1))
        if force_fail_scene is not None and n == force_fail_scene:
            return None  # simulate: every provider failed for this scene
        clip = work_dir / f"scene_{n:02d}_final.mp4"
        clip.parent.mkdir(parents=True, exist_ok=True)
        clip.write_bytes(b"0" * 20_000)  # fake >10KB "clip"
        return clip

    def fake_concat_scenes(clips, out):
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"0" * 20_000)
        return True

    def fake_probe_duration(path):
        return 5.0

    class FakeVerdict:
        passed = True
        round_failed = 0
        reason = "all 3 rounds passed"

    def fake_evaluate(clip, expected_dur, tag=""):
        evaluate_called["n"] += 1
        return FakeVerdict()

    def fake_on_council_approved(channel, ep_id, final_path, title):
        hook_called["n"] += 1

    with mock.patch.object(empire_render, "BASE_DIR", tmp_dir), \
         mock.patch.object(empire_render, "render_scene_clip", side_effect=fake_render_scene_clip), \
         mock.patch.object(empire_render, "concat_scenes", side_effect=fake_concat_scenes), \
         mock.patch.object(empire_render, "probe_duration", side_effect=fake_probe_duration), \
         mock.patch.object(empire_render, "mix_music"), \
         mock.patch("orchestrator.agents.council_evaluator.evaluate", side_effect=fake_evaluate), \
         mock.patch("social_clips.post_render.on_council_approved", side_effect=fake_on_council_approved):
        result = empire_render.render_episode(
            channel="LO", episode_id="TEST_EP000", script_path=script_path,
            music_path=None, clips_dir=None, multi_agent=False,
        )
    return result, evaluate_called["n"], hook_called["n"]


def main() -> int:
    tmp_root = BASE_DIR / "_test_completeness_tmp"
    if tmp_root.exists():
        shutil.rmtree(tmp_root, ignore_errors=True)
    tmp_root.mkdir(parents=True)
    failures: list[str] = []

    try:
        # ── Case 1: incomplete episode (scene 3 of 5 fails) ────────────────
        script_path = _make_script(tmp_root, 5)
        result, eval_calls, hook_calls = _run_with_mocks(tmp_root, script_path, force_fail_scene=3)
        if result is not None:
            failures.append(f"INCOMPLETE case: expected render_episode() to return None, got {result}")
        if eval_calls != 0:
            failures.append(f"INCOMPLETE case: expected council_evaluator.evaluate() to be called 0 times, got {eval_calls}")
        if hook_calls != 0:
            failures.append(f"INCOMPLETE case: expected on_council_approved() to be called 0 times, got {hook_calls}")
        print(f"[test] INCOMPLETE case — result={result}, evaluate_calls={eval_calls}, hook_calls={hook_calls}")

        # ── Case 2: complete episode (all 5 scenes succeed) ─────────────────
        tmp_root2 = BASE_DIR / "_test_completeness_tmp2"
        if tmp_root2.exists():
            shutil.rmtree(tmp_root2, ignore_errors=True)
        tmp_root2.mkdir(parents=True)
        script_path2 = _make_script(tmp_root2, 5)
        result2, eval_calls2, hook_calls2 = _run_with_mocks(tmp_root2, script_path2, force_fail_scene=None)
        if result2 is None:
            failures.append("COMPLETE case: expected render_episode() to return a path, got None")
        if eval_calls2 != 1:
            failures.append(f"COMPLETE case: expected council_evaluator.evaluate() to be called exactly once, got {eval_calls2}")
        if hook_calls2 != 1:
            failures.append(f"COMPLETE case: expected on_council_approved() to be called exactly once, got {hook_calls2}")
        print(f"[test] COMPLETE case — result={result2}, evaluate_calls={eval_calls2}, hook_calls={hook_calls2}")
        shutil.rmtree(tmp_root2, ignore_errors=True)

    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)

    if failures:
        print("\nFAIL:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nPASS: completeness gate regression test — all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
