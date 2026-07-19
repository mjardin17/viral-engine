#!/usr/bin/env python3
"""
Empire OS — Episode Credit Planner
Budget optimizer for Higgsfield credit-stretching. Run BEFORE committing an
episode to render so Josh can see the cost breakdown and interactively adjust
scene tiers to hit a target budget.

Usage:
    python episode_credit_planner.py prompts/little_olympus/LO_EP002.json
    python episode_credit_planner.py <script.json> --budget 50 --approved
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

BASE_DIR: Path = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scene_classifier import classify_episode, estimate_episode_cost, _print_report

TAG = "[credit_planner]"


class EpisodeCreditPlanner:
    """Interactive budget planner — shows cost, lets Josh adjust tiers to fit budget."""

    def __init__(self, script_path: str, max_hf_video: int = 4, max_hf_image: int = 8):
        self.script_path = Path(script_path)
        self.max_hf_video = max_hf_video
        self.max_hf_image = max_hf_image
        self.classification = classify_episode(str(self.script_path), max_hf_video, max_hf_image)
        self.cost = estimate_episode_cost(self.classification)
        self.approved = False

    def show_plan(self) -> str:
        """Print formatted budget plan."""
        buf = []
        buf.append(f"\n{TAG} Budget Plan for {self.classification['episode_id']}\n")
        buf.append(f"Script: {self.script_path}\n")
        _print_report(self.classification, self.cost)
        return "\n".join(buf)

    def set_budget(self, max_credits: float) -> bool:
        """Adjust scene tiers downward to fit budget. Returns True if successful."""
        current_credits = self.cost["higgsfield_credits_est"]
        if current_credits <= max_credits:
            print(f"{TAG} Already within budget: {current_credits:.1f} <= {max_credits:.1f}")
            return True

        print(f"\n{TAG} Over budget by {current_credits - max_credits:.1f} credits.")
        print(f"Downgrading low-priority scenes...")

        # Find higgsfield_image scenes (lowest priority) and downgrade to free
        scenes = self.classification["scenes"]
        downgraded = 0
        for scene in scenes:
            if current_credits <= max_credits:
                break
            if scene["render_tier"] == "higgsfield_image":
                old_tier = scene["render_tier"]
                scene["render_tier"] = "free"
                scene["reason"] = f"Downgraded from {old_tier} to fit budget"
                current_credits -= 2.5
                downgraded += 1
                print(f"  ↓ {scene['scene_id']}: {old_tier} → free")

        # If still over, downgrade higgsfield_video (but preserve explicit peaks)
        for scene in scenes:
            if current_credits <= max_credits:
                break
            if (
                scene["render_tier"] == "higgsfield_video"
                and not scene.get("is_peak_moment")
            ):
                old_tier = scene["render_tier"]
                scene["render_tier"] = "higgsfield_image"
                scene["reason"] = f"Downgraded from {old_tier} to fit budget"
                current_credits -= 7.5
                downgraded += 1
                print(f"  ↓ {scene['scene_id']}: {old_tier} → higgsfield_image")

        # Recalculate
        summary = self.classification["summary"]
        tier_counts = {t: 0 for t in ["higgsfield_video", "higgsfield_image", "composited", "free"]}
        for scene in scenes:
            tier_counts[scene["render_tier"]] += 1
        summary["tier_counts"] = tier_counts

        self.cost = estimate_episode_cost(self.classification)
        if self.cost["higgsfield_credits_est"] <= max_credits:
            print(f"\n{TAG} ✓ Within budget after downgrading {downgraded} scene(s)")
            print(f"New estimate: {self.cost['higgsfield_credits_est']:.1f} credits")
            return True
        else:
            print(
                f"\n{TAG} ⚠ Still over budget even after downgrading. "
                f"Need {self.cost['higgsfield_credits_est'] - max_credits:.1f} more cuts."
            )
            return False

    def swap_scene_tier(self, scene_id: str, new_tier: str) -> bool:
        """Manually override a scene's tier."""
        for scene in self.classification["scenes"]:
            if scene["scene_id"] == scene_id:
                old = scene["render_tier"]
                scene["render_tier"] = new_tier
                scene["reason"] = f"Manual override: {old} → {new_tier}"

                # Recalculate
                summary = self.classification["summary"]
                tier_counts = {t: 0 for t in ["higgsfield_video", "higgsfield_image", "composited", "free"]}
                for s in self.classification["scenes"]:
                    tier_counts[s["render_tier"]] += 1
                summary["tier_counts"] = tier_counts

                self.cost = estimate_episode_cost(self.classification)
                print(f"{TAG} Scene {scene_id}: {old} → {new_tier}")
                print(f"New estimate: {self.cost['higgsfield_credits_est']:.1f} credits")
                return True
        print(f"{TAG} Scene {scene_id} not found")
        return False

    def approve(self) -> Path:
        """Mark plan as approved and write render_plan.json."""
        self.approved = True
        plan = {
            **self.classification,
            "cost_estimate": self.cost,
            "approved": True,
        }
        out_path = self.script_path.parent / f"{self.classification['episode_id']}_render_plan.json"
        out_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
        print(f"\n{TAG} ✓ Render plan approved and saved: {out_path}")
        return out_path

    def total_cost_summary(self) -> dict:
        """Return full cost summary."""
        return {
            "episode_id": self.classification["episode_id"],
            "total_scenes": self.cost["total_scenes"],
            "higgsfield_credits_est": self.cost["higgsfield_credits_est"],
            "fal_cost_usd": self.cost["fal_cost_usd"],
            "breakdown": self.cost["breakdown"],
            "approved": self.approved,
        }


def main():
    parser = argparse.ArgumentParser(description="Budget planner for Higgsfield-stretching episodes")
    parser.add_argument("script_path", help="Path to episode JSON script")
    parser.add_argument("--max-higgsfield-video", type=int, default=4)
    parser.add_argument("--max-higgsfield-image", type=int, default=8)
    parser.add_argument("--budget", type=float, help="Target max Higgsfield credits")
    parser.add_argument("--approved", action="store_true", help="Auto-approve and save render plan")
    args = parser.parse_args()

    planner = EpisodeCreditPlanner(args.script_path, args.max_higgsfield_video, args.max_higgsfield_image)
    print(planner.show_plan())

    if args.budget:
        if planner.set_budget(args.budget):
            print(f"\n{TAG} Budget adjustment successful")
        else:
            print(f"\n{TAG} ⚠ Could not fully fit budget — manual adjustments needed")

    if args.approved:
        planner.approve()
    else:
        print(f"\n{TAG} To save and approve this plan, run with --approved flag")
        print(f"{TAG} Or make manual adjustments and re-run")


if __name__ == "__main__":
    main()
