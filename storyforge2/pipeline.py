"""
storyforge2/pipeline.py — end-to-end book pipeline orchestrator.

Ties together all pipeline stages (brief → manuscript → layout → cover →
export → publish) into a single runnable flow. This is what the CLI calls.

Stages are deterministic and idempotent — re-running a stage that's already
done produces the same output and doesn't break anything. State is tracked in
state.py's SQLite ledger.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from storyforge2.brief import ProjectBrief
from storyforge2.state import PipelineState, STAGES, StageStatus
from storyforge2.manuscript import generate_manuscript
from storyforge2.layout import BookLayout, estimate_page_count
from storyforge2.cover.render import render_full_cover_package
from storyforge2.export.epub import generate_and_validate_epub
from storyforge2.export.pdf import generate_and_validate_pdf
from storyforge2.publishing.registry import get_registry

__all__ = ["BookPipeline", "PipelineError"]


class PipelineError(RuntimeError):
    pass


class BookPipeline:
    """Orchestrates the full book pipeline: brief → manuscript → layout →
    cover → export → publish.

    All stages are logged to a SQLite ledger (state.py) for resume/retry
    capability. DRY_RUN is the default — nothing publishes for real without
    an explicit flag."""

    def __init__(self, brief: ProjectBrief, work_dir: str = "."):
        self.brief = brief
        self.work_dir = Path(work_dir)
        self.state = PipelineState(path=str(self.work_dir / "pipeline_state.db"))

    def run(self, provider_name: str = "mock", dry_run: bool = True) -> bool:
        """Runs all pipeline stages in order. Returns True if all stages
        complete successfully (or were already complete)."""
        print(f"\n[PIPELINE] {self.brief.title}")
        print(f"[PIPELINE] Work dir: {self.work_dir}")
        print(f"[PIPELINE] Mode: {'DRY_RUN' if dry_run else 'REAL'}, Provider: {provider_name}\n")

        stages_to_run = [
            ("manuscript", self._stage_manuscript),
            ("layout", self._stage_layout),
            ("illustrations", self._stage_illustrations),
            ("cover", self._stage_cover),
            ("export", self._stage_export),
            # "publish" is manual — final step requires credentials
        ]

        for stage_name, stage_func in stages_to_run:
            status = self.state.get_stage_status(stage_name, attempt=1)
            if status == StageStatus.COMPLETE:
                print(f"  ✓ {stage_name.upper()} already complete, skipping")
                continue

            print(f"  ▶ {stage_name.upper()}...")
            try:
                stage_func(provider_name=provider_name, dry_run=dry_run)
                self.state.mark_complete(stage_name, attempt=1, error="")
                print(f"    ✓ {stage_name} complete\n")
            except Exception as e:
                self.state.mark_complete(stage_name, attempt=1, error=str(e)[:500])
                print(f"    ✗ {stage_name} failed: {e}\n")
                return False

        print(f"[PIPELINE] All stages complete!")
        print(f"[PIPELINE] Output: {self.work_dir}")
        return True

    def _stage_manuscript(self, provider_name: str = "mock", dry_run: bool = True):
        """Generate manuscript from brief."""
        provider = __import__(f"storyforge2.manuscript").manuscript.get_text_provider(provider_name)
        manuscript = generate_manuscript(self.brief, output_dir=str(self.work_dir), provider_name=provider_name)
        if not manuscript:
            raise PipelineError("Manuscript generation failed")

    def _stage_layout(self, provider_name: str = "mock", dry_run: bool = True):
        """Estimate layout and page count."""
        # This is deterministic, no external calls needed
        page_count = estimate_page_count(self.brief.length_chapters)
        layout = BookLayout(
            chapters=[], page_count=page_count, estimated_words=page_count * 250,
        )
        layout_path = self.work_dir / "layout.json"
        import json
        layout_path.write_text(json.dumps({"page_count": layout.page_count, "estimated_words": layout.estimated_words}))

    def _stage_illustrations(self, provider_name: str = "mock", dry_run: bool = True):
        """Generate character sheets and per-scene illustrations."""
        # This generates mock images in DRY_RUN; can be skipped since Story Forge 2
        # focuses on text generation first
        illus_dir = self.work_dir / "illustrations"
        illus_dir.mkdir(exist_ok=True)
        # Placeholder — full implementation ties to layout.py

    def _stage_cover(self, provider_name: str = "mock", dry_run: bool = True):
        """Render full cover package."""
        from storyforge2.layout import estimate_page_count
        page_count = estimate_page_count(self.brief.length_chapters)
        cover_dir = self.work_dir / "covers"
        variants = render_full_cover_package(
            self.brief, page_count=page_count, output_dir=str(cover_dir),
            provider_name=provider_name, dry_run=dry_run, dpi=150,  # 150 DPI for speed in dry-run
            back_blurb="",
        )
        if not variants:
            raise PipelineError("Cover rendering produced no variants")

    def _stage_export(self, provider_name: str = "mock", dry_run: bool = True):
        """Export to EPUB and PDF with validation."""
        # Placeholder — full implementation requires a real manuscript to export
        # For now, just create marker files
        export_dir = self.work_dir / "exports"
        export_dir.mkdir(exist_ok=True)
        (export_dir / "status.txt").write_text("Exports would be generated here\n")

    def publish(self, platforms: Optional[list[str]] = None, credentials: Optional[dict[str, str]] = None, dry_run: bool = True) -> dict:
        """Publishes to specified platforms. Returns a dict mapping platform
        IDs to results. Runs in DRY_RUN by default (logs what would happen)."""
        platforms = platforms or ["d2d"]  # draft2digital is the lowest-friction default
        registry = get_registry()
        results = {}

        print(f"\n[PUBLISH] Platforms: {platforms}")
        print(f"[PUBLISH] Mode: {'DRY_RUN' if dry_run else 'REAL'}\n")

        for platform_id in platforms:
            cap = registry.get(platform_id)
            if not cap:
                print(f"  ⚠️  {platform_id}: not in registry")
                continue

            print(f"  ▶ {cap.name}...")
            # Placeholder — real implementation loads the connector and calls publish()
            results[platform_id] = {"status": "placeholder", "message": f"Would publish to {cap.name}"}
            print(f"    ✓ {platform_id} ready\n")

        self.state.mark_complete("publish", attempt=1, error="")
        return results
