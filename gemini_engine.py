"""
gemini_engine.py — Empire OS script + metadata generator via Gemini API.
Usage: python gemini_engine.py --channel GG --topic "Battle of Lepanto" --scenes 60
"""
import os
import json
import argparse
import glob
import google.generativeai as genai
from dotenv import load_dotenv
from typing import Dict, Any, Optional

# --- CONFIGURATION ---
_ENV_PATH = os.path.join(os.path.dirname(__file__), "echoes-council", ".env")
load_dotenv(dotenv_path=_ENV_PATH)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

CHANNEL_CONTEXTS: Dict[str, str] = {
    "GG": "Gods & Glory: cinematic history/battle documentary, adult audience",
    "ED": "Empire Decoded: AI/tech explainer channel",
    "LO": "Little Olympus: Greek mythology, kids + adults",
    "IL": "Iron Legends: original IP 80s cartoon mech/robot anime",
    "EO": "Echoes of Eternity: lost civilizations documentary, mystery tone",
}

CHANNEL_PROMPT_DIRS: Dict[str, str] = {
    "GG": "prompts/gods_glory",
    "ED": "prompts/empire_decoded",
    "LO": "prompts/little_olympus",
    "IL": "prompts/iron_legends",
    "EO": "prompts/echoes",
}


def _next_episode_id(channel: str) -> str:
    """Find the highest existing EP number for this channel and return the next one."""
    prompt_dir = os.path.join(os.path.dirname(__file__), CHANNEL_PROMPT_DIRS.get(channel, f"prompts/{channel.lower()}"))
    existing = glob.glob(os.path.join(prompt_dir, f"{channel}_EP*.json"))
    if not existing:
        return f"{channel}_EP001"
    nums = []
    for f in existing:
        base = os.path.basename(f)
        try:
            nums.append(int(base.replace(f"{channel}_EP", "").replace(".json", "")))
        except ValueError:
            pass
    next_num = max(nums) + 1 if nums else 1
    return f"{channel}_EP{next_num:03d}"


# --- ENGINE FUNCTIONS ---
def call_gemini(prompt: str, model_name: str) -> Dict[str, Any]:
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"},
        )
        return json.loads(response.text)
    except Exception as e:
        return {"error": str(e), "status": "failed"}


def generate_script(channel: str, topic: str, num_scenes: int = 60) -> Dict[str, Any]:
    episode_id = _next_episode_id(channel)
    prompt = f"""
You are a professional documentary scriptwriter for {CHANNEL_CONTEXTS.get(channel, 'a YouTube channel')}.

Write a full video script about: "{topic}"

STRICT REQUIREMENTS:
- Exactly {num_scenes} scenes
- Each scene narration: 85-100 words
- Total duration_sec across all scenes: >= 2700 seconds
- Every visual_prompt must be completely unique — no scene reuse ever
- bg_colors: two dark hex colors that match the scene mood

Return ONLY valid JSON in this exact structure:
{{
  "channel": "{channel}",
  "episode_id": "{episode_id}",
  "title": "Compelling episode title",
  "scenes": [
    {{
      "scene_number": 1,
      "type": "intro",
      "title": "Scene title",
      "narration": "85-100 words of narration here",
      "visual_prompt": "Highly detailed, unique image generation prompt",
      "bg_colors": ["#1a0a00", "#2a1000"],
      "duration_sec": 45
    }}
  ]
}}

Scene types to use: intro, narration, outro (only 1 intro and 1 outro, rest are narration)
"""
    return call_gemini(prompt, "gemini-1.5-pro")


def generate_metadata(episode_json: Dict[str, Any]) -> Dict[str, Any]:
    channel = episode_json.get("channel", "")
    title = episode_json.get("title", "")
    scenes = episode_json.get("scenes", [])
    narrations = " ".join(s.get("narration", "") for s in scenes[:5])

    prompt = f"""
Create YouTube metadata for this video:
Channel: {CHANNEL_CONTEXTS.get(channel, channel)}
Title: {title}
Opening narration summary: {narrations}

Return ONLY valid JSON:
{{
  "titles": ["Title option 1", "Title option 2", "Title option 3"],
  "description": "Full YouTube description with hook, episode breakdown, and subscribe CTA",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8", "tag9", "tag10", "tag11", "tag12", "tag13", "tag14", "tag15", "tag16", "tag17", "tag18", "tag19", "tag20"],
  "chapters": ["0:00 Introduction", "1:30 Section 2"]
}}
"""
    return call_gemini(prompt, "gemini-1.5-flash")


def quality_check(episode_json: Dict[str, Any]) -> Dict[str, Any]:
    scenes = episode_json.get("scenes", [])
    total_duration = sum(s.get("duration_sec", 0) for s in scenes)
    short_narration = [s["scene_number"] for s in scenes if len(s.get("narration", "").split()) < 80]

    prompt = f"""
Audit this video script for quality. Check:
- Narration word count (should be 85-100 words per scene)
- Visual prompt uniqueness (flag any that seem repeated)
- Scene flow and pacing
- Total duration: {total_duration}s (needs >= 2700s)
- Scenes with short narration detected: {short_narration}

Script title: {episode_json.get('title')}
Scene count: {len(scenes)}

Return ONLY valid JSON:
{{
  "score": 85,
  "passed": true,
  "issues": ["issue description if any"],
  "total_duration_sec": {total_duration},
  "short_narration_scenes": {short_narration}
}}
"""
    return call_gemini(prompt, "gemini-1.5-flash")


# --- CLI ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Empire OS Gemini Script Engine")
    parser.add_argument("--channel", required=True, choices=["GG", "ED", "LO", "IL", "EO"])
    parser.add_argument("--topic", required=True, help="Episode topic")
    parser.add_argument("--scenes", type=int, default=60)
    parser.add_argument("--test", action="store_true", help="Test API connection only")
    args = parser.parse_args()

    if args.test:
        print("Testing Gemini API connection...")
        result = call_gemini("Say OK in JSON like {\"status\": \"OK\"}", "gemini-1.5-flash")
        if result.get("status") == "OK":
            print("✓ Gemini API connected and working")
        else:
            print(f"✗ API issue: {result}")
    else:
        print(f"[1/3] Generating {args.scenes}-scene script for {args.channel}: {args.topic}")
        script = generate_script(args.channel, args.topic, args.scenes)
        if "error" in script:
            print(f"✗ Script generation failed: {script['error']}")
            exit(1)

        print(f"[2/3] Generating metadata...")
        meta = generate_metadata(script)

        print(f"[3/3] Running quality check...")
        check = quality_check(script)

        # Save script to prompts folder
        prompt_dir = os.path.join(os.path.dirname(__file__), CHANNEL_PROMPT_DIRS.get(args.channel, "prompts"))
        os.makedirs(prompt_dir, exist_ok=True)
        script_path = os.path.join(prompt_dir, f"{script['episode_id']}.json")
        with open(script_path, "w", encoding="utf-8") as f:
            json.dump(script, f, indent=2, ensure_ascii=False)

        # Save metadata alongside script
        meta_path = script_path.replace(".json", "_metadata.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({"metadata": meta, "audit": check}, f, indent=2, ensure_ascii=False)

        score = check.get("score", "N/A")
        passed = check.get("passed", False)
        print(f"\n{'✓' if passed else '!'} Done — Audit score: {score}/100")
        print(f"  Script: {script_path}")
        print(f"  Metadata: {meta_path}")
        if not passed:
            print(f"  Issues: {check.get('issues', [])}")
