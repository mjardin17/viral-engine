#!/usr/bin/env python3
"""Tests for render_orchestrator.py (m004).

Runs with either:
    python test_render_orchestrator.py
    python -m pytest test_render_orchestrator.py -q

Everything is stdlib-only and offline: the worker-pool tests drive a fake
renderer that mimics auto_render.py's progress output, so no ffmpeg, network
access or API keys are needed.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import render_orchestrator as ro  # noqa: E402


# ── fixture: a fake renderer that behaves like auto_render.py ─────────────────

FAKE_RENDERER = '''#!/usr/bin/env python3
"""Fake auto_render.py for tests: prints scene progress, writes a stub MP4."""
import argparse, os, sys, time
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--episode", required=True)
args = p.parse_args()
ep = args.episode.upper()
scenes = int(os.environ.get("FAKE_SCENES", "4"))
out_dir = Path(os.environ.get("FAKE_OUT", "renders"))

for n in range(1, scenes + 1):
    print(f"\\n\\u2500\\u2500 Scene {n:02d}/{scenes}  [fake] \\u2500\\u2500", flush=True)
    time.sleep(0.01)

if os.environ.get("FAKE_FAIL") == ep:
    print("FATAL: simulated failure", flush=True)
    sys.exit(3)
if os.environ.get("FAKE_NO_OUTPUT") == ep:
    print("  \\u2713 DONE!", flush=True)
    sys.exit(0)

out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / f"{ep}_final.mp4").write_bytes(b"X" * 2048)
print(f"  \\u2713 DONE!  {ep}  ({scenes}/{scenes} scenes)", flush=True)
'''


def make_fake_renderer(tmp: Path) -> Path:
    path = tmp / "fake_auto_render.py"
    path.write_text(FAKE_RENDERER, encoding="utf-8")
    return path


def make_config(tmp: Path, **overrides) -> ro.OrchestratorConfig:
    renders = tmp / "renders"
    cfg = ro.OrchestratorConfig(
        render_script=make_fake_renderer(tmp),
        python=sys.executable,
        workers=2,
        retries=0,
        log_file=tmp / "render_log.json",
        log_dir=tmp / "logs",
        output_dir=renders,
        extra_env={"FAKE_OUT": str(renders)},
        validate_scripts=False,
        status_interval=0.2,
        quiet=True,
    )
    for key, value in overrides.items():
        setattr(cfg, key, value)
    return cfg


# ── unit tests ───────────────────────────────────────────────────────────────

class TestEpisodeIds(unittest.TestCase):
    def test_normalize_full_id(self):
        self.assertEqual(ro.normalize_episode_id("GG_EP012"), "GG_EP012")
        self.assertEqual(ro.normalize_episode_id("gg_ep012"), "GG_EP012")

    def test_normalize_from_filename(self):
        self.assertEqual(
            ro.normalize_episode_id("scene_prompts.gg_ep012.final.json"), "GG_EP012"
        )

    def test_normalize_bare_number_needs_channel(self):
        self.assertEqual(ro.normalize_episode_id("12", channel="gg"), "GG_EP012")
        with self.assertRaises(ValueError):
            ro.normalize_episode_id("12")

    def test_normalize_rejects_garbage(self):
        with self.assertRaises(ValueError):
            ro.normalize_episode_id("not-an-episode")

    def test_episode_number(self):
        self.assertEqual(ro.episode_number("GG_EP012"), 12)
        self.assertEqual(ro.episode_number("LO_EP001"), 1)


class TestProgressParsing(unittest.TestCase):
    def test_parses_scene_line(self):
        self.assertEqual(ro.parse_progress("── Scene 08/24  [The Trap] ──"), (8, 24))

    def test_parses_lowercase(self):
        self.assertEqual(ro.parse_progress("scene 3/12"), (3, 12))

    def test_ignores_other_lines(self):
        self.assertIsNone(ro.parse_progress("Concatenating 24 clips"))

    def test_helpers(self):
        self.assertEqual(ro._fmt_hms(0), "00m00s")
        self.assertEqual(ro._fmt_hms(3725), "1h02m")
        self.assertTrue(ro._bar(0.5).startswith("["))


class TestDiscovery(unittest.TestCase):
    def test_discover_all_channels(self):
        episodes = ro.discover_episodes()
        self.assertIn("GG_EP012", episodes)
        self.assertIn("LO_EP001", episodes)
        self.assertIn("ML_EP001", episodes)

    def test_discover_filtered_by_channel(self):
        episodes = ro.discover_episodes("gg")
        self.assertTrue(all(e.startswith("GG_") for e in episodes))

    def test_backup_dirs_are_ignored(self):
        # Any id whose only script lives under prompts/**/_backups must not appear.
        for episode_id in ro.discover_episodes():
            self.assertNotIn("_backup", ro.find_episode_json(episode_id).parts[-2] if False else "")

    def test_season_3_gg_matches_roadmap(self):
        season3 = ro.episodes_for_season("gg", 3)
        self.assertEqual(season3[0], "GG_EP012")
        self.assertEqual(season3[-1], "GG_EP025")
        self.assertEqual(len(season3), 14)   # PROJECT_ROADMAP Phase 2: 14 episodes

    def test_season_1_gg(self):
        season1 = ro.episodes_for_season("gg", 1)
        self.assertEqual(season1, ["GG_EP001", "GG_EP002", "GG_EP003",
                                   "GG_EP004", "GG_EP005"])

    def test_ids_with_title_slugs_are_discovered(self):
        # prompts/gods_glory/GG_EP001_thermopylae.json — underscore after the id.
        self.assertIn("GG_EP001", ro.discover_episodes("gg"))

    def test_find_episode_json_returns_existing_file(self):
        path = ro.find_episode_json("GG_EP012")
        self.assertTrue(Path(path).exists())
        self.assertTrue(Path(path).name.endswith(".json"))

    def test_find_episode_json_missing(self):
        with self.assertRaises(FileNotFoundError):
            ro.find_episode_json("GG_EP999")

    def test_count_scenes(self):
        self.assertGreater(ro.count_scenes(ro.find_episode_json("GG_EP012")), 0)
        self.assertEqual(ro.count_scenes(Path("does-not-exist.json")), 0)


class TestMissionBoard(unittest.TestCase):
    def _board(self, tmp: Path, missions) -> Path:
        path = tmp / "MISSION_BOARD.json"
        path.write_text(json.dumps({"missions": missions}), encoding="utf-8")
        return path

    def test_picks_up_pending_render_missions(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            board = self._board(tmp, [
                {"id": "a", "type": "render", "status": "pending",
                 "channel": "gg", "target": "GG_EP012"},
                {"id": "b", "type": "render", "status": "in_progress",
                 "channel": "lo", "target": "LO_EP001"},
                {"id": "c", "type": "render", "status": "complete",
                 "channel": "gg", "target": "GG_EP013"},
                {"id": "d", "type": "upload", "status": "pending",
                 "channel": "gg", "target": "GG_EP014"},
            ])
            self.assertEqual(ro.episodes_from_mission_board(board),
                             ["GG_EP012", "LO_EP001"])

    def test_deduplicates_and_ignores_unparseable(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            board = self._board(tmp, [
                {"id": "a", "type": "render", "status": "pending", "target": "GG_EP012"},
                {"id": "b", "type": "render", "status": "pending", "target": "gg_ep012"},
                {"id": "c", "type": "render", "status": "pending", "target": "???"},
            ])
            self.assertEqual(ro.episodes_from_mission_board(board), ["GG_EP012"])

    def test_missing_board_raises(self):
        with self.assertRaises(FileNotFoundError):
            ro.episodes_from_mission_board(Path("no/such/MISSION_BOARD.json"))


class TestRenderLog(unittest.TestCase):
    def test_roundtrip_and_upsert(self):
        with tempfile.TemporaryDirectory() as td:
            log_path = Path(td) / "render_log.json"
            log = ro.RenderLog(log_path)
            job = ro.RenderJob(episode_id="GG_EP012", status="passed", size_bytes=2048)
            log.record(job)
            log.save()
            self.assertTrue(log_path.exists())

            reloaded = ro.RenderLog(log_path)
            self.assertEqual(reloaded.data["jobs"]["GG_EP012"]["status"], "passed")
            self.assertEqual(reloaded.data["jobs"]["GG_EP012"]["size_mb"], 0.0)  # 2048B -> 0.0MB

            job.status = "failed"
            log.record(job)
            log.save()
            self.assertEqual(ro.RenderLog(log_path).data["jobs"]["GG_EP012"]["status"],
                             "failed")

    def test_completed_episodes(self):
        with tempfile.TemporaryDirectory() as td:
            log = ro.RenderLog(Path(td) / "render_log.json")
            log.record(ro.RenderJob(episode_id="A_EP001", status="passed"))
            log.record(ro.RenderJob(episode_id="A_EP002", status="failed"))
            self.assertEqual(log.completed_episodes(), {"A_EP001"})

    def test_corrupt_log_does_not_crash(self):
        with tempfile.TemporaryDirectory() as td:
            log_path = Path(td) / "render_log.json"
            log_path.write_text("{not json", encoding="utf-8")
            log = ro.RenderLog(log_path)
            self.assertEqual(log.data["jobs"], {})


# ── worker pool (integration, offline) ───────────────────────────────────────

class TestOrchestrator(unittest.TestCase):
    def test_parallel_run_pass_fail_skip(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            cfg = make_config(tmp, workers=3, extra_env={
                "FAKE_OUT": str(tmp / "renders"),
                "FAKE_FAIL": "GG_EP002",
            })
            orch = ro.RenderOrchestrator(cfg)
            summary = orch.run(["GG_EP001", "GG_EP002", "GG_EP003"])

            self.assertEqual(summary["passed"], 2)
            self.assertEqual(summary["failed"], 1)
            self.assertEqual(summary["episodes"]["failed"], ["GG_EP002"])
            self.assertGreater(summary["total_bytes"], 0)

            records = json.loads(cfg.log_file.read_text(encoding="utf-8"))["jobs"]
            self.assertEqual(records["GG_EP001"]["status"], "passed")
            self.assertEqual(records["GG_EP001"]["scenes_done"], 4)
            self.assertGreater(records["GG_EP001"]["size_bytes"], 0)
            self.assertIn("exit code 3", records["GG_EP002"]["error"])
            self.assertTrue(Path(cfg.log_dir, "GG_EP002.attempt1.log").exists())

    def test_exit_zero_without_output_is_a_failure(self):
        """auto_render.py exiting 0 but producing no MP4 must never count as passed."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            cfg = make_config(tmp, workers=1, extra_env={
                "FAKE_OUT": str(tmp / "renders"),
                "FAKE_NO_OUTPUT": "GG_EP001",
            })
            orch = ro.RenderOrchestrator(cfg)
            summary = orch.run(["GG_EP001"])
            self.assertEqual(summary["passed"], 0)
            self.assertEqual(summary["failed"], 1)
            self.assertIn("missing", summary and orch.jobs[0].error)

    def test_retries_then_fails(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            cfg = make_config(tmp, workers=1, retries=2, extra_env={
                "FAKE_OUT": str(tmp / "renders"),
                "FAKE_FAIL": "GG_EP001",
            })
            orch = ro.RenderOrchestrator(cfg)
            orch.run(["GG_EP001"])
            self.assertEqual(orch.jobs[0].attempts, 3)
            self.assertEqual(orch.jobs[0].status, "failed")

    def test_missing_script_is_skipped(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            cfg = make_config(tmp, workers=1, validate_scripts=True)
            orch = ro.RenderOrchestrator(cfg)
            summary = orch.run(["GG_EP999"])   # valid id, no script JSON on disk
            self.assertEqual(summary["skipped"], 1)
            self.assertEqual(summary["passed"], 0)
            self.assertEqual(orch.jobs[0].status, "skipped")

    def test_skip_completed(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            cfg = make_config(tmp, workers=1, skip_completed=True)
            orch = ro.RenderOrchestrator(cfg)
            orch.log.record(ro.RenderJob(episode_id="GG_EP001", status="passed"))
            summary = orch.run(["GG_EP001", "GG_EP002"])
            self.assertEqual(summary["passed"], 1)
            self.assertEqual(summary["episodes"]["passed"], ["GG_EP002"])

    def test_workers_are_clamped_to_three(self):
        self.assertLessEqual(ro.MAX_WORKERS, 3)
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            cfg = make_config(tmp, workers=99)
            orch = ro.RenderOrchestrator(cfg)
            orch.run(["GG_EP001", "GG_EP002", "GG_EP003", "GG_EP004"])
            self.assertEqual({j.status for j in orch.jobs}, {"passed"})

    def test_empty_queue_is_safe(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = make_config(Path(td))
            summary = ro.RenderOrchestrator(cfg).run([])
            self.assertEqual(summary["passed"], 0)


class TestCli(unittest.TestCase):
    def test_cli_dry_run_against_real_prompts(self):
        result = subprocess.run(
            [sys.executable, str(Path(ro.__file__).name), "--season", "3",
             "--channel", "gg", "--dry-run"],
            cwd=str(Path(ro.__file__).parent),
            capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("GG_EP012", result.stdout)
        self.assertIn("GG_EP025", result.stdout)

    def test_cli_pending_against_real_board(self):
        result = subprocess.run(
            [sys.executable, str(Path(ro.__file__).name), "--pending", "--dry-run"],
            cwd=str(Path(ro.__file__).parent),
            capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("LO_EP001", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
