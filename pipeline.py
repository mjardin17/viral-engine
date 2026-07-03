#!/usr/bin/env python3
"""
pipeline.py

LEGEND EMPIRE video pre-production pipeline.

Usage:
  python3 pipeline.py --auto

In --auto mode:
  1. Reads episode_state.json to find the next episode number/topic.
  2. Calls bots/gemini_bot.py to draft a scene/shot list for that episode.
  3. Calls bots/chatgpt_bot.py to QA the draft.
  4. Writes prompts/scene_prompts.epNNN.final.json.
  5. Advances next_episode_number in episode_state.json and records history.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(ROOT, "episode_state.json")
PROMPTS_DIR = os.path.join(ROOT, "prompts")
BOTS_DIR = os.path.join(ROOT, "bots")
BACKUPS_DIR = os.path.join(ROOT, "_backups")


def load_state():
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    # Save primary copy
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

    # Save redundant backups (timestamped + rolling "latest")
    os.makedirs(BACKUPS_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    with open(os.path.join(BACKUPS_DIR, f"episode_state.{ts}.json"), "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    with open(os.path.join(BACKUPS_DIR, "episode_state.latest.json"), "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def run_bot(script_name, input_payload):
    script_path = os.path.join(BOTS_DIR, script_name)
    proc = subprocess.run(
        [sys.executable, script_path],
        input=json.dumps(input_payload),
        capture_output=True,
        text=True,
        check=True,
    )
    if proc.stderr.strip():
        print(f"[{script_name} stderr] {proc.stderr.strip()}", file=sys.stderr)
    return json.loads(proc.stdout)


def pick_topic(state, episode_number):
    backlog = state.get("topic_backlog", [])
    if not backlog:
        return f"Untitled Episode {episode_number}"
    idx = (episode_number - 1) % len(backlog)
    return backlog[idx]


def write_final(result, episode_number):
    os.makedirs(PROMPTS_DIR, exist_ok=True)
    filename = f"scene_prompts.ep{episode_number:03d}.final.json"
    final_path = os.path.join(PROMPTS_DIR, filename)
    with open(final_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    # Redundant backups of the final shot list too
    os.makedirs(BACKUPS_DIR, exist_ok=True)
    with open(os.path.join(BACKUPS_DIR, filename), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    with open(os.path.join(BACKUPS_DIR, f"{filename}.{ts}.bak"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    return final_path


def run_auto():
    state = load_state()
    episode_number = state.get("next_episode_number", 1)
    topic = pick_topic(state, episode_number)
    series_name = state.get("series_name", "LEGEND EMPIRE")

    print(f"=== {series_name}: generating episode {episode_number:03d} ===")
    print(f"Topic: {topic}")

    gemini_input = {
        "series_name": series_name,
        "episode_number": episode_number,
        "topic": topic,
    }
    print("Running gemini_bot.py ...")
    draft = run_bot("gemini_bot.py", gemini_input)
    print(f"  gemini source: {draft.get('source')}")

    print("Running chatgpt_bot.py (QA) ...")
    final = run_bot("chatgpt_bot.py", draft)
    print(f"  chatgpt source: {final.get('generation', {}).get('chatgpt_source')}")
    for note in final.get("qa_notes", []):
        print(f"  QA: {note}")

    final_path = write_final(final, episode_number)
    print(f"Wrote {final_path}")

    # Advance state
    state["next_episode_number"] = episode_number + 1
    history_entry = {
        "episode_number": episode_number,
        "topic": topic,
        "title": final.get("title", topic),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gemini_source": final.get("generation", {}).get("gemini_source"),
        "chatgpt_source": final.get("generation", {}).get("chatgpt_source"),
        "prompts_file": os.path.relpath(final_path, ROOT),
    }
    state.setdefault("history", []).append(history_entry)
    save_state(state)
    print(f"Updated episode_state.json -> next_episode_number = {state['next_episode_number']}")
    print("Saved redundant backups to _backups/ (timestamped + latest).")


def main():
    if "--auto" in sys.argv:
        run_auto()
    else:
        print("Usage: python3 pipeline.py --auto")
        sys.exit(1)


if __name__ == "__main__":
    main()
