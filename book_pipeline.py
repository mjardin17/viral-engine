#!/usr/bin/env python3
"""Empire OS — AI Book Publishing Pipeline.

Commands:
    research    Scan 8 profitable niches via Google Books API, find topic gaps.
    generate    Write a full non-fiction book with Gemini (gemini-1.5-pro).
    package     Build an EPUB from generated chapters (ebooklib).
    distribute  Submit / print instructions for Draft2Digital + Amazon KDP.
    status      Show the books_queue.json pipeline table.

Usage:
    python book_pipeline.py research
    python book_pipeline.py generate --niche "personal finance" --title "The 30-Day Money Reset"
    python book_pipeline.py package --title "The 30-Day Money Reset"
    python book_pipeline.py distribute --title "The 30-Day Money Reset"
    python book_pipeline.py status

Author: Empire OS (Josh Jardin)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent
ENV_PATH = REPO_ROOT / ".env"
QUEUE_PATH = REPO_ROOT / "books_queue.json"
RESEARCH_PATH = REPO_ROOT / "books_research.json"
BOOKS_OUTPUT_DIR = REPO_ROOT / "output" / "books"
EPUB_OUTPUT_DIR = REPO_ROOT / "renders" / "books"

GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"
D2D_API_URL = "https://www.draft2digital.com/api/v2/books"
KDP_URL = "https://kdp.amazon.com/en_US/title-setup/kindle"

GEMINI_MODEL = "gemini-1.5-pro"
AUTHOR_NAME = "Josh Jardin"
CHAPTER_COUNT = 10
CHAPTER_WORDS = 1500
RATE_LIMIT_WAIT_S = 30

NICHES: List[str] = [
    "personal finance",
    "self help",
    "business",
    "health wellness",
    "productivity",
    "mindset",
    "relationships",
    "spirituality",
]

# Angle keywords used to detect topic gaps in the top results of a niche.
GAP_ANGLES: List[str] = [
    "for beginners",
    "30-day",
    "workbook",
    "step-by-step",
    "for women",
    "for men",
    "over 50",
    "for teens",
    "journal",
    "science-based",
    "for entrepreneurs",
    "quick start",
    "daily habits",
    "checklist",
]


# ---------------------------------------------------------------------------
# Small utilities
# ---------------------------------------------------------------------------

def load_env(path: Path = ENV_PATH) -> Dict[str, str]:
    """Parse a simple KEY=VALUE .env file (stdlib only, no python-dotenv)."""
    env: Dict[str, str] = {}
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def safe_title(title: str) -> str:
    """Filesystem-safe slug: 'The 30-Day Money Reset' -> 'the_30_day_money_reset'."""
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    return slug or "untitled"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def count_words(text: str) -> int:
    return len(text.split())


# ---------------------------------------------------------------------------
# books_queue.json helpers
# ---------------------------------------------------------------------------

def load_queue() -> Dict[str, Any]:
    if QUEUE_PATH.exists():
        try:
            data = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("books"), list):
                return data
        except json.JSONDecodeError:
            print(f"[WARN] {QUEUE_PATH.name} is corrupt — starting a fresh queue "
                  f"(old file backed up as {QUEUE_PATH.name}.bak)")
            QUEUE_PATH.replace(QUEUE_PATH.with_suffix(".json.bak"))
    return {"books": []}


def save_queue(queue: Dict[str, Any]) -> None:
    QUEUE_PATH.write_text(json.dumps(queue, indent=2, ensure_ascii=False), encoding="utf-8")


def find_book(queue: Dict[str, Any], title: str) -> Optional[Dict[str, Any]]:
    slug = safe_title(title)
    for book in queue["books"]:
        if safe_title(book.get("title", "")) == slug:
            return book
    return None


def upsert_book(queue: Dict[str, Any], title: str, niche: str = "") -> Dict[str, Any]:
    book = find_book(queue, title)
    if book is None:
        book = {
            "id": str(uuid.uuid4()),
            "title": title,
            "niche": niche,
            "status": "new",
            "created": now_iso(),
            "word_count": 0,
            "epub_path": "",
            "platforms": [],
        }
        queue["books"].append(book)
    elif niche and not book.get("niche"):
        book["niche"] = niche
    return book


# ---------------------------------------------------------------------------
# Command: research
# ---------------------------------------------------------------------------

def cmd_research(_args: argparse.Namespace) -> int:
    import requests  # already in the pipeline stack

    print("=" * 64)
    print("EMPIRE OS BOOK PIPELINE — NICHE RESEARCH (Google Books API)")
    print("=" * 64)

    research: Dict[str, List[Dict[str, Any]]] = {}
    niche_scores: List[Dict[str, Any]] = []

    for niche in NICHES:
        print(f"\n[Research] Niche: {niche} ...", flush=True)
        try:
            resp = requests.get(
                GOOGLE_BOOKS_URL,
                params={
                    "q": f"subject:{niche}",
                    "orderBy": "relevance",
                    "maxResults": 10,
                },
                timeout=30,
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])
        except Exception as exc:  # noqa: BLE001 — report and continue, no silent failure
            print(f"  [ERROR] Google Books request failed for '{niche}': {exc}")
            research[niche] = []
            continue

        combined_text = ""
        entries: List[Dict[str, Any]] = []

        for item in items[:5]:
            info = item.get("volumeInfo", {})
            title = info.get("title", "Unknown")
            authors = info.get("authors", ["Unknown"])
            description = info.get("description", "") or ""
            page_count = info.get("pageCount", 0) or 0
            rating = info.get("averageRating")
            ratings_count = info.get("ratingsCount", 0) or 0
            combined_text += f" {title} {description}".lower()

            if ratings_count > 5000:
                competition = "high"
            elif ratings_count > 500:
                competition = "medium"
            else:
                competition = "low"

            entries.append({
                "title": title,
                "author": ", ".join(authors),
                "description": description[:300],
                "page_count": page_count,
                "avg_rating": rating,
                "ratings_count": ratings_count,
                "competition_level": competition,
            })
            rating_str = f"{rating}★" if rating else "no rating"
            print(f"  - {title} — {', '.join(authors)} ({page_count}p, {rating_str}, competition: {competition})")

        # Topic gaps: angles nobody in the top 5 covers.
        gaps = [angle for angle in GAP_ANGLES if angle not in combined_text]
        for i, entry in enumerate(entries):
            angle = gaps[i % len(gaps)] if gaps else "fresh modern take"
            entry["gap_opportunity"] = (
                f"No strong '{angle}' book in top {niche} results — "
                f"opportunity: '{niche.title()} {angle.title()}' style title"
            )

        research[niche] = entries

        comp_score = {"low": 0, "medium": 1, "high": 2}
        avg_comp = (
            sum(comp_score[e["competition_level"]] for e in entries) / len(entries)
            if entries else 2.0
        )
        # More gaps + lower competition = better opportunity.
        opportunity = len(gaps) * 1.0 + (2.0 - avg_comp) * 3.0
        niche_scores.append({
            "niche": niche,
            "opportunity_score": round(opportunity, 1),
            "topic_gaps": gaps[:5],
            "avg_competition": ["low", "medium", "high"][min(2, round(avg_comp))],
        })
        if gaps:
            print(f"  Gaps found: {', '.join(gaps[:5])}")

    if not any(research.values()):
        print("\n[ERROR] Every niche request failed — check the network connection. "
              "Nothing saved (refusing to overwrite research with empty data).")
        return 1

    RESEARCH_PATH.write_text(json.dumps(research, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[OK] Research saved -> {RESEARCH_PATH}")

    niche_scores.sort(key=lambda n: n["opportunity_score"], reverse=True)
    print("\n" + "=" * 64)
    print("RANKED NICHE OPPORTUNITIES (best first)")
    print("=" * 64)
    for rank, n in enumerate(niche_scores, 1):
        print(f"{rank}. {n['niche']:<18} score {n['opportunity_score']:>5}  "
              f"competition: {n['avg_competition']}")
        if n["topic_gaps"]:
            print(f"   gaps: {', '.join(n['topic_gaps'])}")
    print("\nNext: python book_pipeline.py generate --niche \"<niche>\" --title \"<title>\"")
    return 0


# ---------------------------------------------------------------------------
# Command: generate
# ---------------------------------------------------------------------------

def _gemini_call(model: Any, prompt: str) -> str:
    """Call Gemini with one 30s-wait retry on rate limits."""
    for attempt in (1, 2):
        try:
            response = model.generate_content(prompt)
            text = getattr(response, "text", "") or ""
            if not text.strip():
                raise RuntimeError("Gemini returned an empty response")
            return text
        except Exception as exc:  # noqa: BLE001
            message = str(exc).lower()
            is_rate_limit = any(tok in message for tok in ("429", "rate", "quota", "exhausted", "resource"))
            if attempt == 1 and is_rate_limit:
                print(f"  [RATE LIMIT] {exc} — waiting {RATE_LIMIT_WAIT_S}s and retrying once...")
                time.sleep(RATE_LIMIT_WAIT_S)
                continue
            raise
    raise RuntimeError("unreachable")


def _parse_outline_json(raw: str) -> Dict[str, Any]:
    """Extract the JSON object from a Gemini response (handles ```json fences)."""
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            text = text[start:end + 1]
    return json.loads(text)


def cmd_generate(args: argparse.Namespace) -> int:
    env = load_env()
    api_key = env.get("GEMINI_API_KEY", "")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY not found in .env — add it and re-run.")
        return 1

    try:
        import google.generativeai as genai
    except ImportError:
        print("[ERROR] google-generativeai not installed. Run:")
        print(f'  "{sys.executable}" -m pip install google-generativeai')
        return 1

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(GEMINI_MODEL)

    title: str = args.title
    niche: str = args.niche
    book_dir = BOOKS_OUTPUT_DIR / safe_title(title)
    book_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 64)
    print(f"GENERATING BOOK: {title}  (niche: {niche}, model: {GEMINI_MODEL})")
    print("=" * 64)

    # ---- Step 1: outline (reuse existing outline if present — never overwrite) ----
    outline_path = book_dir / "outline.json"
    if outline_path.exists():
        print("[Outline] outline.json already exists — reusing it (no overwrite).")
        outline = json.loads(outline_path.read_text(encoding="utf-8"))
    else:
        print("[Outline] Generating detailed outline...")
        outline_prompt = f"""You are a bestselling non-fiction ghostwriter. Create a detailed outline for a book.

Book title: "{title}"
Niche: {niche}
Author: {AUTHOR_NAME}

Return ONLY valid JSON (no commentary) with exactly this structure:
{{
  "title": "{title}",
  "subtitle": "a compelling marketable subtitle",
  "introduction_summary": "2-3 sentence summary of the introduction",
  "chapters": [
    {{"number": 1, "title": "chapter title", "subheadings": ["sub 1", "sub 2", "sub 3"]}}
  ],
  "conclusion_summary": "2-3 sentence summary of the conclusion"
}}

Requirements: exactly {CHAPTER_COUNT} chapters, each with exactly 3 subheadings.
Make the outline practical, actionable, and targeted at the {niche} audience."""
        raw = _gemini_call(model, outline_prompt)
        try:
            outline = _parse_outline_json(raw)
        except (json.JSONDecodeError, ValueError) as exc:
            print(f"[ERROR] Could not parse outline JSON from Gemini: {exc}")
            (book_dir / "outline_raw.txt").write_text(raw, encoding="utf-8")
            print(f"  Raw response saved to {book_dir / 'outline_raw.txt'} for inspection.")
            return 1
        outline_path.write_text(json.dumps(outline, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[Outline] Saved -> {outline_path}")

    chapters: List[Dict[str, Any]] = outline.get("chapters", [])[:CHAPTER_COUNT]
    subtitle: str = outline.get("subtitle", "")
    print(f"[Outline] Subtitle: {subtitle}")
    print(f"[Outline] {len(chapters)} chapters planned.")

    # ---- Step 2: introduction ----
    intro_path = book_dir / "introduction.txt"
    if intro_path.exists():
        print("[Intro] introduction.txt exists — skipping (no overwrite).")
    else:
        print("[Intro] Writing introduction...")
        intro = _gemini_call(model, (
            f'Write the introduction (600-800 words) for the non-fiction book "{title}: {subtitle}" '
            f"in the {niche} niche. Summary of the intro: {outline.get('introduction_summary', '')}. "
            f"Hook the reader, promise a transformation, preview the {len(chapters)} chapters. "
            "Plain text only, no markdown headers."
        ))
        intro_path.write_text(intro, encoding="utf-8")

    # ---- Step 3: chapters ----
    chapter_titles = ", ".join(c.get("title", f"Chapter {c.get('number', '?')}") for c in chapters)
    for i, chapter in enumerate(chapters, 1):
        ch_title = chapter.get("title", f"Chapter {i}")
        ch_path = book_dir / f"chapter_{i:02d}.txt"
        print(f"[Chapter {i}/{len(chapters)}] Writing: {ch_title}...")
        if ch_path.exists():
            print(f"  -> chapter_{i:02d}.txt exists — skipping (no overwrite).")
            continue
        subs = chapter.get("subheadings", [])
        content = _gemini_call(model, (
            f'Write chapter {i} of the non-fiction book "{title}: {subtitle}" ({niche} niche).\n'
            f'Chapter title: "{ch_title}"\n'
            f"Cover these 3 sections in order: {'; '.join(subs)}\n"
            f"Full book chapter list for context: {chapter_titles}\n\n"
            f"Requirements: approximately {CHAPTER_WORDS} words, practical and actionable, "
            "concrete examples, conversational expert tone. "
            "Use the 3 section headings as plain-text headings on their own lines. "
            "Do not repeat content from other chapters. Plain text, no markdown symbols."
        ))
        ch_path.write_text(content, encoding="utf-8")
        print(f"  -> saved ({count_words(content)} words)")

    # ---- Step 4: conclusion ----
    concl_path = book_dir / "conclusion.txt"
    if concl_path.exists():
        print("[Conclusion] conclusion.txt exists — skipping (no overwrite).")
    else:
        print("[Conclusion] Writing conclusion...")
        concl = _gemini_call(model, (
            f'Write the conclusion (500-700 words) for "{title}: {subtitle}" ({niche} niche). '
            f"Summary: {outline.get('conclusion_summary', '')}. "
            "Recap the transformation, end with a motivating call to action. "
            "Plain text only, no markdown."
        ))
        concl_path.write_text(concl, encoding="utf-8")

    # ---- Step 5: metadata + queue ----
    total_words = sum(
        count_words(p.read_text(encoding="utf-8"))
        for p in sorted(book_dir.glob("*.txt"))
        if p.name != "outline_raw.txt"
    )
    metadata = {
        "title": title,
        "subtitle": subtitle,
        "author": AUTHOR_NAME,
        "genre": niche,
        "word_count": total_words,
        "status": "written",
        "generated": now_iso(),
        "model": GEMINI_MODEL,
    }
    (book_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    queue = load_queue()
    book = upsert_book(queue, title, niche)
    book["status"] = "written"
    book["word_count"] = total_words
    save_queue(queue)

    print("\n" + "=" * 64)
    print(f"[DONE] '{title}' written — {total_words:,} words -> {book_dir}")
    print(f'Next: python book_pipeline.py package --title "{title}"')
    return 0


# ---------------------------------------------------------------------------
# Command: package
# ---------------------------------------------------------------------------

def cmd_package(args: argparse.Namespace) -> int:
    try:
        from ebooklib import epub
    except ImportError:
        print("[ERROR] ebooklib not installed. Run:")
        print(f'  "{sys.executable}" -m pip install ebooklib')
        return 1

    title: str = args.title
    slug = safe_title(title)
    book_dir = BOOKS_OUTPUT_DIR / slug
    if not book_dir.exists():
        print(f"[ERROR] No generated book at {book_dir} — run generate first.")
        return 1

    meta_path = book_dir / "metadata.json"
    metadata: Dict[str, Any] = (
        json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    )
    subtitle = metadata.get("subtitle", "")
    genre = metadata.get("genre", "")

    print(f"[Package] Building EPUB for '{title}'...")

    def txt_to_html(heading: str, text: str) -> str:
        paragraphs = "".join(
            f"<p>{p.strip()}</p>" for p in text.split("\n\n") if p.strip()
        )
        return f"<h1>{heading}</h1>{paragraphs}"

    book = epub.EpubBook()
    book.set_identifier(f"empireos-{slug}-{uuid.uuid4().hex[:8]}")
    book.set_title(f"{title}: {subtitle}" if subtitle else title)
    book.set_language("en")
    book.add_author(AUTHOR_NAME)
    if genre:
        book.add_metadata("DC", "subject", genre)

    spine: List[Any] = ["nav"]
    toc: List[Any] = []

    sections: List[tuple[str, Path]] = []
    intro = book_dir / "introduction.txt"
    if intro.exists():
        sections.append(("Introduction", intro))
    outline: Dict[str, Any] = {}
    outline_path = book_dir / "outline.json"
    if outline_path.exists():
        outline = json.loads(outline_path.read_text(encoding="utf-8"))
    chapter_titles = {
        int(c.get("number", i + 1)): c.get("title", f"Chapter {i + 1}")
        for i, c in enumerate(outline.get("chapters", []))
    }
    for ch_file in sorted(book_dir.glob("chapter_*.txt")):
        num = int(ch_file.stem.split("_")[1])
        sections.append((chapter_titles.get(num, f"Chapter {num}"), ch_file))
    concl = book_dir / "conclusion.txt"
    if concl.exists():
        sections.append(("Conclusion", concl))

    if not sections:
        print(f"[ERROR] No chapter/intro/conclusion .txt files found in {book_dir}")
        return 1

    for idx, (heading, path) in enumerate(sections, 1):
        item = epub.EpubHtml(
            title=heading, file_name=f"section_{idx:02d}.xhtml", lang="en"
        )
        item.content = txt_to_html(heading, path.read_text(encoding="utf-8"))
        book.add_item(item)
        spine.append(item)
        toc.append(item)
        print(f"  + {heading}")

    book.toc = toc
    book.spine = spine
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    EPUB_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    epub_path = EPUB_OUTPUT_DIR / f"{slug}.epub"
    epub.write_epub(str(epub_path), book)
    size_kb = epub_path.stat().st_size / 1024
    print(f"[OK] EPUB written -> {epub_path} ({size_kb:.0f} KB)")

    queue = load_queue()
    entry = upsert_book(queue, title, genre)
    entry["status"] = "packaged"
    entry["epub_path"] = str(epub_path.relative_to(REPO_ROOT)).replace("\\", "/")
    if metadata.get("word_count"):
        entry["word_count"] = metadata["word_count"]
    save_queue(queue)

    print(f'Next: python book_pipeline.py distribute --title "{title}"')
    return 0


# ---------------------------------------------------------------------------
# Command: distribute
# ---------------------------------------------------------------------------

def cmd_distribute(args: argparse.Namespace) -> int:
    title: str = args.title
    queue = load_queue()
    book = find_book(queue, title)
    if book is None:
        print(f"[ERROR] '{title}' not found in books_queue.json — run generate + package first.")
        return 1
    if book.get("status") not in ("packaged", "distributed"):
        print(f"[ERROR] '{title}' status is '{book.get('status')}' — package it first:")
        print(f'  python book_pipeline.py package --title "{title}"')
        return 1

    epub_path = REPO_ROOT / book.get("epub_path", "")
    if not book.get("epub_path") or not epub_path.exists():
        print(f"[ERROR] EPUB missing at {epub_path} — re-run package.")
        return 1

    env = load_env()
    d2d_key = env.get("D2D_API_KEY", "")
    platforms: List[str] = list(book.get("platforms", []))

    print("=" * 64)
    print(f"DISTRIBUTION — {title}")
    print("=" * 64)
    print(f"EPUB: {epub_path}")

    # ---- Draft2Digital ----
    print("\n--- Draft2Digital (40+ stores: Apple, Kobo, B&N, libraries) ---")
    if d2d_key:
        import requests
        print(f"[D2D] API key found — submitting to {D2D_API_URL} ...")
        try:
            with epub_path.open("rb") as fh:
                resp = requests.post(
                    D2D_API_URL,
                    headers={"Authorization": f"Bearer {d2d_key}"},
                    data={
                        "title": book["title"],
                        "author": AUTHOR_NAME,
                        "genre": book.get("niche", ""),
                    },
                    files={"epub": (epub_path.name, fh, "application/epub+zip")},
                    timeout=120,
                )
            if resp.ok:
                print(f"[D2D] Submitted OK (HTTP {resp.status_code})")
                if "draft2digital" not in platforms:
                    platforms.append("draft2digital")
            else:
                print(f"[D2D] Submission failed: HTTP {resp.status_code} — {resp.text[:300]}")
                print("[D2D] NOTE: endpoint/payload is a v2 stub — verify against the official "
                      "D2D API docs for your account before relying on it.")
        except Exception as exc:  # noqa: BLE001
            print(f"[D2D] Request error: {exc}")
    else:
        print("Add D2D_API_KEY to .env to enable auto-distribution")
        print("Manual upload meanwhile:")
        print("  1. Log in at https://www.draft2digital.com")
        print("  2. My Books -> Add New Book")
        print(f"  3. Upload: {epub_path}")
        print(f"  4. Author: {AUTHOR_NAME} | Genre: {book.get('niche', '')}")
        print("  5. Select all stores, set price, publish")
        print(f"  (API stub ready: POST {D2D_API_URL})")

    # ---- Amazon KDP (always manual — no public upload API) ----
    print("\n--- Amazon KDP (manual — Amazon has no public upload API) ---")
    print(f"  1. Open {KDP_URL}")
    print("  2. Create -> Kindle eBook")
    print(f"  3. Title: {book['title']} | Author: {AUTHOR_NAME}")
    print(f"  4. Upload manuscript: {epub_path}")
    print("  5. Upload/generate a cover, pick categories + 7 keywords")
    print("  6. Price at $2.99-$9.99 for the 70% royalty tier, then Publish")
    if "kdp_manual" not in platforms:
        platforms.append("kdp_manual")

    book["platforms"] = platforms
    book["status"] = "distributed"
    book["distributed_at"] = now_iso()
    save_queue(queue)
    print(f"\n[OK] Distribution record saved -> {QUEUE_PATH.name} (status: distributed)")
    return 0


# ---------------------------------------------------------------------------
# Command: status
# ---------------------------------------------------------------------------

def cmd_status(_args: argparse.Namespace) -> int:
    queue = load_queue()
    books = queue["books"]
    print("=" * 88)
    print("EMPIRE OS BOOK PIPELINE — STATUS")
    print("=" * 88)
    if not books:
        print("Queue is empty. Start with: python book_pipeline.py research")
        return 0

    header = f"{'TITLE':<36} {'NICHE':<18} {'STATUS':<12} {'WORDS':>8}  PLATFORMS"
    print(header)
    print("-" * 88)
    counts = {"written": 0, "packaged": 0, "distributed": 0}
    for b in books:
        status = b.get("status", "?")
        if status in counts:
            counts[status] += 1
        platforms = ", ".join(b.get("platforms", [])) or "-"
        print(f"{b.get('title', '?')[:35]:<36} {b.get('niche', '-')[:17]:<18} "
              f"{status:<12} {b.get('word_count', 0):>8,}  {platforms}")
    print("-" * 88)
    print(f"Totals: {counts['written']} written | {counts['packaged']} packaged | "
          f"{counts['distributed']} distributed | {len(books)} total")
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="book_pipeline.py",
        description="Empire OS AI book publishing pipeline (research -> generate -> package -> distribute)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("research", help="Scan 8 niches via Google Books API for topic gaps")

    p_gen = sub.add_parser("generate", help="Write a full book with Gemini")
    p_gen.add_argument("--niche", required=True, help='e.g. "personal finance"')
    p_gen.add_argument("--title", required=True, help='e.g. "The 30-Day Money Reset"')

    p_pkg = sub.add_parser("package", help="Build an EPUB from generated chapters")
    p_pkg.add_argument("--title", required=True)

    p_dist = sub.add_parser("distribute", help="Submit to Draft2Digital / print KDP steps")
    p_dist.add_argument("--title", required=True)

    sub.add_parser("status", help="Show the pipeline queue table")

    args = parser.parse_args(argv)
    handlers = {
        "research": cmd_research,
        "generate": cmd_generate,
        "package": cmd_package,
        "distribute": cmd_distribute,
        "status": cmd_status,
    }
    try:
        return handlers[args.command](args)
    except KeyboardInterrupt:
        print("\n[ABORTED] Interrupted by user — progress files already written are kept.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
