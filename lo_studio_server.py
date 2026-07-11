"""
Little Olympus Studio Server
==============================
Production-ready Flask backend for the LO Studio web UI.

AI Pipeline (in priority order):
  Tier 1 — Ollama local (free, private)     → OllamaAdapter
  Tier 2 — OpenAI gpt-4o-mini (cheap)       → OpenAIAdapter
  Tier 3 — Error with clear message          → Never silent failure

Character Consistency:
  CHARACTER_BIBLE dict hard-coded from Little_Olympus_Master_Bible.md
  Every image prompt auto-injects character appearance descriptors.

Routes:
  GET  /                          → lo_studio.html
  GET  /api/status                → system health (Ollama + OpenAI + adapters)
  GET  /api/bible/characters      → all character data
  GET  /api/bible/locations       → world locations
  GET  /api/episodes              → list all existing LO episode JSONs
  GET  /api/episodes/<id>         → single episode JSON
  POST /api/generate/outline      → episode outline from idea
  POST /api/generate/script       → full scenes from outline
  POST /api/generate/image-prompts → image prompts with character consistency
  POST /api/generate/voice-script → character-tagged voice acting script
  POST /api/generate/parent-guide → parent learning guide
  POST /api/generate/seo          → YouTube metadata package
  POST /api/generate/full         → one-button: idea → full package
  GET  /api/projects              → list saved projects
  POST /api/projects              → save project
  GET  /api/projects/<id>         → load project
  DELETE /api/projects/<id>       → delete project
  POST /api/export/json           → download episode JSON
  POST /api/export/markdown       → download episode as Markdown
  GET  /api/adapters              → all adapter statuses
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path

# ── Flask ──────────────────────────────────────────────────────────────────────
try:
    from flask import Flask, jsonify, request, send_file, send_from_directory
    from flask_cors import CORS
except ImportError:
    print("\n[ERROR] Flask not installed.")
    print("Run: pip install flask flask-cors python-dotenv")
    print("Or:  pip install -r requirements_lo_studio.txt\n")
    sys.exit(1)

# ── dotenv ─────────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv optional; env vars may already be set

# ── Adapters ───────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
from adapters.lo_adapters.ollama_adapter import OllamaAdapter
from adapters.lo_adapters.openai_adapter import OpenAIAdapter
from adapters.lo_adapters.higgsfield import HiggsFieldAdapter
from adapters.lo_adapters.storyforge import StoryForgeAdapter
from adapters.lo_adapters.crosspost import CrossPostAdapter
from adapters.lo_adapters.empire_os import EmpireOSAdapter
from adapters.lo_adapters.video_factory import VideoFactoryAdapter

# ── Config ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
PROMPTS_DIR = BASE_DIR / "prompts"
PROJECTS_DIR = BASE_DIR / "projects" / "little-olympus"
BIBLE_PATH = BASE_DIR / "Little_Olympus_Master_Bible.md"
PORT = int(os.environ.get("LO_STUDIO_PORT", 5050))

PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [LO-STUDIO] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("lo_studio")

# ── Adapter instances ───────────────────────────────────────────────────────────
ollama = OllamaAdapter()
openai_adapter = OpenAIAdapter()
higgsfield = HiggsFieldAdapter()
storyforge = StoryForgeAdapter()
crosspost = CrossPostAdapter()
empire_os = EmpireOSAdapter()
video_factory = VideoFactoryAdapter()

# ── CHARACTER BIBLE ────────────────────────────────────────────────────────────
# Hard-coded from Little_Olympus_Master_Bible.md for consistency enforcement.
# NEVER let AI override these appearance descriptors.
CHARACTER_BIBLE: dict[str, dict] = {
    "little_zeus": {
        "name": "Little Zeus",
        "age": 7,
        "role": "Main protagonist",
        "appearance": (
            "white-blonde curly hair, electric blue eyes, golden crown, "
            "white tunic with lightning bolt gold clasp, barefoot or sandals made of compressed clouds, "
            "always carrying or reaching for his small golden thunderbolt toy"
        ),
        "personality": "confident, brave, impulsive, heart of gold, stubborn, secretly sensitive",
        "voice": "medium-high child voice, punchy short sentences, over-excited, emphasis on random words",
        "catchphrase": "THAT IS THE BEST IDEA. Let's do it RIGHT NOW.",
        "colors": ["#F5E642", "#4FC3F7", "#FFFFFF", "#FFD700"],
    },
    "baby_hercules": {
        "name": "Baby Hercules",
        "age": 5,
        "role": "Youngest, comic relief, genuine heart",
        "appearance": (
            "smallest of the group but with massively oversized muscular arms, "
            "lion-skin cape draped over one shoulder, giant hands, brown leather sandals, "
            "almost always has food nearby or crumbs on his face, "
            "wide innocent eyes, chubby toddler cheeks despite the arms"
        ),
        "personality": "cheerful, confused, helpful, accidentally destructive, loves everyone",
        "voice": "lower than expected for youngest, slightly husky toddler warmth, slow and confident, wrong words used confidently",
        "catchphrase": "I helped! (while standing in the crater he just made)",
        "colors": ["#8B6914", "#D4A847", "#F5DEB3"],
    },
    "athena": {
        "name": "Athena",
        "age": 8,
        "role": "The smart one, reluctant voice of reason",
        "appearance": (
            "long dark hair with silver streaks, neat loose braid or half-up, "
            "round glasses, pale blue and silver peplos, "
            "small grey owl named Archie perched on shoulder, "
            "always carrying a scroll or small tablet"
        ),
        "personality": "precise, calm, measured, sighs a lot, genuinely kind beneath the exasperation",
        "voice": "clear steady voice, measured delivery, complete sentences, three types of sighs",
        "catchphrase": "[The Sigh] — I did say this would happen.",
        "colors": ["#B0BEC5", "#546E7A", "#E3F2FD", "#78909C"],
    },
    "little_perseus": {
        "name": "Little Perseus",
        "age": 7,
        "role": "Audience surrogate, brave-while-scared",
        "appearance": (
            "slightly shorter than Zeus, slender, wiry, "
            "dark shaggy hair that falls over forehead, bright green curious eyes, "
            "medium warm brown skin, simple earthy tunic in greens and browns, "
            "small leather satchel across body, small round bronze shield (reflective, used as mirror), "
            "sometimes winged sandals (borrowed from Hermes, activate randomly at worst moments)"
        ),
        "personality": "curious, resourceful, polite, terrible sense of direction, devoted to friends",
        "voice": "medium slightly breathy, hesitant at sentence starts then gains confidence, thinks aloud",
        "catchphrase": "Wait, so if... okay. OKAY. We can do this.",
        "colors": ["#5D4037", "#8D6E63", "#4CAF50", "#DCEDC8"],
    },
    "young_achilles": {
        "name": "Young Achilles",
        "age": 7,
        "role": "The fastest kid on Olympus, protective, quietly emotional",
        "appearance": (
            "tallest of the core group, lean athletic build, "
            "golden blonde hair cut short and windswept from running, "
            "amber/gold sharp tracking eyes, golden tan skin, "
            "deep blue athletic tunic with silver trim, "
            "special speed sandals with tiny wing embellishments that leave sparkle trails when running, "
            "left heel: looks normal, he gets nervous if anyone looks at it"
        ),
        "personality": "confident without arrogance, thrill-seeker, protective, competitive with himself",
        "voice": "clear confident clipped voice, short direct sentences, voice rises when speed is involved",
        "catchphrase": "It's fine. The heel is FINE. Nobody asked about the heel.",
        "colors": ["#FFD54F", "#FF8F00", "#1565C0", "#C5E1A5"],
    },
    "mini_medusa": {
        "name": "Mini Medusa",
        "age": 7,
        "role": "Recurring antagonist who is misunderstood, secretly wants friends",
        "appearance": (
            "small slightly hunched figure, pale green skin with small scale patterns on arms, "
            "seven snakes as hair (named: Hissy, Slick, Noodle, Chomp, Dreamy, Zigzag, Tiny), "
            "gold/green eyes with slit pupils always hidden behind large round gold-framed sunglasses, "
            "purple and gold layered wraps, shell jewelry"
        ),
        "personality": "dramatically grumpy, secretly lonely, excellent taste, speaks in proclamations",
        "voice": "medium with slight hiss on S sounds, dramatic proclamations with beat-pauses",
        "catchphrase": "I shall turn you to STONE and then feel bad about it afterward!",
        "colors": ["#7B1FA2", "#AB47BC", "#4CAF50", "#FFD700"],
    },
    "uncle_hades": {
        "name": "Uncle Hades",
        "age_apparent": "adult (acts 40)",
        "role": "Funny adult, ruler of Underworld, accidental babysitter",
        "appearance": (
            "tall thin slightly translucent at edges in bright light, "
            "black slicked-back hair, deep purple warm eyes, "
            "black robes with subtle skull patterns, crown of black gems, "
            "always holding a cup with skeleton-shaped handle"
        ),
        "personality": "spooky aesthetic, completely harmless, tries his best, secretly loves visitors",
        "voice": "low warm slightly echoing voice, tired but not unhappy, dry wit delivered straight",
        "catchphrase": "Would anyone like a tour? (No one ever does. He gives one anyway.)",
        "colors": ["#212121", "#4A148C", "#6A1B9A", "#B0BEC5"],
    },
    "archie": {
        "name": "Archie the Owl",
        "role": "Athena's companion, non-verbal but expressive",
        "appearance": (
            "small grey owl, can roll his eyes (owls shouldn't be able to, Archie does), "
            "puffed up aggressively when anyone dismisses Athena, "
            "often half-asleep at inconvenient moments"
        ),
        "personality": "deeply sarcastic, loyal to Athena, hates Hermes's snakes",
        "colors": ["#90A4AE", "#607D8B", "#ECEFF1"],
    },
}

WORLD_LOCATIONS = {
    "mount_olympus": {
        "name": "Mount Olympus — The Main Hub",
        "description": "A magical mountain floating above the clouds with a sprawling, beautiful, slightly chaotic community of gods-as-children.",
        "colors": ["#E3F2FD", "#BBDEFB", "#FFD700", "#FFFFFF"],
        "mood": "Bright, warm, golden light, clouds everywhere, grand marble structures at child scale",
    },
    "training_grounds": {
        "name": "The Training Grounds",
        "description": "Where the kids practice their powers, usually badly. Scorched patches everywhere. Targets in various states of destruction.",
        "colors": ["#FFF9C4", "#A5D6A7", "#8D6E63"],
        "mood": "Active, slightly chaotic, comedy of errors energy",
    },
    "underworld": {
        "name": "The Underworld — Uncle Hades's Domain",
        "description": "Spooky but actually quite cozy if you know Hades. Stone corridors that echo, warm torchlight, surprisingly tasteful decor.",
        "colors": ["#212121", "#4A148C", "#FF6F00"],
        "mood": "Dark but warm, slightly gothic, tea-time energy despite the skeletons",
    },
    "the_sea": {
        "name": "Poseidon's Sea",
        "description": "The ocean — wild and dramatic like its ruler. Sea creatures everywhere. Poseidon trips constantly on land but here he's graceful.",
        "colors": ["#006064", "#0097A7", "#B2EBF2", "#40C4FF"],
        "mood": "Grand, theatrical, slightly over-the-top like its owner",
    },
    "medusas_garden": {
        "name": "Medusa's Stone Garden",
        "description": "Everything Mini Medusa has accidentally (or intentionally) petrified. Actually beautiful — she has excellent taste.",
        "colors": ["#7B1FA2", "#E1BEE7", "#9E9E9E"],
        "mood": "Eerie but oddly beautiful, like an art gallery that gives you chills",
    },
}

# ── System prompts ─────────────────────────────────────────────────────────────
LO_SYSTEM_PROMPT = """You are a writer for Little Olympus, a YouTube animated series about Greek mythology characters as kids.
Target audience: ages 3-10. YouTube Kids + Main YouTube.

EPISODE SPECS:
- Duration: 4-6 minutes (12-24 scenes at 10-20s each)
- Tone: Bright, warm, funny, educational, emotionally resonant
- Each episode has ONE clear lesson for kids
- Content: 100% child-safe, no violence, no scary elements (Medusa is "dramatic" not truly scary)

CHARACTER VOICE RULES (enforce in all dialogue/narration):
- Little Zeus: punchy, over-excited, short sentences, emphasis on random words
- Baby Hercules: slow, confident, wrong words used with full confidence, accidentally destructive
- Athena: measured, complete sentences, three types of sighs, faster when she's figured something out
- Little Perseus: slightly hesitant starts, thinks aloud, gains confidence mid-sentence
- Young Achilles: clipped, direct, gets faster when speed is involved, defensive about his heel
- Mini Medusa: dramatic proclamations, beat-pauses, second-guesses her own threats

OUTPUT: Valid JSON only. No markdown, no commentary, no explanation."""

# ── Flask app ──────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=None)
CORS(app)


# ── Helpers ────────────────────────────────────────────────────────────────────

def ai_generate(
    prompt: str,
    system: str = LO_SYSTEM_PROMPT,
    quality: str = "medium",
    force_cloud: bool = False,
) -> dict[str, str]:
    """
    Unified AI generation. Ollama first, OpenAI fallback.
    quality: "fast" | "medium" | "high"
    Returns: {"text": str, "gateway": str, "error": str | None}
    """
    if not force_cloud and ollama.is_available():
        try:
            text = ollama.generate(prompt, system)
            if text.strip():
                log.info(f"[AI] Ollama → {len(text)} chars")
                return {"text": text, "gateway": "OLLAMA_LOCAL", "error": None}
            log.warning("[AI] Ollama returned empty — falling back")
        except Exception as e:
            log.warning(f"[AI] Ollama failed: {e}")

    if openai_adapter.is_available():
        try:
            model = "gpt-4o" if quality == "high" else "gpt-4o-mini"
            text = openai_adapter.generate(prompt, system, model)
            log.info(f"[AI] OpenAI {model} → {len(text)} chars")
            return {"text": text, "gateway": f"OPENAI_{model.upper()}", "error": None}
        except Exception as e:
            log.error(f"[AI] OpenAI failed: {e}")
            return {"text": "", "gateway": "FAILED", "error": str(e)}

    return {
        "text": "",
        "gateway": "NONE",
        "error": "No AI available. Start Ollama (ollama serve) or add OPENAI_API_KEY to .env",
    }


def extract_json(text: str) -> list | dict | None:
    """Robustly extract JSON from AI output."""
    text = text.strip()
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try extracting JSON block
    match = re.search(r"```(?:json)?\s*([\[\{].*?[\]\}])\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Try finding array or object
    for pattern in [r"(\[[\s\S]*?\])", r"(\{[\s\S]*?\})"]:
        match = re.search(pattern, text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
    return None


def inject_character_appearances(visual_prompt: str, characters: list[str]) -> str:
    """
    Append character appearance descriptors to image prompts.
    This is the core character consistency enforcement mechanism.
    Called on EVERY visual_prompt before returning to the client.
    """
    if not characters:
        return visual_prompt
    descriptors = []
    for char in characters:
        key = (
            char.lower()
            .replace(" ", "_")
            .replace("little_", "little_")
            .replace("baby_", "baby_")
            .replace("young_", "young_")
            .replace("mini_", "mini_")
            .replace("uncle_", "uncle_")
        )
        # Normalize common name variants
        aliases = {
            "zeus": "little_zeus",
            "hercules": "baby_hercules",
            "herc": "baby_hercules",
            "athena": "athena",
            "perseus": "little_perseus",
            "achilles": "young_achilles",
            "medusa": "mini_medusa",
            "hades": "uncle_hades",
            "archie": "archie",
        }
        if key in aliases:
            key = aliases[key]
        if key in CHARACTER_BIBLE:
            c = CHARACTER_BIBLE[key]
            descriptors.append(f"{c['name']}: {c['appearance']}")
    if descriptors:
        return f"{visual_prompt} | CHARACTER CONSISTENCY: {' | '.join(descriptors)}"
    return visual_prompt


def build_scene_system_prompt(characters: list[str]) -> str:
    """Build a system prompt with character appearance notes for scene generation."""
    char_notes = []
    for char in characters:
        key = char.lower().replace(" ", "_")
        if key in CHARACTER_BIBLE:
            c = CHARACTER_BIBLE[key]
            char_notes.append(f"- {c['name']}: {c['appearance']}")
    char_section = "\n".join(char_notes) if char_notes else "- See character bible for appearances"
    return f"{LO_SYSTEM_PROMPT}\n\nCHARACTERS IN THIS EPISODE:\n{char_section}"


def list_existing_episodes() -> list[dict]:
    """List all existing LO episode JSON files."""
    episodes = []
    for f in sorted(PROMPTS_DIR.glob("scene_prompts.lo_ep*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            episodes.append({
                "file": f.name,
                "episode_id": data.get("episode_id", f.stem),
                "episode_number": data.get("episode_number", 0),
                "title": data.get("title", "Untitled"),
                "tagline": data.get("tagline", ""),
                "lesson": data.get("lesson", ""),
                "scenes": len(data.get("scenes", [])),
                "duration_min": data.get("duration_target_min", 5),
                "characters": data.get("characters", []),
            })
        except Exception as e:
            log.warning(f"Could not read {f.name}: {e}")
    return sorted(episodes, key=lambda x: x["episode_number"])


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    html_path = BASE_DIR / "lo_studio.html"
    if not html_path.exists():
        return "<h1>lo_studio.html not found</h1><p>Run the full setup script.</p>", 404
    return send_file(str(html_path))


@app.route("/api/status")
def status():
    return jsonify({
        "server": "Little Olympus Studio",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "ai": {
            "ollama": ollama.get_status(),
            "openai": openai_adapter.get_status(),
        },
        "paths": {
            "prompts": str(PROMPTS_DIR),
            "projects": str(PROJECTS_DIR),
            "bible": str(BIBLE_PATH),
            "bible_exists": BIBLE_PATH.exists(),
        },
        "episodes": {"total": len(list_existing_episodes())},
    })


@app.route("/api/adapters")
def adapters_status():
    return jsonify({
        "adapters": [
            ollama.get_status(),
            openai_adapter.get_status(),
            higgsfield.get_status(),
            storyforge.get_status(),
            crosspost.get_status(),
            empire_os.get_status(),
            video_factory.get_status(),
        ]
    })


# ── Character Manager — persistent custom characters ───────────────────────

CUSTOM_CHARS_FILE = BASE_DIR / "data" / "custom_characters.json"
CHAR_IMAGES_DIR   = BASE_DIR / "data" / "character_images"


def _load_custom_chars() -> dict:
    """Load custom characters from disk, return empty dict if missing."""
    if CUSTOM_CHARS_FILE.exists():
        try:
            return json.loads(CUSTOM_CHARS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_custom_chars(chars: dict) -> None:
    CUSTOM_CHARS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CUSTOM_CHARS_FILE.write_text(json.dumps(chars, indent=2, ensure_ascii=False), encoding="utf-8")


def _all_characters() -> dict:
    """Merge bible + custom (custom overrides bible keys)."""
    merged = dict(CHARACTER_BIBLE)
    merged.update(_load_custom_chars())
    return merged


@app.route("/api/bible/characters")
def bible_characters():
    return jsonify({"characters": _all_characters()})


@app.route("/api/characters", methods=["GET"])
def characters_list():
    """All characters (bible + custom) with source flag."""
    custom = _load_custom_chars()
    out = {}
    for k, v in CHARACTER_BIBLE.items():
        out[k] = {**v, "_source": "bible", "_locked": True}
    for k, v in custom.items():
        out[k] = {**v, "_source": "custom", "_locked": False}
    return jsonify({"characters": out})


@app.route("/api/characters/<char_key>", methods=["GET"])
def character_get(char_key: str):
    all_chars = _all_characters()
    if char_key not in all_chars:
        return jsonify({"error": f"Character '{char_key}' not found"}), 404
    source = "bible" if char_key in CHARACTER_BIBLE else "custom"
    return jsonify({**all_chars[char_key], "_source": source, "_key": char_key})


@app.route("/api/characters", methods=["POST"])
def character_create():
    """Create a new custom character."""
    body = request.json or {}
    name = (body.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    key = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    if not key:
        return jsonify({"error": "Could not derive a valid key from name"}), 400

    custom = _load_custom_chars()
    if key in CHARACTER_BIBLE:
        return jsonify({"error": f"'{key}' is a locked bible character — use PUT to override"}), 409
    if key in custom:
        return jsonify({"error": f"Character '{key}' already exists — use PUT to update"}), 409

    char = {
        "name": name,
        "age": body.get("age", "unknown"),
        "role": body.get("role", ""),
        "appearance": body.get("appearance", ""),
        "personality": body.get("personality", ""),
        "voice": body.get("voice", ""),
        "catchphrase": body.get("catchphrase", ""),
        "colors": body.get("colors", []),
        "relationships": body.get("relationships", {}),
        "consistency_locked": body.get("consistency_locked", False),
        "reference_image": body.get("reference_image", ""),
        "notes": body.get("notes", ""),
    }
    custom[key] = char
    _save_custom_chars(custom)
    log.info(f"[CHARS] Created custom character: {key}")
    return jsonify({"key": key, "character": char, "message": f"Character '{name}' created"}), 201


@app.route("/api/characters/<char_key>", methods=["PUT"])
def character_update(char_key: str):
    """Update a custom character (cannot edit bible characters except to override)."""
    body = request.json or {}
    custom = _load_custom_chars()
    existing = custom.get(char_key) or CHARACTER_BIBLE.get(char_key)
    if not existing:
        return jsonify({"error": f"Character '{char_key}' not found"}), 404

    updated = {**existing}
    for field in ("name","age","role","appearance","personality","voice","catchphrase",
                  "colors","relationships","consistency_locked","reference_image","notes"):
        if field in body:
            updated[field] = body[field]
    custom[char_key] = updated
    _save_custom_chars(custom)
    log.info(f"[CHARS] Updated character: {char_key}")
    return jsonify({"key": char_key, "character": updated})


@app.route("/api/characters/<char_key>", methods=["DELETE"])
def character_delete(char_key: str):
    """Delete a custom character (cannot delete bible characters)."""
    if char_key in CHARACTER_BIBLE:
        return jsonify({"error": "Cannot delete a bible character"}), 403
    custom = _load_custom_chars()
    if char_key not in custom:
        return jsonify({"error": f"Character '{char_key}' not found"}), 404
    del custom[char_key]
    _save_custom_chars(custom)
    log.info(f"[CHARS] Deleted character: {char_key}")
    return jsonify({"message": f"Character '{char_key}' deleted"})


@app.route("/api/characters/<char_key>/image", methods=["POST"])
def character_upload_image(char_key: str):
    """Upload a reference image for a character."""
    all_chars = _all_characters()
    if char_key not in all_chars:
        return jsonify({"error": f"Character '{char_key}' not found"}), 404
    if "image" not in request.files:
        return jsonify({"error": "No image file in request"}), 400
    img = request.files["image"]
    if not img.filename:
        return jsonify({"error": "Empty filename"}), 400
    ext = Path(img.filename).suffix.lower()
    if ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        return jsonify({"error": "Only png/jpg/webp/gif allowed"}), 400
    CHAR_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    dest = CHAR_IMAGES_DIR / f"{char_key}{ext}"
    img.save(str(dest))
    # Store relative path in custom record
    custom = _load_custom_chars()
    char_data = custom.get(char_key) or dict(CHARACTER_BIBLE.get(char_key, {}))
    char_data["reference_image"] = f"data/character_images/{char_key}{ext}"
    custom[char_key] = char_data
    _save_custom_chars(custom)
    log.info(f"[CHARS] Reference image saved: {dest}")
    return jsonify({"key": char_key, "image_path": char_data["reference_image"]})


@app.route("/api/characters/generate-appearance", methods=["POST"])
def character_generate_appearance():
    """Use AI to draft an appearance description from a rough description."""
    body = request.json or {}
    name = body.get("name", "New character")
    role = body.get("role", "")
    notes = body.get("notes", "")
    prompt = f"""Draft a visual appearance description for a Little Olympus cartoon character.
Name: {name}  |  Role: {role}
Notes from creator: {notes}

Rules:
- Style must match existing characters: bright-color cartoon, soft-edge, child-safe
- Describe hair, eyes, clothing, accessories, distinguishing features
- Note any signature items they always carry
- Keep it under 60 words, specific and visual
- Must be consistent enough that an AI image generator produces the same character every time

Return JSON: {{"appearance": "...", "color_palette": ["#hex1","#hex2","#hex3"], "signature_item": "..."}}"""
    result = ai_generate(prompt, quality="fast")
    if result["error"]:
        return jsonify({"error": result["error"]}), 500
    parsed = extract_json(result["text"])
    if not parsed:
        return jsonify({"raw": result["text"], "gateway": result["gateway"]}), 200
    return jsonify({**parsed, "gateway": result["gateway"]})


@app.route("/api/characters/<char_key>/generate-traits", methods=["POST"])
def character_generate_traits(char_key: str):
    """Use AI to expand personality, voice, and catchphrase for a character."""
    all_chars = _all_characters()
    char = all_chars.get(char_key, {})
    body = request.json or {}
    name = body.get("name") or char.get("name", char_key)
    role = body.get("role") or char.get("role", "")
    appearance = body.get("appearance") or char.get("appearance", "")
    prompt = f"""Generate personality, voice profile, and catchphrase for a Little Olympus character.
Name: {name}  |  Role: {role}
Appearance: {appearance}

The show targets ages 3-10, is warm and funny, teaches friendship and problem-solving.
Existing cast: Little Zeus (brave/impulsive), Baby Hercules (confused/strong), Athena (smart/sighs), Perseus (resourceful/lost), Achilles (fast/worried about heel), Mini Medusa (dramatic/lonely), Uncle Hades (bumbling adult).

Return JSON:
{{
  "personality": "3-5 traits separated by commas",
  "voice": "voice description for a voice actor (pitch, pace, quirks, delivery style)",
  "catchphrase": "their signature line that will make kids repeat it",
  "relationship_to_zeus": "how they relate to Little Zeus",
  "comedy_angle": "what makes them funny",
  "lesson_they_teach": "what life lesson this character embodies"
}}"""
    result = ai_generate(prompt, quality="fast")
    if result["error"]:
        return jsonify({"error": result["error"]}), 500
    parsed = extract_json(result["text"])
    if not parsed:
        return jsonify({"raw": result["text"], "gateway": result["gateway"]}), 200
    return jsonify({**parsed, "gateway": result["gateway"]})


@app.route("/api/bible/locations")
def bible_locations():
    return jsonify({"locations": WORLD_LOCATIONS})


@app.route("/api/episodes")
def episodes_list():
    return jsonify({"episodes": list_existing_episodes()})


@app.route("/api/episodes/<episode_id>")
def episode_detail(episode_id: str):
    # Try exact filename match first
    exact = PROMPTS_DIR / f"scene_prompts.{episode_id.lower()}.json"
    if exact.exists():
        return jsonify(json.loads(exact.read_text(encoding="utf-8")))
    # Try .final.json
    final = PROMPTS_DIR / f"scene_prompts.{episode_id.lower()}.final.json"
    if final.exists():
        return jsonify(json.loads(final.read_text(encoding="utf-8")))
    # Fuzzy search
    for f in PROMPTS_DIR.glob(f"*{episode_id.lower()}*.json"):
        return jsonify(json.loads(f.read_text(encoding="utf-8")))
    return jsonify({"error": f"Episode {episode_id} not found"}), 404


# ── Generation Routes ──────────────────────────────────────────────────────────

@app.route("/api/generate/outline", methods=["POST"])
def generate_outline():
    body = request.json or {}
    idea = body.get("idea", "")
    title = body.get("title", "")
    lesson = body.get("lesson", "")
    characters = body.get("characters", ["Little Zeus", "Baby Hercules", "Athena"])
    scene_count = body.get("scene_count", 18)  # 5-min target

    char_str = ", ".join(characters)
    prompt = f"""Create a {scene_count}-scene episode outline for Little Olympus.

EPISODE CONCEPT:
Title: {title or "TBD"}
Idea: {idea}
Lesson for kids: {lesson or "TBD — pick one that fits naturally"}
Characters: {char_str}

Return a JSON object with these fields:
{{
  "title": "Episode Title",
  "tagline": "One punchy line",
  "lesson": "The lesson kids will learn",
  "arc": "3-act structure in 2 sentences",
  "outline": [
    {{"scene": 1, "type": "hook|narrative|action|emotional|teaching|resolution", "brief": "What happens in 1-2 sentences"}}
  ]
}}

Make it funny, warm, age-appropriate (3-10). The lesson should emerge naturally from the story, not be lectured."""

    result = ai_generate(prompt, build_scene_system_prompt(characters))
    if result["error"]:
        return jsonify({"error": result["error"]}), 500

    parsed = extract_json(result["text"])
    if not parsed:
        return jsonify({"raw": result["text"], "gateway": result["gateway"], "warning": "Could not parse JSON"}), 200

    return jsonify({**parsed, "gateway": result["gateway"]})


@app.route("/api/generate/script", methods=["POST"])
def generate_script():
    body = request.json or {}
    outline = body.get("outline", [])
    title = body.get("title", "Untitled Episode")
    lesson = body.get("lesson", "")
    characters = body.get("characters", ["Little Zeus"])
    duration_min = body.get("duration_min", 5)

    if not outline:
        return jsonify({"error": "outline required"}), 400

    outline_text = "\n".join([
        f"Scene {s['scene']}: [{s['type'].upper()}] {s['brief']}"
        for s in outline
    ])
    char_str = ", ".join(characters)

    prompt = f"""Write a full episode script for Little Olympus.

EPISODE: {title}
LESSON: {lesson}
CHARACTERS: {char_str}
TARGET DURATION: {duration_min} minutes

SCENE OUTLINE:
{outline_text}

Return a JSON array of scene objects. Each scene:
{{
  "scene_number": 1,
  "type": "hook",
  "title": "Scene Title",
  "narration": "35-55 words of warm narrator text. Engaging, descriptive, kid-friendly.",
  "dialogue": [{{"character": "Little Zeus", "line": "dialogue line"}}],
  "visual_prompt": "Detailed cartoon scene description for image generation. Bright, colorful, warm.",
  "bg_colors": ["#hexcolor1", "#hexcolor2"],
  "duration_sec": 15,
  "characters_visible": ["Little Zeus", "Baby Hercules"]
}}

Rules:
- 4 photos per scene (visual_prompt describes the main composition; system generates variants)
- NO scene reuse — every scene is visually distinct
- Keep all content completely child-safe
- Character voices must match their personality (see system prompt)
- bg_colors: 2 colors that set the scene's mood"""

    result = ai_generate(prompt, build_scene_system_prompt(characters), quality="medium")
    if result["error"]:
        return jsonify({"error": result["error"]}), 500

    scenes = extract_json(result["text"])
    if not scenes or not isinstance(scenes, list):
        return jsonify({"raw": result["text"], "gateway": result["gateway"], "warning": "Could not parse scenes"}), 200

    # Enforce character consistency on all visual prompts
    for scene in scenes:
        visible = scene.get("characters_visible", characters)
        scene["visual_prompt"] = inject_character_appearances(
            scene.get("visual_prompt", ""), visible
        )

    return jsonify({"scenes": scenes, "count": len(scenes), "gateway": result["gateway"]})


@app.route("/api/generate/image-prompts", methods=["POST"])
def generate_image_prompts():
    """Refine or generate detailed image prompts with character consistency baked in."""
    body = request.json or {}
    scenes = body.get("scenes", [])
    characters = body.get("characters", [])

    if not scenes:
        return jsonify({"error": "scenes required"}), 400

    enhanced = []
    for scene in scenes:
        visible = scene.get("characters_visible", characters)
        base_prompt = scene.get("visual_prompt", "")
        # Inject character appearance descriptors
        enhanced_prompt = inject_character_appearances(base_prompt, visible)
        # Add Higgsfield-compatible camera note
        camera_prompt = higgsfield.get_lo_camera_prompt(scene.get("type", "narrative"), enhanced_prompt)
        enhanced.append({
            **scene,
            "visual_prompt": enhanced_prompt,
            "higgsfield_prompt": camera_prompt,
            "image_variants": [
                enhanced_prompt,
                enhanced_prompt + ", alternate camera angle, different composition",
                enhanced_prompt + ", close-up detail shot, dramatic framing",
                enhanced_prompt + ", wide establishing shot, sweeping cinematic angle",
            ],
        })

    return jsonify({"scenes": enhanced, "count": len(enhanced)})


@app.route("/api/generate/voice-script", methods=["POST"])
def generate_voice_script():
    body = request.json or {}
    scenes = body.get("scenes", [])
    title = body.get("title", "Untitled")
    characters = body.get("characters", [])

    if not scenes:
        return jsonify({"error": "scenes required"}), 400

    # Build a condensed scene summary for the voice script prompt
    scene_summaries = []
    for s in scenes:
        narration = s.get("narration", "")
        dialogue = s.get("dialogue", [])
        dialogue_text = " / ".join([f"{d['character']}: \"{d['line']}\"" for d in dialogue]) if dialogue else ""
        scene_summaries.append(f"Scene {s.get('scene_number', '?')} [{s.get('type', '?')}]: {narration} {dialogue_text}".strip())

    prompt = f"""Create a production voice script for Little Olympus episode: "{title}"

SCENES:
{chr(10).join(scene_summaries[:24])}

Return a JSON array of voice cue objects:
{{
  "scene_number": 1,
  "type": "narrator|character",
  "character": "Narrator",
  "text": "The text to speak",
  "direction": "Voice direction note (e.g., 'warm, excited', 'slow and confused')",
  "duration_estimate_sec": 8
}}

Voice rules:
- Narrator: warm, storytelling, pauses for effect, like a favorite bedtime story
- Little Zeus: punchy, excited, random words CAPITALIZED for emphasis
- Baby Hercules: slow, confident, slightly confused
- Athena: measured, complete, occasional sigh marked as [SIGH]
- Little Perseus: curious, thinks aloud, slight hesitation at sentence starts
- Young Achilles: clipped, direct, nervous when heel mentioned"""

    result = ai_generate(prompt, LO_SYSTEM_PROMPT, quality="medium")
    if result["error"]:
        return jsonify({"error": result["error"]}), 500

    cues = extract_json(result["text"])
    if not cues:
        return jsonify({"raw": result["text"], "gateway": result["gateway"]}), 200

    total_duration = sum(c.get("duration_estimate_sec", 10) for c in cues if isinstance(cues, list))
    return jsonify({"cues": cues, "total_duration_sec": total_duration, "gateway": result["gateway"]})


@app.route("/api/generate/parent-guide", methods=["POST"])
def generate_parent_guide():
    body = request.json or {}
    title = body.get("title", "")
    lesson = body.get("lesson", "")
    scenes = body.get("scenes", [])
    characters = body.get("characters", [])

    char_str = ", ".join(characters) if characters else "Little Zeus and friends"
    narrations = " ".join([s.get("narration", "") for s in scenes[:8]])

    prompt = f"""Write a parent learning guide for the Little Olympus episode: "{title}"
Lesson: {lesson}
Characters: {char_str}
Episode summary: {narrations[:500]}

Return a JSON object:
{{
  "title": "Parent Guide: {title}",
  "age_range": "3-10 years",
  "lesson_summary": "2-3 sentences explaining the lesson for parents",
  "talking_points": [
    {{"question": "A question to ask your child after watching", "purpose": "What this teaches"}}
  ],
  "mythology_facts": [
    {{"fact": "A real fact about the myth this episode references", "kid_explanation": "How to explain it to a young child"}}
  ],
  "activities": [
    {{"name": "Activity name", "description": "Simple activity to reinforce the lesson", "age_range": "3-5 or 6-10"}}
  ],
  "vocabulary": [
    {{"word": "A word from the episode", "definition": "Kid-friendly definition"}}
  ]
}}"""

    result = ai_generate(prompt, quality="medium")
    if result["error"]:
        return jsonify({"error": result["error"]}), 500

    guide = extract_json(result["text"])
    if not guide:
        return jsonify({"raw": result["text"], "gateway": result["gateway"]}), 200

    return jsonify({**guide, "gateway": result["gateway"]})


@app.route("/api/generate/seo", methods=["POST"])
def generate_seo():
    body = request.json or {}
    title = body.get("title", "")
    lesson = body.get("lesson", "")
    characters = body.get("characters", [])
    scenes = body.get("scenes", [])

    char_str = ", ".join(characters) if characters else "Little Zeus"
    narrations = " ".join([s.get("narration", "") for s in scenes[:6]])

    prompt = f"""Create a complete YouTube SEO package for a Little Olympus kids episode.

Episode: "{title}"
Lesson: {lesson}
Characters: {char_str}
Content preview: {narrations[:400]}

Channel: @LittleOlympusTV (YouTube Kids + Main YouTube)
Target: parents searching for educational kids content about Greek mythology

Return JSON:
{{
  "youtube_title": "Primary title (60 chars max, keyword-rich, parent and kid friendly)",
  "title_options": ["3 alt title options"],
  "description": "Full YouTube description (300-500 words, includes lesson, characters, what parents should know)",
  "tags": ["15-20 SEO tags"],
  "chapters": [{{"time": "0:00", "label": "Chapter name"}}],
  "thumbnail_concept": "Describe the thumbnail image (characters, emotion, text overlay, colors)",
  "shorts_ideas": ["3 clip ideas for YouTube Shorts from this episode"],
  "social_posts": {{
    "instagram": "Instagram caption with hashtags",
    "twitter": "Twitter/X post under 280 chars",
    "facebook": "Facebook post (more detail, parent-focused)"
  }},
  "series_keywords": ["keywords that build series recognition"]
}}"""

    result = ai_generate(prompt, quality="fast")  # SEO doesn't need high quality
    if result["error"]:
        return jsonify({"error": result["error"]}), 500

    seo = extract_json(result["text"])
    if not seo:
        return jsonify({"raw": result["text"], "gateway": result["gateway"]}), 200

    return jsonify({**seo, "gateway": result["gateway"]})


@app.route("/api/generate/full", methods=["POST"])
def generate_full_pipeline():
    """
    One-button pipeline: idea → full episode package.
    Runs: outline → script → image prompts → voice script → parent guide → SEO
    Returns the complete episode JSON ready to feed into little_olympus_render.py
    """
    body = request.json or {}
    idea = body.get("idea", "")
    title = body.get("title", "")
    lesson = body.get("lesson", "")
    characters = body.get("characters", ["Little Zeus", "Baby Hercules", "Athena"])
    episode_number = body.get("episode_number", 0)
    duration_min = body.get("duration_min", 5)

    if not idea:
        return jsonify({"error": "idea required"}), 400

    log.info(f"[PIPELINE] Starting full generation: {title or idea[:50]}")
    steps = {}

    # Step 1: Outline
    scene_count = {"4": 12, "5": 18, "6": 24}.get(str(duration_min), 18)
    outline_prompt = f"""Create a {scene_count}-scene episode outline.
Title: {title or "TBD"}
Idea: {idea}
Lesson: {lesson or "pick one that fits"}
Characters: {', '.join(characters)}

Return JSON: {{"title": str, "tagline": str, "lesson": str, "arc": str, "outline": [{{"scene": int, "type": str, "brief": str}}]}}"""

    outline_result = ai_generate(outline_prompt, build_scene_system_prompt(characters))
    if outline_result["error"]:
        return jsonify({"error": f"Outline failed: {outline_result['error']}"}), 500
    outline_data = extract_json(outline_result["text"]) or {}
    steps["outline"] = outline_data
    resolved_title = outline_data.get("title", title or "Untitled")
    resolved_lesson = outline_data.get("lesson", lesson)

    # Step 2: Script
    outline_items = outline_data.get("outline", [])
    outline_text = "\n".join([f"Scene {s['scene']}: [{s['type']}] {s['brief']}" for s in outline_items])
    script_prompt = f"""Write the full script for Little Olympus episode: "{resolved_title}"
Lesson: {resolved_lesson}
Characters: {', '.join(characters)}

Outline:
{outline_text}

Return JSON array of scene objects with all required fields (scene_number, type, title, narration, dialogue, visual_prompt, bg_colors, duration_sec, characters_visible)."""

    script_result = ai_generate(script_prompt, build_scene_system_prompt(characters), quality="medium")
    if script_result["error"]:
        return jsonify({"error": f"Script failed: {script_result['error']}"}), 500
    scenes = extract_json(script_result["text"])
    if not scenes or not isinstance(scenes, list):
        scenes = []
    steps["scenes"] = len(scenes)

    # Enforce character consistency on all visual prompts
    for scene in scenes:
        visible = scene.get("characters_visible", characters)
        scene["visual_prompt"] = inject_character_appearances(scene.get("visual_prompt", ""), visible)

    # Step 3: SEO (lightweight — Ollama only)
    seo_prompt = f"""YouTube SEO for Little Olympus "{resolved_title}".
Return JSON: {{"youtube_title": str, "description": str, "tags": [str], "thumbnail_concept": str, "shorts_ideas": [str]}}"""
    seo_result = ai_generate(seo_prompt, quality="fast")
    seo_data = extract_json(seo_result["text"]) or {}

    # Step 4: Assemble final episode JSON (matches little_olympus_render.py format)
    ep_id = f"LO_EP{episode_number:03d}" if episode_number else f"LO_EP{datetime.now().strftime('%Y%m%d%H%M')}"
    episode_json = {
        "channel": "LO",
        "episode_number": episode_number,
        "episode_id": ep_id,
        "series_name": "Little Olympus",
        "title": resolved_title,
        "tagline": outline_data.get("tagline", ""),
        "duration_target_min": duration_min,
        "lesson": resolved_lesson,
        "arc": outline_data.get("arc", ""),
        "aesthetic": "bright, warm, soft-edge cartoon, Olympus color palette, child-safe",
        "characters": characters,
        "scenes": scenes,
        "music": "warm orchestral with playful percussion, Greek-inspired instruments",
        "voice_style": "warm storyteller narrator, expressive character voices",
        "youtube_title": seo_data.get("youtube_title", resolved_title),
        "youtube_description": seo_data.get("description", ""),
        "tags": seo_data.get("tags", []),
        "thumbnail_concept": seo_data.get("thumbnail_concept", ""),
        "shorts_ideas": seo_data.get("shorts_ideas", []),
        "generated_at": datetime.now().isoformat(),
        "generated_by": "LO Studio v1.0",
        "gateways_used": [outline_result["gateway"], script_result["gateway"], seo_result["gateway"]],
    }

    log.info(f"[PIPELINE] Complete — {len(scenes)} scenes, ep_id={ep_id}")
    return jsonify({
        "episode": episode_json,
        "steps": steps,
        "render_command": f"python little_olympus_render.py --episode {ep_id}",
    })


# ── Project Management ─────────────────────────────────────────────────────────

@app.route("/api/projects", methods=["GET"])
def list_projects():
    projects = []
    for f in sorted(PROJECTS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            projects.append({
                "id": f.stem,
                "title": data.get("title", f.stem),
                "episode_id": data.get("episode_id", ""),
                "updated": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                "scenes": len(data.get("scenes", [])),
            })
        except Exception:
            pass
    return jsonify({"projects": projects})


@app.route("/api/projects", methods=["POST"])
def save_project():
    body = request.json or {}
    project_id = body.get("id") or str(uuid.uuid4())[:8]
    body["id"] = project_id
    body["saved_at"] = datetime.now().isoformat()
    path = PROJECTS_DIR / f"{project_id}.json"
    path.write_text(json.dumps(body, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info(f"[PROJECT] Saved: {project_id}")
    return jsonify({"id": project_id, "saved": True})


@app.route("/api/projects/<project_id>", methods=["GET"])
def load_project(project_id: str):
    path = PROJECTS_DIR / f"{project_id}.json"
    if not path.exists():
        return jsonify({"error": "Project not found"}), 404
    return jsonify(json.loads(path.read_text(encoding="utf-8")))


@app.route("/api/projects/<project_id>", methods=["DELETE"])
def delete_project(project_id: str):
    path = PROJECTS_DIR / f"{project_id}.json"
    if path.exists():
        path.unlink()
        return jsonify({"deleted": True})
    return jsonify({"error": "Not found"}), 404


# ── Export Routes ──────────────────────────────────────────────────────────────

@app.route("/api/export/json", methods=["POST"])
def export_json():
    body = request.json or {}
    episode = body.get("episode", body)
    ep_id = episode.get("episode_id", "lo_episode")
    filename = f"{ep_id.lower()}.json"
    tmp_path = PROJECTS_DIR / filename
    tmp_path.write_text(json.dumps(episode, indent=2, ensure_ascii=False), encoding="utf-8")
    return send_file(str(tmp_path), as_attachment=True, download_name=filename, mimetype="application/json")


@app.route("/api/export/markdown", methods=["POST"])
def export_markdown():
    body = request.json or {}
    episode = body.get("episode", body)
    title = episode.get("title", "Untitled")
    ep_id = episode.get("episode_id", "LO_EP000")
    lesson = episode.get("lesson", "")
    characters = episode.get("characters", [])
    scenes = episode.get("scenes", [])

    md_lines = [
        f"# {title}",
        f"**Episode:** {ep_id}  ",
        f"**Lesson:** {lesson}  ",
        f"**Characters:** {', '.join(characters)}  ",
        f"**Generated:** {episode.get('generated_at', 'unknown')}  ",
        "",
        "---",
        "",
        "## Episode Outline",
        "",
    ]

    for scene in scenes:
        md_lines += [
            f"### Scene {scene.get('scene_number', '?')}: {scene.get('title', '')}",
            f"**Type:** `{scene.get('type', 'narrative')}` | **Duration:** {scene.get('duration_sec', 15)}s",
            "",
            f"**Narration:**",
            f"> {scene.get('narration', '')}",
            "",
        ]
        dialogue = scene.get("dialogue", [])
        if dialogue:
            md_lines.append("**Dialogue:**")
            for d in dialogue:
                md_lines.append(f"- **{d.get('character', '?')}:** \"{d.get('line', '')}\"")
            md_lines.append("")
        md_lines += [
            f"**Visual Prompt:**",
            f"`{scene.get('visual_prompt', '')}`",
            "",
            "---",
            "",
        ]

    # YouTube metadata
    md_lines += [
        "## YouTube Metadata",
        "",
        f"**Title:** {episode.get('youtube_title', title)}",
        "",
        f"**Description:**",
        episode.get("youtube_description", ""),
        "",
        f"**Tags:** {', '.join(episode.get('tags', []))}",
        "",
        f"**Thumbnail:** {episode.get('thumbnail_concept', '')}",
        "",
        "## Shorts Ideas",
        "",
    ]
    for idea in episode.get("shorts_ideas", []):
        md_lines.append(f"- {idea}")

    md_content = "\n".join(md_lines)
    filename = f"{ep_id.lower()}.md"
    tmp_path = PROJECTS_DIR / filename
    tmp_path.write_text(md_content, encoding="utf-8")
    return send_file(str(tmp_path), as_attachment=True, download_name=filename, mimetype="text/markdown")



# ── Research / Camera / SFX / Music / Coloring / Activity / Export Package ────

@app.route("/api/generate/research", methods=["POST"])
def generate_research():
    """Research mythology + educational angles for the episode."""
    body = request.json or {}
    idea = body.get("idea", "")
    characters = body.get("characters", ["Little Zeus"])
    age_range = body.get("age_range", "3-10")
    prompt = f"""Research the mythology behind this Little Olympus episode idea:
"{idea}"
Characters: {', '.join(characters)}  |  Audience: ages {age_range}

Return JSON:
{{
  "mythology_background": "2-3 sentences on the real myth this references",
  "age_appropriate_facts": ["4-6 real facts simplified for young children"],
  "educational_angles": ["3-4 ways this story teaches something real"],
  "vocabulary": [{{"word": "str", "kid_definition": "str", "example_sentence": "str"}}],
  "mythology_connections": ["How characters relate to real mythology"],
  "parent_notes": "What parents should know to discuss this with their kids",
  "similar_stories": ["2-3 other myths with similar themes"],
  "warnings": "Any cultural sensitivities to handle carefully, or empty string"
}}"""
    result = ai_generate(prompt, quality="medium")
    if result["error"]:
        return jsonify({"error": result["error"]}), 500
    parsed = extract_json(result["text"])
    if not parsed:
        return jsonify({"raw": result["text"], "gateway": result["gateway"]}), 200
    return jsonify({**parsed, "gateway": result["gateway"]})


@app.route("/api/generate/music", methods=["POST"])
def generate_music():
    """Background music guide per scene + overall episode theme."""
    body = request.json or {}
    title = body.get("title", "")
    lesson = body.get("lesson", "")
    scenes = body.get("scenes", [])
    tone = body.get("tone", "warm, adventurous, kid-friendly")
    scene_moods = [
        f"Scene {s.get('scene_number','?')} [{s.get('type','?')}]: {s.get('title','')}"
        for s in scenes[:16]
    ]
    prompt = f"""Create background music recommendations for Little Olympus episode: "{title}"
Lesson: {lesson}  |  Tone: {tone}

Scene flow:
{chr(10).join(scene_moods) if scene_moods else 'General episode'}

Return JSON:
{{
  "main_theme": {{
    "description": "Main episode theme",
    "style": "Musical style",
    "tempo": "Fast/Medium/Slow",
    "instruments": ["key instruments"],
    "reference_tracks": ["2-3 existing tracks with similar feel"]
  }},
  "scene_music": [{{"scene_type": "str", "mood": "str", "music_note": "str", "transition": "str"}}],
  "sound_effects": ["Key SFX needed"],
  "intro_music": "Opening 5-second music description",
  "outro_music": "Closing music description",
  "music_sources": ["Free/royalty-free libraries that would work"]
}}"""
    result = ai_generate(prompt, quality="fast")
    if result["error"]:
        return jsonify({"error": result["error"]}), 500
    parsed = extract_json(result["text"])
    if not parsed:
        return jsonify({"raw": result["text"], "gateway": result["gateway"]}), 200
    return jsonify({**parsed, "gateway": result["gateway"]})


@app.route("/api/generate/camera", methods=["POST"])
def generate_camera():
    """Camera direction notes for every scene (shot type, movement, transition)."""
    body = request.json or {}
    scenes = body.get("scenes", [])
    title = body.get("title", "")
    if not scenes:
        return jsonify({"error": "scenes required"}), 400
    scene_summaries = [
        f"Scene {s.get('scene_number','?')} [{s.get('type','')}]: {s.get('title','')} — {s.get('narration','')[:80]}"
        for s in scenes[:36]
    ]
    prompt = f"""Write camera direction notes for every scene in Little Olympus animated episode: "{title}"

Scenes:
{chr(10).join(scene_summaries)}

Return JSON array — one object per scene:
[{{
  "scene_number": 1,
  "shot_type": "wide/medium/close-up/extreme-close-up/aerial/POV/over-the-shoulder",
  "camera_direction": "What the camera does: push in, pull back, pan left, hold on, arc around, etc.",
  "focus_point": "What the camera is focused on",
  "transition_in": "How this scene opens: cut, fade in, match cut, smash cut, wipe, iris in",
  "transition_out": "How this scene closes: cut to, fade to black, smash cut, wipe, dissolve",
  "duration_note": "Pacing note: quick cut, held beat, slow reveal, etc."
}}]

Animation rules: wide shots establish location; push-ins for emotion; quick cuts for action; slow pulls for reveals; hold on face for lessons."""
    result = ai_generate(prompt, quality="fast")
    if result["error"]:
        return jsonify({"error": result["error"]}), 500
    parsed = extract_json(result["text"])
    if not parsed:
        return jsonify({"raw": result["text"], "gateway": result["gateway"]}), 200
    return jsonify({"camera_directions": parsed if isinstance(parsed, list) else parsed, "gateway": result["gateway"]})


@app.route("/api/generate/sfx", methods=["POST"])
def generate_sfx():
    """Sound effects guide — per scene + master SFX list + character sounds."""
    body = request.json or {}
    scenes = body.get("scenes", [])
    characters = body.get("characters", [])
    title = body.get("title", "")
    scene_types = list({s.get("type", "") for s in scenes})
    char_str = ", ".join(characters)
    prompt = f"""Create a complete sound effects guide for Little Olympus animated episode: "{title}"
Characters: {char_str}
Scene types in this episode: {', '.join(scene_types)}

Return JSON:
{{
  "master_sfx_list": [
    {{"name": "str", "description": "str", "category": "ambient|character|action|magic|transition|comedy", "scenes": [1, 3]}}
  ],
  "per_scene_sfx": [
    {{"scene_number": 1, "sfx": ["list of sound effect names for this scene"]}}
  ],
  "character_sounds": {{
    "Little Zeus": ["thunderbolt crackle", "excited gasp", "laugh"],
    "Baby Hercules": ["heavy footstep", "crunch when eating", "accidental crash"]
  }},
  "ambient_loops": ["Background ambient sounds needed for different locations"],
  "music_stingers": ["Short music stings for key moments (reveal, joke landing, lesson moment)"],
  "comedy_sfx": ["Cartoon sound effects for comedic moments"]
}}

Keep all sounds kid-friendly, warm, and cartoon-appropriate. No scary sounds."""
    result = ai_generate(prompt, quality="fast")
    if result["error"]:
        return jsonify({"error": result["error"]}), 500
    parsed = extract_json(result["text"])
    if not parsed:
        return jsonify({"raw": result["text"], "gateway": result["gateway"]}), 200
    return jsonify({**parsed, "gateway": result["gateway"]})


@app.route("/api/generate/music-prompts", methods=["POST"])
def generate_music_prompts():
    """AI music generation prompts for Suno, Udio, Soundraw, etc."""
    body = request.json or {}
    title = body.get("title", "")
    lesson = body.get("lesson", "")
    scenes = body.get("scenes", [])
    music_data = body.get("music_data", {})

    main_style = music_data.get("main_theme", {}).get("style", "warm orchestral, Greek instruments, children's educational")
    scene_types = list({s.get("type", "") for s in scenes})

    prompt = f"""Create AI music generation prompts for Little Olympus episode: "{title}"
Lesson: {lesson}
Overall style: {main_style}
Scene types: {', '.join(scene_types)}

Generate prompts formatted for Suno/Udio/Soundraw AI music generators.

Return JSON:
{{
  "main_theme_prompt": "Full Suno/Udio prompt for the main episode theme (include: genre, instruments, mood, tempo BPM, style tags, no lyrics)",
  "opening_sequence": "Prompt for the 8-second intro jingle",
  "closing_sequence": "Prompt for the warm 8-second outro",
  "action_cue": "Prompt for exciting action sequence music",
  "emotional_cue": "Prompt for soft emotional/lesson moment music",
  "comedy_cue": "Prompt for playful comedy moment music",
  "transition_cue": "Prompt for short scene transition stinger",
  "suno_tips": "Tips for getting the best results from Suno specifically",
  "udio_tips": "Tips for getting the best results from Udio specifically",
  "example_tags": ["List of useful style tags to add to any of these prompts"]
}}

Each prompt should be 1-3 sentences, specific, and ready to paste into an AI music tool."""
    result = ai_generate(prompt, quality="fast")
    if result["error"]:
        return jsonify({"error": result["error"]}), 500
    parsed = extract_json(result["text"])
    if not parsed:
        return jsonify({"raw": result["text"], "gateway": result["gateway"]}), 200
    return jsonify({**parsed, "gateway": result["gateway"]})


@app.route("/api/generate/coloring-page", methods=["POST"])
def generate_coloring_page():
    """Generate a coloring page image prompt for this episode."""
    body = request.json or {}
    title = body.get("title", "")
    characters = body.get("characters", ["Little Zeus"])
    lesson = body.get("lesson", "")
    scenes = body.get("scenes", [])

    # Pick the most visually interesting scene for the coloring page
    hook_scenes = [s for s in scenes if s.get("type") in ("hook", "action", "emotional")]
    featured_scene = hook_scenes[0] if hook_scenes else (scenes[0] if scenes else {})
    scene_desc = featured_scene.get("visual_prompt", f"Little Olympus characters in a fun adventure")

    char_str = ", ".join(characters[:3])
    char_appearances = []
    for c in characters[:3]:
        key = c.lower().replace(" ", "_").replace("little_", "little_").replace("baby_", "baby_").replace("young_", "young_").replace("mini_", "mini_").replace("uncle_", "uncle_")
        aliases = {"zeus": "little_zeus", "hercules": "baby_hercules", "athena": "athena", "perseus": "little_perseus", "achilles": "young_achilles", "medusa": "mini_medusa", "hades": "uncle_hades"}
        if key in aliases:
            key = aliases[key]
        if key in CHARACTER_BIBLE:
            char_appearances.append(CHARACTER_BIBLE[key]["appearance"])

    prompt = f"""Create a coloring page image prompt for Little Olympus episode: "{title}"
Featured characters: {char_str}
Lesson: {lesson}
Scene inspiration: {scene_desc[:200]}

Return JSON:
{{
  "coloring_page_prompt": "Detailed prompt for generating a black-and-white line-art coloring page. Include: character poses, background details, clear outlines, age-appropriate complexity. Specify: 'black and white line art, coloring book style, thick clean outlines, no shading, simple background, cartoon style, kid-friendly'",
  "scene_description": "What the coloring page shows in simple terms",
  "difficulty": "easy (ages 3-5) / medium (ages 5-8) / detailed (ages 8+)",
  "coloring_tips": "Suggested colors for each character and area (for the printed guide)",
  "caption": "A short fun caption to print at the top of the coloring page",
  "activity_prompt": "A simple question or prompt printed at the bottom (e.g. 'What color is Zeus's thunderbolt?')"
}}"""
    result = ai_generate(prompt, quality="fast")
    if result["error"]:
        return jsonify({"error": result["error"]}), 500
    parsed = extract_json(result["text"])
    if not parsed:
        return jsonify({"raw": result["text"], "gateway": result["gateway"]}), 200
    return jsonify({**parsed, "gateway": result["gateway"]})


@app.route("/api/generate/activity-sheet", methods=["POST"])
def generate_activity_sheet():
    """Generate printable activity sheet ideas for kids."""
    body = request.json or {}
    title = body.get("title", "")
    lesson = body.get("lesson", "")
    characters = body.get("characters", [])
    research_data = body.get("research_data", {})
    vocab = research_data.get("vocabulary", [])
    facts = research_data.get("age_appropriate_facts", [])

    char_str = ", ".join(characters)
    vocab_words = ", ".join([v.get("word", "") for v in vocab[:5]]) if vocab else "adventure, strength, wisdom"

    prompt = f"""Create a complete printable activity sheet for Little Olympus episode: "{title}"
Lesson: {lesson}
Characters: {char_str}
Vocabulary words: {vocab_words}
Key facts: {'; '.join(facts[:3]) if facts else 'Greek mythology themed'}

Return JSON:
{{
  "activity_sheet_title": "Fun title for the activity sheet",
  "activities": [
    {{
      "type": "word_search|crossword|maze|connect_dots|fill_in_blank|true_false|draw_and_color|match_columns|word_scramble",
      "title": "Activity name",
      "instructions": "Simple instructions for the child",
      "content": "The actual activity content (word list, questions, items to match, etc.)",
      "age_group": "3-5 / 5-8 / 8+"
    }}
  ],
  "discussion_questions": ["3-4 questions kids can answer after watching"],
  "mini_quiz": [
    {{"question": "str", "answer": "str", "hint": "str"}}
  ],
  "mythology_fun_fact": "One amazing fun fact from the episode to print on the sheet",
  "take_home_message": "The lesson in one kid-friendly sentence",
  "parent_corner": "A short note to parents about how to use this sheet"
}}

Make all activities age-appropriate, fun, and educational. Content must be 100% child-safe."""
    result = ai_generate(prompt, quality="medium")
    if result["error"]:
        return jsonify({"error": result["error"]}), 500
    parsed = extract_json(result["text"])
    if not parsed:
        return jsonify({"raw": result["text"], "gateway": result["gateway"]}), 200
    return jsonify({**parsed, "gateway": result["gateway"]})


@app.route("/api/export/package", methods=["POST"])
def export_package():
    """
    Complete production ZIP package — 15 files covering every deliverable.
    Receives all pipeline results assembled by the client.
    """
    import io
    import zipfile as zf

    body = request.json or {}
    episode   = body.get("episode", {})
    research  = body.get("research", {})
    voice     = body.get("voice_script", {})
    guide     = body.get("parent_guide", {})
    seo       = body.get("seo", {})
    music     = body.get("music", {})
    camera    = body.get("camera", {})
    sfx       = body.get("sfx", {})
    music_ai  = body.get("music_ai", {})
    coloring  = body.get("coloring", {})
    activity  = body.get("activity", {})

    ep_id   = episode.get("episode_id", f"LO_EP{datetime.now().strftime('%Y%m%d%H%M')}")
    title   = episode.get("title", "Untitled")
    scenes  = episode.get("scenes", [])
    lesson  = episode.get("lesson", "")
    chars   = episode.get("characters", [])

    zb = io.BytesIO()
    with zf.ZipFile(zb, "w", zf.ZIP_DEFLATED) as z:

        # 01 — Episode JSON (render-ready for little_olympus_render.py)
        z.writestr(f"{ep_id}/01_episode.json",
                   json.dumps(episode, indent=2, ensure_ascii=False))

        # 02 — Full screenplay
        lines = [f"# {title}", f"**{ep_id}** | Lesson: {lesson}",
                 f"Characters: {', '.join(chars)}", "", "---", ""]
        for s in scenes:
            cam = next((c for c in (camera.get("camera_directions") or [])
                        if c.get("scene_number") == s.get("scene_number")), {})
            sfx_scene = next((x for x in (sfx.get("per_scene_sfx") or [])
                              if x.get("scene_number") == s.get("scene_number")), {})
            lines += [
                f"## Scene {s.get('scene_number','?')}: {s.get('title','')}",
                f"**Type:** {s.get('type','')} | **Duration:** {s.get('duration_sec',15)}s",
            ]
            if cam:
                lines.append(f"**Camera:** [{cam.get('shot_type','')}] {cam.get('camera_direction','')} — {cam.get('transition_in','')} → {cam.get('transition_out','')}")
            lines += ["", f"**NARRATION:** {s.get('narration','')}", ""]
            for d in s.get("dialogue", []):
                lines.append(f"**{d.get('character','?')}:** \"{d.get('line','')}\"")
            if sfx_scene.get("sfx"):
                lines.append(f"**SFX:** {', '.join(sfx_scene['sfx'])}")
            lines += ["", "---", ""]
        z.writestr(f"{ep_id}/02_full_screenplay.md", "\n".join(lines))

        # 03 — Scene breakdown
        sb = [f"# Scene Breakdown: {title}", f"**{ep_id}** | {len(scenes)} scenes", "", "---", ""]
        for s in scenes:
            sb += [
                f"| Scene {s.get('scene_number','?')} | {s.get('type','').upper()} | {s.get('title','')} | {s.get('duration_sec',15)}s |",
            ]
        sb = [f"# Scene Breakdown: {title}", "", "| # | Type | Title | Duration |",
              "|---|------|-------|----------|"]
        for s in scenes:
            sb.append(f"| {s.get('scene_number','?')} | {s.get('type','')} | {s.get('title','')} | {s.get('duration_sec',15)}s |")
        sb += ["", "## Scene Summaries", ""]
        for s in scenes:
            sb += [f"**Scene {s.get('scene_number','?')}: {s.get('title','')}**",
                   s.get('narration',''), ""]
        z.writestr(f"{ep_id}/03_scene_breakdown.md", "\n".join(sb))

        # 04 — Cartoon image prompts (4 variants per scene)
        ip = [f"# Cartoon Image Prompts: {title}",
              "4 variants per scene — auto_render.py generates these automatically", "", "---", ""]
        for s in scenes:
            vp = s.get("visual_prompt", "")
            ip += [
                f"## Scene {s.get('scene_number','?')}: {s.get('title','')}",
                f"**BG Colors:** {', '.join(s.get('bg_colors', []))}",
                "",
                f"**Variant 1 (main):**", f"> {vp}", "",
                f"**Variant 2 (alt angle):**", f"> {vp}, alternate camera angle, different composition", "",
                f"**Variant 3 (close-up):**", f"> {vp}, close-up detail shot, dramatic framing", "",
                f"**Variant 4 (wide):**", f"> {vp}, wide establishing shot, sweeping cinematic angle", "",
                "---", "",
            ]
        z.writestr(f"{ep_id}/04_image_prompts.md", "\n".join(ip))

        # 05 — Animation prompts (Higgsfield)
        ap = [f"# Animation Prompts — Higgsfield: {title}", "", "---", ""]
        for s in scenes:
            hp = higgsfield.get_lo_camera_prompt(s.get("type", "narrative"), s.get("visual_prompt", ""))
            ap += [f"## Scene {s.get('scene_number','?')}: {s.get('title','')}",
                   f"> {hp}", "", "---", ""]
        z.writestr(f"{ep_id}/05_animation_prompts.md", "\n".join(ap))

        # 06 — Camera directions
        cd = [f"# Camera Directions: {title}", "", "---", ""]
        cam_dirs = camera.get("camera_directions", [])
        if cam_dirs:
            for c in cam_dirs:
                cd += [
                    f"## Scene {c.get('scene_number','?')}",
                    f"**Shot:** {c.get('shot_type','')} | **Focus:** {c.get('focus_point','')}",
                    f"**Movement:** {c.get('camera_direction','')}",
                    f"**In:** {c.get('transition_in','')} | **Out:** {c.get('transition_out','')}",
                    f"**Pacing:** {c.get('duration_note','')}",
                    "", "---", "",
                ]
        else:
            cd.append("Camera directions not generated in this run.")
        z.writestr(f"{ep_id}/06_camera_directions.md", "\n".join(cd))

        # 07 — Sound effects guide
        sfx_lines = [f"# Sound Effects Guide: {title}", "", "---", ""]
        if sfx:
            sfx_lines += ["## Master SFX List", ""]
            for item in (sfx.get("master_sfx_list") or []):
                sfx_lines.append(f"- **{item.get('name','')}** [{item.get('category','')}]: {item.get('description','')} (Scenes: {item.get('scenes',[])})")
            sfx_lines += ["", "## Per-Scene SFX", ""]
            for ps in (sfx.get("per_scene_sfx") or []):
                sfx_lines.append(f"**Scene {ps.get('scene_number','?')}:** {', '.join(ps.get('sfx',[]))}")
            sfx_lines += ["", "## Character Sounds", ""]
            for char, sounds in (sfx.get("character_sounds") or {}).items():
                sfx_lines.append(f"**{char}:** {', '.join(sounds)}")
            sfx_lines += ["", "## Ambient Loops", ""]
            for al in (sfx.get("ambient_loops") or []):
                sfx_lines.append(f"- {al}")
            sfx_lines += ["", "## Comedy SFX", ""]
            for cs in (sfx.get("comedy_sfx") or []):
                sfx_lines.append(f"- {cs}")
        else:
            sfx_lines.append("Sound effects not generated in this run.")
        z.writestr(f"{ep_id}/07_sound_effects.md", "\n".join(sfx_lines))

        # 08 — AI Music prompts (Suno/Udio)
        mp_lines = [f"# AI Music Prompts — Suno/Udio: {title}",
                    "Paste these directly into Suno, Udio, Soundraw, or any AI music tool.", "", "---", ""]
        if music_ai:
            mp_lines += [
                "## Main Theme", f"```", music_ai.get("main_theme_prompt",""), "```", "",
                "## Opening Jingle (8s)", f"```", music_ai.get("opening_sequence",""), "```", "",
                "## Closing Outro (8s)", f"```", music_ai.get("closing_sequence",""), "```", "",
                "## Action Cue", f"```", music_ai.get("action_cue",""), "```", "",
                "## Emotional/Lesson Moment", f"```", music_ai.get("emotional_cue",""), "```", "",
                "## Comedy Moment", f"```", music_ai.get("comedy_cue",""), "```", "",
                "## Transition Stinger", f"```", music_ai.get("transition_cue",""), "```", "",
                "", "## Suno Tips", music_ai.get("suno_tips",""), "",
                "## Udio Tips", music_ai.get("udio_tips",""), "",
                "## Recommended Style Tags", ", ".join(music_ai.get("example_tags",[])),
            ]
        else:
            mp_lines.append("AI music prompts not generated in this run.")
        z.writestr(f"{ep_id}/08_ai_music_prompts.md", "\n".join(mp_lines))

        # 09 — Voice guide
        cues = (voice.get("cues") or voice) if isinstance(voice, dict) else voice
        vl = [f"# Voice Script: {title}", f"Est. {voice.get('total_duration_sec','?')}s total", "", "---", ""]
        if isinstance(cues, list):
            for c in cues:
                vl += [
                    f"**[Scene {c.get('scene_number','?')}] {c.get('character','?').upper()}**",
                    f"*Direction: {c.get('direction','')}* | Est. {c.get('duration_estimate_sec',8)}s",
                    f"\"{c.get('text','')}\"", "",
                ]
        else:
            vl.append("Voice script not generated in this run.")
        z.writestr(f"{ep_id}/09_voice_script.md", "\n".join(vl))

        # 10 — Music guide
        ml = [f"# Music Guide: {title}", "", "---", ""]
        if music:
            mt = music.get("main_theme", {})
            ml += [
                "## Main Theme",
                f"**Style:** {mt.get('style','')} | **Tempo:** {mt.get('tempo','')}",
                f"**Instruments:** {', '.join(mt.get('instruments',[]))}",
                f"**Description:** {mt.get('description','')}",
                "", "## Scene Music", "",
            ]
            for sm in (music.get("scene_music") or []):
                ml.append(f"- **{sm.get('scene_type','')}** [{sm.get('mood','')}]: {sm.get('music_note','')}")
            ml += ["", "## Royalty-Free Sources", ""]
            for src in (music.get("music_sources") or []):
                ml.append(f"- {src}")
        z.writestr(f"{ep_id}/10_music_guide.md", "\n".join(ml))

        # 11 — Parent discussion guide
        pl = [f"# Parent Guide: {title}", ""]
        if guide:
            pl += [f"**Lesson:** {guide.get('lesson_summary', lesson)}", "", "## Talking Points", ""]
            for tp in (guide.get("talking_points") or []):
                pl += [f"**Q:** {tp.get('question','')}", f"*{tp.get('purpose','')}*", ""]
            pl += ["## Mythology Facts", ""]
            for fi in (guide.get("mythology_facts") or []):
                pl += [f"- **{fi.get('fact','')}**", f"  ↳ {fi.get('kid_explanation','')}", ""]
            pl += ["## Activities", ""]
            for ac in (guide.get("activities") or []):
                pl += [f"**{ac.get('name','')}** ({ac.get('age_range','')}): {ac.get('description','')}", ""]
            pl += ["## Vocabulary", ""]
            for v in (guide.get("vocabulary") or []):
                pl.append(f"- **{v.get('word','')}**: {v.get('definition','')}")
        z.writestr(f"{ep_id}/11_parent_discussion_guide.md", "\n".join(pl))

        # 12 — Coloring page prompt
        cp = [f"# Coloring Page Prompt: {title}", ""]
        if coloring:
            cp += [
                f"**Scene:** {coloring.get('scene_description','')}",
                f"**Caption:** {coloring.get('caption','')}",
                f"**Difficulty:** {coloring.get('difficulty','')}",
                "", "## Image Generation Prompt", "",
                f"```", coloring.get("coloring_page_prompt",""), "```", "",
                "## Coloring Tips (print on reverse)", "",
            ]
            for tip in str(coloring.get("coloring_tips","")).split(","):
                if tip.strip():
                    cp.append(f"- {tip.strip()}")
            cp += ["", f"**Bottom Activity:** {coloring.get('activity_prompt','')}"]
        else:
            cp.append("Coloring page not generated in this run.")
        z.writestr(f"{ep_id}/12_coloring_page_prompt.md", "\n".join(cp))

        # 13 — Activity sheet
        al = [f"# Activity Sheet: {title}", ""]
        if activity:
            al.append(f"## {activity.get('activity_sheet_title','Activities')}")
            al.append("")
            for act in (activity.get("activities") or []):
                al += [
                    f"### {act.get('title','')} ({act.get('type','').replace('_',' ').title()}) — Ages {act.get('age_group','')}",
                    f"*{act.get('instructions','')}*",
                    "", act.get("content",""), "",
                ]
            al += ["## Discussion Questions", ""]
            for q in (activity.get("discussion_questions") or []):
                al.append(f"- {q}")
            al += ["", "## Mini Quiz", ""]
            for q in (activity.get("mini_quiz") or []):
                al.append(f"**Q:** {q.get('question','')} | **A:** {q.get('answer','')} | *Hint: {q.get('hint','')}*")
            al += ["", "---",
                   f"**Fun Fact:** {activity.get('mythology_fun_fact','')}",
                   f"**Remember:** {activity.get('take_home_message','')}",
                   "", f"*Parent Corner: {activity.get('parent_corner','')}*"]
        else:
            al.append("Activity sheet not generated in this run.")
        z.writestr(f"{ep_id}/13_activity_sheet.md", "\n".join(al))

        # 14 — YouTube metadata
        yl = [f"# YouTube Metadata: {title}", ""]
        yl += [f"## Primary Title", seo.get("youtube_title", episode.get("youtube_title", title)), "",
               "## Alt Titles", ""]
        for alt in (seo.get("title_options") or []):
            yl.append(f"- {alt}")
        yl += ["", "## Description", "", seo.get("description", episode.get("youtube_description","")), "",
               "## Tags", "", ", ".join(seo.get("tags", episode.get("tags",[]))), "",
               "## Chapters", ""]
        for ch in (seo.get("chapters") or []):
            yl.append(f"{ch.get('time','?')} — {ch.get('label','')}")
        yl += ["", "## Thumbnail Concept", "", seo.get("thumbnail_concept", episode.get("thumbnail_concept","")), "",
               "## Shorts Ideas", ""]
        for si in (seo.get("shorts_ideas", episode.get("shorts_ideas",[]))):
            yl.append(f"- {si}")
        if "social_posts" in seo:
            sp = seo["social_posts"]
            yl += ["", "## Social Posts", "",
                   f"**Instagram:** {sp.get('instagram','')}", "",
                   f"**Twitter/X:** {sp.get('twitter','')}", "",
                   f"**Facebook:** {sp.get('facebook','')}"]
        z.writestr(f"{ep_id}/14_youtube_metadata.md", "\n".join(yl))

        # 15 — Production checklist
        cl = [
            f"# Production Checklist: {title}",
            f"**Episode:** {ep_id} | **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "", "## ✍️ Pre-Production",
            "- [ ] Script reviewed and approved",
            "- [ ] All character appearances match Character Bible",
            "- [ ] Lesson emerges naturally — no lecturing",
            "- [ ] No scene reuse — all visuals are distinct",
            "- [ ] Parent guide reviewed",
            "", "## 🖼️ Image Generation",
            f"- [ ] {len(scenes) * 4} images generated ({len(scenes)} scenes × 4 variants)",
            "- [ ] All character images match bible appearance",
            "- [ ] No inappropriate content",
            "- [ ] Coloring page image generated",
            "", "## 🎬 Animation",
            "- [ ] Animation prompts fed into Higgsfield (or motion tool)",
            "- [ ] Camera directions reviewed",
            "- [ ] Scene transitions match notes",
            "", "## 🔊 Audio",
            "- [ ] Narration recorded",
            f"- [ ] All character dialogue recorded ({len(chars)} characters)",
            "- [ ] Background music sourced/generated",
            "- [ ] Sound effects sourced",
            "- [ ] AI music prompts used for custom tracks",
            "", "## 🎥 Video Assembly",
            f"- [ ] Render: `python little_olympus_render.py --episode {ep_id}`",
            f"- [ ] Duration check: target {episode.get('duration_target_min',5)} min",
            "- [ ] Final MP4 quality checked",
            "- [ ] Captions/subtitles added",
            "", "## 📤 Publishing",
            "- [ ] Thumbnail created from coloring page prompt",
            "- [ ] YouTube metadata added (title, description, tags)",
            "- [ ] Chapters set in YouTube Studio",
            "- [ ] Shorts clips extracted",
            "- [ ] Social media posts ready",
            "- [ ] Activity sheet uploaded to community post",
            "- [ ] Coloring page shared in description",
            "", "## 📦 Files in This Package",
            "```",
            f"01_episode.json          ← Render-ready script",
            f"02_full_screenplay.md    ← Narration + dialogue + camera",
            f"03_scene_breakdown.md    ← Scene table + summaries",
            f"04_image_prompts.md      ← 4 variants per scene",
            f"05_animation_prompts.md  ← Higgsfield camera prompts",
            f"06_camera_directions.md  ← Shot type + transitions",
            f"07_sound_effects.md      ← Master SFX + per-scene guide",
            f"08_ai_music_prompts.md   ← Suno/Udio ready prompts",
            f"09_voice_script.md       ← Character-tagged cues",
            f"10_music_guide.md        ← Theme + mood guide",
            f"11_parent_discussion_guide.md",
            f"12_coloring_page_prompt.md",
            f"13_activity_sheet.md",
            f"14_youtube_metadata.md   ← Title, tags, description",
            f"15_production_checklist.md",
            "```",
        ]
        z.writestr(f"{ep_id}/15_production_checklist.md", "\n".join(cl))

    zb.seek(0)
    log.info(f"[EXPORT] {ep_id} — 15-file production package created")
    return send_file(
        zb,
        as_attachment=True,
        download_name=f"{ep_id}_production_package.zip",
        mimetype="application/zip",
    )


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("=" * 60)
    log.info("  LITTLE OLYMPUS STUDIO v1.1")
    log.info("  AI: Ollama (free local) → OpenAI (paid fallback)")
    log.info(f"  UI: http://localhost:{PORT}")
    log.info("=" * 60)
    ollama_st = ollama.get_status()
    openai_st = openai_adapter.get_status()
    log.info(f"  Ollama: {'✓ LIVE' if ollama_st['available'] else '✗ OFFLINE'} — {ollama_st['message']}")
    log.info(f"  OpenAI: {'✓ READY' if openai_st['available'] else '✗ NO KEY'} — {openai_st['message']}")
    log.info(f"  Episodes: {len(list_existing_episodes())} LO episodes in prompts/")
    log.info("=" * 60)
    app.run(host="0.0.0.0", port=PORT, debug=False)
