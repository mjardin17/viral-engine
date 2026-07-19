"""
asset_cache.py — Empire OS Character/Background Asset Cache (BUILD 3)
=======================================================================
Tracks which LO/IL characters and backgrounds already have a one-time
Higgsfield-generated reference sheet, so scene_classifier.py can route
repeat appearances to cheap FLUX Kontext compositing instead of paying
for Higgsfield again every single scene.

ADDITIVE ONLY — new module, touches nothing else. Directory layout:

    assets/
      characters/
        little_olympus/
          little_zeus/
            manifest.json   (name, reference_images, generated_date, poses, higgsfield_job_id)
          hera/
        iron_legends/
          pilot_mech/
      backgrounds/
        little_olympus/
          olympus_throne_room/
            manifest.json   (name, image_path, generated_date)

Usage:
    from asset_cache import AssetCache
    cache = AssetCache()
    cache.save_character("little_olympus", "little_zeus",
                         reference_images=["assets/characters/little_olympus/little_zeus/ref1.png"])
    entry = cache.get_character("little_olympus", "little_zeus")
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

BASE_DIR: Path = Path(__file__).resolve().parent


def _slug(text: str) -> str:
    return "_".join(str(text).strip().lower().split())


class AssetCache:
    """Filesystem-backed cache of known character/background reference assets."""

    def __init__(self, cache_root: str = "assets") -> None:
        root = Path(cache_root)
        self.cache_root: Path = root if root.is_absolute() else BASE_DIR / root
        self.characters_dir: Path = self.cache_root / "characters"
        self.backgrounds_dir: Path = self.cache_root / "backgrounds"
        self.characters_dir.mkdir(parents=True, exist_ok=True)
        self.backgrounds_dir.mkdir(parents=True, exist_ok=True)

    # ── characters ───────────────────────────────────────────────────────────
    def _character_dir(self, channel: str, character_name: str) -> Path:
        return self.characters_dir / _slug(channel) / _slug(character_name)

    def get_character(self, channel: str, character_name: str) -> dict | None:
        """Return cached character manifest, or None if not cached."""
        manifest = self._character_dir(channel, character_name) / "manifest.json"
        if not manifest.exists():
            return None
        try:
            return json.loads(manifest.read_text(encoding="utf-8"))
        except Exception:
            return None

    def save_character(self, channel: str, character_name: str,
                       reference_images: list[str], poses: list[str] | None = None,
                       higgsfield_job_id: str | None = None) -> dict:
        """Record a character's reference sheet. Returns the saved manifest."""
        d = self._character_dir(channel, character_name)
        d.mkdir(parents=True, exist_ok=True)
        manifest = {
            "name": character_name,
            "channel": _slug(channel),
            "reference_images": list(reference_images),
            "poses": list(poses) if poses else [],
            "higgsfield_job_id": higgsfield_job_id,
            "generated_date": datetime.now().isoformat(),
        }
        (d / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return manifest

    def list_cached_characters(self, channel: str) -> list[str]:
        d = self.characters_dir / _slug(channel)
        if not d.exists():
            return []
        return sorted(p.name for p in d.iterdir()
                     if p.is_dir() and (p / "manifest.json").exists())

    # ── backgrounds ──────────────────────────────────────────────────────────
    def _background_dir(self, channel: str, location_name: str) -> Path:
        return self.backgrounds_dir / _slug(channel) / _slug(location_name)

    def get_background(self, channel: str, location_name: str) -> dict | None:
        """Return cached background manifest, or None if not cached."""
        manifest = self._background_dir(channel, location_name) / "manifest.json"
        if not manifest.exists():
            return None
        try:
            return json.loads(manifest.read_text(encoding="utf-8"))
        except Exception:
            return None

    def save_background(self, channel: str, location_name: str, image_path: str) -> dict:
        """Record a background reference image. Returns the saved manifest."""
        d = self._background_dir(channel, location_name)
        d.mkdir(parents=True, exist_ok=True)
        manifest = {
            "name": location_name,
            "channel": _slug(channel),
            "image_path": str(image_path),
            "generated_date": datetime.now().isoformat(),
        }
        (d / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return manifest

    def list_cached_backgrounds(self, channel: str) -> list[str]:
        d = self.backgrounds_dir / _slug(channel)
        if not d.exists():
            return []
        return sorted(p.name for p in d.iterdir()
                     if p.is_dir() and (p / "manifest.json").exists())
