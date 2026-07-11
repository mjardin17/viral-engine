"""
storyforge/generator.py — Empire OS Book Generator
Takes a niche/topic → generates full book content via Gemini + cover via Pollinations.
Outputs: storyforge/books/{slug}/  (content.json, cover.png, manuscript.txt)

Usage:
    python storyforge/generator.py --niche "Military History" --title "Lost Battles of WWII"
    python storyforge/generator.py --auto   # picks top niche from NICHE_BOARD.json
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

import requests

REPO        = Path(__file__).parent.parent
BOOKS_DIR   = Path(__file__).parent / "books"
NICHE_BOARD = Path(__file__).parent / "NICHE_BOARD.json"
BOOKS_DIR.mkdir(exist_ok=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_URL     = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

HEADERS = {"User-Agent": "Mozilla/5.0"}


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:40]


def call_gemini(prompt: str) -> str:
    """Call Gemini API, return generated text."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set in .env — Josh: add it to .env file")

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.8, "maxOutputTokens": 8192},
    }
    resp = requests.post(
        f"{GEMINI_URL}?key={GEMINI_API_KEY}",
        json=payload, timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def generate_book_plan(niche: str, title: str) -> dict:
    """Generate a full book outline with chapter titles and descriptions."""
    print(f"  [GEN] Generating book plan for: {title}")
    prompt = f"""You are a bestselling author creating a book for Amazon KDP.
Niche: {niche}
Title: {title}

Create a complete book plan with:
1. Subtitle (compelling, SEO-optimized for Amazon)
2. Author bio (short, 2 sentences, authoritative)
3. Book description (150 words, Amazon-optimized)
4. 7 chapter titles with 1-sentence descriptions each
5. 5 Amazon keywords (comma-separated)
6. Target audience (1 sentence)

Format as JSON with keys: subtitle, author_bio, description, chapters (list of {{title, summary}}), keywords, audience.
Only output valid JSON, no markdown."""

    raw = call_gemini(prompt)
    # Strip any markdown fences
    raw = re.sub(r"```json\s*|\s*```", "", raw).strip()
    return json.loads(raw)


def generate_chapter(chapter_title: str, chapter_summary: str, book_title: str, niche: str) -> str:
    """Generate full chapter content (~1500-2000 words)."""
    print(f"    [GEN] Writing chapter: {chapter_title}")
    prompt = f"""You are a bestselling author writing for Amazon KDP.
Book: "{book_title}" — Niche: {niche}
Chapter: "{chapter_title}"
Chapter summary: {chapter_summary}

Write a compelling, well-researched chapter of 1500-2000 words.
- Engaging storytelling style
- Real facts and vivid details
- Subheadings to break up the text
- End with a compelling transition to the next chapter
Output only the chapter text, no commentary."""

    return call_gemini(prompt)


def generate_cover(title: str, niche: str, slug: str, book_dir: Path) -> Path:
    """Generate book cover using Pollinations (free)."""
    cover_path = book_dir / "cover.png"
    if cover_path.exists():
        return cover_path

    print(f"  [GEN] Generating cover for: {title}")
    prompt = (
        f"Professional book cover for '{title}', {niche} genre, "
        "dramatic cinematic lighting, epic composition, bestseller quality, "
        "dark rich colors, bold typography space at top and bottom"
    )
    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}?width=1600&height=2560&nologo=true"

    for attempt in range(3):
        try:
            resp = requests.get(url, timeout=60, headers=HEADERS)
            if resp.status_code == 200 and len(resp.content) > 10000:
                cover_path.write_bytes(resp.content)
                print(f"  [GEN] Cover saved ({len(resp.content)//1024}KB)")
                return cover_path
        except Exception as e:
            print(f"  [GEN] Cover attempt {attempt+1} failed: {e}")
            time.sleep(3)

    print("  [GEN] Cover generation failed — using placeholder")
    return cover_path


def run_generator(niche: str, title: str) -> Path:
    """Full pipeline: plan → chapters → cover → save manifest."""
    slug     = slugify(title)
    book_dir = BOOKS_DIR / slug
    book_dir.mkdir(exist_ok=True)

    manifest_path = book_dir / "manifest.json"
    if manifest_path.exists():
        print(f"  [GEN] Book already exists at {book_dir} — skipping")
        return book_dir

    # 1. Generate plan
    plan = generate_book_plan(niche, title)
    time.sleep(1)

    # 2. Generate all chapters
    chapters: list[dict] = []
    for ch in plan["chapters"]:
        content = generate_chapter(ch["title"], ch["summary"], title, niche)
        chapters.append({"title": ch["title"], "content": content})
        time.sleep(2)

    # 3. Generate cover
    cover_path = generate_cover(title, niche, slug, book_dir)

    # 4. Write full manuscript text
    manuscript = f"# {title}\n## {plan.get('subtitle','')}\n\n"
    for ch in chapters:
        manuscript += f"\n\n## {ch['title']}\n\n{ch['content']}\n"
    (book_dir / "manuscript.txt").write_text(manuscript, encoding="utf-8")

    # 5. Save manifest
    manifest = {
        "title":       title,
        "subtitle":    plan.get("subtitle", ""),
        "niche":       niche,
        "slug":        slug,
        "author_bio":  plan.get("author_bio", ""),
        "description": plan.get("description", ""),
        "keywords":    plan.get("keywords", ""),
        "audience":    plan.get("audience", ""),
        "chapters":    [{"title": c["title"]} for c in chapters],
        "cover":       str(cover_path),
        "manuscript":  str(book_dir / "manuscript.txt"),
        "created_at":  datetime.utcnow().isoformat() + "Z",
        "status":      "generated",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"\n[GEN] Book complete: {book_dir}")
    print(f"       Title:    {title}")
    print(f"       Subtitle: {plan.get('subtitle','')}")
    print(f"       Chapters: {len(chapters)}")
    return book_dir


def auto_pick_niche() -> tuple[str, str]:
    """Pick top niche from NICHE_BOARD.json and generate a title via Gemini."""
    if not NICHE_BOARD.exists():
        raise RuntimeError("NICHE_BOARD.json not found — run scanner.py first")

    data   = json.loads(NICHE_BOARD.read_text(encoding="utf-8"))
    top    = data["niches"][0]
    niche  = top["category"]
    sample = top["sample_titles"]

    print(f"  [GEN] Auto-picked niche: {niche}")
    prompt = f"""Suggest a unique, compelling Amazon KDP book title for the {niche} genre.
    Existing bestsellers for inspiration (do NOT copy): {', '.join(sample[:3])}
    Output ONLY the title, nothing else."""
    title = call_gemini(prompt).strip().strip('"')
    return niche, title


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--niche", default="")
    p.add_argument("--title", default="")
    p.add_argument("--auto",  action="store_true")
    args = p.parse_args()

    if args.auto or not args.niche:
        niche, title = auto_pick_niche()
    else:
        niche, title = args.niche, args.title

    run_generator(niche, title)
