"""
storyforge2/books/factory.py — main Book Factory orchestrator.

Coordinates all stages: trend scanning → brief generation → manuscript →
cover → metadata → publishing. Runs 24/7 autonomously via a scheduler or
event loop.

The BookFactory operates in DRY_RUN mode by default (nothing publishes
without explicit approval). A full cycle takes ~30-60 minutes per book,
with the longest step being manuscript generation (Claude API).

State is tracked in books/factory_state.db (SQLite) for resumability.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from datetime import datetime
import sqlite3
from dataclasses import dataclass

from storyforge2.brief import ProjectBrief
from storyforge2.books.trends import TrendScanner, TrendOpportunity
from storyforge2.books.metadata import MetadataBuilder, BookMetadata

__all__ = ["BookFactory", "BookFactoryError"]


class BookFactoryError(RuntimeError):
    pass


class MockPipelineError(RuntimeError):
    """Simplified error for mock pipeline."""
    pass


@dataclass
class BookCycle:
    """A single book generation cycle: opportunity → published book."""

    cycle_id: str  # unique identifier
    opportunity: TrendOpportunity
    brief: Optional[ProjectBrief] = None
    metadata: Optional[BookMetadata] = None
    work_dir: Optional[Path] = None
    status: str = "initialized"  # initialized → manuscript → cover → metadata → publish
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    def is_complete(self) -> bool:
        return self.status == "published"

    def is_failed(self) -> bool:
        return self.status == "failed"


class BookFactory:
    """24/7 autonomous book generation factory.

    Context manager to ensure DB connections are cleaned up properly.
    Use: with BookFactory() as factory: factory.run_cycle()

    Operates in a loop:
    1. Scan for a new trend opportunity (every 4 hours)
    2. Convert opportunity to ProjectBrief
    3. Run manuscript generation pipeline (DRY_RUN by default)
    4. Generate cover
    5. Build metadata
    6. Queue for publishing (manual approval in MVP)

    All state is persisted to disk for resumability.
    """

    def __init__(self, work_base: Path | str = "books"):
        self.work_base = Path(work_base)
        self.work_base.mkdir(parents=True, exist_ok=True)

        self.trend_scanner = TrendScanner(state_db=self.work_base / "trends_state.json")
        self.state_db = self.work_base / "factory_state.db"
        self._open_connections = []
        self._init_db()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cleanup()
        return False

    def _cleanup(self):
        """Close any open database connections."""
        for conn in self._open_connections:
            try:
                conn.close()
            except Exception:
                pass
        self._open_connections.clear()

    def _init_db(self):
        """Initialize SQLite ledger for cycle tracking."""
        conn = sqlite3.connect(self.state_db)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cycles (
                    cycle_id TEXT PRIMARY KEY,
                    opportunity_niche TEXT,
                    title TEXT,
                    status TEXT,
                    work_dir TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    error TEXT
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def run_cycle(self, dry_run: bool = True) -> Optional[BookCycle]:
        """Execute one full book generation cycle.

        Returns:
            BookCycle if a book was generated, None if no opportunity was due.
        """
        print(f"\n[BOOK FACTORY] Running cycle (dry_run={dry_run})")

        # 1. Scan for opportunity
        opportunity = self.trend_scanner.scan(dry_run=dry_run)
        if not opportunity:
            print("[BOOK FACTORY] No opportunity due yet. Skipping cycle.")
            return None

        print(f"[BOOK FACTORY] Opportunity: {opportunity.title}")
        print(f"[BOOK FACTORY] Niche: {opportunity.niche}")
        print(f"[BOOK FACTORY] Pitch: {opportunity.premise}")

        # Create a cycle
        cycle = BookCycle(
            cycle_id=opportunity.scan_id,
            opportunity=opportunity,
            work_dir=self.work_base / opportunity.scan_id,
            started_at=datetime.utcnow(),
        )

        # 2. Convert opportunity to ProjectBrief
        try:
            cycle.brief = self._opportunity_to_brief(opportunity)
            print(f"[BOOK FACTORY] Brief ready: {cycle.brief.title}")
        except Exception as e:
            cycle.status = "failed"
            cycle.error = f"Brief generation failed: {e}"
            print(f"[BOOK FACTORY] ✗ {cycle.error}")
            self._save_cycle(cycle)
            return cycle

        # 3. Run manuscript generation pipeline (mock for MVP)
        try:
            cycle.work_dir.mkdir(parents=True, exist_ok=True)

            # Mock pipeline: create placeholder manuscript files
            # In production, this would call BookPipeline.run()
            manuscript_path = cycle.work_dir / "manuscript.txt"
            manuscript_path.write_text(
                f"# {cycle.brief.title}\n\n"
                f"## Premise\n{cycle.brief.premise}\n\n"
                f"## Audience\n{cycle.brief.audience}\n\n"
                f"(Mock manuscript - {len(cycle.brief.premise)} words)\n"
            )

            if not manuscript_path.exists():
                raise MockPipelineError("Manuscript file not created")

            cycle.status = "manuscript"
            print(f"[BOOK FACTORY] ✓ Manuscript generated (mock)")
        except Exception as e:
            cycle.status = "failed"
            cycle.error = f"Manuscript generation failed: {e}"
            print(f"[BOOK FACTORY] ✗ {cycle.error}")
            self._save_cycle(cycle)
            return cycle

        # 4. Build metadata
        try:
            cycle.metadata = MetadataBuilder.build(
                title=cycle.brief.title,
                niche=opportunity.niche,
                keywords=opportunity.keywords,
                base_description=cycle.brief.premise,
                author=cycle.brief.author_name,
            )
            print(f"[BOOK FACTORY] ✓ Metadata built: ISBN {cycle.metadata.isbn}")
            cycle.status = "metadata"
        except Exception as e:
            cycle.status = "failed"
            cycle.error = f"Metadata generation failed: {e}"
            print(f"[BOOK FACTORY] ✗ {cycle.error}")
            self._save_cycle(cycle)
            return cycle

        # 5. Mark as ready for publishing
        cycle.status = "ready_publish"
        cycle.completed_at = datetime.utcnow()
        print(f"[BOOK FACTORY] ✓ Book ready for publishing")
        self._save_cycle(cycle)

        return cycle

    def _opportunity_to_brief(self, opportunity: TrendOpportunity) -> ProjectBrief:
        """Convert TrendOpportunity to ProjectBrief for the pipeline."""
        return ProjectBrief(
            title=opportunity.title,
            premise=opportunity.premise,
            audience=opportunity.target_audience,
            genre="non-fiction",
            author_name="Empire OS Publishing",
            length_chapters=12,  # 20k-40k words in 12 chapters
            platform_targets=["draft2digital", "gumroad"],  # will add more later
            marketing_platforms=[],
        )

    def _save_cycle(self, cycle: BookCycle):
        """Persist cycle to SQLite ledger."""
        conn = sqlite3.connect(self.state_db)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO cycles
                (cycle_id, opportunity_niche, title, status, work_dir, started_at, completed_at, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cycle.cycle_id,
                cycle.opportunity.niche,
                cycle.opportunity.title,
                cycle.status,
                str(cycle.work_dir) if cycle.work_dir else None,
                cycle.started_at.isoformat() if cycle.started_at else None,
                cycle.completed_at.isoformat() if cycle.completed_at else None,
                cycle.error,
            ))
            conn.commit()
        finally:
            conn.close()

    def get_ready_to_publish(self) -> list[BookCycle]:
        """Get all books ready to be published."""
        cycles = []
        conn = sqlite3.connect(self.state_db)
        try:
            rows = conn.execute(
                "SELECT cycle_id FROM cycles WHERE status = 'ready_publish' ORDER BY started_at DESC LIMIT 10"
            ).fetchall()
            for (cycle_id,) in rows:
                # Reconstruct from disk (simplified for MVP)
                cycles.append(BookCycle(
                    cycle_id=cycle_id,
                    opportunity=TrendOpportunity(
                        niche="unknown",
                        title="Reconstructed Book",
                        premise="",
                        keywords=[],
                        target_audience="",
                        estimated_audience_size="medium",
                    ),
                    status="ready_publish",
                ))
        finally:
            conn.close()
        return cycles

    def status_report(self) -> dict:
        """Generate a status report of the factory."""
        conn = sqlite3.connect(self.state_db)
        try:
            total = conn.execute("SELECT COUNT(*) FROM cycles").fetchone()[0]
            complete = conn.execute("SELECT COUNT(*) FROM cycles WHERE status = 'published'").fetchone()[0]
            ready = conn.execute("SELECT COUNT(*) FROM cycles WHERE status = 'ready_publish'").fetchone()[0]
            failed = conn.execute("SELECT COUNT(*) FROM cycles WHERE status = 'failed'").fetchone()[0]
        finally:
            conn.close()

        from storyforge2.books.trends import EVERGREEN_NICHES
        return {
            "total_cycles": total,
            "published": complete,
            "ready_publish": ready,
            "failed": failed,
            "trend_scanner_state": {
                "last_scan": self.trend_scanner.last_scan.isoformat() if self.trend_scanner.last_scan else None,
                "last_niche": list(EVERGREEN_NICHES.keys())[self.trend_scanner.last_niche_index] if self.trend_scanner.last_niche_index >= 0 else None,
            },
        }


# Placeholder for testing
if __name__ == "__main__":
    factory = BookFactory()
    cycle = factory.run_cycle(dry_run=True)
    if cycle:
        print(f"\n✓ Generated cycle: {cycle.cycle_id}")
        print(f"  Status: {cycle.status}")
        if cycle.metadata:
            print(f"  ISBN: {cycle.metadata.isbn}")
    print(f"\nFactory status: {json.dumps(factory.status_report(), indent=2)}")
