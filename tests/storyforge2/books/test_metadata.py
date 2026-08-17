"""Tests for storyforge2.books.metadata — book metadata generation."""

import pytest
from datetime import datetime

from storyforge2.books.metadata import (
    BookMetadata, ISBNGenerator, MetadataBuilder
)


class TestISBNGenerator:
    """Test ISBN generation."""

    def test_generate_format(self):
        """ISBN should be in 978-1-{8hex}-{digit} format."""
        isbn = ISBNGenerator.generate("Test Title", "personal-finance")
        assert isbn.startswith("978-1-")
        parts = isbn.split("-")
        assert len(parts) == 4
        assert len(parts[2]) == 8  # hash part
        assert parts[3].isdigit() and len(parts[3]) == 1  # check digit

    def test_generate_deterministic(self):
        """Same title + niche should produce same ISBN."""
        isbn1 = ISBNGenerator.generate("Book Title", "ai-for-business")
        isbn2 = ISBNGenerator.generate("Book Title", "ai-for-business")
        assert isbn1 == isbn2

    def test_generate_different_niche(self):
        """Different niche should produce different ISBN."""
        isbn1 = ISBNGenerator.generate("Book Title", "ai-for-business")
        isbn2 = ISBNGenerator.generate("Book Title", "personal-finance")
        assert isbn1 != isbn2

    def test_validate_placeholder(self):
        """Valid ISBNs should pass validation."""
        isbn = ISBNGenerator.generate("Test", "health-wellness")
        assert ISBNGenerator.validate_placeholder(isbn)

    def test_validate_invalid(self):
        """Invalid ISBNs should fail validation."""
        assert not ISBNGenerator.validate_placeholder("123-456-789")
        assert not ISBNGenerator.validate_placeholder("978-2-12345678-1")  # wrong prefix


class TestBookMetadata:
    """Test BookMetadata data class."""

    def test_creation(self):
        meta = BookMetadata(
            isbn="978-1-12345678-1",
            title="Test Book",
            description="A test description",
            keywords=["test", "book"],
            niche="personal-finance",
        )
        assert meta.isbn == "978-1-12345678-1"
        assert meta.title == "Test Book"
        assert meta.base_price == 9.99

    def test_to_dict(self):
        meta = BookMetadata(
            isbn="978-1-12345678-1",
            title="Test Book",
            niche="productivity-systems",
        )
        data = meta.to_dict()
        assert data["isbn"] == "978-1-12345678-1"
        assert isinstance(data["generated_at"], str)

    def test_json_roundtrip(self):
        meta = BookMetadata(
            isbn="978-1-87654321-5",
            title="JSON Test",
            keywords=["json", "test"],
            niche="ai-for-business",
        )
        json_str = meta.to_json()
        reconstructed = BookMetadata.from_json(json_str)
        assert reconstructed.isbn == meta.isbn
        assert reconstructed.title == meta.title


class TestMetadataBuilder:
    """Test MetadataBuilder."""

    def test_build_complete_metadata(self):
        """Build should produce valid, complete metadata."""
        metadata = MetadataBuilder.build(
            title="AI for Freelancers",
            niche="ai-for-business",
            keywords=["ChatGPT", "automation", "productivity"],
            base_description="Learn to use AI to 10x your freelance business.",
        )

        assert metadata.title == "AI for Freelancers"
        assert metadata.niche == "ai-for-business"
        assert len(metadata.keywords) == 3
        assert len(metadata.categories) > 0
        assert metadata.isbn
        assert ISBNGenerator.validate_placeholder(metadata.isbn)

    def test_niche_pricing(self):
        """Different niches should have appropriate pricing."""
        meta_tech = MetadataBuilder.build(
            title="Technical Writing Guide",
            niche="technical-writing",
            keywords=["writing"],
        )
        assert meta_tech.base_price == 14.99

        meta_ml = MetadataBuilder.build(
            title="ML Fundamentals",
            niche="machine-learning",
            keywords=["AI"],
        )
        assert meta_ml.base_price == 19.99

        meta_finance = MetadataBuilder.build(
            title="Personal Finance",
            niche="personal-finance",
            keywords=["money"],
        )
        assert meta_finance.base_price == 9.99

    def test_category_assignment(self):
        """Correct BISAC categories should be assigned per niche."""
        meta = MetadataBuilder.build(
            title="Productivity Mastery",
            niche="productivity-systems",
            keywords=["time management"],
        )
        assert "SELF-HELP" in " ".join(meta.categories)

    def test_keyword_extraction_empty(self):
        """MVP keyword extraction returns empty (placeholder)."""
        keywords = MetadataBuilder.extract_keywords_from_content("Some sample text here.")
        assert keywords == []  # MVP returns empty; future: implement NLP


class TestMetadataIntegration:
    """Integration tests for metadata."""

    def test_full_metadata_build_from_opportunity(self):
        """Test building metadata from a TrendOpportunity."""
        from storyforge2.books.trends import TrendOpportunity

        opp = TrendOpportunity(
            niche="health-wellness",
            title="Sleep Optimization Guide",
            premise="Master your sleep for peak performance.",
            keywords=["sleep", "health", "performance"],
            target_audience="health-conscious professionals",
            estimated_audience_size="large",
        )

        # Build metadata from opportunity
        metadata = MetadataBuilder.build(
            title=opp.title,
            niche=opp.niche,
            keywords=opp.keywords,
            base_description=opp.premise,
        )

        assert metadata.niche == opp.niche
        assert metadata.title == opp.title
        assert set(metadata.keywords) == set(opp.keywords)
        assert metadata.isbn.startswith("978-1-")
