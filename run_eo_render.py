"""
run_eo_render.py — Renders all Echoes of Eternity episodes sequentially.
Calls auto_render.py for each EO episode found in prompts/echoes/.
"""

import subprocess
import sys
import os
import glob
import json

PYTHON = r"C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe"
SCRIPT = os.path.join(os.path.dirname(__file__), "auto_render.py")
PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts", "echoes")


def get_eo_episodes():
    """Find all EO episode JSON files sorted by episode number."""
    pattern = os.path.join(PROMPTS_DIR, "EO_EP*.json")
    files = sorted(glob.glob(pattern))
    return files


def main():
    episodes = get_eo_episodes()
    if not episodes:
        print("No EO episodes found in prompts/echoes/")
        sys.exit(1)

    print(f"Found {len(episodes)} EO episode(s) to render:")
    for ep in episodes:
        fname = os.path.basename(ep)
        # Read episode title
        try:
            with open(ep, "r", encoding="utf-8") as f:
                data = json.load(f)
            title = data.get("title", fname)
            scene_count = len(data.get("scenes", []))
            print(f"  {fname} — {title} ({scene_count} scenes)")
        except Exception:
            print(f"  {fname}")

    print("\n" + "="*60)
    print("STARTING ECHOES OF ETERNITY RENDER")
    print("="*60 + "\n")

    for i, ep_path in enumerate(episodes):
        ep_id = os.path.basename(ep_path).replace(".json", "")
        print(f"\n[{i+1}/{len(episodes)}] Rendering {ep_id}...")
        print("-" * 40)

        result = subprocess.run(
            [PYTHON, SCRIPT, ep_id],
            capture_output=False,
            text=True
        )

        if result.returncode == 0:
            print(f"✓ {ep_id} complete.")
        else:
            print(f"✗ {ep_id} FAILED (exit code {result.returncode}). Continuing...")

    print("\n" + "="*60)
    print("ALL EO RENDERS COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()
