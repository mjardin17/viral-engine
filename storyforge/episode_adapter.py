"""
storyforge/episode_adapter.py — Convert video episode scripts to book outlines.
Takes channel episode JSON (scenes + narration + characters) and generates a book manifest.

Usage:
    from storyforge.episode_adapter import adapt_episode
    manifest = adapt_episode("prompts/iron_legends/IL_EP001.json")
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass
class BookOutline:
    """Book outline derived from episode script."""
    title: str
    episode_id: str
    channel: str
    description: str
    characters: dict[str, str]
    chapters: list[dict[str, Any]]
    target_word_count: int
    reading_level: str  # "YA" or "MG" (middle-grade)


def adapt_episode(episode_path: str | Path) -> BookOutline:
    """Convert episode JSON to book outline."""
    episode_path = Path(episode_path)
    if not episode_path.exists():
        raise FileNotFoundError(f"Episode file not found: {episode_path}")

    episode = json.loads(episode_path.read_text(encoding="utf-8"))
    channel = episode.get("channel", "UNKNOWN")
    episode_id = episode.get("episode_id")
    title = episode.get("title", "Untitled")
    scenes = episode.get("scenes", [])
    characters = episode.get("characters", {})

    # Determine reading level and chapter structure
    if channel == "IL":
        reading_level = "YA"
        words_per_chapter = 600  # IL is action-heavy, slightly longer chapters
        scene_grouping = 4  # 4-5 scenes per chapter
    else:  # LO
        reading_level = "MG"
        words_per_chapter = 500  # Kids content, punchier chapters
        scene_grouping = 3  # 3 scenes per chapter

    # Group scenes into chapters
    chapters = []
    for chapter_num, i in enumerate(range(0, len(scenes), scene_grouping), start=1):
        chapter_scenes = scenes[i : i + scene_grouping]
        chapters.append({
            "chapter_number": chapter_num,
            "title": chapter_scenes[0].get("title", f"Chapter {chapter_num}"),
            "scenes": [s.get("scene_number") for s in chapter_scenes],
            "narration": " ".join([s.get("narration", "") for s in chapter_scenes]),
            "scene_count": len(chapter_scenes),
            "target_words": words_per_chapter,
        })

    # Build description from narration of first 3 scenes
    description = " ".join([s.get("narration", "") for s in scenes[:3]])[:300] + "..."

    # Calculate total word count
    target_word_count = len(chapters) * words_per_chapter

    # Format characters for prompt injection
    char_descriptions = {}
    for key, char in characters.items():
        if isinstance(char, dict):
            name = char.get("name", key)
            visual = char.get("visual", "")
            char_descriptions[name.lower()] = f"{name}: {visual}"

    return BookOutline(
        title=title,
        episode_id=episode_id,
        channel=channel,
        description=description,
        characters=char_descriptions,
        chapters=chapters,
        target_word_count=target_word_count,
        reading_level=reading_level,
    )


def episode_to_manifest(outline: BookOutline) -> dict[str, Any]:
    """Convert BookOutline to storyforge manifest format."""
    import re
    from datetime import datetime

    slug = re.sub(r"[^a-z0-9]+", "_", outline.episode_id.lower()).strip("_")

    manifest = {
        "id": slug,
        "episode_id": outline.episode_id,
        "title": outline.title,
        "channel": outline.channel,
        "description": outline.description,
        "genre": "Action" if outline.reading_level == "YA" else "Adventure",
        "reading_level": outline.reading_level,
        "word_count": outline.target_word_count,
        "chapter_count": len(outline.chapters),
        "characters": outline.characters,
        "chapters": outline.chapters,
        "status": "outline_ready",
        "created_at": datetime.now().isoformat(),
        "voice_profile": {
            "tone": "cinematic" if outline.reading_level == "YA" else "playful",
            "pov": "third_person_limited",
            "forbidden_phrases": ["As an AI", "In conclusion", "delve"],
        },
        "series": {
            "name": f"@{'ironlegendsai' if outline.channel == 'IL' else 'littleolympusai'}",
            "book_number": 1,
            "next_book_hook": "",  # Will be filled by generator
        },
    }

    return manifest


def save_manifest(manifest: dict, output_path: Path) -> None:
    """Save manifest to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
