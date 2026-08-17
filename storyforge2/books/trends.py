"""
storyforge2/books/trends.py — trend discovery and opportunity generation.

Scans for book market opportunities. MVP uses a curated list of evergreen niches;
production can integrate Google Trends, Amazon bestseller lists, Reddit/Twitter
social signals, etc.

A TrendOpportunity is a potential book idea with:
- niche: e.g. "personal-finance" or "ai-productivity"
- keywords: 3-5 search terms for the book
- target_audience: e.g. "busy professionals" or "indie hackers"
- pitch: one-sentence premise
- estimated_audience_size: rough market size (small/medium/large)

Rules:
- Pick ONE niche per scan (24-hour rotation across niches)
- Evergreen niches only (no trend-of-the-week, no time-bound topics)
- Each scan produces AT MOST one opportunity (avoid spam)
- Dry-run mode returns a TrendOpportunity without any state changes
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Optional, Any
import json
from pathlib import Path
import hashlib

__all__ = ["TrendOpportunity", "TrendScanner"]

# Evergreen niches with consistent demand, repeated yearly
EVERGREEN_NICHES = {
    "personal-finance": {
        "name": "Personal Finance",
        "keywords": ["financial independence", "budgeting", "investing basics"],
        "audience": "working professionals aged 25-45",
        "pitch_template": "A practical guide to building wealth on a {profession} salary",
        "avg_audience_size": "large",
    },
    "productivity-systems": {
        "name": "Productivity Systems",
        "keywords": ["time management", "focus", "deep work"],
        "audience": "knowledge workers, creators, entrepreneurs",
        "pitch_template": "How to implement {system} for {context}",
        "avg_audience_size": "large",
    },
    "ai-for-business": {
        "name": "AI for Business",
        "keywords": ["ChatGPT", "automation", "AI workflows"],
        "audience": "small business owners, freelancers, SMBs",
        "pitch_template": "{AI tool} for {business_type}: a practical handbook",
        "avg_audience_size": "medium",
    },
    "health-wellness": {
        "name": "Health & Wellness",
        "keywords": ["sleep optimization", "nutrition", "fitness"],
        "audience": "health-conscious adults",
        "pitch_template": "The science-backed guide to {health_topic}",
        "avg_audience_size": "large",
    },
    "remote-work": {
        "name": "Remote Work",
        "keywords": ["work from home", "async teams", "digital nomad"],
        "audience": "remote workers and distributed teams",
        "pitch_template": "Building a {work_aspect} strategy for remote teams",
        "avg_audience_size": "medium",
    },
    "side-hustle": {
        "name": "Side Hustles",
        "keywords": ["passive income", "freelancing", "micro-businesses"],
        "audience": "part-time entrepreneurs",
        "pitch_template": "Starting your {business_type} side hustle: a 90-day plan",
        "avg_audience_size": "large",
    },
    "technical-writing": {
        "name": "Technical Writing",
        "keywords": ["documentation", "API docs", "technical communication"],
        "audience": "developers, technical writers, product managers",
        "pitch_template": "Making {technology} understandable: a technical writing guide",
        "avg_audience_size": "small",
    },
    "machine-learning": {
        "name": "Machine Learning Basics",
        "keywords": ["neural networks", "ML workflow", "model training"],
        "audience": "aspiring ML engineers, data scientists",
        "pitch_template": "From zero to ML: a practical introduction for {background}",
        "avg_audience_size": "medium",
    },
}


@dataclass
class TrendOpportunity:
    """A potential book market opportunity."""

    niche: str  # key from EVERGREEN_NICHES
    title: str  # generated title
    premise: str  # one-sentence pitch
    keywords: list[str]  # 3-5 search terms
    target_audience: str  # description of ideal reader
    estimated_audience_size: str  # small/medium/large

    # Metadata
    generated_at: datetime = field(default_factory=datetime.utcnow)
    scan_id: str = ""  # unique ID for this scan session

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["generated_at"] = self.generated_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TrendOpportunity:
        """Reconstruct from JSON."""
        if isinstance(data.get("generated_at"), str):
            data["generated_at"] = datetime.fromisoformat(data["generated_at"])
        return cls(**data)


class TrendScanner:
    """Discovers book market opportunities.

    MVP uses a round-robin schedule across evergreen niches. Each niche is
    visited every N days (where N = number of niches). This ensures stable
    content generation without redundant topics.

    Future: integrate Google Trends, Amazon bestseller lists, Reddit/Twitter
    social signals, etc.
    """

    def __init__(self, state_db: Path | str = "books/trends_state.json"):
        self.state_db = Path(state_db)
        self.state_db.parent.mkdir(parents=True, exist_ok=True)
        self._load_state()

    def _load_state(self):
        """Load scan history and last-scanned niche."""
        if self.state_db.exists():
            with open(self.state_db) as f:
                state = json.load(f)
                self.last_scan: Optional[datetime] = (
                    datetime.fromisoformat(state.get("last_scan"))
                    if state.get("last_scan") else None
                )
                self.last_niche_index: int = state.get("last_niche_index", -1)
                self.scan_history: list[str] = state.get("scan_history", [])
        else:
            self.last_scan = None
            self.last_niche_index = -1
            self.scan_history = []

    def _save_state(self):
        """Persist scan history to disk."""
        state = {
            "last_scan": self.last_scan.isoformat() if self.last_scan else None,
            "last_niche_index": self.last_niche_index,
            "scan_history": self.scan_history[-100:],  # keep last 100 scans
        }
        with open(self.state_db, "w") as f:
            json.dump(state, f, indent=2)

    def scan(self, dry_run: bool = True) -> Optional[TrendOpportunity]:
        """Scan for the next niche opportunity.

        Returns a TrendOpportunity if a new niche is due for scanning, else None.
        Rounds through EVERGREEN_NICHES in order.

        Args:
            dry_run: If True, don't persist state changes.

        Returns:
            TrendOpportunity if a niche is due, else None.
        """
        niche_keys = list(EVERGREEN_NICHES.keys())
        next_index = (self.last_niche_index + 1) % len(niche_keys)
        niche_key = niche_keys[next_index]
        niche_spec = EVERGREEN_NICHES[niche_key]

        # Generate a TrendOpportunity
        scan_id = hashlib.md5(
            f"{niche_key}:{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:8]

        opportunity = TrendOpportunity(
            niche=niche_key,
            title=f"[Opportunity] {niche_spec['name']} Book",
            premise=niche_spec["pitch_template"].replace("{profession}", "tech").replace(
                "{system}", "Getting Things Done"
            ).replace(
                "{context}", "creative work"
            ).replace(
                "{AI tool}", "ChatGPT"
            ).replace(
                "{business_type}", "freelance"
            ).replace(
                "{work_aspect}", "hiring"
            ).replace(
                "{health_topic}", "sleep"
            ).replace(
                "{background}", "software engineers"
            ),
            keywords=niche_spec["keywords"],
            target_audience=niche_spec["audience"],
            estimated_audience_size=niche_spec["avg_audience_size"],
            scan_id=scan_id,
        )

        if not dry_run:
            self.last_niche_index = next_index
            self.last_scan = datetime.utcnow()
            self.scan_history.append(f"{niche_key}:{scan_id}")
            self._save_state()

        return opportunity

    def get_niche_for_date(self, date: datetime) -> str:
        """Deterministic niche selection by date.

        Given a date, return which niche should be scanned that day (for
        scheduled tasks that need reproducibility).
        """
        niche_keys = list(EVERGREEN_NICHES.keys())
        day_of_year = date.timetuple().tm_yday
        niche_index = day_of_year % len(niche_keys)
        return niche_keys[niche_index]
