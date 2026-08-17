"""Tests for storyforge2.books.trends — trend discovery."""

import pytest
from datetime import datetime
from pathlib import Path
import json
import tempfile

from storyforge2.books.trends import (
    TrendOpportunity, TrendScanner, EVERGREEN_NICHES
)


class TestTrendOpportunity:
    """Test TrendOpportunity data class."""

    def test_creation(self):
        opp = TrendOpportunity(
            niche="personal-finance",
            title="Test Book",
            premise="A guide to saving money",
            keywords=["budgeting", "investing"],
            target_audience="professionals",
            estimated_audience_size="large",
        )
        assert opp.niche == "personal-finance"
        assert opp.title == "Test Book"
        assert opp.estimated_audience_size == "large"

    def test_to_dict(self):
        opp = TrendOpportunity(
            niche="ai-for-business",
            title="AI Book",
            premise="A practical guide",
            keywords=["ChatGPT"],
            target_audience="SMBs",
            estimated_audience_size="medium",
        )
        data = opp.to_dict()
        assert data["niche"] == "ai-for-business"
        assert isinstance(data["generated_at"], str)

    def test_from_dict(self):
        data = {
            "niche": "productivity-systems",
            "title": "Focus Book",
            "premise": "Deep work guide",
            "keywords": ["focus"],
            "target_audience": "workers",
            "estimated_audience_size": "large",
            "generated_at": "2026-08-17T10:00:00",
            "scan_id": "abc123",
        }
        opp = TrendOpportunity.from_dict(data)
        assert opp.niche == "productivity-systems"
        assert opp.title == "Focus Book"


class TestTrendScanner:
    """Test TrendScanner."""

    def test_creation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "trends.json"
            scanner = TrendScanner(state_db=db_path)
            assert scanner.state_db == db_path
            assert scanner.last_niche_index == -1

    def test_scan_round_robin(self):
        """Test that scan() rotates through niches."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "trends.json"
            scanner = TrendScanner(state_db=db_path)

            niche_keys = list(EVERGREEN_NICHES.keys())

            # First scan should pick index 0
            opp1 = scanner.scan(dry_run=True)
            assert opp1 is not None
            assert opp1.niche == niche_keys[0]

            # Dry-run shouldn't update state
            assert scanner.last_niche_index == -1

            # Non-dry-run should update state
            opp2 = scanner.scan(dry_run=False)
            assert opp2 is not None
            assert opp2.niche == niche_keys[0]
            assert scanner.last_niche_index == 0

            # Next scan should pick index 1
            opp3 = scanner.scan(dry_run=False)
            assert opp3.niche == niche_keys[1]
            assert scanner.last_niche_index == 1

    def test_state_persistence(self):
        """Test that scan state persists to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "trends.json"

            scanner1 = TrendScanner(state_db=db_path)
            opp = scanner1.scan(dry_run=False)
            assert scanner1.last_niche_index == 0

            # Create new scanner, should load persisted state
            scanner2 = TrendScanner(state_db=db_path)
            assert scanner2.last_niche_index == 0
            assert scanner2.scan_history[-1] == f"{opp.niche}:{opp.scan_id}"

    def test_niche_for_date(self):
        """Test deterministic niche selection by date."""
        scanner = TrendScanner()
        date1 = datetime(2026, 1, 1)
        date2 = datetime(2026, 1, 2)

        niche1 = scanner.get_niche_for_date(date1)
        niche2 = scanner.get_niche_for_date(date2)

        # Different days should produce (likely) different niches
        # Same date should always produce same niche
        niche1_again = scanner.get_niche_for_date(date1)
        assert niche1 == niche1_again

    def test_evergreen_niches_complete(self):
        """Verify all evergreen niches have required fields."""
        for niche_key, spec in EVERGREEN_NICHES.items():
            assert "name" in spec
            assert "keywords" in spec
            assert len(spec["keywords"]) >= 3
            assert "audience" in spec
            assert "pitch_template" in spec
            assert "avg_audience_size" in spec
            assert spec["avg_audience_size"] in ["small", "medium", "large"]


class TestTrendIntegration:
    """Integration tests for trend scanning."""

    def test_full_scan_cycle(self):
        """Test a complete scan-to-opportunity cycle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "trends.json"
            scanner = TrendScanner(state_db=db_path)

            # Scan produces an opportunity
            opp = scanner.scan(dry_run=False)
            assert opp is not None
            assert opp.niche in EVERGREEN_NICHES
            assert opp.title
            assert opp.premise
            assert opp.keywords
            assert opp.target_audience
            assert opp.estimated_audience_size

            # Opportunity is JSON-serializable
            data = opp.to_dict()
            json_str = json.dumps(data, default=str)
            assert json_str
            reconstructed = TrendOpportunity.from_dict(json.loads(json_str))
            assert reconstructed.niche == opp.niche
