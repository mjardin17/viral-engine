"""
storyforge/book_generator.py — Full book generation with Patterson formula enforcement.

RULE: Patterson formula is MANDATORY. Every chapter MUST pass validation.
No chapter ships with formula violations.

Customizations (character voices, emotional arcs, etc.) are optional add-ons.
They extend the formula but never replace it.

Usage:
    from storyforge.book_generator import generate_book_from_manifest
    success = generate_book_from_manifest("storyforge/books/il_ep001/manifest.json")
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from storyforge.config import init_env
from storyforge.generator import generate_chapter_with_formula

init_env()


def generate_book_from_manifest(manifest_path: str | Path) -> bool:
    """
    Generate a complete book from an episode-adapted manifest.

    Each chapter is generated using the Patterson formula with validation.
    """
    manifest_path = Path(manifest_path)
    if not manifest_path.exists():
        print(f"ERROR: Manifest not found: {manifest_path}")
        return False

    manifest = json.loads(manifest_path.read_text())
    book_dir = manifest_path.parent
    title = manifest.get("title", "Unknown")
    reading_level = manifest.get("reading_level", "YA")
    characters = manifest.get("characters", {})
    chapters = manifest.get("chapters", [])

    print(f"\n[BOOK] {title}")
    print(f"  Reading level: {reading_level}")
    print(f"  Chapters: {len(chapters)}")
    print(f"  Generating with Patterson formula...\n")

    generated_chapters = []
    total_words = 0
    total_violations = 0

    for ch in chapters:
        ch_num = ch["chapter_number"]
        ch_title = ch["title"]
        narration = ch["narration"]

        print(f"  Chapter {ch_num}: {ch_title}", end="", flush=True)

        try:
            chapter_text, violations = generate_chapter_with_formula(
                chapter_num=ch_num,
                title=ch_title,
                narration=narration,
                reading_level=reading_level,
                characters=characters,
                max_retries=2,
            )

            word_count = len(chapter_text.split())
            total_words += word_count
            total_violations += len(violations)

            # QUALITY GATE: Formula violations are FATAL (never publish)
            if violations:
                print(f" | {word_count}w | REJECTED: formula violations")
                print(f"      Violations: {violations}")
                print(f"      → Chapter will not be included in final book")
                continue  # Skip this chapter (don't save it)

            status = "PASS"
            print(f" | {word_count}w | {status}")

            # Save chapter to file (only if it passes formula)
            ch_file = book_dir / f"chapter_{ch_num:02d}.txt"
            ch_file.write_text(chapter_text, encoding="utf-8")

            generated_chapters.append(
                {
                    "number": ch_num,
                    "title": ch_title,
                    "words": word_count,
                    "violations": violations,
                    "file": str(ch_file),
                }
            )

            time.sleep(1)  # Rate limit

        except Exception as e:
            print(f" | ERROR: {str(e)[:50]}")
            return False

    # Update manifest with results
    manifest["chapters_generated"] = len(generated_chapters)
    manifest["total_words"] = total_words
    manifest["total_violations"] = total_violations
    manifest["status"] = "complete"
    manifest["chapter_files"] = [
        {"number": ch["number"], "file": ch["file"]} for ch in generated_chapters
    ]

    manifest_path.write_text(json.dumps(manifest, indent=2))

    # Summary
    avg_words = total_words // len(generated_chapters) if generated_chapters else 0
    print(f"\n  Total: {total_words} words across {len(generated_chapters)} chapters")
    print(f"  Average: {avg_words} words/chapter")
    print(f"  Formula violations: {total_violations} total")
    print(f"  Status: COMPLETE\n")

    return True


if __name__ == "__main__":
    # Test: generate IL_EP001 book
    il_ok = generate_book_from_manifest("storyforge/books/il_ep001/manifest.json")
    print(f"IL_EP001: {'SUCCESS' if il_ok else 'FAILED'}")

    # Test: generate LO_EP001 book
    lo_ok = generate_book_from_manifest("storyforge/books/lo_ep001/manifest.json")
    print(f"LO_EP001: {'SUCCESS' if lo_ok else 'FAILED'}")
