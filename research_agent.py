#!/usr/bin/env python3
"""
research_agent.py — Autonomous Research Agent for Viral Engine

Replaces the manual research stage completely.
Pipeline: Topic Discovery → Research → Score → Reject → Script Generation → JSON Output

Usage:
    python research_agent.py --channel gg
    python research_agent.py --channel ml
    python research_agent.py --channel lo
    python research_agent.py --channel gg --topic "Battle of Salamis"
    python research_agent.py --channel gg --dry-run

Output:
    prompts/gods_glory/scene_prompts.gg_ep027.final.json  (fully populated, render-ready)
    prompts/mech_legends/scene_prompts.ml_ep002.final.json
    prompts/little_olympus/scene_prompts.lo_ep002.final.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent
PROMPTS_DIR = BASE_DIR / "prompts"
LOG_FILE    = BASE_DIR / "research_agent.log"

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_MODEL    = "gemini-2.0-flash"
GEMINI_FALLBACK = "gemini-1.5-flash"

QUALITY_THRESHOLD = 72   # Reject topics scoring below this (out of 100)
MAX_CANDIDATES    = 5    # How many topics to evaluate before selecting the best

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("research_agent")

# ── .env loader ───────────────────────────────────────────────────────────────
def _load_dotenv():
    env = BASE_DIR / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v

_load_dotenv()

# ── Channel definitions ───────────────────────────────────────────────────────
CHANNEL_CONFIGS = {
    "gg": {
        "name":          "Gods & Glory",
        "handle":        "@GodsAndGloryAI",
        "prefix":        "GG",
        "prompts_subdir": "gods_glory",
        "scene_count":   24,
        "scene_duration": 47,
        "aesthetic":     "cinematic documentary",
        "narrator_tone": "authoritative, dramatic, documentary",
        "bg_colors_pool": [
            ["#8B0000","#1A1A2E","#C9A227"],
            ["#1A1A2E","#4A3728","#8B8B6B"],
            ["#2C3E1A","#8B6914","#4A2810"],
            ["#1A2E3E","#4A6878","#8B8B6B"],
            ["#C9A227","#2C1A00","#8B1A1A"],
            ["#2C1A00","#8B1A1A","#4A4A4A"],
        ],
        "system_prompt": (
            "You are the head writer for Gods & Glory, a YouTube documentary channel "
            "that covers history's greatest battles and turning points. Your episodes "
            "are cinematic, dramatic, and rigorously historically accurate. You write "
            "with the authority of a historian and the pacing of a filmmaker. "
            "Your narrations are punchy, vivid, and 18–20 minutes long across 24 scenes."
        ),
    },
    "ml": {
        "name":          "Mech Legends",
        "handle":        "@MechLegendsTV",
        "prefix":        "ML",
        "prompts_subdir": "mech_legends",
        "scene_count":   10,
        "scene_duration": 9,
        "aesthetic":     "cinematic action anime, high-energy, dynamic",
        "narrator_tone": "urgent, epic, cinematic action",
        "bg_colors_pool": [
            ["#CC0000","#1A1A2E","#8B008B"],
            ["#FF6B00","#1A1A2E","#CC0000"],
            ["#1A1A2E","#8B008B","#3A0A5E"],
        ],
        "system_prompt": (
            "You are the head writer for Mech Legends, a YouTube animated series "
            "about giant mecha robots in epic battles. Your episodes are 90-second "
            "action-packed stories following BLAZE (hero, red mech) and RUMBLE "
            "(villain, dark mech) and their allies. Each episode has 10 fast scenes "
            "with extreme action, emotional stakes, and a cliffhanger ending."
        ),
    },
    "lo": {
        "name":          "Little Olympus",
        "handle":        "@LittleOlympusTV",
        "prefix":        "LO",
        "prompts_subdir": "little_olympus",
        "scene_count":   7,
        "scene_duration": 9,
        "aesthetic":     "bright kids cartoon, CoComelon energy, big expressive eyes",
        "narrator_tone": "warm, playful, encouraging",
        "bg_colors_pool": [
            ["#FFD700","#1A1060","#00B4E6"],
            ["#FF6B35","#FFD700","#1A1060"],
            ["#00B4E6","#FFD700","#FF6B35"],
        ],
        "system_prompt": (
            "You are the head writer for Little Olympus, a YouTube kids channel "
            "about baby versions of Greek gods having fun adventures on Mount Olympus. "
            "Little Zeus is 5 years old, curious, and brave. Athena is smart. "
            "Hermes is fast and mischievous. Episodes are 7 scenes, ~9 seconds each, "
            "and always teach a simple life lesson in a warm, funny way."
        ),
    },
}

# ── Topic Pools (large, curated, avoids existing episodes) ────────────────────
TOPIC_POOLS = {
    "gg": [
        # Ancient World
        "Battle of Salamis: How 300 Greek Ships Sank the Persian Empire",
        "Siege of Syracuse: How Athens Destroyed Its Own Empire",
        "Battle of Zama: The Day Hannibal Finally Lost",
        "Alexander at the Hydaspes: The Battle That Stopped a God",
        "Battle of Philippi: The Death of the Roman Republic",
        "Caesar Crosses the Rubicon: The Point of No Return",
        "The Siege of Masada: 960 Jews vs. the Roman Empire",
        "Battle of Actium: The Naval War That Made Augustus Emperor",
        "The Sack of Rome 410 AD: The Day the Unthinkable Happened",
        "Battle of Adrianople: How the Goths Shattered Roman Invincibility",
        "The Battle of Teutoburg Forest: Rome's Greatest Defeat",
        "Hannibal Crosses the Alps: History's Most Audacious March",
        # Medieval
        "Battle of Lepanto: The Naval Battle That Saved Europe from Ottoman Rule",
        "Siege of Jerusalem 1099: The First Crusade's Bloody Triumph",
        "Battle of Ain Jalut: The Day the Mongols Were Stopped",
        "Siege of Constantinople 1204: When Crusaders Sacked the Wrong City",
        "Battle of Crécy: The Arrow Storm That Changed Warfare Forever",
        "The Fall of Baghdad 1258: The Night the Islamic Golden Age Ended",
        "Battle of Mohi: The Day the Mongols Destroyed Hungary",
        "The Black Death Siege of Caffa: How a Plague Ended the Middle Ages",
        "Siege of Acre: The Crusaders' Last Stand",
        "Battle of Kosovo 1389: The Defeat That Defined a Nation for 600 Years",
        "Battle of Nicopolis: Europe's Last Great Crusade",
        "Siege of Rhodes 1522: The Knights of St. John's Final Stand",
        # Early Modern
        "Battle of Pavia: How Spain Captured the King of France",
        "Spanish Armada 1588: The Fleet That Was Meant to Conquer England",
        "Siege of Osaka: The Last Stand of the Toyotomi Clan",
        "Battle of White Mountain: The War That Devastated Europe for 30 Years",
        "Breitenfeld 1631: The Battle That Saved Protestantism",
        "Battle of Rocroi: The Day Spain Lost Its Military Dominance",
        "Battle of Blenheim: Marlborough's Masterpiece",
        "Great Northern War: Charles XII vs Peter the Great",
        "Battle of Poltava: The Defeat That Made Russia a Superpower",
        "Siege of Gibraltar 1779: The Longest Siege in British History",
        "Battle of Plassey: How 3,000 Men Conquered India",
        "Battle of Quebec 1759: The 15-Minute Battle That Made Canada British",
        # Napoleonic & 19th Century
        "Battle of Austerlitz: Napoleon's Greatest Victory",
        "Battle of Borodino: The Bloodiest Day in Napoleon's Empire",
        "Battle of Leipzig: The Battle of Nations That Ended Napoleon's Empire",
        "Battle of Gettysburg: The Three Days That Decided America",
        "Battle of Sedan 1870: The Defeat That Created Modern Germany",
        "Charge of the Light Brigade: The Attack That Should Never Have Happened",
        "Battle of Isandlwana: The Day the Zulus Destroyed a British Army",
        "Battle of Tsushima: The Naval Battle That Shocked the World",
        "Siege of Port Arthur: The Forgotten Battle of the Russo-Japanese War",
        # World War I
        "Battle of Verdun: The Meat Grinder That Bled France White",
        "Battle of the Somme: One Million Casualties in One Battle",
        "Gallipoli: Churchill's Gamble That Ended in Catastrophe",
        "Battle of Jutland: The Greatest Naval Battle in History",
        "The Hundred Days Offensive: How the Allies Won WWI in 100 Days",
        "Lawrence of Arabia and the Arab Revolt",
        "The Christmas Truce of 1914: One Night of Peace in Four Years of Hell",
        "The Meuse-Argonne Offensive: America's Bloodiest Battle",
        # World War II (not already covered)
        "Battle of Britain: The Air War That Saved England",
        "Operation Barbarossa: The Largest Military Invasion in History",
        "Fall of Singapore: Churchill's Greatest Military Disaster",
        "Battle of Monte Cassino: The Monastery That Wouldn't Fall",
        "Operation Overlord Planning: The Secret Behind D-Day",
        "Battle of Kursk: The Largest Tank Battle in History",
        "Battle of Leyte Gulf: The Largest Naval Battle Ever Fought",
        "The Battle of Hurtgen Forest: America's Forgotten Nightmare",
        "Operation Chastise: The Dam Busters Raid",
        "Battle of Berlin 1945: The Final Battle for the Nazi Capital",
        "The Fall of Corregidor: MacArthur's Retreat and Return",
        # Modern
        "Korean War Chosin Reservoir: Marines vs. an Army in a Frozen Hell",
        "Dien Bien Phu: The Battle That Ended French Colonialism",
        "Six Day War 1967: How Israel Won in 132 Hours",
        "Battle of Mogadishu 1993: Black Hawk Down",
        "Operation Desert Storm: The 100-Hour Ground War",
        "Siege of Sarajevo: The Longest Siege in Modern History",
        "Battle of Fallujah: Urban Warfare in the 21st Century",
        # Naval Battles
        "Battle of Trafalgar: Nelson's Last Victory",
        "Battle of Hampton Roads: The First Battle of Ironclads",
        "Sinking of the Bismarck: Europe's Greatest Naval Hunt",
        "Battle of Cape Matapan: The Night Battle That Saved Malta",
        # Sieges & Assaults
        "Siege of Leningrad: 872 Days of Survival",
        "Fall of Saigon: The Helicopter Evacuation That Ended a War",
        "Operation Entebbe: The Most Audacious Rescue Mission Ever",
        "Battle of Dak To: Vietnam's Forgotten Hill Fight",
    ],
    "ml": [
        "BLAZE vs GRANITE: Brothers Divided",
        "The Iron Storm: RUMBLE's Aerial Armada",
        "NOVA's Secret Power Awakening",
        "The Lost Mech Graveyard of Sector 7",
        "BLAZE and the Underwater Fortress",
        "TITAN's Last Stand at the Solar Gate",
        "RUMBLE Steals the Thunder Core",
        "The Great Mech Racing Championship",
        "BLAZE's Emergency Repair in Enemy Territory",
        "The Day the Power Grid Failed",
        "NOVA and the Ancient Mech Temple",
        "RUMBLE's Betrayal of His Own Army",
        "BLAZE Saves the Mech Academy",
        "The Storm That Swallowed the Sky Fleet",
        "GRANITE's Secret Mission Behind Enemy Lines",
        "BLAZE and the Magnetic Disruptor",
        "RUMBLE's Massive Mech Army Invasion",
        "The Battle at the Edge of the World",
        "NOVA Decodes the Ancient War Map",
        "BLAZE's Toughest Training Day Ever",
        "RUMBLE vs. His Own Rebellion",
        "The Midnight Attack on Mech City",
        "BLAZE and the Frozen Canyon Ambush",
        "NOVA's Greatest Invention Goes Wrong",
    ],
    "lo": [
        "Little Zeus and the Lost Thunderbolt",
        "Baby Hercules Tries to Lift a Mountain",
        "Athena's Big Test at School",
        "Little Hermes and the Speedy Shoes",
        "Poseidon Floods the Playground",
        "Baby Aphrodite Makes Everyone Fall in Love",
        "Little Ares and the Paint Fight",
        "Hephaestus Builds a Robot Friend",
        "Little Dionysus and the Magic Grapes",
        "Artemis Loses Her Favorite Arrow",
        "Apollo Sings the Wrong Song",
        "Little Zeus and the Thunderstorm Sleepover",
        "Athena and the Homework Dragon",
        "Hermes Delivers the Wrong Package",
        "Little Persephone Plants a Garden in Hades",
        "Baby Cyclops Tries to Make Friends",
        "Little Zeus and the Cloud Castle",
        "Athena vs. Ares: The Big Argument",
        "Hermes and the Missing Golden Sandal",
        "Little Zeus Shares His Thunderbolt",
        "Poseidon and the Sunken Toy",
        "Baby Medusa Before She Had Snake Hair",
        "Little Achilles Won't Get in the River",
        "Hephaestus's Workshop Gets Too Messy",
    ],
}

# ── Scene type templates per channel ──────────────────────────────────────────
SCENE_TYPES = {
    "gg": [
        "cold_open","context","character_intro","historical","historical",
        "conflict_build","turning_point","battle","battle","aftermath",
        "context","historical","character_moment","battle","pivotal_action",
        "historical","irony","consequence","reflection","battle",
        "historical","aftermath","lesson","outro_cta",
    ],
    "ml": [
        "cold_open","hero_intro","villain_intro","villain_dominance","battle_attempt",
        "darkest_moment","crisis","turning_point","hero_action","cliffhanger",
    ],
    "lo": [
        "hook","setup","problem","attempt","solution","resolution","lesson_and_cta",
    ],
}

# ── Gemini API ────────────────────────────────────────────────────────────────
def gemini_call(prompt: str, temperature: float = 0.7, max_tokens: int = 8192,
                model: str = GEMINI_MODEL) -> str:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in .env")

    url = f"{GEMINI_API_BASE}/{model}:generateContent?key={api_key}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            "responseMimeType": "text/plain",
        },
    }).encode("utf-8")

    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"]
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            if "MODEL_NOT_FOUND" in body and model == GEMINI_MODEL:
                log.warning(f"Model {model} not found, falling back to {GEMINI_FALLBACK}")
                return gemini_call(prompt, temperature, max_tokens, model=GEMINI_FALLBACK)
            log.warning(f"Gemini HTTP error (attempt {attempt}/3): {e.code} — {body[:200]}")
            if attempt < 3:
                time.sleep(5 * attempt)
        except Exception as e:
            log.warning(f"Gemini error (attempt {attempt}/3): {e}")
            if attempt < 3:
                time.sleep(5 * attempt)

    raise RuntimeError("Gemini API failed after 3 attempts")


def gemini_json(prompt: str, temperature: float = 0.4) -> dict | list:
    """Call Gemini and parse JSON from the response."""
    text = gemini_call(prompt, temperature=temperature, max_tokens=16384)
    # Strip markdown code fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text.strip())
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON object/array from the text
        m = re.search(r"(\{[\s\S]+\}|\[[\s\S]+\])", text)
        if m:
            return json.loads(m.group(1))
        raise ValueError(f"Could not parse JSON from Gemini response:\n{text[:500]}")


# ── Topic Discovery ────────────────────────────────────────────────────────────
def scan_existing_topics(channel: str) -> set[str]:
    """Return a set of lowercase topic keywords from already-written scripts."""
    cfg = CHANNEL_CONFIGS[channel]
    subdir = PROMPTS_DIR / cfg["prompts_subdir"]
    keywords: set[str] = set()
    if subdir.exists():
        for f in subdir.glob("*.final.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                title = data.get("title", "").lower()
                # Extract key words (3+ chars)
                keywords.update(w for w in re.findall(r"[a-z]{3,}", title))
            except Exception:
                pass
    return keywords


def select_candidates(channel: str, forced_topic: str | None = None,
                      n: int = MAX_CANDIDATES) -> list[str]:
    """Pick N topic candidates that don't duplicate existing episodes."""
    if forced_topic:
        return [forced_topic]

    existing_kw = scan_existing_topics(channel)
    pool = TOPIC_POOLS.get(channel, [])

    candidates = []
    for topic in pool:
        # Skip if 2+ significant words overlap with existing topics
        topic_words = set(re.findall(r"[a-z]{4,}", topic.lower()))
        overlap = topic_words & existing_kw
        if len(overlap) >= 2:
            continue
        candidates.append(topic)
        if len(candidates) >= n:
            break

    if not candidates:
        log.warning("Pool exhausted — generating new topics via Gemini")
        candidates = generate_topic_suggestions(channel, existing_kw, n)

    return candidates[:n]


def generate_topic_suggestions(channel: str, existing_kw: set[str], n: int = 5) -> list[str]:
    """Ask Gemini to suggest new topics when the pool is exhausted."""
    cfg = CHANNEL_CONFIGS[channel]
    avoid = ", ".join(sorted(existing_kw)[:40])
    prompt = f"""
You are a YouTube content strategist for {cfg['name']} ({cfg['handle']}).
The channel covers: {cfg['aesthetic']}.
Narrator tone: {cfg['narrator_tone']}.

Generate {n} compelling, YouTube-viral episode topics that have NOT been covered yet.
Avoid topics that overlap with these keywords: {avoid}

Return a JSON array of {n} strings, each being a compelling episode title.
Example format: ["Title One: Subtitle", "Title Two: Subtitle", ...]

Return ONLY the JSON array, no other text.
"""
    result = gemini_json(prompt)
    if isinstance(result, list):
        return [str(t) for t in result[:n]]
    return []


# ── Research ──────────────────────────────────────────────────────────────────
def research_topic(topic: str, channel: str) -> dict:
    """
    Deep-research a topic using Gemini.
    Returns structured research notes.
    """
    cfg = CHANNEL_CONFIGS[channel]
    log.info(f"Researching: {topic}")

    prompt = f"""
{cfg['system_prompt']}

Research the following topic in depth for a YouTube documentary episode:
TOPIC: {topic}

Produce a structured research report with these exact fields as JSON:

{{
  "topic": "{topic}",
  "verified_title": "Best YouTube title for this topic (under 80 chars, include year if applicable)",
  "subtitle": "One-line historical context (under 60 chars)",
  "tagline": "One emotional hook sentence (under 100 chars)",
  "viral_hook": "The single most shocking or surprising fact about this topic (1-2 sentences)",
  "villain_mandate": "The antagonist or opposing force and what they represent",
  "lesson": "The universal human lesson this episode teaches",
  "key_facts": [
    "Verified fact 1 with date/number",
    "Verified fact 2 with date/number",
    "Verified fact 3 with date/number",
    "Verified fact 4 with date/number",
    "Verified fact 5 with date/number",
    "Verified fact 6 with date/number",
    "Verified fact 7 with date/number",
    "Verified fact 8 with date/number"
  ],
  "key_figures": [
    {{"name": "Person 1", "role": "Their role", "fate": "What happened to them"}},
    {{"name": "Person 2", "role": "Their role", "fate": "What happened to them"}},
    {{"name": "Person 3", "role": "Their role", "fate": "What happened to them"}}
  ],
  "dramatic_moments": [
    "The most visually dramatic scene from this event",
    "The turning point moment",
    "The most emotionally resonant moment",
    "The surprising or ironic aftermath"
  ],
  "visual_palette": {{
    "primary_mood": "dark/bright/gritty/etc",
    "time_period_aesthetic": "Description of visual era",
    "key_visual_elements": ["element1", "element2", "element3"]
  }},
  "act_structure": [
    {{"act": 1, "title": "Setup", "summary": "What happens in act 1 (scenes 1-8)"}},
    {{"act": 2, "title": "Conflict", "summary": "What happens in act 2 (scenes 9-16)"}},
    {{"act": 3, "title": "Resolution", "summary": "What happens in act 3 (scenes 17-24)"}}
  ],
  "accuracy_confidence": "high/medium/low",
  "accuracy_notes": "Any caveats about historical accuracy or disputed facts"
}}

Return ONLY the JSON object, no markdown, no extra text.
"""
    return gemini_json(prompt)


# ── Quality Scoring ───────────────────────────────────────────────────────────
def score_topic(topic: str, research: dict, channel: str) -> dict:
    """
    Score a researched topic on 4 axes (25 points each = 100 max).
    Returns score dict with breakdown and pass/fail decision.
    """
    cfg = CHANNEL_CONFIGS[channel]
    log.info(f"Scoring: {topic}")

    prompt = f"""
You are a YouTube content quality assessor for {cfg['name']}.
The channel aesthetic is: {cfg['aesthetic']}.

Evaluate this episode topic for YouTube documentary viability.
Score each axis from 0–25:

TOPIC: {topic}
RESEARCH SUMMARY:
- Viral hook: {research.get('viral_hook', '')}
- Key facts count: {len(research.get('key_facts', []))}
- Dramatic moments: {'; '.join(research.get('dramatic_moments', [])[:2])}
- Accuracy confidence: {research.get('accuracy_confidence', 'unknown')}

SCORING AXES (each 0–25):
1. DRAMA SCORE: How emotionally gripping is this? Stakes, conflict, human cost.
2. VISUAL RICHNESS: How many strong cinematic images can be generated? Battles, faces, landscapes.
3. HISTORICAL ACCURACY: How well-documented and verifiable is this? (high=25, medium=15, low=5)
4. YOUTUBE VIRALITY: Will people click? Is the hook strong? Is the topic search-friendly?

Return ONLY this JSON object:
{{
  "drama_score": <0-25>,
  "visual_richness_score": <0-25>,
  "historical_accuracy_score": <0-25>,
  "youtube_virality_score": <0-25>,
  "total_score": <0-100>,
  "verdict": "PASS" or "REJECT",
  "rejection_reason": "Reason if REJECT, else null",
  "notes": "One sentence of feedback"
}}
"""
    scores = gemini_json(prompt)

    # Enforce threshold
    total = (
        scores.get("drama_score", 0)
        + scores.get("visual_richness_score", 0)
        + scores.get("historical_accuracy_score", 0)
        + scores.get("youtube_virality_score", 0)
    )
    scores["total_score"] = total
    scores["verdict"] = "PASS" if total >= QUALITY_THRESHOLD else "REJECT"
    if total < QUALITY_THRESHOLD and not scores.get("rejection_reason"):
        scores["rejection_reason"] = f"Score {total} below threshold {QUALITY_THRESHOLD}"

    log.info(
        f"Score: {total}/100 — {scores['verdict']} "
        f"(D:{scores.get('drama_score')} V:{scores.get('visual_richness_score')} "
        f"A:{scores.get('historical_accuracy_score')} Y:{scores.get('youtube_virality_score')})"
    )
    return scores


# ── Script Generation ─────────────────────────────────────────────────────────
def generate_script(channel: str, ep_num: int, research: dict, scores: dict) -> dict:
    """
    Generate a complete, render-ready episode JSON with all 24 scenes populated.
    No [WRITE: ...] placeholders. Every field filled in.
    """
    cfg = CHANNEL_CONFIGS[channel]
    scene_count = cfg["scene_count"]
    scene_duration = cfg["scene_duration"]
    scene_types = SCENE_TYPES[channel]
    ep_id = f"{cfg['prefix']}_EP{ep_num:03d}"

    log.info(f"Generating full {scene_count}-scene script for {ep_id}: {research.get('verified_title')}")

    # Build the scene type list
    type_list = json.dumps(scene_types)
    facts_block = "\n".join(f"- {f}" for f in research.get("key_facts", []))
    figures_block = json.dumps(research.get("key_figures", []), indent=2)
    dramatic_block = "\n".join(f"- {d}" for d in research.get("dramatic_moments", []))
    act_structure = json.dumps(research.get("act_structure", []), indent=2)
    bg_colors_pool = cfg["bg_colors_pool"]

    prompt = f"""
{cfg['system_prompt']}

Generate a COMPLETE, RENDER-READY episode script.
Every field must be fully written. No placeholders. No [WRITE: ...] tags.

EPISODE: {ep_id}
TITLE: {research.get('verified_title')}
SUBTITLE: {research.get('subtitle')}
TAGLINE: {research.get('tagline')}
VIRAL HOOK: {research.get('viral_hook')}
VILLAIN/ANTAGONIST: {research.get('villain_mandate')}
LESSON: {research.get('lesson')}

KEY VERIFIED FACTS:
{facts_block}

KEY FIGURES:
{figures_block}

MOST DRAMATIC MOMENTS TO INCLUDE:
{dramatic_block}

THREE-ACT STRUCTURE:
{act_structure}

VISUAL PALETTE: {json.dumps(research.get('visual_palette', {}))}

REQUIREMENTS:
- Exactly {scene_count} scenes
- Each scene narration: 40–80 words, punchy, vivid, present-tense energy
- Each visual_prompt: Detailed cinematic image prompt. Start with "Gods & Glory cinematic documentary."
  Include: setting, lighting, characters, action, emotion, time period. End with "16:9 cinematic."
- Scene types in order: {type_list}
- Duration per scene: {scene_duration} seconds
- Total duration: {scene_count * scene_duration} seconds
- narrator_tone: {cfg['narrator_tone']}
- The cold_open MUST use the viral hook as its first sentence
- The outro_cta MUST end with a clear YouTube subscribe call-to-action

BG_COLORS reference pool (pick the most tonally appropriate for each scene):
{json.dumps(bg_colors_pool, indent=2)}

Return ONLY this exact JSON structure with all {scene_count} scenes fully written:
{{
  "channel": "{cfg['prefix']}",
  "episode_number": {ep_num},
  "episode_id": "{ep_id}",
  "title": <verified_title>,
  "subtitle": <subtitle>,
  "tagline": <tagline>,
  "villain_mandate": <villain_mandate>,
  "duration_target_sec": {scene_count * scene_duration},
  "viral_hook": <viral_hook>,
  "youtube_title": <compelling YouTube title under 70 chars>,
  "lesson": <lesson>,
  "highlight_scene": <scene number with most visual drama, integer>,
  "scenes": [
    {{
      "scene_number": 1,
      "type": "cold_open",
      "title": <scene title>,
      "duration_sec": {scene_duration},
      "narration": <40-80 word narration, no quotes needed>,
      "visual_prompt": <detailed cinematic image prompt>,
      "bg_colors": <pick 3 hex colors from the pool above>
    }},
    ... (all {scene_count} scenes)
  ]
}}

Return ONLY the JSON. No markdown. No explanation. Start with {{ and end with }}.
"""
    return gemini_json(prompt, temperature=0.65)


# ── Validation ────────────────────────────────────────────────────────────────
def validate_script(script: dict, channel: str) -> list[str]:
    """Return list of validation errors. Empty list = pass."""
    errors = []
    cfg = CHANNEL_CONFIGS[channel]
    required_top = ["episode_id", "title", "scenes", "viral_hook", "lesson"]
    for key in required_top:
        if not script.get(key):
            errors.append(f"Missing top-level field: {key}")

    scenes = script.get("scenes", [])
    expected_count = cfg["scene_count"]
    if len(scenes) != expected_count:
        errors.append(f"Expected {expected_count} scenes, got {len(scenes)}")

    for i, scene in enumerate(scenes, 1):
        narration = scene.get("narration", "").strip()
        visual = scene.get("visual_prompt", "").strip()
        if not narration or "[WRITE" in narration or len(narration) < 20:
            errors.append(f"Scene {i}: narration missing or placeholder")
        if not visual or "[WRITE" in visual or len(visual) < 20:
            errors.append(f"Scene {i}: visual_prompt missing or placeholder")
        if not scene.get("bg_colors"):
            errors.append(f"Scene {i}: bg_colors missing")

    return errors


# ── Next Episode Number ────────────────────────────────────────────────────────
def next_episode_number(channel: str) -> int:
    cfg = CHANNEL_CONFIGS[channel]
    prefix = cfg["prefix"]
    subdir = PROMPTS_DIR / cfg["prompts_subdir"]
    if not subdir.exists():
        return 1
    existing = sorted(subdir.glob(f"scene_prompts.{prefix.lower()}_ep*.final.json"))
    if not existing:
        return 1
    last = existing[-1].stem  # e.g. scene_prompts.gg_ep026.final
    m = re.search(r"ep(\d+)", last)
    return int(m.group(1)) + 1 if m else 1


# ── Write Output ──────────────────────────────────────────────────────────────
def write_output(script: dict, channel: str) -> Path:
    cfg = CHANNEL_CONFIGS[channel]
    subdir = PROMPTS_DIR / cfg["prompts_subdir"]
    subdir.mkdir(parents=True, exist_ok=True)

    ep_id = script["episode_id"].lower()  # e.g. gg_ep027
    out_path = subdir / f"scene_prompts.{ep_id}.final.json"
    out_path.write_text(json.dumps(script, indent=2, ensure_ascii=False), encoding="utf-8")

    # Backup
    backup_dir = BASE_DIR / "_backups"
    backup_dir.mkdir(exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    shutil.copy2(out_path, backup_dir / f"scene_prompts.{ep_id}.{ts}.json")

    log.info(f"Script written: {out_path}")
    return out_path


# ── Main Pipeline ─────────────────────────────────────────────────────────────
def run(channel: str, forced_topic: str | None = None, dry_run: bool = False) -> Path | None:
    """
    Full autonomous pipeline:
    Topic Discovery → Research → Score → Reject → Script → Validate → Write
    Returns path to written JSON, or None if all candidates rejected.
    """
    if channel not in CHANNEL_CONFIGS:
        raise ValueError(f"Unknown channel: {channel}. Use: {list(CHANNEL_CONFIGS.keys())}")

    cfg = CHANNEL_CONFIGS[channel]
    ep_num = next_episode_number(channel)
    ep_id  = f"{cfg['prefix']}_EP{ep_num:03d}"

    log.info("=" * 60)
    log.info(f"RESEARCH AGENT — {cfg['name']} — {ep_id}")
    log.info("=" * 60)

    # ── Stage 1: Topic Discovery
    candidates = select_candidates(channel, forced_topic=forced_topic, n=MAX_CANDIDATES)
    log.info(f"Candidates ({len(candidates)}): {'; '.join(candidates)}")

    if dry_run:
        log.info("[DRY RUN] Would research and score these topics. Exiting.")
        return None

    # ── Stage 2–4: Research + Score each candidate, pick the best passing one
    best_script = None
    best_score  = 0

    for topic in candidates:
        log.info(f"\n── Topic: {topic}")
        try:
            research = research_topic(topic, channel)
            score    = score_topic(topic, research, channel)

            if score["verdict"] == "REJECT":
                log.info(f"REJECTED ({score['total_score']}/100): {score.get('rejection_reason')}")
                continue

            log.info(f"PASSED ({score['total_score']}/100) — generating script")

            # ── Stage 5: Script Generation
            script = generate_script(channel, ep_num, research, score)

            # ── Stage 6: Validate
            errors = validate_script(script, channel)
            if errors:
                log.warning(f"Validation errors: {errors}")
                # Attempt one retry
                log.info("Retrying script generation...")
                script = generate_script(channel, ep_num, research, score)
                errors = validate_script(script, channel)
                if errors:
                    log.error(f"Script still invalid after retry: {errors}")
                    continue

            if score["total_score"] > best_score:
                best_score  = score["total_score"]
                best_script = script
                log.info(f"New best candidate: {score['total_score']}/100")

            # If we have a strong pass (85+), stop early
            if best_score >= 85:
                break

        except Exception as e:
            log.error(f"Error processing topic '{topic}': {e}")
            continue

    if not best_script:
        log.error("All candidates rejected or failed. No script produced.")
        return None

    # ── Stage 7: Write
    out_path = write_output(best_script, channel)

    log.info("")
    log.info("=" * 60)
    log.info(f"RESEARCH AGENT COMPLETE")
    log.info(f"  Episode : {best_script['episode_id']}")
    log.info(f"  Title   : {best_script['title']}")
    log.info(f"  Score   : {best_score}/100")
    log.info(f"  Scenes  : {len(best_script['scenes'])}")
    log.info(f"  Output  : {out_path}")
    log.info("=" * 60)

    return out_path


# ── CLI ────────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(
        description="Viral Engine — Autonomous Research Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python research_agent.py --channel gg
  python research_agent.py --channel ml
  python research_agent.py --channel lo
  python research_agent.py --channel gg --topic "Battle of Salamis"
  python research_agent.py --channel gg --dry-run
        """
    )
    ap.add_argument("--channel", "-c", required=True, choices=["gg", "ml", "lo"],
                    help="Channel: gg=Gods & Glory, ml=Mech Legends, lo=Little Olympus")
    ap.add_argument("--topic", "-t", default=None,
                    help="Force a specific topic (skip topic discovery)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Show selected candidates without calling Gemini or writing files")
    args = ap.parse_args()

    result = run(args.channel, forced_topic=args.topic, dry_run=args.dry_run)
    if result:
        print(f"\n✓ Script ready: {result}")
        print(f"  Next: python generate_images.py --episode {result.stem.split('.')[1].upper()}")
    else:
        print("\n✗ Research agent produced no output. Check research_agent.log")
        sys.exit(1)


if __name__ == "__main__":
    main()
