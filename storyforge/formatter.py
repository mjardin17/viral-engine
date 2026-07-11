"""
storyforge/formatter.py — Empire OS Book Formatter
Converts manuscript → EPUB + PDF ready for Amazon KDP and Draft2Digital.

Usage:
    python storyforge/formatter.py --slug lost_battles_of_wwii
    python storyforge/formatter.py --all   # formats all books in books/
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

BOOKS_DIR = Path(__file__).parent / "books"


def make_epub(manifest: dict, book_dir: Path) -> Path:
    """Generate KDP-ready EPUB from manifest."""
    try:
        from ebooklib import epub
    except ImportError:
        print("  [FORMAT] ebooklib not installed — run: pip install ebooklib --break-system-packages")
        return Path()

    book = epub.EpubBook()
    book.set_identifier(manifest["slug"])
    book.set_title(manifest["title"])
    book.set_language("en")
    book.add_author("Empire OS Publishing")

    # Cover
    cover_path = Path(manifest.get("cover", ""))
    if cover_path.exists():
        book.set_cover("cover.png", cover_path.read_bytes())

    # Style
    style = epub.EpubItem(
        uid="style", file_name="style.css", media_type="text/css",
        content=b"""
body { font-family: Georgia, serif; font-size: 1em; line-height: 1.6; margin: 5% 8%; }
h1 { font-size: 2em; text-align: center; margin-bottom: 0.5em; }
h2 { font-size: 1.4em; margin-top: 2em; }
p  { margin: 0.8em 0; text-indent: 1.5em; }
""")
    book.add_item(style)

    chapters_epub: list = []
    manuscript_path = Path(manifest.get("manuscript", ""))
    if not manuscript_path.exists():
        print(f"  [FORMAT] Manuscript not found: {manuscript_path}")
        return Path()

    raw = manuscript_path.read_text(encoding="utf-8")
    # Split by chapter headings
    parts = raw.split("\n\n## ")

    for i, part in enumerate(parts[1:], 1):  # skip title block
        lines = part.split("\n", 1)
        ch_title = lines[0].strip()
        ch_body  = lines[1].strip() if len(lines) > 1 else ""

        # Convert plain text to basic HTML
        paragraphs = "".join(
            f"<p>{para.strip()}</p>\n"
            for para in ch_body.split("\n\n") if para.strip()
        )
        html = f"<h2>{ch_title}</h2>\n{paragraphs}"

        ch = epub.EpubHtml(title=ch_title, file_name=f"chap_{i:02d}.xhtml", lang="en")
        ch.set_content(f"<html><body>{html}</body></html>")
        ch.add_item(style)
        book.add_item(ch)
        chapters_epub.append(ch)

    book.toc    = tuple(chapters_epub)
    book.spine  = ["nav"] + chapters_epub
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    out_path = book_dir / f"{manifest['slug']}.epub"
    epub.write_epub(str(out_path), book)
    print(f"  [FORMAT] EPUB saved: {out_path.name} ({out_path.stat().st_size // 1024}KB)")
    return out_path


def make_pdf(manifest: dict, book_dir: Path) -> Path:
    """Generate KDP-ready PDF (6x9 inch) from manuscript."""
    try:
        from reportlab.lib.pagesizes import inch
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, PageBreak
        )
        from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    except ImportError:
        print("  [FORMAT] reportlab not installed — run: pip install reportlab --break-system-packages")
        return Path()

    out_path  = book_dir / f"{manifest['slug']}.pdf"
    page_size = (6 * inch, 9 * inch)
    margin    = 0.75 * inch

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=page_size,
        leftMargin=margin, rightMargin=margin,
        topMargin=margin, bottomMargin=margin,
    )

    styles   = getSampleStyleSheet()
    title_s  = ParagraphStyle("title",  parent=styles["Title"],  fontSize=22, spaceAfter=12, alignment=TA_CENTER)
    sub_s    = ParagraphStyle("sub",    parent=styles["Normal"], fontSize=13, spaceAfter=20, alignment=TA_CENTER, textColor="#555555")
    h2_s     = ParagraphStyle("h2",     parent=styles["Heading2"], fontSize=14, spaceBefore=20, spaceAfter=8)
    body_s   = ParagraphStyle("body",   parent=styles["Normal"], fontSize=11, leading=16, alignment=TA_JUSTIFY, firstLineIndent=18)

    story = [
        Paragraph(manifest["title"],    title_s),
        Paragraph(manifest.get("subtitle", ""), sub_s),
        PageBreak(),
    ]

    manuscript_path = Path(manifest.get("manuscript", ""))
    if manuscript_path.exists():
        raw   = manuscript_path.read_text(encoding="utf-8")
        parts = raw.split("\n\n## ")

        for part in parts[1:]:
            lines    = part.split("\n", 1)
            ch_title = lines[0].strip()
            ch_body  = lines[1].strip() if len(lines) > 1 else ""

            story.append(Paragraph(ch_title, h2_s))
            for para in ch_body.split("\n\n"):
                para = para.strip()
                if not para:
                    continue
                # Strip markdown subheadings
                if para.startswith("###"):
                    story.append(Paragraph(para.lstrip("# "), h2_s))
                else:
                    story.append(Paragraph(para, body_s))
            story.append(PageBreak())

    doc.build(story)
    print(f"  [FORMAT] PDF  saved: {out_path.name} ({out_path.stat().st_size // 1024}KB)")
    return out_path


def format_book(slug: str) -> dict[str, Path]:
    book_dir = BOOKS_DIR / slug
    manifest_path = book_dir / "manifest.json"

    if not manifest_path.exists():
        raise FileNotFoundError(f"No manifest for slug '{slug}' — run generator.py first")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    print(f"\n[FORMAT] Formatting: {manifest['title']}")

    epub_path = make_epub(manifest, book_dir)
    pdf_path  = make_pdf(manifest, book_dir)

    # Update manifest with output paths
    manifest["epub"] = str(epub_path) if epub_path.exists() else ""
    manifest["pdf"]  = str(pdf_path)  if pdf_path.exists()  else ""
    manifest["status"] = "formatted"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"[FORMAT] Done — {slug}")
    return {"epub": epub_path, "pdf": pdf_path}


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--slug", default="")
    p.add_argument("--all",  action="store_true")
    args = p.parse_args()

    if args.all:
        for d in BOOKS_DIR.iterdir():
            if d.is_dir() and (d / "manifest.json").exists():
                m = json.loads((d / "manifest.json").read_text())
                if m.get("status") == "generated":
                    format_book(d.name)
    elif args.slug:
        format_book(args.slug)
    else:
        print("Provide --slug <slug> or --all")
