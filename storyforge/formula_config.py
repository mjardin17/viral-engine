"""
storyforge/formula_config.py — Formula + Customization Architecture

RULE: Patterson formula is MANDATORY and non-negotiable.
Customizations can be added ON TOP but never replace the formula.

Architecture:
  PattersonFormula (BASELINE - required)
  └─ CustomizationLayer (OPTIONAL - extends only)
     ├─ Character voice profiles
     ├─ Emotional arcs
     ├─ Cultural adaptation
     ├─ Series continuity hooks
     └─ ... (anything except formula violations)

Quality gate:
  1. Generate chapter using formula + customization
  2. ALWAYS validate against formula (non-negotiable)
  3. If violations exist: REJECT (never publish with violations)
  4. If violations zero: PASS (publish)

This ensures every StoryForge book ALWAYS follows Patterson's mechanical formula.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from storyforge.patterson_formula import PattersonFormula, ReadingLevel


@dataclass
class CustomizationLayer:
    """Optional customizations that extend (never replace) the formula."""

    # Character voice: each character speaks with distinct style
    character_voices: dict[str, str] = field(default_factory=dict)
    # e.g. {"Axon": "robotic, technical", "The Council": "authoritative, cryptic"}

    # Emotional beats: inject emotional escalation into chapters
    emotion_arc: list[str] = field(default_factory=list)
    # e.g. ["tension", "confusion", "fear", "revelation"]

    # Series continuity: specific callbacks/foreshadowing to other books
    series_callbacks: list[str] = field(default_factory=list)
    # e.g. ["mention the prophecy from book 1", "hint at the betrayal"]

    # Cultural adaptation: region/language specific tweaks
    cultural_markers: dict[str, str] = field(default_factory=dict)
    # e.g. {"setting": "Nevada", "slang": "American"}

    # Custom prompt suffix: additional requirements (non-formula)
    custom_instructions: str = ""
    # e.g. "Make this scene comedic" (humor added, formula still enforced)

    def to_prompt_suffix(self) -> str:
        """Convert customization layer to prompt instructions."""
        parts = []

        if self.character_voices:
            voices = "\n  ".join(
                [f"{name}: {style}" for name, style in self.character_voices.items()]
            )
            parts.append(f"VOICE CONSISTENCY:\n  {voices}")

        if self.emotion_arc:
            parts.append(f"EMOTIONAL ARC: {' → '.join(self.emotion_arc)}")

        if self.series_callbacks:
            parts.append(f"SERIES CONTINUITY:\n  " + "\n  ".join(self.series_callbacks))

        if self.cultural_markers:
            markers = ", ".join([f"{k}={v}" for k, v in self.cultural_markers.items()])
            parts.append(f"CULTURAL CONTEXT: {markers}")

        if self.custom_instructions:
            parts.append(f"CUSTOM REQUIREMENTS: {self.custom_instructions}")

        return "\n\n".join(parts)


@dataclass
class BookConfig:
    """Complete book generation configuration: formula + customization."""

    # MANDATORY: core Patterson formula
    formula: PattersonFormula

    # OPTIONAL: customization layer (extends, never replaces)
    customization: CustomizationLayer = field(default_factory=CustomizationLayer)

    # SAFETY: quality gate function (called before publishing)
    quality_gate: Optional[Callable[[str], bool]] = None

    def validate_and_generate(self, prompt: str, generator_fn: Callable) -> tuple[str, list[str]]:
        """
        Generate chapter with formula enforcement.

        RULE: If formula violations exist, REJECT.
        Customization is bonus; formula is non-negotiable.
        """
        # Generate using formula + customization
        full_prompt = self._build_full_prompt(prompt)
        chapter = generator_fn(full_prompt)

        # ALWAYS validate against formula (non-negotiable)
        violations = self.formula.validate_chapter(chapter)

        if violations:
            # REJECT: formula violations are fatal
            return chapter, violations

        # Optional quality gate (beyond formula)
        if self.quality_gate and not self.quality_gate(chapter):
            return chapter, ["Quality gate failed (custom check)"]

        # PASS: formula satisfied + optional quality gate passed
        return chapter, []

    def _build_full_prompt(self, base_prompt: str) -> str:
        """Combine formula prompt + customization layer."""
        customization_text = self.customization.to_prompt_suffix()

        if customization_text:
            return f"{base_prompt}\n\n{customization_text}"
        return base_prompt


# Preset configurations for common book types

# Iron Legends: YA action, mech anime, intense but clean
IL_CONFIG = BookConfig(
    formula=PattersonFormula(reading_level=ReadingLevel.YA),
    customization=CustomizationLayer(
        character_voices={
            "Axon": "stoic, technical, hints of loneliness",
            "The Iron Council": "commanding, ominous, ancient authority",
            "Null": "seductive, philosophical, morally inverted",
        },
        emotion_arc=["mystery", "danger", "determination", "revelation"],
        series_callbacks=[
            "hint at the Fracture's origin",
            "foreshadow the betrayal",
            "show hints of Axon's hidden past",
        ],
        cultural_markers={"setting": "Nevada desert", "tech_level": "futuristic"},
    ),
)

# Little Olympus: MG adventure, kids content, warm and playful
LO_CONFIG = BookConfig(
    formula=PattersonFormula(reading_level=ReadingLevel.MG),
    customization=CustomizationLayer(
        character_voices={
            "Little Zeus": "excited, curious, brave but young",
            "Baby Hercules": "confused, silly, accidentally helpful",
            "Athena": "wise, patient, one step ahead",
            "Stormy": "sad underneath grumpy, misunderstood villain",
        },
        emotion_arc=["wonder", "trouble", "bravery", "friendship"],
        series_callbacks=[
            "introduce a new Olympian in the coda",
            "hint at the bigger prophecy",
        ],
        cultural_markers={"setting": "Mount Olympus", "tone": "kids adventure"},
        custom_instructions="Keep humor warm and inclusive. No scary moments.",
    ),
)

# Adult thriller: sophisticated formula + literary depth
ADULT_CONFIG = BookConfig(
    formula=PattersonFormula(reading_level=ReadingLevel.ADULT),
    customization=CustomizationLayer(
        emotion_arc=["suspicion", "paranoia", "revelation", "reckoning"],
        custom_instructions="Add psychological depth to character motivations. Moral ambiguity welcome.",
    ),
)


def get_book_config(book_type: str) -> BookConfig:
    """Get preset configuration for a book type."""
    configs = {
        "iron_legends": IL_CONFIG,
        "little_olympus": LO_CONFIG,
        "adult_thriller": ADULT_CONFIG,
    }
    if book_type not in configs:
        raise ValueError(f"Unknown book type: {book_type}. Choose: {list(configs.keys())}")
    return configs[book_type]
